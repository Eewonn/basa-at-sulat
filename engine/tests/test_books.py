import subprocess
import wave

import pytest
from fastapi.testclient import TestClient

from app.db import connect, init_db
from app.main import app

client = TestClient(app)
STORY = "Si Ben ay may pulang saranggola."


@pytest.fixture(autouse=True)
def env(tmp_path, monkeypatch):
    """A fresh database and a throwaway storage folder; the real model is never loaded."""
    monkeypatch.setenv("BASA_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BASA_STORAGE_DIR", str(tmp_path / "storage"))
    init_db(tmp_path / "test.db")

    def fake_word_timings(audio_path, text):
        return [
            {"i": i, "text": w, "start": round(i * 0.5, 2), "end": round(i * 0.5 + 0.4, 2)}
            for i, w in enumerate(text.split())
        ]

    monkeypatch.setattr("app.books.word_timings", fake_word_timings, raising=False)
    return tmp_path


def make_reading(tmp_path, ext="webm", seconds=3):
    path = tmp_path / f"reading.{ext}"
    codec = ["-c:a", "libopus"] if ext in ("webm", "ogg") else []
    subprocess.run(
        ["ffmpeg", "-nostdin", "-y", "-v", "error", "-f", "lavfi", "-i",
         f"sine=frequency=440:duration={seconds}", "-ar", "48000", *codec, str(path)],
        check=True,
    )
    return path


def post_book(path, **overrides):
    form = {"title": "Ang Saranggola", "language": "fil", "text": STORY, **overrides}
    with open(path, "rb") as f:
        return client.post("/books", data=form, files={"audio": (path.name, f)})


def test_posting_a_book_returns_its_id_and_word_timings(env):
    r = post_book(make_reading(env))
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"id", "words"}
    assert body["id"].startswith("b_")
    assert body["words"] == [
        {"i": i, "text": w, "start": round(i * 0.5, 2), "end": round(i * 0.5 + 0.4, 2)}
        for i, w in enumerate(STORY.split())
    ]


def test_getting_a_book_returns_what_was_saved(env):
    posted = post_book(make_reading(env)).json()
    r = client.get(f"/books/{posted['id']}")
    assert r.status_code == 200
    assert r.json() == {
        "id": posted["id"],
        "title": "Ang Saranggola",
        "language": "fil",
        "text": STORY,
        "words": posted["words"],
    }


def test_getting_an_unknown_book_is_404(env):
    assert client.get("/books/b_nope").status_code == 404


def test_getting_the_audio_returns_the_16k_mono_wav(env, tmp_path):
    posted = post_book(make_reading(env, "webm", seconds=2)).json()
    r = client.get(f"/books/{posted['id']}/audio")
    assert r.status_code == 200
    assert r.headers["content-type"] == "audio/wav"
    saved = tmp_path / "downloaded.wav"
    saved.write_bytes(r.content)
    with wave.open(str(saved), "rb") as f:
        assert (f.getframerate(), f.getnchannels()) == (16000, 1)
        assert f.getnframes() / f.getframerate() == pytest.approx(2, abs=0.2)


def test_getting_the_audio_of_an_unknown_book_is_404(env):
    assert client.get("/books/b_nope/audio").status_code == 404


def test_the_original_upload_is_not_kept(env, tmp_path):
    posted = post_book(make_reading(env, "ogg")).json()
    files = sorted(p.name for p in (tmp_path / "storage" / "books").iterdir())
    assert files == [f"{posted['id']}.wav"]


@pytest.mark.parametrize("audio_path", [None, "../outside.wav", "/etc/passwd"])
def test_a_book_without_usable_audio_is_404_not_a_crash_or_a_leak(env, tmp_path, audio_path):
    (tmp_path / "outside.wav").write_bytes(b"keep out")
    conn = connect()
    conn.execute(
        "INSERT INTO books (id, title, language, text, audio_path) VALUES ('b_odd', 'T', 'fil', 'Ben', ?)",
        (audio_path,),
    )
    conn.commit()
    conn.close()
    assert client.get("/books/b_odd/audio").status_code == 404


def nothing_kept(env):
    """No audio files and no book rows were left behind."""
    books_dir = env / "storage" / "books"
    assert not books_dir.exists() or list(books_dir.iterdir()) == []
    conn = connect()
    try:
        assert conn.execute("SELECT COUNT(*) FROM books").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM book_words").fetchone()[0] == 0
    finally:
        conn.close()


@pytest.mark.parametrize(
    "overrides",
    [{"title": "   "}, {"language": "Filipino"}, {"language": "FIL"}, {"language": "f"}, {"text": "  \n "}],
    ids=["blank-title", "language-name", "uppercase-language", "one-letter-language", "blank-text"],
)
def test_invalid_fields_are_422_and_nothing_is_kept(env, overrides):
    assert post_book(make_reading(env), **overrides).status_code == 422
    nothing_kept(env)


def test_a_story_over_3000_words_is_422(env):
    assert post_book(make_reading(env), text=" ".join(["Ben"] * 3001)).status_code == 422
    nothing_kept(env)


def test_a_missing_audio_file_is_422(env):
    r = client.post("/books", data={"title": "T", "language": "fil", "text": STORY})
    assert r.status_code == 422
    nothing_kept(env)


def test_audio_over_the_size_limit_is_413_and_nothing_is_kept(env, monkeypatch):
    monkeypatch.setattr("app.books.MAX_AUDIO_BYTES", 1000, raising=False)
    assert post_book(make_reading(env)).status_code == 413
    nothing_kept(env)


def test_unreadable_audio_is_400_and_nothing_is_kept(env):
    bad = env / "bad.webm"
    bad.write_bytes(b"not audio at all")
    assert post_book(bad).status_code == 400
    nothing_kept(env)


def test_audio_too_short_for_the_story_is_422_and_nothing_is_kept(env, monkeypatch):
    def too_short(audio_path, text):
        raise ValueError("the audio is too short to hold this text")

    monkeypatch.setattr("app.books.word_timings", too_short)
    r = post_book(make_reading(env))
    assert r.status_code == 422
    assert "too short" in r.json()["detail"]
    nothing_kept(env)


def test_without_the_scoring_model_installed_it_is_503_and_nothing_is_kept(env, monkeypatch):
    def missing(audio_path, text):
        raise ModuleNotFoundError("No module named 'torch'")

    monkeypatch.setattr("app.books.word_timings", missing)
    assert post_book(make_reading(env)).status_code == 503
    nothing_kept(env)


def test_a_failure_while_timing_is_500_and_nothing_is_kept(env, monkeypatch):
    def broken(audio_path, text):
        raise RuntimeError("boom")

    monkeypatch.setattr("app.books.word_timings", broken)
    assert post_book(make_reading(env)).status_code == 500
    nothing_kept(env)


def test_a_failure_while_saving_is_500_and_nothing_is_kept(env, monkeypatch):
    def misaligned(audio_path, text):
        # Two entries with the same index: the book_words primary key refuses it.
        return [{"i": 0, "text": "Si", "start": 0.0, "end": 0.1}, {"i": 0, "text": "Ben", "start": 0.1, "end": 0.2}]

    monkeypatch.setattr("app.books.word_timings", misaligned)
    assert post_book(make_reading(env)).status_code == 500
    nothing_kept(env)


def test_without_a_database_it_is_503_and_creates_nothing(env, monkeypatch):
    rec = make_reading(env)
    missing = env / "no-such.db"
    monkeypatch.setenv("BASA_DB_PATH", str(missing))
    r = post_book(rec)
    assert r.status_code == 503 and "database" in r.json()["detail"]
    assert not missing.exists()
    assert not (env / "storage" / "books").exists()
