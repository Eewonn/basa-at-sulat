"""The engine's command line: python -m app [--port N] [--data-dir D]. Real subprocesses, no model."""

import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

ENGINE_DIR = Path(__file__).resolve().parents[1]


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start(args, env_extra=None):
    env = {k: v for k, v in os.environ.items() if k not in ("PORT", "BASA_DB_PATH", "BASA_STORAGE_DIR")}
    env.update(env_extra or {})
    return subprocess.Popen(
        [sys.executable, "-m", "app", *args], cwd=ENGINE_DIR, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )


def get(port, path, timeout=20):
    """GET http://127.0.0.1:port/path, retrying until the engine is up. Returns (status, json)."""
    deadline = time.time() + timeout
    while True:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=5) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as err:
            return err.code, json.loads(err.read())
        except (urllib.error.URLError, ConnectionError):
            if time.time() > deadline:
                raise
            time.sleep(0.2)


@pytest.fixture
def engine():
    started = []

    def run(args, env_extra=None):
        proc = start(args, env_extra)
        started.append(proc)
        return proc

    yield run
    for proc in started:
        proc.terminate()
        proc.wait(timeout=10)


def test_port_flag_sets_the_port(engine):
    port = free_port()
    engine(["--port", str(port)])
    status, body = get(port, "/health")
    assert status == 200 and body["ok"] is True


def test_the_port_variable_still_works(engine):
    port = free_port()
    engine([], {"PORT": str(port)})
    assert get(port, "/health")[0] == 200


def test_the_port_flag_wins_over_the_port_variable(engine):
    flag_port, env_port = free_port(), free_port()
    engine(["--port", str(flag_port)], {"PORT": str(env_port)})
    assert get(flag_port, "/health")[0] == 200


def test_data_dir_holds_the_database_and_the_storage(engine, tmp_path):
    port = free_port()
    engine(["--port", str(port), "--data-dir", str(tmp_path / "data")])
    status, body = get(port, "/books/b_x")  # no database there yet, so the guard names the path it looked at
    assert status == 503
    assert str(tmp_path / "data" / "basa.db") in body["detail"]


@pytest.mark.parametrize("bad", ["0", "70000", "-1", "abc"])
def test_a_bad_port_exits_with_a_clear_error(bad):
    proc = start(["--port", bad])
    try:
        out, err = proc.communicate(timeout=20)
    except subprocess.TimeoutExpired:
        proc.kill()  # never leave a stray engine behind when the test fails
        proc.communicate()
        pytest.fail("the engine kept running with a bad port")
    assert proc.returncode != 0
    assert "port" in err.lower()
