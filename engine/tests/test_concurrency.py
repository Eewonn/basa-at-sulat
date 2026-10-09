"""Overlapping requests against a real server.

TestClient sends one request at a time, so it can't show a connection that is opened in one
worker thread and used in another. A real uvicorn can.
"""

import socket
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


@pytest.fixture
def server(tmp_path, monkeypatch):
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
