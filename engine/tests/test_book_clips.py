import subprocess
import wave

import pytest
from fastapi.testclient import TestClient

from app.db import connect, init_db
from app.main import app

client = TestClient(app)
WORDS = ["Si", "Ben", "ay", "saranggola"]
TEXT = " ".join(WORDS)
WORD_SEC = 0.5
TONES = [300, 600, 900, 1200]  # one tone per word, so a clip's pitch shows which word it holds


@pytest.fixture(autouse=True)
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("BASA_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BASA_STORAGE_DIR", str(tmp_path / "storage"))
    init_db(tmp_path / "test.db")
    set_timings(monkeypatch)
    return tmp_path


def set_timings(monkeypatch, timings=None):
    """Replace the model: word i spans [i*0.5, i*0.5+0.5] unless `timings` says otherwise."""
    spans = timings or [(i * WORD_SEC, (i + 1) * WORD_SEC) for i in range(len(WORDS))]

    def fake(audio_path, text):
        return [{"i": i, "text": w, "start": s, "end": e} for i, (w, (s, e)) in enumerate(zip(text.split(), spans))]

    monkeypatch.setattr("app.books.word_timings", fake)


def make_tone_reading(tmp_path):
    """A recording where word i is a pure tone of TONES[i] Hz lasting 0.5 s."""
    path = tmp_path / "reading.wav"
    inputs = []
    for hz in TONES:
        inputs += ["-f", "lavfi", "-i", f"sine=frequency={hz}:duration={WORD_SEC}"]
    n = len(TONES)
    subprocess.run(
        ["ffmpeg", "-nostdin", "-y", "-v", "error", *inputs, "-filter_complex",
         f"concat=n={n}:v=0:a=1", "-ar", "48000", str(path)],
        check=True,
    )
    return path


def post_book(tmp_path):
    path = make_tone_reading(tmp_path)
    with open(path, "rb") as f:
        r = client.post(
            "/books", data={"title": "T", "language": "fil", "text": TEXT}, files={"audio": ("r.wav", f)}
        )
    assert r.status_code == 200, r.text
    return r.json()["id"]


def read_wav(tmp_path, content, name="clip.wav"):
    path = tmp_path / name
    path.write_bytes(content)
    with wave.open(str(path), "rb") as f:
        return f.getframerate(), f.getnchannels(), f.getsampwidth(), f.readframes(f.getnframes())


def test_a_clip_is_a_valid_16k_mono_wav_as_long_as_the_word(env):
    book = post_book(env)
    r = client.get(f"/books/{book}/clips/1")
    assert r.status_code == 200
    assert r.headers["content-type"] == "audio/wav"
    rate, channels, width, frames = read_wav(env, r.content)
    assert (rate, channels) == (16000, 1)
    assert len(frames) / width / rate == pytest.approx(WORD_SEC, abs=0.01)


def pitch_hz(frames, rate):
    """Estimate the tone's frequency from how often the 16-bit signal crosses zero."""
    samples = [int.from_bytes(frames[k:k + 2], "little", signed=True) for k in range(0, len(frames) - 1, 2)]
    crossings = sum(1 for a, b in zip(samples, samples[1:]) if (a < 0) != (b < 0))
    return crossings / 2 / (len(samples) / rate)


@pytest.mark.parametrize("i", range(len(WORDS)))
def test_a_clip_holds_only_that_words_audio(env, i):
    book = post_book(env)
    rate, _, _, frames = read_wav(env, client.get(f"/books/{book}/clips/{i}").content)
    assert pitch_hz(frames, rate) == pytest.approx(TONES[i], rel=0.03)


def test_an_unknown_book_is_404(env):
    assert client.get("/books/b_nope/clips/0").status_code == 404


@pytest.mark.parametrize("i", [len(WORDS), 99, -1])
def test_a_word_that_does_not_exist_is_404(env, i):
    book = post_book(env)
    assert client.get(f"/books/{book}/clips/{i}").status_code == 404


def test_a_word_index_that_is_not_a_number_is_422(env):
    book = post_book(env)
    assert client.get(f"/books/{book}/clips/first").status_code == 422


def test_a_word_with_no_audio_is_422(env, monkeypatch):
    # Words with no letters (digits, dashes) come back from the aligner with zero length.
    set_timings(monkeypatch, [(0.0, 0.5), (0.5, 0.5), (0.5, 1.0), (1.0, 1.5)])
    book = post_book(env)
    r = client.get(f"/books/{book}/clips/1")
    assert r.status_code == 422
    assert "no audio" in r.json()["detail"]


def test_a_word_that_starts_after_the_recording_ends_is_422(env, monkeypatch):
    set_timings(monkeypatch, [(0.0, 0.5), (0.5, 1.0), (1.0, 1.5), (50.0, 51.0)])
    book = post_book(env)
    assert client.get(f"/books/{book}/clips/3").status_code == 422


def test_a_word_that_ends_after_the_recording_is_cut_at_the_end(env, monkeypatch):
    set_timings(monkeypatch, [(0.0, 0.5), (0.5, 1.0), (1.0, 1.5), (1.5, 9.0)])
    book = post_book(env)
    r = client.get(f"/books/{book}/clips/3")
    assert r.status_code == 200
    rate, _, width, frames = read_wav(env, r.content)
    assert len(frames) / width / rate == pytest.approx(0.5, abs=0.02)


@pytest.mark.parametrize("audio_path", [None, "../outside.wav", "/etc/passwd", "books/gone.wav"])
def test_a_book_without_usable_audio_is_404_not_a_crash_or_a_leak(env, audio_path):
    (env / "outside.wav").write_bytes(b"keep out")
    conn = connect()
    conn.execute("INSERT INTO books (id, title, language, text, audio_path) VALUES ('b_odd', 'T', 'fil', 'Ben', ?)", (audio_path,))
    conn.execute("INSERT INTO book_words (book_id, i, text, start_sec, end_sec) VALUES ('b_odd', 0, 'Ben', 0.0, 0.5)")
    conn.commit()
    conn.close()
    assert client.get("/books/b_odd/clips/0").status_code == 404


def test_a_file_that_is_not_a_wav_is_404_not_a_crash(env):
    (env / "storage" / "books").mkdir(parents=True)
    (env / "storage" / "books" / "b_bad.wav").write_bytes(b"not a wav")
    conn = connect()
    conn.execute("INSERT INTO books (id, title, language, text, audio_path) VALUES ('b_bad', 'T', 'fil', 'Ben', 'books/b_bad.wav')")
    conn.execute("INSERT INTO book_words (book_id, i, text, start_sec, end_sec) VALUES ('b_bad', 0, 'Ben', 0.0, 0.5)")
    conn.commit()
    conn.close()
    assert client.get("/books/b_bad/clips/0").status_code == 404


def test_without_a_database_it_is_503_and_creates_nothing(env, monkeypatch):
    missing = env / "no-such.db"
    monkeypatch.setenv("BASA_DB_PATH", str(missing))
    r = client.get("/books/b_1/clips/0")
    assert r.status_code == 503
    assert not missing.exists()
