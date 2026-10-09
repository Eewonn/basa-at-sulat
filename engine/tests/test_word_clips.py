"""GET /assessments/{id}/clips/{i}: a word as the child read it, for the review screen. Contract: docs/API.md."""

import io
import subprocess
import wave
from contextlib import closing

import pytest
from fastapi.testclient import TestClient

from app.assessments import save_assessment
from app.db import connect
from app.main import app
from app.seed import seed_db

client = TestClient(app)
RATE = 16000


@pytest.fixture(autouse=True)
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("BASA_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BASA_STORAGE_DIR", str(tmp_path / "storage"))
    seed_db(tmp_path / "test.db")
    (tmp_path / "storage" / "audio").mkdir(parents=True)
    # A 3 s, 16 kHz recording: the check's words sit at 1.0-1.5 s and 2.0-2.5 s.
    subprocess.run(
        ["ffmpeg", "-nostdin", "-y", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
         "-ar", str(RATE), "-ac", "1", str(tmp_path / "storage" / "audio" / "a_1.wav")],
        check=True,
    )
    with closing(connect(tmp_path / "test.db")) as conn:
        text = conn.execute("SELECT text FROM passages WHERE id = 'eng_g2_01'").fetchone()["text"]
        words = [{"i": i, "text": w, "label": "matched", "score": 0.9, "start": None, "end": None}
                 for i, w in enumerate(text.split())]
        words[0].update(start=1.0, end=1.5)
        words[1].update(start=2.0, end=2.5)
        save_assessment(conn, {"assessment_id": "a_1", "learner_id": "l_01", "passage_id": "eng_g2_01",
                               "duration_sec": 3.0, "words": words, "pauses": []}, audio_path="audio/a_1.wav")
    return tmp_path


def seconds(body: bytes) -> float:
    with wave.open(io.BytesIO(body)) as w:
        return w.getnframes() / w.getframerate()


def test_clip_is_the_word_with_a_little_padding():
    r = client.get("/assessments/a_1/clips/0")
    assert r.status_code == 200
    assert r.headers["content-type"] == "audio/wav"
    assert seconds(r.content) == pytest.approx(0.5 + 2 * 0.15, abs=0.01)


def test_padding_stops_at_the_end_of_the_recording(env):
    with closing(connect(env / "test.db")) as conn, conn:
        conn.execute("UPDATE word_results SET end_sec = 2.95 WHERE assessment_id = 'a_1' AND i = 1")
    assert seconds(client.get("/assessments/a_1/clips/1").content) == pytest.approx(3.0 - 1.85, abs=0.01)


def test_a_word_with_no_timing_has_nothing_to_play():
    assert client.get("/assessments/a_1/clips/2").status_code == 422


def test_unknown_assessment_or_word_is_404():
    assert client.get("/assessments/a_9/clips/0").status_code == 404
    assert client.get("/assessments/a_1/clips/999").status_code == 404


def test_after_confirm_the_recording_is_gone():
    assert client.post("/assessments/a_1/confirm").status_code == 200
    assert client.get("/assessments/a_1/clips/0").status_code == 410
