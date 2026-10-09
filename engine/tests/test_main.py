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


@pytest.fixture(autouse=True)
def fake_score(monkeypatch):
    """Never load the real model in tests: the scorer needs torch and ~1.2 GB of weights."""

    def fake(audio_path, passage_text):
        words = passage_text.split()
        return {
            "words": [
                {"i": i, "text": w, "label": "matched", "score": 0.9, "start": i * 0.1, "end": i * 0.1 + 0.1}
                for i, w in enumerate(words)
            ],
            "pauses": [],
        }

    monkeypatch.setattr("app.assess.score", fake)


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


def test_health_reports_a_loaded_aligner(monkeypatch):
    monkeypatch.setattr("ai.aligner.model_loaded", lambda: True)
    assert client.get("/health").json()["models"]["aligner"] == "loaded"


def test_warm_up_is_off_by_default(monkeypatch):
    called = []
    monkeypatch.setattr("ai.aligner.warm_up", lambda: called.append(1))
    with TestClient(app):
        pass
    assert called == []


def test_warm_up_runs_when_enabled(monkeypatch):
    called = []
    monkeypatch.setenv("BASA_WARM_UP", "1")
    monkeypatch.setattr("ai.aligner.warm_up", lambda: called.append(1))
    with TestClient(app):
        pass
    assert called == [1]


def test_a_failed_warm_up_does_not_stop_the_engine(monkeypatch):
    def boom():
        raise ModuleNotFoundError("torch")

    monkeypatch.setenv("BASA_WARM_UP", "1")
    monkeypatch.setattr("ai.aligner.warm_up", boom)
    with TestClient(app) as c:
        assert c.get("/health").status_code == 200


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
        words = [{"i": 0, "text": "Nagtanim", "label": "matched", "score": 0.9, "start": 0.0, "end": 0.5}]
        return {"words": words, "pauses": [{"before_word": 1, "seconds": 1.5}]}

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


def test_assess_without_the_model_installed_is_503_and_leaves_no_files(env, monkeypatch):
    def missing(audio_path, passage_text):
        raise ModuleNotFoundError("No module named 'torch'")

    monkeypatch.setattr("app.assess.score", missing)
    assert post(make_recording(env, "wav")).status_code == 503
    assert list((env / "storage" / "audio").iterdir()) == []


def test_assess_scoring_failure_is_500_and_leaves_no_files(env, monkeypatch):
    def broken(audio_path, passage_text):
        raise RuntimeError("unreadable")

    monkeypatch.setattr("app.assess.score", broken)
    assert post(make_recording(env, "wav")).status_code == 500
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


def test_assess_stores_the_result_and_returns_real_wcpm_and_level(env):
    body = post(make_recording(env, "wav")).json()
    assert isinstance(body["wcpm"], int)
    assert "level" in body  # null until P1-BE2-2 settles the DepEd level names
    # Stored: the teacher can override a word of this assessment.
    patched = client.patch(f"/assessments/{body['assessment_id']}/words/3", json={"label": "misread"})
    assert patched.status_code == 200
    assert patched.json()["words"][3]["label"] == "misread"


def test_assess_reports_the_scorers_align_and_score_timings(env, monkeypatch):
    def timed(audio_path, passage_text):
        return {
            "words": [{"i": 0, "text": "Nagtanim", "label": "matched", "score": 0.9, "start": 0.0, "end": 0.5}],
            "pauses": [],
            "timings": {"align_ms": 1234.5, "score_ms": 6.5},
        }

    monkeypatch.setattr("app.assess.score", timed)
    t = post(make_recording(env, "wav")).json()["timings"]
    assert (t["align_ms"], t["score_ms"]) == (1234.5, 6.5)
    assert t["convert_ms"] >= 0


def test_assess_that_cannot_be_saved_is_500_and_deletes_the_audio(env, monkeypatch):
    def off_script(audio_path, passage_text):
        # Word text that is not the passage's word at that index: the store refuses it.
        return {"words": [{"i": 0, "text": "Mali", "label": "matched", "score": 0.9, "start": 0.0, "end": 0.5}], "pauses": []}

    monkeypatch.setattr("app.assess.score", off_script)
    assert post(make_recording(env, "wav")).status_code == 500
    assert list((env / "storage" / "audio").iterdir()) == []


def assessed(env):
    """Run /assess and return (assessment_id, path of the stored WAV)."""
    body = post(make_recording(env, "wav")).json()
    return body["assessment_id"], env / "storage" / "audio" / f"{body['assessment_id']}.wav"


def test_confirm_marks_it_final_and_deletes_the_audio(env):
    aid, wav = assessed(env)
    assert wav.exists()
    r = client.post(f"/assessments/{aid}/confirm")
    assert r.status_code == 200
    assert r.json()["status"] == "confirmed"
    assert not wav.exists()


def test_confirm_with_keep_audio_keeps_the_file(env):
    aid, wav = assessed(env)
    r = client.post(f"/assessments/{aid}/confirm", json={"keep_audio": True})
    assert r.status_code == 200 and r.json()["status"] == "confirmed"
    assert wav.exists()


def test_confirm_with_keep_audio_false_deletes_the_file(env):
    aid, wav = assessed(env)
    assert client.post(f"/assessments/{aid}/confirm", json={"keep_audio": False}).status_code == 200
    assert not wav.exists()


def test_confirm_rejects_a_bad_keep_audio_value_and_keeps_the_file_and_draft(env):
    aid, wav = assessed(env)
    assert client.post(f"/assessments/{aid}/confirm", json={"keep_audio": "maybe"}).status_code == 422
    assert wav.exists()
    assert client.post(f"/assessments/{aid}/confirm").status_code == 200  # still a draft, so it can be confirmed


def test_confirm_unknown_assessment_is_404(env):
    assert client.post("/assessments/a_nope/confirm").status_code == 404


def test_confirming_twice_is_409_and_never_deletes_a_kept_recording(env):
    aid, wav = assessed(env)
    assert client.post(f"/assessments/{aid}/confirm", json={"keep_audio": True}).status_code == 200
    assert client.post(f"/assessments/{aid}/confirm").status_code == 409
    assert wav.exists()


def stored_audio_path(aid):
    conn = connect()
    try:
        return conn.execute("SELECT audio_path FROM assessments WHERE id = ?", (aid,)).fetchone()[0]
    finally:
        conn.close()


def test_confirm_succeeds_when_the_file_is_already_gone_and_clears_audio_path(env):
    aid, wav = assessed(env)
    wav.unlink()
    assert client.post(f"/assessments/{aid}/confirm").status_code == 200
    assert stored_audio_path(aid) is None


def test_confirm_clears_audio_path_when_it_deletes_and_keeps_it_when_kept(env):
    deleted, _ = assessed(env)
    kept, _ = assessed(env)
    client.post(f"/assessments/{deleted}/confirm")
    client.post(f"/assessments/{kept}/confirm", json={"keep_audio": True})
    assert stored_audio_path(deleted) is None
    assert stored_audio_path(kept) == f"audio/{kept}.wav"


def test_a_failed_delete_is_500_but_leaves_the_row_confirmed_with_audio_path_set(env, monkeypatch):
    aid, wav = assessed(env)

    def locked(path):
        raise PermissionError("locked")

    monkeypatch.setattr("app.retention.delete_audio", locked)
    r = client.post(f"/assessments/{aid}/confirm")
    assert r.status_code == 500
    assert "audio" in r.json()["detail"]
    assert wav.exists()
    assert stored_audio_path(aid) == f"audio/{aid}.wav"  # the owed deletion stays findable
    assert client.post(f"/assessments/{aid}/confirm").status_code == 409  # confirmed: a retry is 'already saved'


def test_assess_without_a_database_is_503_and_creates_nothing(env, monkeypatch):
    rec = make_recording(env, "wav")
    missing = env / "no-such.db"
    monkeypatch.setenv("BASA_DB_PATH", str(missing))
    r = post(rec)
    assert r.status_code == 503
    assert "database" in r.json()["detail"]
    assert not missing.exists()
    assert not (env / "storage" / "audio").exists() or list((env / "storage" / "audio").iterdir()) == []


def confirm_with_a_locked_file(env, monkeypatch):
    """Confirm an assessment whose audio cannot be deleted, leaving a deletion owed."""
    aid, wav = assessed(env)
    with monkeypatch.context() as m:
        def locked(path):
            raise PermissionError("locked")

        m.setattr("app.retention.delete_audio", locked)
        assert client.post(f"/assessments/{aid}/confirm").status_code == 500
    return aid, wav


def test_starting_the_engine_deletes_audio_that_is_still_owed(env, monkeypatch):
    aid, wav = confirm_with_a_locked_file(env, monkeypatch)
    assert wav.exists()
    with TestClient(app):
        pass
    assert not wav.exists()
    assert stored_audio_path(aid) is None


def test_starting_the_engine_never_touches_kept_recordings_or_drafts(env):
    kept, kept_wav = assessed(env)
    draft, draft_wav = assessed(env)
    client.post(f"/assessments/{kept}/confirm", json={"keep_audio": True})
    with TestClient(app):
        pass
    assert kept_wav.exists() and draft_wav.exists()
    assert stored_audio_path(kept) == f"audio/{kept}.wav"
    assert stored_audio_path(draft) == f"audio/{draft}.wav"


def test_a_deletion_that_still_fails_is_logged_and_the_engine_still_starts(env, monkeypatch, caplog):
    aid, wav = confirm_with_a_locked_file(env, monkeypatch)

    def locked(path):
        raise PermissionError("locked")

    monkeypatch.setattr("app.retention.delete_audio", locked)
    with caplog.at_level(logging.ERROR, logger="engine.retention"):
        with TestClient(app) as c:
            assert c.get("/health").status_code == 200
    assert wav.exists()
    assert stored_audio_path(aid) == f"audio/{aid}.wav"  # still owed, so the next start retries
    assert any(aid in r.getMessage() for r in caplog.records)


def test_the_engine_starts_when_there_is_no_database_yet(env, monkeypatch):
    monkeypatch.setenv("BASA_DB_PATH", str(env / "no-such.db"))
    with TestClient(app) as c:
        assert c.get("/health").status_code == 200
    assert not (env / "no-such.db").exists()


def test_one_stuck_file_does_not_stop_the_others_from_being_deleted(env, monkeypatch):
    stuck, stuck_wav = confirm_with_a_locked_file(env, monkeypatch)
    free, free_wav = confirm_with_a_locked_file(env, monkeypatch)
    real_delete = __import__("app.audio", fromlist=["delete_audio"]).delete_audio

    def only_stuck_is_locked(path):
        if stuck in path:
            raise PermissionError("locked")
        real_delete(path)

    monkeypatch.setattr("app.retention.delete_audio", only_stuck_is_locked)
    with TestClient(app):
        pass
    assert stuck_wav.exists() and not free_wav.exists()
    assert stored_audio_path(stuck) is not None and stored_audio_path(free) is None
