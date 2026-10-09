import subprocess
from pathlib import Path


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
