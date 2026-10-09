"""Mistake-detection metrics for the aligner test (P0-AI-1). Pure functions, no model and no audio.

Gold standard: eval/ground_truth.csv, one row per planted mistake (see eval/README.md).
  - swap / skip rows mark passage word `word_index` as a mistake. These are what F1 is computed on.
  - insert rows (an extra word said that isn't in the passage) have no passage word of their own, so
    they are counted and reported but kept out of precision/recall/F1.
  - none rows mark a clean reading: every word is correct, so any flag there is a false alarm.

`word_index` counts words in the passage text split on whitespace, from 0 (same as ai.score's `i`).
"""
import csv
from dataclasses import dataclass, field

SCORED_TYPES = {"swap", "skip"}
ALL_TYPES = SCORED_TYPES | {"insert", "none"}
FLAGGED_LABELS = {"misread", "skipped"}
GATE_F1 = 0.6


class GroundTruthError(ValueError):
    pass


@dataclass
class Recording:
    id: str
    language: str
    passage_id: str
    errors: dict = field(default_factory=dict)  # word index -> "swap" | "skip"
    inserts: list = field(default_factory=list)  # word index the extra word came before
    clean: bool = False


def load_ground_truth(path) -> dict:
    """Read ground_truth.csv into {recording_id: Recording}. Raises GroundTruthError with the row number."""
    recordings: dict = {}
    with open(path, newline="", encoding="utf-8") as f:
        for n, row in enumerate(csv.DictReader(f), start=2):  # row 1 is the header
            rec_id = (row.get("recording_id") or "").strip()
            if not rec_id:
                continue  # blank line
            kind = (row.get("error_type") or "").strip().lower()
            if kind not in ALL_TYPES:
                raise GroundTruthError(f"row {n} ({rec_id}): error_type {kind!r} must be one of {sorted(ALL_TYPES)}")
            language = (row.get("language") or "").strip()
            passage_id = (row.get("passage_id") or "").strip()
            if not language or not passage_id:
                raise GroundTruthError(f"row {n} ({rec_id}): language and passage_id are required")

            rec = recordings.setdefault(rec_id, Recording(rec_id, language, passage_id))
            if (rec.language, rec.passage_id) != (language, passage_id):
                raise GroundTruthError(f"row {n} ({rec_id}): language/passage_id differ from this recording's earlier rows")

            if kind == "none":
                rec.clean = True
                continue
            try:
                index = int(row["word_index"])
            except (TypeError, ValueError):
                raise GroundTruthError(f"row {n} ({rec_id}): word_index must be a whole number for {kind}") from None
            if index < 0:
                raise GroundTruthError(f"row {n} ({rec_id}): word_index can't be negative")
            if kind == "insert":
                rec.inserts.append(index)
            else:
                rec.errors[index] = kind

    for rec in recordings.values():
        if rec.clean and (rec.errors or rec.inserts):
            raise GroundTruthError(f"{rec.id}: has a 'none' row (clean) and also planted mistakes")
    return recordings


def _flag_by_label(word: dict) -> bool:
    return word["label"] in FLAGGED_LABELS


def confusion(recordings: dict, predictions: dict, flag=_flag_by_label) -> dict:
    """Word-level tp/fp/fn/tn over every recording that has a prediction.

    `predictions` is {recording_id: {"words": [{"i", "label", "score"}, ...], ...}}.
    A planted mistake whose word index is beyond the predicted words counts as a miss.
    """
    c = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
    for rec_id, pred in predictions.items():
        rec = recordings.get(rec_id)
        if rec is None:
            continue
        seen = set()
        for word in pred["words"]:
            seen.add(word["i"])
            gold, flagged = word["i"] in rec.errors, flag(word)
            c["tp" if gold and flagged else "fn" if gold else "fp" if flagged else "tn"] += 1
        c["fn"] += sum(1 for i in rec.errors if i not in seen)
    return c


def prf(c: dict) -> dict:
    """Precision, recall, F1 from a confusion dict. 0.0 where the ratio is undefined (nothing flagged / nothing to find)."""
    tp, fp, fn = c["tp"], c["fp"], c["fn"]
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1, **c}


def flag_below(threshold: float):
    """Flag a word when its score is at or under the threshold."""
    return lambda word: word["score"] <= threshold


def best_threshold(recordings: dict, predictions: dict):
    """The score cutoff with the best F1 on these predictions: (threshold, prf dict). None if there are no words.

    Candidates are the observed scores, so the optimum is exact. Ties go to the lowest threshold.
    """
    candidates = sorted({w["score"] for p in predictions.values() for w in p["words"]})
    best = None
    for t in candidates:
        result = prf(confusion(recordings, predictions, flag_below(t)))
        if best is None or result["f1"] > best[1]["f1"]:
            best = (t, result)
    return best


def held_out(recordings: dict, predictions: dict):
    """2-fold cross-validated F1: pick the threshold on half the recordings, score it on the other half.

    Returns a prf dict pooled over both folds, or None when there aren't at least 2 recordings with planted
    mistakes (a fold with none has nothing to tune a cutoff on).
    The best-threshold F1 is tuned on the data it's measured on, so it flatters us. This one doesn't.

    Recordings with mistakes and clean ones are dealt into folds separately, so each fold gets both kinds
    no matter how the recording ids happen to sort.
    """
    ids = sorted(r for r in predictions if r in recordings)
    with_mistakes = [r for r in ids if recordings[r].errors]
    clean = [r for r in ids if not recordings[r].errors]
    if len(with_mistakes) < 2:
        return None
    fold = {r: i % 2 for group in (with_mistakes, clean) for i, r in enumerate(group)}
    pooled = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
    for k in (0, 1):
        train = {r: predictions[r] for r in ids if fold[r] != k}
        test = {r: predictions[r] for r in ids if fold[r] == k}
        chosen = best_threshold(recordings, train)
        if chosen is None:
            return None
        part = confusion(recordings, test, flag_below(chosen[0]))
        pooled = {key: pooled[key] + part[key] for key in pooled}
    return prf(pooled)


def recall_by_type(recordings: dict, predictions: dict, flag=_flag_by_label) -> dict:
    """{"swap": (caught, total), "skip": (caught, total)} over recordings with predictions."""
    out = {kind: [0, 0] for kind in sorted(SCORED_TYPES)}
    for rec_id, pred in predictions.items():
        rec = recordings.get(rec_id)
        if rec is None:
            continue
        by_index = {w["i"]: w for w in pred["words"]}
        for index, kind in rec.errors.items():
            out[kind][1] += 1
            if index in by_index and flag(by_index[index]):
                out[kind][0] += 1
    return {kind: tuple(v) for kind, v in out.items()}


def verdict(f1: float | None) -> str:
    if f1 is None:
        return "not enough data"
    return "GO" if f1 >= GATE_F1 else "NO-GO"
