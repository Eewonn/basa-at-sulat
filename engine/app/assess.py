"""POST /assess: recording in, scored words out (P1-BE1-1)."""

import logging
import os
import sys
import time
import uuid
import wave
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.audio import AudioConversionError, convert_to_wav16k
from app.db import ENGINE_DIR, connect

# `ai` is a sibling package at the repo root, not under engine/.
REPO_ROOT = ENGINE_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
from ai import score  # noqa: E402

log = logging.getLogger("engine.assess")
router = APIRouter()


def storage_dir() -> Path:
    """Where audio lives at runtime. engine/storage/ is git-ignored."""
    override = os.environ.get("BASA_STORAGE_DIR")
    return Path(override) if override else ENGINE_DIR / "storage"


def _ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 1)


def _lookup(table: str, row_id: str, columns: str):
    conn = connect()
    try:
        return conn.execute(f"SELECT {columns} FROM {table} WHERE id = ?", (row_id,)).fetchone()
    finally:
        conn.close()


@router.post("/assess")
def assess(
    audio: UploadFile = File(...),
    passage_id: str = Form(...),
    learner_id: str = Form(...),
):
    started = time.perf_counter()

    passage = _lookup("passages", passage_id, "text")
    if passage is None:
        raise HTTPException(404, f"unknown passage_id: {passage_id}")
    if _lookup("learners", learner_id, "id") is None:
        raise HTTPException(404, f"unknown learner_id: {learner_id}")

    assessment_id = f"a_{uuid.uuid4().hex[:8]}"
    audio_dir = storage_dir() / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    upload_path = audio_dir / f"{assessment_id}.upload"
    wav_path = audio_dir / f"{assessment_id}.wav"

    try:
        upload_path.write_bytes(audio.file.read())

        t = time.perf_counter()
        try:
            convert_to_wav16k(upload_path, wav_path)
        except AudioConversionError as err:
            raise HTTPException(400, f"could not read the audio: {err}") from err
        convert_ms = _ms(t)
    except Exception:
        wav_path.unlink(missing_ok=True)
        raise
    finally:
        # The raw browser upload is never kept; only the converted WAV is.
        upload_path.unlink(missing_ok=True)

    with wave.open(str(wav_path), "rb") as f:
        duration_sec = round(f.getnframes() / f.getframerate(), 2)

    t = time.perf_counter()
    scored = score(str(wav_path), passage["text"])
    # ai.score does alignment and scoring in one call, so align_ms covers both.
    align_ms = _ms(t)

    total_ms = _ms(started)
    log.info(
        "assess %s passage=%s learner=%s audio=%.1fs convert=%.0fms score=%.0fms total=%.0fms",
        assessment_id, passage_id, learner_id, duration_sec, convert_ms, align_ms, total_ms,
    )

    return {
        "assessment_id": assessment_id,
        "learner_id": learner_id,
        "passage_id": passage_id,
        "duration_sec": duration_sec,
        "words": scored["words"],
        "pauses": scored["pauses"],
        # Computed from the final results by Backend 2 (P1-BE2-2).
        "wcpm": None,
        "level": None,
        "status": "draft",
        "timings": {"convert_ms": convert_ms, "align_ms": align_ms, "score_ms": 0.0},
    }
