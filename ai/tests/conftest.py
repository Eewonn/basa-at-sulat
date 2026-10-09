import struct
import wave

import pytest

from ai import aligner

requires_model = pytest.mark.skipif(
    not aligner.weights_cached(),
    reason="MMS weights not downloaded yet (run ai/smoke_test.py once to fetch them)",
)


@pytest.fixture
def make_wav(tmp_path):
    """make_wav(seconds) -> path of a silent 16 kHz mono wav."""

    def make(seconds: float) -> str:
        path = tmp_path / f"silence_{seconds}.wav"
        with wave.open(str(path), "wb") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(16000)
            f.writeframes(struct.pack("<h", 0) * int(16000 * seconds))
        return str(path)

    return make
