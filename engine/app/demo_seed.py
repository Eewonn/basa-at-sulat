"""Load demo Basa checks so the level, class and progress screens have data.

Run from engine/: python -m app.seed --demo

The checks start as real score() results from the AI engineer's test
recordings (data/demo_checks/, one JSON per recording). data/demo_seed.json
says which recording becomes which learner's check, and changes it for the demo:

- target_wcpm or duration_sec: the readers were adults (80-155 WCPM), so every
  check is slowed to a child's pace. Word times and pauses are scaled by the
  same factor so they still fit inside the recording.
- relabel: the recordings have at most 3 mistakes, which only reaches
  Transitioning and At Grade Level. The lower levels need accuracy under 80%,
  so some checks have words relabeled BY HAND. These are synthetic results.

Every demo check is saved as confirmed, with an id starting with "demo_" so the
accuracy report (P3-AI-1) can leave it out. A run replaces all demo_ checks and
never touches real ones. None of this is evidence of scoring accuracy.
"""

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.assessments import save_assessment, validate_result

DEMO_PREFIX = "demo_"
CONFIRM_DELAY = timedelta(minutes=5)  # a teacher reviews, then confirms

# A relabeled word keeps its timing but gets a score that fits its new label,
# so the score shown next to a flagged word doesn't contradict the flag.
RELABEL_SCORE_CAP = {"misread": 0.3, "skipped": 0.05}

ENTRY_FIELDS = ("id", "source", "learner_id", "checked_at")


class DemoSeedError(Exception):
    """Raised when the demo config or a source check is invalid."""


@dataclass
class DemoCheck:
    """One prepared demo check: an /assess-shaped result plus when it happened."""

    result: dict
    created_at: str
    confirmed_at: str
    expected_level: str | None


@dataclass
class DemoSeedResult:
    loaded: int = 0
    replaced: int = 0
    practice_removed: int = 0
    level_mismatches: list[str] | None = None


# --- Reading and preparing -------------------------------------------------

def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise DemoSeedError(f"{path}: file not found") from None
    except (OSError, json.JSONDecodeError) as err:
        raise DemoSeedError(f"{path}: could not read: {err}") from None


def _is_positive_number(value) -> bool:
    # bool is a subclass of int, so `true` would otherwise count as 1.
    return not isinstance(value, bool) and isinstance(value, (int, float)) and value > 0


def _parse_time(value, where: str) -> datetime:
    """Accept an ISO 8601 timestamp with a timezone; store it in UTC."""
    if not isinstance(value, str):
        raise DemoSeedError(f"{where}: 'checked_at' must be an ISO 8601 timestamp")
    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise DemoSeedError(f"{where}: 'checked_at' is not a valid timestamp: {value}") from None
    if moment.tzinfo is None:
        raise DemoSeedError(f"{where}: 'checked_at' needs a timezone, e.g. a trailing Z")
    return moment.astimezone(timezone.utc)


def _db_time(moment: datetime) -> str:
    """The schema's own timestamp format, so ordering by created_at stays correct."""
    return moment.strftime("%Y-%m-%dT%H:%M:%S.") + f"{moment.microsecond // 1000:03d}Z"


def _apply_relabel(words: list[dict], relabel, where: str) -> None:
    """Change the listed word indices to a new label, in place."""
    if not isinstance(relabel, dict):
        raise DemoSeedError(f"{where}: 'relabel' must map a label to a list of word indices")
    by_index = {word["i"]: word for word in words}
    seen = set()
    for label, indices in relabel.items():
        if label not in RELABEL_SCORE_CAP:
            raise DemoSeedError(f"{where}: can only relabel to misread or skipped, not '{label}'")
        if not isinstance(indices, list):
            raise DemoSeedError(f"{where}: relabel '{label}' must be a list of word indices")
        for i in indices:
            if isinstance(i, bool) or not isinstance(i, int) or i not in by_index:
                raise DemoSeedError(f"{where}: relabel index {i!r} is not a word in the check")
            if i in seen:
                raise DemoSeedError(f"{where}: word {i} is relabeled twice")
            seen.add(i)
            word = by_index[i]
            word["label"] = label
            word["score"] = min(word["score"], RELABEL_SCORE_CAP[label])


def _new_duration(entry: dict, words: list[dict], source_duration: float, where: str) -> float:
    """Pick the demo duration from target_wcpm or duration_sec (not both)."""
    has_target = "target_wcpm" in entry
    has_duration = "duration_sec" in entry
    if has_target and has_duration:
        raise DemoSeedError(f"{where}: give target_wcpm or duration_sec, not both")
    if has_duration:
        if not _is_positive_number(entry["duration_sec"]):
            raise DemoSeedError(f"{where}: 'duration_sec' must be a number greater than 0")
        return float(entry["duration_sec"])
    if has_target:
        if not _is_positive_number(entry["target_wcpm"]):
            raise DemoSeedError(f"{where}: 'target_wcpm' must be a number greater than 0")
        correct = sum(1 for word in words if word["label"] == "matched")
        if correct == 0:
            # 0 correct words is 0 WCPM at any speed, so no duration reaches a target.
            raise DemoSeedError(f"{where}: no words are matched, so use duration_sec instead")
        return round(correct * 60 / entry["target_wcpm"], 2)
    return source_duration


def _scale_times(result: dict, factor: float) -> None:
    """Stretch word times and pauses so they fit the new duration."""
    for word in result["words"]:
        for key in ("start", "end"):
            if word.get(key) is not None:
                word[key] = round(word[key] * factor, 2)
    for pause in result["pauses"]:
        pause["seconds"] = round(pause["seconds"] * factor, 2)


def prepare_demo_checks(config_path: Path, checks_dir: Path) -> list[DemoCheck]:
    """Read the config and its source checks, and build every demo result.

    Touches no database, so a mistake in the config can't leave the demo data
    half replaced.
    """
    config = _read_json(config_path)
    entries = config.get("checks") if isinstance(config, dict) else None
    if not isinstance(entries, list) or not entries:
        raise DemoSeedError(f"{config_path}: expected an object with a non-empty 'checks' list")

    prepared, seen_ids = [], set()
    for index, entry in enumerate(entries):
        where = f"{config_path}: check {index}"
        if not isinstance(entry, dict):
            raise DemoSeedError(f"{where}: must be an object")
        missing = [field for field in ENTRY_FIELDS if field not in entry]
        if missing:
            raise DemoSeedError(f"{where}: missing {', '.join(missing)}")

        check_id = entry["id"]
        if not isinstance(check_id, str) or not check_id.startswith(DEMO_PREFIX):
            raise DemoSeedError(f"{where}: 'id' must start with '{DEMO_PREFIX}'")
        if check_id in seen_ids:
            raise DemoSeedError(f"{config_path}: duplicate id '{check_id}'")
        seen_ids.add(check_id)
        where = f"{config_path}: '{check_id}'"

        source = _read_json(checks_dir / f"{entry['source']}.json")
        result = {
            "assessment_id": check_id,
            "learner_id": entry["learner_id"],
            "passage_id": source["passage_id"],
            "duration_sec": source["duration_sec"],
            "words": [dict(word) for word in source["words"]],
            "pauses": [dict(pause) for pause in source.get("pauses", [])],
        }
        _apply_relabel(result["words"], entry.get("relabel", {}), where)

        duration = _new_duration(entry, result["words"], source["duration_sec"], where)
        _scale_times(result, duration / source["duration_sec"])
        result["duration_sec"] = duration

        checked_at = _parse_time(entry["checked_at"], where)
        prepared.append(DemoCheck(
            result=result,
            created_at=_db_time(checked_at),
            confirmed_at=_db_time(checked_at + CONFIRM_DELAY),
            expected_level=entry.get("expected_level"),
        ))
    return prepared


# --- Writing ---------------------------------------------------------------

def load_demo_checks(conn: sqlite3.Connection, checks: list[DemoCheck]) -> DemoSeedResult:
    """Replace every demo_ check with the prepared ones, saved as confirmed.

    Every check is validated against the database before anything is deleted.
    save_assessment commits each check on its own, so if a later insert still
    fails, earlier ones stay; re-running replaces them all again.
    """
    for check in checks:
        try:
            validate_result(conn, check.result)
        except Exception as err:
            raise DemoSeedError(f"'{check.result['assessment_id']}': {err}") from None

    outcome = DemoSeedResult(level_mismatches=[])
    like = DEMO_PREFIX.replace("_", r"\_") + "%"  # _ is a LIKE wildcard
    with conn:
        # practice_attempts has no ON DELETE CASCADE, so practice done on a demo
        # check during a rehearsal has to go first.
        outcome.practice_removed = conn.execute(
            r"DELETE FROM practice_attempts WHERE assessment_id LIKE ? ESCAPE '\'", (like,)
        ).rowcount
        outcome.replaced = conn.execute(
            r"DELETE FROM assessments WHERE id LIKE ? ESCAPE '\'", (like,)
        ).rowcount

    for check in checks:
        saved = save_assessment(conn, check.result)
        with conn:
            conn.execute(
                "UPDATE assessments SET status = 'confirmed', keep_audio = 0, "
                "created_at = ?, confirmed_at = ? WHERE id = ?",
                (check.created_at, check.confirmed_at, saved["assessment_id"]),
            )
        outcome.loaded += 1
        if check.expected_level and saved["level"] != check.expected_level:
            outcome.level_mismatches.append(
                f"{saved['assessment_id']}: expected {check.expected_level}, got {saved['level']}"
            )
    return outcome
