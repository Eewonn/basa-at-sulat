"""Assessment endpoints (P1-BE2-1). Contract: docs/API.md."""

import sqlite3
import wave
from collections.abc import Iterator
from contextlib import closing
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Path
from fastapi.responses import Response
from pydantic import BaseModel, StrictBool

from app.assessments import (
    AssessmentConfirmedError,
    AssessmentNotFoundError,
    override_word,
)
from app.audio import cut_wav, stored_wav
from app.db import connect, get_db_path
from app.retention import AudioDeletionError, confirm_and_delete_audio
from app.stats import local_day

router = APIRouter(prefix="/assessments", tags=["assessments"])


class WordOverride(BaseModel):
    """PATCH body. Anything other than the three labels is rejected with 422."""

    label: Literal["matched", "misread", "skipped"]


def get_conn() -> Iterator[sqlite3.Connection]:
    """One connection per request, always closed (an open one locks the file on Windows)."""
    db_path = get_db_path()
    # connect() would silently create an empty file here, and every query
    # would then fail with "no such table".
    if not db_path.exists():
        raise HTTPException(
            status_code=503,
            detail=f"no database at {db_path}. Run `python -m app.seed` from engine/ first.",
        )
    with closing(connect(db_path)) as conn:
        yield conn


@router.get("/recent")
def recent(conn=Depends(get_conn)) -> list[dict]:
    """The 10 most recently confirmed checks, newest first, for the Basa tab."""
    rows = conn.execute(
        """
        SELECT a.id AS assessment_id, a.learner_id, l.display_name,
               a.confirmed_at, p.title AS passage_title, a.wcpm
        FROM assessments a
        JOIN learners l ON l.id = a.learner_id
        JOIN passages p ON p.id = a.passage_id
        WHERE a.status = 'confirmed'
        ORDER BY a.confirmed_at DESC, a.created_at DESC, a.id DESC
        LIMIT 10
        """
    ).fetchall()
    return [
        {
            "assessment_id": r["assessment_id"], "learner_id": r["learner_id"], "display_name": r["display_name"],
            "date": local_day(r["confirmed_at"]).isoformat(), "passage_title": r["passage_title"],
            "wcpm": None if r["wcpm"] is None else int(r["wcpm"]),
        }
        for r in rows
    ]


# Clips start a little early and end a little late, so the teacher hears the whole word.
CLIP_PAD_SEC = 0.15


@router.get("/{assessment_id}/clips/{i}")
def word_clip(assessment_id: str, i: int = Path(ge=0), conn=Depends(get_conn)) -> Response:
    """Word `i` as the child read it, cut from the check's recording, so the teacher can hear a flag before deciding.

    Only while the recording exists: it is deleted on confirm unless the teacher kept it.
    """
    row = conn.execute("SELECT audio_path FROM assessments WHERE id = ?", (assessment_id,)).fetchone()
    if row is None:
        raise HTTPException(404, f"no assessment '{assessment_id}'")
    word = conn.execute(
        "SELECT start_sec, end_sec FROM word_results WHERE assessment_id = ? AND i = ?", (assessment_id, i)
    ).fetchone()
    if word is None:
        raise HTTPException(404, f"assessment '{assessment_id}' has no word {i}")
    if word["start_sec"] is None or word["end_sec"] is None:
        raise HTTPException(422, f"word {i} has no timing, so there is nothing to play")
    path = stored_wav(row["audio_path"])
    if path is None:
        raise HTTPException(410, "the recording was deleted when the check was confirmed")
    try:
        clip = cut_wav(path, word["start_sec"] - CLIP_PAD_SEC, word["end_sec"] + CLIP_PAD_SEC)
    except (ValueError, wave.Error, EOFError):
        raise HTTPException(410, "the recording can't be read") from None
    return Response(clip, media_type="audio/wav")


@router.patch("/{assessment_id}/words/{i}")
def patch_word(
    body: WordOverride,
    assessment_id: str,
    i: int = Path(ge=0),
    conn=Depends(get_conn),
) -> dict:
    """Apply the teacher's override and return the recomputed assessment."""
    try:
        return override_word(conn, assessment_id, i, body.label)
    except AssessmentNotFoundError as err:
        raise HTTPException(status_code=404, detail=str(err)) from None
    except AssessmentConfirmedError as err:
        raise HTTPException(status_code=409, detail=str(err)) from None


class ConfirmBody(BaseModel):
    keep_audio: StrictBool = False


@router.post("/{assessment_id}/confirm")
def confirm(assessment_id: str, body: ConfirmBody | None = None, conn=Depends(get_conn)) -> dict:
    """Mark the assessment final and delete the child's audio unless keep_audio is true."""
    keep = body.keep_audio if body else False
    try:
        return confirm_and_delete_audio(conn, assessment_id, keep)
    except AssessmentNotFoundError as err:
        raise HTTPException(status_code=404, detail=str(err)) from None
    except AssessmentConfirmedError as err:
        raise HTTPException(status_code=409, detail=str(err)) from None
    except AudioDeletionError:
        raise HTTPException(
            status_code=500,
            detail="confirmed, but the audio could not be deleted yet",
        ) from None
