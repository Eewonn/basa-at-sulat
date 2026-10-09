"""GET /learners, GET /passages, GET /books and POST /practice/check. Contract: docs/API.md."""

import subprocess

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.seed import seed_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("BASA_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BASA_STORAGE_DIR", str(tmp_path / "storage"))
    seed_db(tmp_path / "test.db")
    return tmp_path


def tone(tmp_path, seconds=0.5):
    path = tmp_path / "say.wav"
    subprocess.run(
        ["ffmpeg", "-nostdin", "-y", "-v", "error", "-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}",
         str(path)],
        check=True,
    )
    return path


def test_learners_lists_the_seeded_class():
    r = client.get("/learners")
    assert r.status_code == 200
    rows = r.json()
    assert rows[0] == {"id": "l_01", "display_name": "A.R.", "grade": 1}
    assert [x["id"] for x in rows] == sorted(x["id"] for x in rows)


def test_passages_lists_the_seeded_texts():
    r = client.get("/passages")
    assert r.status_code == 200
    rows = r.json()
    assert {"fil_g2_01", "eng_g2_01"} <= {p["id"] for p in rows}
    assert set(rows[0]) == {"id", "title", "language", "grade", "text"}


def test_books_is_empty_then_lists_newest_first(monkeypatch, tmp_path):
    assert client.get("/books").json() == []
    monkeypatch.setattr(
        "app.books.word_timings",
        lambda path, text: [{"i": i, "text": w, "start": i * 0.1, "end": i * 0.1 + 0.1} for i, w in enumerate(text.split())],
    )
    for title in ["Una", "Ikalawa"]:
        with open(tone(tmp_path), "rb") as f:
            r = client.post("/books", data={"title": title, "language": "fil", "text": "Si Ben"}, files={"audio": ("r.wav", f)})
        assert r.status_code == 200, r.text
    rows = client.get("/books").json()
    assert [b["title"] for b in rows] == ["Ikalawa", "Una"]
    assert set(rows[0]) == {"id", "title", "language", "text"}


def test_practice_check_scores_the_word_and_keeps_no_audio(monkeypatch, tmp_path):
    seen = {}

    def fake(audio_path, word):
        seen["path"] = audio_path
        return {"result": "match", "score": 0.83}

    monkeypatch.setattr("app.routes.practice.check_word", fake)
    with open(tone(tmp_path), "rb") as f:
        r = client.post("/practice/check", data={"word": "palay", "learner_id": "l_01"}, files={"audio": ("w.webm", f)})
    assert r.status_code == 200, r.text
    assert r.json() == {"word": "palay", "result": "match", "score": 0.83}
    assert not (tmp_path / "storage").exists()
    from pathlib import Path
    assert not Path(seen["path"]).exists()


def test_practice_check_rejects_unreadable_audio(monkeypatch):
    monkeypatch.setattr("app.routes.practice.check_word", lambda *a: pytest.fail("should not score"))
    r = client.post("/practice/check", data={"word": "palay"}, files={"audio": ("w.webm", b"not audio")})
    assert r.status_code == 400


def test_practice_check_needs_a_word():
    r = client.post("/practice/check", data={"word": "  "}, files={"audio": ("w.webm", b"x")})
    assert r.status_code == 422


def test_practice_check_reports_a_missing_model(monkeypatch, tmp_path):
    def missing(*a):
        raise ImportError("no torch")

    monkeypatch.setattr("app.routes.practice.check_word", missing)
    with open(tone(tmp_path), "rb") as f:
        r = client.post("/practice/check", data={"word": "palay"}, files={"audio": ("w.wav", f)})
    assert r.status_code == 503
