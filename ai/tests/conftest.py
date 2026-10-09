import importlib.util
import struct
import wave

import pytest

from ai import aligner

requires_model = pytest.mark.skipif(
    importlib.util.find_spec("torch") is None or not aligner.weights_cached(),
    reason="needs torch and the MMS weights (pip install -r ai/requirements.txt, then run ai/smoke_test.py once)",
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
