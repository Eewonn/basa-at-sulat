"""Confirming a check and deleting the child's audio (P1-BE1-2)."""

import logging
import sqlite3
from contextlib import closing

from app.assessments import confirm_assessment, get_assessment
from app.audio import delete_audio
from app.db import connect, get_db_path

log = logging.getLogger("engine.retention")


class AudioDeletionError(Exception):
    """The assessment is confirmed, but its audio file could not be deleted."""


def confirm_and_delete_audio(conn: sqlite3.Connection, assessment_id: str, keep_audio: bool = False) -> dict:
    """Confirm the assessment, then delete its audio and clear audio_path (unless keep_audio)."""
    confirm_assessment(conn, assessment_id, keep_audio)
    row = conn.execute("SELECT audio_path FROM assessments WHERE id = ?", (assessment_id,)).fetchone()
    if row["audio_path"] and not keep_audio:
        try:
            delete_audio(row["audio_path"])
        except (OSError, ValueError) as err:
            # audio_path stays set: confirmed + not kept + audio_path set lists the deletions still owed.
            log.error("confirmed %s but could not delete %s: %s", assessment_id, row["audio_path"], err)
            raise AudioDeletionError(str(err)) from err
        with conn:
            conn.execute("UPDATE assessments SET audio_path = NULL WHERE id = ?", (assessment_id,))
    return get_assessment(conn, assessment_id)


def delete_owed_audio() -> int:
    """Retry deletions that failed at confirm. Returns how many files were deleted.

    Owed = confirmed, not kept, audio_path still set. Never raises: it runs at engine startup,
    and a missing database or a still-locked file must not stop the engine.
    """
    db_path = get_db_path()
    if not db_path.exists():
        return 0
    deleted = 0
    try:
        with closing(connect(db_path)) as conn:
            owed = conn.execute(
                "SELECT id, audio_path FROM assessments "
                "WHERE status = 'confirmed' AND keep_audio = 0 AND audio_path IS NOT NULL"
            ).fetchall()
            for row in owed:
                try:
                    delete_audio(row["audio_path"])
                except (OSError, ValueError) as err:
                    log.error("still could not delete %s for %s: %s", row["audio_path"], row["id"], err)
                    continue
                with conn:
                    conn.execute("UPDATE assessments SET audio_path = NULL WHERE id = ?", (row["id"],))
                deleted += 1
    except sqlite3.Error as err:
        log.error("could not check for owed audio deletions: %s", err)
    if deleted:
        log.info("deleted %d recording(s) that were owed from an earlier confirm", deleted)
    return deleted
