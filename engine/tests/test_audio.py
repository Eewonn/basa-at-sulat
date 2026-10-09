import json
import shutil
import subprocess

import pytest

from app.audio import AudioConversionError, convert_to_wav16k, delete_audio

needs_ffmpeg = pytest.mark.skipif(
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


@needs_ffmpeg
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


@needs_ffmpeg
def test_empty_file_raises(tmp_path):
    src = tmp_path / "empty.webm"
    src.write_bytes(b"")
    with pytest.raises(AudioConversionError):
        convert_to_wav16k(src, tmp_path / "out.wav")


@needs_ffmpeg
def test_corrupt_file_raises(tmp_path):
    src = tmp_path / "bad.ogg"
    src.write_bytes(b"not audio at all")
    with pytest.raises(AudioConversionError):
        convert_to_wav16k(src, tmp_path / "out.wav")


@pytest.fixture
def storage(tmp_path, monkeypatch):
    monkeypatch.setenv("BASA_STORAGE_DIR", str(tmp_path / "storage"))
    (tmp_path / "storage" / "audio").mkdir(parents=True)
    return tmp_path / "storage"


def test_delete_audio_removes_the_file(storage):
    f = storage / "audio" / "a_1.wav"
    f.write_bytes(b"RIFF")
    delete_audio("audio/a_1.wav")
    assert not f.exists()


def test_delete_audio_missing_file_is_success(storage):
    delete_audio("audio/a_gone.wav")


@pytest.mark.parametrize("bad", ["../outside.wav", "audio/../../outside.wav", "/etc/passwd", "", "."])
def test_delete_audio_refuses_paths_outside_storage(storage, bad):
    outside = storage.parent / "outside.wav"
    outside.write_bytes(b"keep me")
    with pytest.raises(ValueError):
        delete_audio(bad)
    assert outside.exists()


def test_delete_audio_refuses_a_symlink_that_escapes(storage):
    outside = storage.parent / "secret.wav"
    outside.write_bytes(b"keep me")
    (storage / "audio" / "link.wav").symlink_to(outside)
    with pytest.raises(ValueError):
        delete_audio("audio/link.wav")
    assert outside.exists()


def test_delete_audio_raises_on_real_io_errors(storage):
    (storage / "audio" / "a_dir.wav").mkdir()
    with pytest.raises(OSError):
        delete_audio("audio/a_dir.wav")
