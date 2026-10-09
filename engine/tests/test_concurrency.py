"""Overlapping requests against a real server.

TestClient sends one request at a time, so it can't show a connection that is opened in one
worker thread and used in another. A real uvicorn can.
"""

import socket
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest
import uvicorn

from app.assessments import save_assessment
from app.db import connect, init_db
from app.main import app

PASSAGE_TEXT = "Nagtanim si Lina ng palay sa bukid."


def fake_score(audio_path, passage_text):
    words = passage_text.split()
    return {
        "words": [
            {"i": i, "text": w, "label": "matched", "score": 0.9, "start": i * 0.1, "end": i * 0.1 + 0.1}
            for i, w in enumerate(words)
        ],
        "pauses": [],
    }


@pytest.fixture
def server(tmp_path, monkeypatch):
    monkeypatch.setattr("app.assess.score", fake_score)
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("BASA_DB_PATH", str(db_path))
    monkeypatch.setenv("BASA_STORAGE_DIR", str(tmp_path / "storage"))
    init_db(db_path)
    conn = connect(db_path)
    conn.execute("INSERT INTO learners (id, display_name, grade) VALUES ('l_07', 'L.M.', 2)")
    conn.execute(
        "INSERT INTO passages (id, title, language, grade, text) VALUES ('fil_g2_01', 'Palay', 'fil', 2, ?)",
        (PASSAGE_TEXT,),
    )
    conn.commit()
    words = [
        {"i": i, "text": w, "label": "matched", "score": 0.9, "start": i * 0.5, "end": i * 0.5 + 0.4}
        for i, w in enumerate(PASSAGE_TEXT.split())
    ]
    save_assessment(
        conn,
        {"assessment_id": "a_conc", "learner_id": "l_07", "passage_id": "fil_g2_01",
         "duration_sec": 10.0, "words": words, "pauses": []},
    )
    conn.close()

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    srv = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=srv.run, daemon=True)
    thread.start()
    deadline = time.time() + 10
    while not srv.started:
        assert time.time() < deadline, "server did not start"
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}"
    srv.should_exit = True
    thread.join(timeout=10)


def test_overlapping_requests_all_succeed(server):
    def patch(n):
        label = "misread" if n % 2 else "matched"
        return httpx.patch(f"{server}/assessments/a_conc/words/{n % 7}", json={"label": label}, timeout=30).status_code

    with ThreadPoolExecutor(max_workers=16) as pool:
        statuses = list(pool.map(patch, range(100)))

    assert statuses.count(200) == 100, {s: statuses.count(s) for s in set(statuses)}


def test_assess_confirm_and_patch_overlapping_all_succeed(server, tmp_path):
    rec = tmp_path / "rec.wav"
    subprocess.run(
        ["ffmpeg", "-nostdin", "-y", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=1", str(rec)],
        check=True,
    )
    form = {"passage_id": "fil_g2_01", "learner_id": "l_07"}

    def assess(_):
        with open(rec, "rb") as f:
            return httpx.post(f"{server}/assess", data=form, files={"audio": ("r.wav", f)}, timeout=60)

    first = [assess(n).json()["assessment_id"] for n in range(8)]  # drafts with audio, to confirm below
    audio_dir = tmp_path / "storage" / "audio"

    def work(n):
        if n % 3 == 0:
            return ("assess", assess(n).status_code)
        if n % 3 == 1:
            r = httpx.patch(f"{server}/assessments/a_conc/words/{n % 7}", json={"label": "misread"}, timeout=60)
            return ("patch", r.status_code)
        r = httpx.post(f"{server}/assessments/{first[n // 3 % 8]}/confirm", timeout=60)
        return ("confirm", r.status_code)

    with ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(work, range(60)))

    # A confirm may be asked twice for the same assessment, so 409 is expected there; nothing may be a 500.
    for kind, status in results:
        assert status in ({"assess": {200}, "patch": {200}, "confirm": {200, 409}}[kind]), (kind, status)
    # Confirm every draft that is left (409 means a worker already did), then no recording may remain.
    for aid in first:
        assert httpx.post(f"{server}/assessments/{aid}/confirm", timeout=60).status_code in (200, 409)
    assert not [f for f in audio_dir.iterdir() if f.stem in first]
