"""POST /assess: recording in, scored words out (P1-BE1-1)."""

import logging
import sys
import time
import uuid
import wave

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.assessments import InvalidAssessmentError, save_assessment
from app.audio import AudioConversionError, convert_to_wav16k, storage_dir
from app.db import ENGINE_DIR
from app.routes.assessments import get_conn

# `ai` is a sibling package at the repo root, not under engine/.
REPO_ROOT = ENGINE_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
from ai import score  # noqa: E402

log = logging.getLogger("engine.assess")
router = APIRouter()


def _ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 1)


def _lookup(conn, table: str, row_id: str, columns: str):
    return conn.execute(f"SELECT {columns} FROM {table} WHERE id = ?", (row_id,)).fetchone()


@router.post("/assess")
def assess(
    audio: UploadFile = File(...),
    passage_id: str = Form(...),
    learner_id: str = Form(...),
    conn=Depends(get_conn),
):
    started = time.perf_counter()

    passage = _lookup(conn, "passages", passage_id, "text")
    if passage is None:
        raise HTTPException(404, f"unknown passage_id: {passage_id}")
    if _lookup(conn, "learners", learner_id, "id") is None:
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
    try:
        scored = score(str(wav_path), passage["text"])
    except ImportError as err:
        wav_path.unlink(missing_ok=True)
        log.error("scoring model is not installed: %s", err)
        raise HTTPException(503, "the scoring model is not installed on this engine") from err
    except Exception as err:
        wav_path.unlink(missing_ok=True)
        log.exception("scoring failed for %s", assessment_id)
        raise HTTPException(500, "scoring failed") from err
    call_ms = _ms(t)
    # Older scorers return no split; then the whole call is reported as alignment.
    split = scored.get("timings", {"align_ms": call_ms, "score_ms": 0.0})

    total_ms = _ms(started)
    log.info(
        "assess %s passage=%s learner=%s audio=%.1fs convert=%.0fms score=%.0fms total=%.0fms",
        assessment_id, passage_id, learner_id, duration_sec, convert_ms, call_ms, total_ms,
    )

    result = {
        "assessment_id": assessment_id,
        "learner_id": learner_id,
        "passage_id": passage_id,
        "duration_sec": duration_sec,
        "words": scored["words"],
        "pauses": scored["pauses"],
    }
    try:
        saved = save_assessment(conn, result, audio_path=f"audio/{assessment_id}.wav")
    except InvalidAssessmentError as err:
        wav_path.unlink(missing_ok=True)
        log.error("could not save %s: %s", assessment_id, err)
        raise HTTPException(500, "could not save the result") from err

    return {
        **saved,
        "timings": {"convert_ms": convert_ms, **split},
    }
