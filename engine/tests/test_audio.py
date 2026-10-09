import json
import shutil
import subprocess

import pytest

from app.audio import AudioConversionError, convert_to_wav16k

pytestmark = pytest.mark.skipif(
    not (shutil.which("ffmpeg") and shutil.which("ffprobe")), reason="ffmpeg/ffprobe not installed"
)

# (extension, extra ffmpeg args): mimic browser recordings; wav is stereo 44.1 kHz.
INPUTS = {
    "webm": ["-ac", "1", "-ar", "48000", "-c:a", "libopus"],
    "ogg": ["-ac", "1", "-ar", "48000", "-c:a", "libopus"],
    "wav": ["-ac", "2", "-ar", "44100"],
}


def make_input(tmp_path, ext):
    src = tmp_path / f"in.{ext}"
    subprocess.run(
        ["ffmpeg", "-nostdin", "-y", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
         *INPUTS[ext], str(src)],
        check=True,
    )
    return src


@pytest.mark.parametrize("ext", INPUTS)
def test_converts_to_16k_mono_wav(tmp_path, ext):
    dst = convert_to_wav16k(make_input(tmp_path, ext), tmp_path / "out.wav")
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries",
         "stream=codec_name,sample_rate,channels:format=format_name", "-of", "json", str(dst)],
        capture_output=True, text=True, check=True,
    )
    info = json.loads(probe.stdout)
    stream = info["streams"][0]
    assert info["format"]["format_name"] == "wav"
    assert stream["sample_rate"] == "16000"
    assert stream["channels"] == 1


def test_empty_file_raises(tmp_path):
    src = tmp_path / "empty.webm"
    src.write_bytes(b"")
    with pytest.raises(AudioConversionError):
        convert_to_wav16k(src, tmp_path / "out.wav")


def test_corrupt_file_raises(tmp_path):
    src = tmp_path / "bad.ogg"
    src.write_bytes(b"not audio at all")
    with pytest.raises(AudioConversionError):
        convert_to_wav16k(src, tmp_path / "out.wav")
