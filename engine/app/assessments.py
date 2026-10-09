"""Store Basa checks and the teacher's overrides (P1-BE2-1).

Every function takes an open connection from app.db.connect() and returns the
assessment in the API's shape (docs/API.md): `label` is the stored
final_label, and start_sec/end_sec go back out as start/end.

wcpm and level are always computed here from the final labels (app.levels),
never taken from the caller, so a stored score can't disagree with its words.
"""

import sqlite3
from datetime import datetime, timezone

from app.levels import recompute

LABELS = ("matched", "misread", "skipped")
REQUIRED_FIELDS = ("assessment_id", "learner_id", "passage_id", "duration_sec", "words")
WORD_FIELDS = ("i", "text", "label", "score", "start", "end")


class AssessmentError(Exception):
    """Base class for assessment errors."""


class InvalidAssessmentError(AssessmentError):
    """The data doesn't fit the contract, the passage or the database."""


class AssessmentNotFoundError(AssessmentError):
    """No assessment, or no word at that index, with the given id."""


class AssessmentConfirmedError(AssessmentError):
    """The assessment is already confirmed, so its results are final."""


def _now() -> str:
    # Same format as the schema's created_at default, so text order is time order.
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _is_whole_number(value) -> bool:
    # bool is a subclass of int, so `true` would otherwise pass as index 1.
    return isinstance(value, int) and not isinstance(value, bool)


# --- Checking a result before it's stored ----------------------------------

def _check_words(words, passage_words: list[str]) -> None:
    """Each word must sit at its index in the passage, once, with a valid label.

    Word results are stored by index, so a word that doesn't match the passage
    at that index would quietly misalign every later step (practice sets,
    progress). A partial list is allowed: the scorer may not return every word.
    """
    if not isinstance(words, list) or not words:
        raise InvalidAssessmentError("'words' must be a non-empty list")

    seen = set()
    for position, word in enumerate(words):
        where = f"words[{position}]"
        if not isinstance(word, dict):
            raise InvalidAssessmentError(f"{where} is not an object")
        missing = [field for field in WORD_FIELDS if field not in word]
        if missing:
            raise InvalidAssessmentError(f"{where}: missing {', '.join(missing)}")

        i = word["i"]
        if not _is_whole_number(i) or i < 0:
            raise InvalidAssessmentError(f"{where}: 'i' must be a whole number from 0")
        if i in seen:
            raise InvalidAssessmentError(f"{where}: word index {i} appears twice")
        seen.add(i)

        if i >= len(passage_words):
            raise InvalidAssessmentError(
                f"{where}: index {i} is past the passage's last word ({len(passage_words) - 1})"
            )
        if word["text"] != passage_words[i]:
            raise InvalidAssessmentError(
                f"{where}: text '{word['text']}' doesn't match the passage's word "
                f"{i}, '{passage_words[i]}'"
            )
        if word["label"] not in LABELS:
            raise InvalidAssessmentError(
                f"{where}: 'label' must be one of {', '.join(LABELS)}"
            )


def _check_pauses(pauses, passage_word_count: int) -> None:
    if not isinstance(pauses, list):
        raise InvalidAssessmentError("'pauses' must be a list")
    for position, pause in enumerate(pauses):
        where = f"pauses[{position}]"
        if not isinstance(pause, dict) or "before_word" not in pause or "seconds" not in pause:
            raise InvalidAssessmentError(f"{where} needs 'before_word' and 'seconds'")
        before = pause["before_word"]
        if not _is_whole_number(before) or not 0 <= before < passage_word_count:
            raise InvalidAssessmentError(
                f"{where}: 'before_word' must be a word index in the passage"
            )


def _check_result(conn: sqlite3.Connection, result) -> None:
    """Reject anything that would store a broken or misaligned check."""
    if not isinstance(result, dict):
        raise InvalidAssessmentError("the result must be an object")
    missing = [field for field in REQUIRED_FIELDS if field not in result]
    if missing:
        raise InvalidAssessmentError(f"missing {', '.join(missing)}")

    if not conn.execute(
        "SELECT 1 FROM learners WHERE id = ?", (result["learner_id"],)
    ).fetchone():
        raise InvalidAssessmentError(f"unknown learner '{result['learner_id']}'")

    passage = conn.execute(
        "SELECT text FROM passages WHERE id = ?", (result["passage_id"],)
    ).fetchone()
    if not passage:
        raise InvalidAssessmentError(f"unknown passage '{result['passage_id']}'")

    duration = result["duration_sec"]
    if isinstance(duration, bool) or not isinstance(duration, (int, float)) or duration <= 0:
        raise InvalidAssessmentError("'duration_sec' must be a number greater than 0")

    # Split on whitespace, the same way the passage is shown word by word.
    passage_words = passage["text"].split()
    _check_words(result["words"], passage_words)
    _check_pauses(result.get("pauses", []), len(passage_words))


# --- Reading and writing ---------------------------------------------------

def get_assessment(conn: sqlite3.Connection, assessment_id: str) -> dict:
    """Return one assessment in the API's shape, or raise AssessmentNotFoundError."""
    row = conn.execute(
        "SELECT id, learner_id, passage_id, duration_sec, wcpm, level, status "
        "FROM assessments WHERE id = ?",
        (assessment_id,),
    ).fetchone()
    if not row:
        raise AssessmentNotFoundError(f"no assessment '{assessment_id}'")

    words = [
        {
            "i": word["i"],
            "text": word["text"],
            "label": word["final_label"],
            "score": word["score"],
            "start": word["start_sec"],
            "end": word["end_sec"],
        }
        for word in conn.execute(
            "SELECT i, text, final_label, score, start_sec, end_sec "
            "FROM word_results WHERE assessment_id = ? ORDER BY i",
            (assessment_id,),
        )
    ]
    pauses = [
        {"before_word": pause["before_word"], "seconds": pause["seconds"]}
        for pause in conn.execute(
            "SELECT before_word, seconds FROM pauses "
            "WHERE assessment_id = ? ORDER BY before_word",
            (assessment_id,),
        )
    ]
    # wcpm is stored as REAL; the API shows it as a whole number.
    wcpm = None if row["wcpm"] is None else int(row["wcpm"])
    return {
        "assessment_id": row["id"],
        "learner_id": row["learner_id"],
        "passage_id": row["passage_id"],
        "duration_sec": row["duration_sec"],
        "words": words,
        "pauses": pauses,
        "wcpm": wcpm,
        "level": row["level"],
        "status": row["status"],
    }


def save_assessment(conn: sqlite3.Connection, result: dict,
                    audio_path: str | None = None) -> dict:
    """Store a /assess result as a draft and return it in the API's shape.

    The assessment, its words and its pauses land in one transaction, so a
    failure partway leaves nothing behind. final_label starts equal to the AI's
    label. Any wcpm or level in `result` is ignored and recomputed.
    """
    _check_result(conn, result)

    words = result["words"]
    wcpm, level = recompute((word["label"] for word in words), result["duration_sec"])

    try:
        with conn:  # commits on success, rolls back if any insert fails
            conn.execute(
                "INSERT INTO assessments "
                "(id, learner_id, passage_id, duration_sec, wcpm, level, audio_path) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (result["assessment_id"], result["learner_id"], result["passage_id"],
                 result["duration_sec"], wcpm, level, audio_path),
            )
            conn.executemany(
                "INSERT INTO word_results "
                "(assessment_id, i, text, ai_label, final_label, score, start_sec, end_sec) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (result["assessment_id"], word["i"], word["text"], word["label"],
                     word["label"], word["score"], word["start"], word["end"])
                    for word in words
                ],
            )
            conn.executemany(
                "INSERT INTO pauses (assessment_id, before_word, seconds) VALUES (?, ?, ?)",
                [
                    (result["assessment_id"], pause["before_word"], pause["seconds"])
                    for pause in result.get("pauses", [])
                ],
            )
    except sqlite3.IntegrityError as err:
        # The schema's own checks: a duplicate id, a score outside 0-1, an end
        # before its start, a non-positive pause, and so on.
        raise InvalidAssessmentError(
            f"assessment '{result['assessment_id']}' could not be saved: {err}"
        ) from None

    return get_assessment(conn, result["assessment_id"])


def _require_draft(conn: sqlite3.Connection, assessment_id: str) -> None:
    """Raise if the assessment is missing or already confirmed."""
    row = conn.execute(
        "SELECT status FROM assessments WHERE id = ?", (assessment_id,)
    ).fetchone()
    if not row:
        raise AssessmentNotFoundError(f"no assessment '{assessment_id}'")
    if row["status"] == "confirmed":
        raise AssessmentConfirmedError(
            f"assessment '{assessment_id}' is confirmed, so its results can't change"
        )


def override_word(conn: sqlite3.Connection, assessment_id: str, i: int,
                  label: str) -> dict:
    """Apply the teacher's label to word i, recompute the score, and return it.

    Setting a word back to the AI's label clears overridden_at, so the count of
    words teachers corrected (P3-AI-1) only includes real corrections.
    """
    if label not in LABELS:
        raise InvalidAssessmentError(f"'label' must be one of {', '.join(LABELS)}")

    with conn:  # the word and the recomputed score change together or not at all
        _require_draft(conn, assessment_id)
        word = conn.execute(
            "SELECT ai_label FROM word_results WHERE assessment_id = ? AND i = ?",
            (assessment_id, i),
        ).fetchone()
        if not word:
            raise AssessmentNotFoundError(f"assessment '{assessment_id}' has no word {i}")

        overridden_at = None if label == word["ai_label"] else _now()
        conn.execute(
            "UPDATE word_results SET final_label = ?, overridden_at = ? "
            "WHERE assessment_id = ? AND i = ?",
            (label, overridden_at, assessment_id, i),
        )

        duration_sec = conn.execute(
            "SELECT duration_sec FROM assessments WHERE id = ?", (assessment_id,)
        ).fetchone()["duration_sec"]
        labels = [
            row["final_label"]
            for row in conn.execute(
                "SELECT final_label FROM word_results WHERE assessment_id = ?",
                (assessment_id,),
            )
        ]
        wcpm, level = recompute(labels, duration_sec)
        conn.execute(
            "UPDATE assessments SET wcpm = ?, level = ? WHERE id = ?",
            (wcpm, level, assessment_id),
        )

    return get_assessment(conn, assessment_id)


def confirm_assessment(conn: sqlite3.Connection, assessment_id: str,
                       keep_audio: bool = False) -> dict:
    """Mark a draft as final and record whether its audio should be kept.

    Data only. Deleting the audio file and clearing audio_path belong to
    backend-1's confirm handler (P1-BE1-2), which should call this first and
    delete the file only if it succeeds.
    """
    with conn:
        _require_draft(conn, assessment_id)
        conn.execute(
            "UPDATE assessments SET status = 'confirmed', confirmed_at = ?, keep_audio = ? "
            "WHERE id = ?",
            (_now(), int(keep_audio), assessment_id),
        )
    return get_assessment(conn, assessment_id)
