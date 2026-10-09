import logging
import subprocess
import wave

import pytest
from fastapi.testclient import TestClient

from app.db import connect, init_db
from app.main import app

client = TestClient(app)
PASSAGE_TEXT = "Nagtanim si Lina ng palay sa bukid."
FORM = {"passage_id": "fil_g2_01", "learner_id": "l_07"}


@pytest.fixture(autouse=True)
def env(tmp_path, monkeypatch):
    """A fresh database with one learner and one passage, and a throwaway audio dir."""
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("BASA_DB_PATH", str(db_path))
    monkeypatch.setenv("BASA_STORAGE_DIR", str(tmp_path / "storage"))
    init_db(db_path)
    conn = connect(db_path)
    conn.execute("INSERT INTO learners (id, display_name, grade) VALUES ('l_07', 'L.M.', 2)")
    conn.execute(
        "INSERT INTO passages (id, title, language, grade, text) VALUES (?, 'Palay', 'fil', 2, ?)",
        ("fil_g2_01", PASSAGE_TEXT),
    )
    conn.commit()
    conn.close()
    return tmp_path


def make_recording(tmp_path, ext, seconds=2):
    path = tmp_path / f"rec.{ext}"
    codec = ["-c:a", "libopus"] if ext in ("webm", "ogg") else []
    subprocess.run(
        ["ffmpeg", "-nostdin", "-y", "-v", "error", "-f", "lavfi", "-i",
         f"sine=frequency=440:duration={seconds}", "-ar", "48000", *codec, str(path)],
        check=True,
    )
    return path


def post(path, **form):
    with open(path, "rb") as f:
        return client.post("/assess", data=form or FORM, files={"audio": (path.name, f)})


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True, "models": {"aligner": "not_loaded", "ollama": "unknown"}}


@pytest.mark.parametrize("ext", ["webm", "ogg", "wav"])
def test_assess_returns_contract_shape(env, ext):
    r = post(make_recording(env, ext))
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {
        "assessment_id", "learner_id", "passage_id", "duration_sec",
        "words", "pauses", "wcpm", "level", "status", "timings",
    }
    assert body["assessment_id"].startswith("a_")
    assert (body["learner_id"], body["passage_id"], body["status"]) == ("l_07", "fil_g2_01", "draft")
    assert body["duration_sec"] == pytest.approx(2, abs=0.2)
    assert [w["text"] for w in body["words"]] == PASSAGE_TEXT.split()
    for w in body["words"]:
        assert set(w) == {"i", "text", "label", "score", "start", "end"}
        assert w["label"] in ("matched", "misread", "skipped")
    assert body["pauses"] == []
    assert set(body["timings"]) == {"convert_ms", "align_ms", "score_ms"}


def test_assess_scores_the_converted_wav(env, monkeypatch):
    seen = {}

    def fake_score(audio_path, passage_text):
        with wave.open(audio_path, "rb") as f:
            seen["rate"], seen["channels"] = f.getframerate(), f.getnchannels()
        seen["text"] = passage_text
        return {"words": [], "pauses": [{"before_word": 1, "seconds": 1.5}]}

    monkeypatch.setattr("app.assess.score", fake_score)
    r = post(make_recording(env, "webm"))
    assert r.status_code == 200
    assert seen == {"rate": 16000, "channels": 1, "text": PASSAGE_TEXT}
    assert r.json()["pauses"] == [{"before_word": 1, "seconds": 1.5}]


def test_assess_keeps_only_the_converted_wav(env):
    body = post(make_recording(env, "webm")).json()
    files = sorted(p.name for p in (env / "storage" / "audio").iterdir())
    assert files == [f"{body['assessment_id']}.wav"]


def test_assess_logs_processing_time(env, caplog):
    with caplog.at_level(logging.INFO, logger="engine.assess"):
        body = post(make_recording(env, "wav")).json()
    line = next(r.getMessage() for r in caplog.records if r.name == "engine.assess")
    assert body["assessment_id"] in line and "total=" in line and "ms" in line


def test_assess_unreadable_audio_is_400_and_leaves_no_files(env):
    bad = env / "bad.webm"
    bad.write_bytes(b"not audio")
    assert post(bad).status_code == 400
    assert list((env / "storage" / "audio").iterdir()) == []


def test_assess_unknown_passage_or_learner_is_404(env):
    rec = make_recording(env, "wav")
    assert post(rec, passage_id="nope", learner_id="l_07").status_code == 404
    assert post(rec, passage_id="fil_g2_01", learner_id="nope").status_code == 404


def test_assess_missing_fields_is_422(env):
    rec = make_recording(env, "wav")
    assert client.post("/assess", data=FORM).status_code == 422
    with open(rec, "rb") as f:
        r = client.post("/assess", data={"passage_id": "p"}, files={"audio": ("a.wav", f)})
    assert r.status_code == 422
