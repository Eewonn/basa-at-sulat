"""Metric maths for the aligner test, checked against hand-worked numbers (P0-AI-1)."""

import pytest

import metrics
from metrics import GroundTruthError

HEADER = "recording_id,language,passage_id,word_index,expected,actual,error_type,reader,notes\n"


def write_csv(tmp_path, *rows):
    path = tmp_path / "ground_truth.csv"
    path.write_text(HEADER + "".join(r + "\n" for r in rows), encoding="utf-8")
    return path


def word(i, label, score):
    return {"i": i, "text": f"w{i}", "label": label, "score": score}


def rec(rec_id="r1", errors=None, clean=False, language="fil"):
    return metrics.Recording(rec_id, language, "p1", errors=errors or {}, clean=clean)


# --- ground truth parsing ---------------------------------------------------

def test_load_groups_rows_by_recording(tmp_path):
    path = write_csv(
        tmp_path,
        "fil_001,fil,fil_g2_01,4,palay,pala,swap,KM,",
        "fil_001,fil,fil_g2_01,7,sa,,skip,KM,fan",
        "fil_001,fil,fil_g2_01,9,,ang,insert,KM,",
        "fil_002,fil,fil_g2_01,,,,none,KM,",
    )
    recs = metrics.load_ground_truth(path)
    assert recs["fil_001"].errors == {4: "swap", 7: "skip"}
    assert recs["fil_001"].inserts == [9]
    assert recs["fil_002"].clean and not recs["fil_002"].errors


def test_empty_ground_truth_is_empty(tmp_path):
    assert metrics.load_ground_truth(write_csv(tmp_path)) == {}


@pytest.mark.parametrize(
    "row",
    [
        "a,fil,p,1,x,y,typo,KM,",  # unknown error_type
        "a,fil,p,,x,y,swap,KM,",  # swap needs an index
        "a,fil,p,-1,x,y,swap,KM,",  # negative index
        "a,fil,p,one,x,y,skip,KM,",  # not a number
        "a,,p,1,x,y,swap,KM,",  # missing language
    ],
)
def test_bad_rows_are_rejected_with_the_row_number(tmp_path, row):
    with pytest.raises(GroundTruthError, match="row 2"):
        metrics.load_ground_truth(write_csv(tmp_path, row))


def test_clean_and_mistakes_in_one_recording_is_rejected(tmp_path):
    path = write_csv(tmp_path, "a,fil,p,,,,none,KM,", "a,fil,p,1,x,y,swap,KM,")
    with pytest.raises(GroundTruthError, match="clean"):
        metrics.load_ground_truth(path)


def test_conflicting_passage_for_one_recording_is_rejected(tmp_path):
    path = write_csv(tmp_path, "a,fil,p1,1,x,y,swap,KM,", "a,fil,p2,2,x,y,swap,KM,")
    with pytest.raises(GroundTruthError, match="differ"):
        metrics.load_ground_truth(path)


# --- confusion and prf ------------------------------------------------------

def test_worked_example_matches_the_documented_numbers():
    # 3 planted mistakes (words 1, 3, 5). We flag 1 and 3 (hits) and 0 and 4 (false alarms), and miss 5.
    recs = {"r1": rec(errors={1: "swap", 3: "skip", 5: "swap"})}
    preds = {"r1": {"words": [
        word(0, "misread", 0.2), word(1, "misread", 0.3), word(2, "matched", 0.9),
        word(3, "skipped", 0.1), word(4, "misread", 0.4), word(5, "matched", 0.8),
    ]}}
    c = metrics.confusion(recs, preds)
    assert c == {"tp": 2, "fp": 2, "fn": 1, "tn": 1}
    r = metrics.prf(c)
    assert r["precision"] == pytest.approx(0.5)
    assert r["recall"] == pytest.approx(2 / 3)
    assert r["f1"] == pytest.approx(4 / 7)


def test_flags_on_a_clean_reading_are_false_alarms():
    recs = {"r1": rec(clean=True)}
    preds = {"r1": {"words": [word(0, "matched", 0.9), word(1, "misread", 0.3)]}}
    assert metrics.confusion(recs, preds) == {"tp": 0, "fp": 1, "fn": 0, "tn": 1}


def test_a_mistake_beyond_the_scored_words_counts_as_missed():
    recs = {"r1": rec(errors={9: "skip"})}
    preds = {"r1": {"words": [word(0, "matched", 0.9)]}}
    assert metrics.confusion(recs, preds)["fn"] == 1


def test_recordings_without_predictions_are_ignored():
    recs = {"r1": rec(errors={0: "swap"}), "r2": rec("r2", errors={0: "swap"})}
    preds = {"r1": {"words": [word(0, "misread", 0.2)]}}
    assert metrics.confusion(recs, preds)["tp"] == 1 and metrics.confusion(recs, preds)["fn"] == 0


def test_prf_with_nothing_flagged_is_zero_not_a_crash():
    r = metrics.prf({"tp": 0, "fp": 0, "fn": 4, "tn": 10})
    assert (r["precision"], r["recall"], r["f1"]) == (0.0, 0.0, 0.0)


# --- thresholds and held-out ------------------------------------------------

def separable(n):
    """n recordings where mistakes score 0.2 and correct words score 0.9."""
    recs, preds = {}, {}
    for k in range(n):
        rid = f"r{k}"
        recs[rid] = rec(rid, errors={1: "swap"})
        preds[rid] = {"words": [word(0, "matched", 0.9), word(1, "matched", 0.2), word(2, "matched", 0.9)]}
    return recs, preds


def test_best_threshold_separates_clean_scores_and_finds_perfect_f1():
    recs, preds = separable(4)
    t, r = metrics.best_threshold(recs, preds)
    assert 0.2 <= t < 0.9
    assert r["f1"] == 1.0


def test_best_threshold_with_no_words_is_none():
    assert metrics.best_threshold({}, {}) is None


def test_held_out_is_perfect_on_separable_data():
    recs, preds = separable(4)
    assert metrics.held_out(recs, preds)["f1"] == 1.0


def test_held_out_is_honest_when_scores_do_not_separate():
    # Mistake and correct words score the same: no cutoff can beat chance, however it's tuned.
    recs, preds = {}, {}
    for k in range(4):
        rid = f"r{k}"
        recs[rid] = rec(rid, errors={1: "swap"})
        preds[rid] = {"words": [word(0, "matched", 0.5), word(1, "matched", 0.5), word(2, "matched", 0.5)]}
    assert metrics.held_out(recs, preds)["f1"] < metrics.GATE_F1


def test_held_out_needs_two_recordings_with_mistakes():
    recs, preds = separable(1)
    assert metrics.held_out(recs, preds) is None


def test_held_out_folds_are_balanced_even_when_ids_alternate_mistake_and_clean():
    # Regression: ids sorted a, b, c, d with mistakes on a and c put every mistake in one fold.
    recs, preds = {}, {}
    for rid, has_mistake in [("a", True), ("b", False), ("c", True), ("d", False)]:
        recs[rid] = rec(rid, errors={1: "swap"} if has_mistake else {}, clean=not has_mistake)
        preds[rid] = {"words": [word(0, "matched", 0.9), word(1, "matched", 0.2 if has_mistake else 0.9), word(2, "matched", 0.9)]}
    assert metrics.held_out(recs, preds)["f1"] == 1.0


# --- by type and verdict ----------------------------------------------------

def test_recall_by_type():
    recs = {"r1": rec(errors={0: "swap", 1: "skip", 2: "skip"})}
    preds = {"r1": {"words": [word(0, "misread", 0.2), word(1, "skipped", 0.1), word(2, "matched", 0.9)]}}
    assert metrics.recall_by_type(recs, preds) == {"skip": (1, 2), "swap": (1, 1)}


def test_verdict_gate_is_inclusive():
    assert metrics.verdict(0.6) == "GO"
    assert metrics.verdict(0.59) == "NO-GO"
    assert metrics.verdict(None) == "not enough data"
