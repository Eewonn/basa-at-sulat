import json

from fastapi.testclient import TestClient

from app.main import FIXTURE, app

client = TestClient(app)
FORM = {"passage_id": "fil_g2_01", "learner_id": "l_07"}


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True, "models": {"aligner": "not_loaded", "ollama": "unknown"}}


def test_assess_returns_fixture():
    r = client.post("/assess", data=FORM, files={"audio": ("a.wav", b"x", "audio/wav")})
    assert r.status_code == 200
    assert r.json() == json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_assess_missing_fields_is_422():
    assert client.post("/assess", data=FORM).status_code == 422
    files = {"audio": ("a.wav", b"x", "audio/wav")}
    assert client.post("/assess", data={"passage_id": "p"}, files=files).status_code == 422
