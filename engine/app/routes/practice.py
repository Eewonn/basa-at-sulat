"""POST /practice/check: Sanay "Say it" (did the child say this word?). Contract: docs/API.md."""

import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from ai import check_word
from ai.text import normalize_word
from app.audio import AudioConversionError, convert_to_wav16k
from app.practice import _latest_confirmed_check, build_practice_set
from app.routes.assessments import get_conn

log = logging.getLogger("engine.practice")
router = APIRouter(prefix="/practice", tags=["practice"])


@router.post("/check")
def check(
    audio: UploadFile = File(...),
    word: str = Form(...),
    learner_id: str | None = Form(None),
    conn=Depends(get_conn),
) -> dict:
    """Score one spoken word. The recording is only used for this answer and never kept.

    With `learner_id`, the attempt is saved (stars and reading days come from these rows),
    linked to the check the word came from.
    """
    if not word.strip():
        raise HTTPException(422, "word can't be blank")
    if learner_id is not None and conn.execute("SELECT 1 FROM learners WHERE id = ?", (learner_id,)).fetchone() is None:
        raise HTTPException(404, f"no learner '{learner_id}'")
    with tempfile.TemporaryDirectory() as tmp:
        upload_path, wav_path = Path(tmp) / "upload", Path(tmp) / "word.wav"
        upload_path.write_bytes(audio.file.read())
        try:
            convert_to_wav16k(upload_path, wav_path)
        except AudioConversionError as err:
            raise HTTPException(400, f"could not read the audio: {err}") from err
        try:
            result = check_word(str(wav_path), word)
        except ImportError as err:
            log.error("scoring model is not installed: %s", err)
            raise HTTPException(503, "the scoring model is not installed on this engine") from err
        except Exception as err:
            log.exception("check_word failed for %r", word)
            raise HTTPException(500, "checking the word failed") from err
    if learner_id is not None:
        _save_attempt(conn, learner_id, word, result)
    return {"word": word, **result}


def _save_attempt(conn, learner_id: str, word: str, result: dict) -> None:
    """Record the attempt against the learner's latest confirmed check, which their practice set comes from.

    A learner with no confirmed check has no practice set, so there is nothing to link to and nothing is saved.
    """
    check = _latest_confirmed_check(conn, learner_id)
    if check is None:
        return
    key = normalize_word(word) or word.casefold()
    item = next((x for x in build_practice_set(conn, learner_id) if (normalize_word(x["word"]) or x["word"].casefold()) == key), None)
    with conn:
        conn.execute(
            "INSERT INTO practice_attempts (learner_id, assessment_id, word, book_id, word_index, result, score) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (learner_id, check["id"], word, item and item["book_id"], item and item["word_index"],
             result["result"], result["score"]),
        )
