import logging
import os
import subprocess
from pathlib import Path

from app.db import ENGINE_DIR

log = logging.getLogger("engine.audio")


class AudioConversionError(Exception):
    pass


def convert_to_wav16k(src: Path, dst: Path) -> Path:
    """Convert any ffmpeg-readable recording (webm, ogg, wav) to 16 kHz mono WAV."""
    src, dst = Path(src), Path(dst)
    if not src.is_file() or src.stat().st_size == 0:
        raise AudioConversionError(f"missing or empty audio file: {src}")
    cmd = ["ffmpeg", "-nostdin", "-y", "-v", "error", "-i", str(src),
           "-vn", "-ar", "16000", "-ac", "1", "-f", "wav", str(dst)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError as e:
        raise AudioConversionError("ffmpeg is not installed") from e
    if result.returncode != 0:
        raise AudioConversionError(result.stderr.strip() or "ffmpeg failed")
    return dst


def storage_dir() -> Path:
    """Where audio lives at runtime. engine/storage/ is git-ignored."""
    override = os.environ.get("BASA_STORAGE_DIR")
    return Path(override) if override else ENGINE_DIR / "storage"


def delete_audio(audio_path: str) -> None:
    """Delete a recording. `audio_path` is relative to storage_dir(), e.g. "audio/a_1b2c3d4e.wav".

    A missing file counts as success. A path that resolves outside storage_dir() is refused.
    Real I/O errors (such as a locked file on Windows) are raised.
    """
    root = storage_dir().resolve()
    target = (root / audio_path).resolve()
    if target == root or not target.is_relative_to(root):
        raise ValueError(f"refusing to delete outside the storage folder: {audio_path}")
    try:
        target.unlink()
    except FileNotFoundError:
        log.info("audio already gone: %s", audio_path)
