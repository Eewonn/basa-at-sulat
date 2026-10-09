"""Progress: two of a learner's checks on the same passage, compared word by word (P2-BE2-2).

Contract: docs/API.md, `GET /learners/{id}/progress`. The pair is the newest
confirmed check that has an earlier confirmed check on the same passage, and
the newest of those earlier ones. Comparing labels word by word only means
something on the same text, so checks on other passages are never paired.

Words come from the passage, not from word_results, because a check may hold
only some of the words (the scorer can leave some out). A word a check has no
result for gets null for that side.
"""

import sqlite3

from app.practice import LearnerNotFoundError

def empty_progress() -> dict:
    """The response when there's no pair to compare. A new dict each time, so callers can't share its lists."""
    return {
        "checks": [],
        "words": [],
        "wcpm_before": None,
        "wcpm_after": None,
        "wcpm_change": None,
    }


def _confirmed_checks(conn: sqlite3.Connection, learner_id: str) -> list[sqlite3.Row]:
    """The learner's confirmed checks, newest first. Drafts may still change, so they're left out."""
    # Same order as the practice set's latest check (app/practice.py), so "latest" means the same on both screens.
    return conn.execute(
        "SELECT id, passage_id, confirmed_at, wcpm, level FROM assessments "
        "WHERE learner_id = ? AND status = 'confirmed' "
        "ORDER BY confirmed_at DESC, created_at DESC, id DESC",
        (learner_id,),
    ).fetchall()


def find_check_pair(conn: sqlite3.Connection, learner_id: str):
    """Return (before, after) rows for the latest same-passage pair, or None if there is none.

    The newest check may be on a passage the learner has read only once; then
    the pair falls back to an older passage, so `after` isn't always the
    learner's latest check.
    """
    newest_on_passage: dict[str, sqlite3.Row] = {}
    for check in _confirmed_checks(conn, learner_id):
        later = newest_on_passage.get(check["passage_id"])
        if later is not None:
            # Rows come newest first, so the first repeat of a passage closes the newest pair.
            return check, later
        newest_on_passage[check["passage_id"]] = check
    return None


def _labels(conn: sqlite3.Connection, assessment_id: str) -> dict[int, str]:
    rows = conn.execute(
        "SELECT i, final_label FROM word_results WHERE assessment_id = ?", (assessment_id,)
    )
    return {row["i"]: row["final_label"] for row in rows}


def _check_summary(check: sqlite3.Row) -> dict:
    return {
        "assessment_id": check["id"],
        "passage_id": check["passage_id"],
        "confirmed_at": check["confirmed_at"],
        "wcpm": check["wcpm"],
        "level": check["level"],
    }


def build_progress(conn: sqlite3.Connection, learner_id: str) -> dict:
    """Compare the learner's latest same-passage pair of confirmed checks.

    Labels are the teacher's final labels, so overrides count. Every passage
    word is listed once per position, in passage order, with its text as
    written (punctuation kept) so the app can show the passage as it reads.
    """
    if conn.execute("SELECT 1 FROM learners WHERE id = ?", (learner_id,)).fetchone() is None:
        raise LearnerNotFoundError(f"no learner '{learner_id}'")

    pair = find_check_pair(conn, learner_id)
    if pair is None:
        return empty_progress()
    before, after = pair

    passage = conn.execute(
        "SELECT text FROM passages WHERE id = ?", (before["passage_id"],)
    ).fetchone()
    before_labels = _labels(conn, before["id"])
    after_labels = _labels(conn, after["id"])
    words = [
        {"i": i, "text": token, "before": before_labels.get(i), "after": after_labels.get(i)}
        for i, token in enumerate(passage["text"].split())
    ]

    # wcpm is filled whenever a check is saved, but the column allows NULL; don't do math on it.
    change = None
    if before["wcpm"] is not None and after["wcpm"] is not None:
        change = after["wcpm"] - before["wcpm"]

    return {
        "checks": [_check_summary(before), _check_summary(after)],
        "words": words,
        "wcpm_before": before["wcpm"],
        "wcpm_after": after["wcpm"],
        "wcpm_change": change,
    }
