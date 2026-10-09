"""GET /learners, /learners/{id}/stats, /passages, /books, /assessments/recent and POST /practice/check. Contract: docs/API.md."""

import subprocess
from contextlib import closing
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.assessments import confirm_assessment, save_assessment
from app.db import connect
from app.main import app
from app.seed import seed_db
from app.stats import streak

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


def save_check(tmp_path, assessment_id, learner_id, missed=(), confirm=True, confirmed_at=None):
    """A check on eng_g2_01 where every word is matched except the indices in `missed`."""
    with closing(connect(tmp_path / "test.db")) as conn:
        text = conn.execute("SELECT text FROM passages WHERE id = 'eng_g2_01'").fetchone()["text"]
        save_assessment(conn, {
            "assessment_id": assessment_id, "learner_id": learner_id, "passage_id": "eng_g2_01",
            "duration_sec": 30.0, "pauses": [],
            "words": [{"i": i, "text": w, "label": "misread" if i in missed else "matched", "score": 0.9,
                       "start": i * 0.5, "end": i * 0.5 + 0.4} for i, w in enumerate(text.split())],
        })
        if confirm:
            confirm_assessment(conn, assessment_id)
        if confirmed_at:
            with conn:
                conn.execute("UPDATE assessments SET confirmed_at = ? WHERE id = ?", (confirmed_at, assessment_id))


def test_learners_lists_the_seeded_class():
    r = client.get("/learners")
    assert r.status_code == 200
    rows = r.json()
    assert rows[0] == {"id": "l_01", "display_name": "A.R.", "grade": 1, "stars": 0, "streak_days": 0}
    assert [x["id"] for x in rows] == sorted(x["id"] for x in rows)


def test_learners_summarise_the_latest_confirmed_check(env):
    save_check(env, "a_old", "l_01", missed={0, 1}, confirmed_at="2026-10-01T08:00:00.000Z")
    save_check(env, "a_new", "l_01", confirmed_at="2026-10-05T08:00:00.000Z")
    save_check(env, "a_02", "l_02", missed={2})
    save_check(env, "a_draft", "l_03", missed={0}, confirm=False)
    rows = {x["id"]: x for x in client.get("/learners").json()}
    assert rows["l_01"]["last_check"] == "2026-10-05"
    assert rows["l_01"]["needs_practice"] is False
    assert isinstance(rows["l_01"]["latest_wcpm"], int)
    assert rows["l_01"]["level"] is not None
    assert rows["l_02"]["needs_practice"] is True
    # Drafts don't count, and a learner with no confirmed check has no summary fields.
    assert rows["l_03"] == {"id": "l_03", "display_name": "C.M.", "grade": 1, "stars": 0, "streak_days": 0}


def test_recent_lists_confirmed_checks_newest_first(env):
    assert client.get("/assessments/recent").json() == []
    save_check(env, "a_1", "l_01", confirmed_at="2026-10-01T08:00:00.000Z")
    save_check(env, "a_2", "l_02", confirmed_at="2026-10-03T08:00:00.000Z")
    save_check(env, "a_3", "l_03", confirm=False)
    rows = client.get("/assessments/recent").json()
    assert [r["assessment_id"] for r in rows] == ["a_2", "a_1"]
    assert rows[0]["display_name"] == "B.T." and rows[0]["date"] == "2026-10-03"
    assert set(rows[0]) == {"assessment_id", "learner_id", "display_name", "date", "passage_title", "wcpm"}


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


def say(tmp_path, monkeypatch, word, learner_id, result="match"):
    monkeypatch.setattr("app.routes.practice.check_word", lambda *a: {"result": result, "score": 0.9 if result == "match" else 0.2})
    with open(tone(tmp_path), "rb") as f:
        return client.post("/practice/check", data={"word": word, "learner_id": learner_id}, files={"audio": ("w.webm", f)})


def attempts(tmp_path):
    with closing(connect(tmp_path / "test.db")) as conn:
        return [dict(r) for r in conn.execute("SELECT learner_id, assessment_id, word, result FROM practice_attempts ORDER BY id")]


def test_practice_check_saves_the_attempt_against_the_latest_check(env, monkeypatch):
    save_check(env, "a_1", "l_01", missed={0})
    assert say(env, monkeypatch, "Ben", "l_01").status_code == 200
    assert say(env, monkeypatch, "Ben", "l_01", result="no_match").status_code == 200
    assert attempts(env) == [
        {"learner_id": "l_01", "assessment_id": "a_1", "word": "Ben", "result": "match"},
        {"learner_id": "l_01", "assessment_id": "a_1", "word": "Ben", "result": "no_match"},
    ]


def test_practice_check_saves_nothing_without_a_confirmed_check_or_a_learner(env, monkeypatch):
    assert say(env, monkeypatch, "Ben", "l_02").status_code == 200
    monkeypatch.setattr("app.routes.practice.check_word", lambda *a: {"result": "match", "score": 0.9})
    with open(tone(env), "rb") as f:
        assert client.post("/practice/check", data={"word": "Ben"}, files={"audio": ("w.webm", f)}).status_code == 200
    assert attempts(env) == []


def test_practice_check_rejects_an_unknown_learner(env, monkeypatch):
    assert say(env, monkeypatch, "Ben", "l_99").status_code == 404


def test_streak_counts_back_from_today_or_yesterday():
    today = date(2026, 10, 10)
    d = lambda n: date(2026, 10, 10 - n)  # noqa: E731
    assert streak({d(0), d(1), d(2), d(4)}, today) == 3
    assert streak({d(1), d(2)}, today) == 2  # not read yet today: the streak still stands
    assert streak({d(2), d(3)}, today) == 0
    assert streak(set(), today) == 0


def test_stats_are_counted_from_saved_rows(env, monkeypatch):
    save_check(env, "a_1", "l_01", missed={0, 1}, confirmed_at="2026-09-01T04:00:00.000Z")
    save_check(env, "a_2", "l_01", missed={1}, confirmed_at="2026-10-05T04:00:00.000Z")
    save_check(env, "a_draft", "l_01", confirm=False)
    say(env, monkeypatch, "has", "l_01")
    say(env, monkeypatch, "has", "l_01", result="no_match")
    r = client.get("/learners/l_01/stats")
    assert r.status_code == 200
    s = r.json()
    assert s["stars"] == 1
    assert [h["date"] for h in s["wcpm_history"]] == ["2026-09-01", "2026-10-05"]  # drafts left out
    assert s["minutes_read"] == 1  # two 30 s checks
    assert s["practicing"] == ["has"]
    assert {"2026-09-01", "2026-10-05", date.today().isoformat()} <= set(s["days_read"])
    assert s["streak_days"] == 1  # the practice today
    assert client.get("/learners").json()[0]["stars"] == 1


def test_stats_for_a_learner_with_nothing_yet_are_empty(env):
    assert client.get("/learners/l_05/stats").json() == {
        "stars": 0, "streak_days": 0, "minutes_read": 0, "wcpm_history": [], "practicing": [], "days_read": [],
    }


def test_stats_404_for_an_unknown_learner():
    assert client.get("/learners/l_99/stats").status_code == 404
