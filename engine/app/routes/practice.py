"""POST /practice/check: Sanay "Say it" (did the child say this word?). Contract: docs/API.md."""

import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from ai import check_word
from app.audio import AudioConversionError, convert_to_wav16k

log = logging.getLogger("engine.practice")
router = APIRouter(prefix="/practice", tags=["practice"])


@router.post("/check")
def check(audio: UploadFile = File(...), word: str = Form(...)) -> dict:
    """Score one spoken word. The recording is only used for this answer and never kept."""
    if not word.strip():
        raise HTTPException(422, "word can't be blank")
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
    return {"word": word, **result}
