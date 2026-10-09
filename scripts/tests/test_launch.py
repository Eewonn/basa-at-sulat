"""launch.py brings the whole app up and tears it down. Real subprocesses; a stub stands in for Electron."""

import json
import os
import shlex
import signal
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1]
LAUNCH = SCRIPTS / "launch.py"

# The stub app: asks the engine for /health on the port it was given, records what it saw, then exits.
STUB_APP = """
import json, os, sys, urllib.request
out, code = sys.argv[1], int(sys.argv[2])
port = os.environ["BASA_ENGINE_PORT"]
with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=10) as r:
    health = json.loads(r.read())
open(out, "w").write(json.dumps({"port": port, "health": health}))
sys.exit(code)
"""
SLOW_APP = "import time; time.sleep(60)"


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def accepts_connections(port):
    with socket.socket() as s:
        s.settimeout(1)
        return s.connect_ex(("127.0.0.1", port)) == 0


@pytest.fixture
def setup(tmp_path):
    stub = tmp_path / "stub_app.py"
    stub.write_text(STUB_APP)
    slow = tmp_path / "slow_app.py"
    slow.write_text(SLOW_APP)
    seen = tmp_path / "seen.json"
    return {"tmp": tmp_path, "stub": stub, "slow": slow, "seen": seen, "data": tmp_path / "data"}


def env_for(setup, app_cmd=None, **extra):
    cmd = app_cmd or [sys.executable, str(setup["stub"]), str(setup["seen"]), "0"]
    env = {k: v for k, v in os.environ.items() if k not in ("PORT", "BASA_DB_PATH", "BASA_STORAGE_DIR")}
    env.update(
        BASA_DATA_DIR=str(setup["data"]),
        BASA_APP_CMD=shlex.join(cmd),
        BASA_WARM_UP="0",
        BASA_OLLAMA_WAIT_SEC="0.3",
        BASA_OLLAMA_URL=f"http://127.0.0.1:{free_port()}",  # nothing listens there
        PATH=str(setup["tmp"] / "no-binaries"),  # so no real `ollama` is ever found
    )
    env.update(extra)
    return env


def launch(setup, **kwargs):
    return subprocess.run(
        [sys.executable, str(LAUNCH)], capture_output=True, text=True, timeout=90, env=env_for(setup, **kwargs)
    )


def test_the_app_gets_the_port_of_a_running_engine(setup):
    result = launch(setup)
    assert result.returncode == 0, result.stderr
    seen = json.loads(setup["seen"].read_text())
    assert int(seen["port"]) > 0 and seen["health"]["ok"] is True


def test_a_fresh_data_folder_gets_a_seeded_database(setup):
    assert launch(setup).returncode == 0
    conn = sqlite3.connect(setup["data"] / "basa.db")
    try:
        assert conn.execute("SELECT COUNT(*) FROM learners").fetchone()[0] > 0
        assert conn.execute("SELECT COUNT(*) FROM passages").fetchone()[0] > 0
    finally:
        conn.close()


def test_an_existing_database_is_left_alone(setup):
    setup["data"].mkdir()
    conn = sqlite3.connect(setup["data"] / "basa.db")
    conn.execute("CREATE TABLE marker (x)")
    conn.execute("INSERT INTO marker VALUES ('keep me')")
    conn.commit()
    conn.close()
    assert launch(setup).returncode == 0
    conn = sqlite3.connect(setup["data"] / "basa.db")
    try:
        assert conn.execute("SELECT x FROM marker").fetchone()[0] == "keep me"
    finally:
        conn.close()


def test_the_engine_is_stopped_when_the_app_closes(setup):
    assert launch(setup).returncode == 0
    port = int(json.loads(setup["seen"].read_text())["port"])
    assert not accepts_connections(port)


def test_the_apps_exit_code_is_passed_on(setup):
    cmd = [sys.executable, str(setup["stub"]), str(setup["seen"]), "7"]
    assert launch(setup, app_cmd=cmd).returncode == 7


@pytest.mark.skipif(os.name == "nt", reason="needs POSIX signals")
def test_stopping_the_launcher_stops_the_engine(setup):
    proc = subprocess.Popen(
        [sys.executable, str(LAUNCH)], env=env_for(setup, app_cmd=[sys.executable, str(setup["slow"])]),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    port = None
    deadline = time.time() + 60
    while port is None and time.time() < deadline:
        line = proc.stdout.readline()
        if line.startswith("engine on port "):
            port = int(line.split()[-1])
    assert port is not None, "the launcher never reported the engine port"
    assert accepts_connections(port)
    proc.send_signal(signal.SIGTERM)
    proc.wait(timeout=30)
    assert not accepts_connections(port)


def test_if_the_engine_cannot_be_set_up_the_app_is_not_started(setup):
    setup["data"].write_text("a file where the data folder should be")
    result = launch(setup)
    assert result.returncode != 0
    assert not setup["seen"].exists()
    assert "data" in (result.stdout + result.stderr).lower()


def test_ollama_is_started_when_installed_and_stopped_afterwards(setup):
    bin_dir = setup["tmp"] / "no-binaries"
    bin_dir.mkdir()
    marker = setup["tmp"] / "ollama-started"
    fake = bin_dir / "ollama"
    fake.write_text(f"#!/bin/sh\n[ \"$1\" = serve ] && echo $$ > '{marker}' && exec sleep 60\n")
    fake.chmod(0o755)
    assert launch(setup).returncode == 0
    assert marker.exists()
    time.sleep(0.5)
    assert subprocess.run(["kill", "-0", marker.read_text().strip()], capture_output=True).returncode != 0


def test_a_running_ollama_is_left_alone(setup):
    bin_dir = setup["tmp"] / "no-binaries"
    bin_dir.mkdir()
    marker = setup["tmp"] / "ollama-started"
    fake = bin_dir / "ollama"
    fake.write_text(f"#!/bin/sh\necho started > '{marker}'\n")
    fake.chmod(0o755)
    with socket.socket() as listener:  # something answers where Ollama would be
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        url = f"http://127.0.0.1:{listener.getsockname()[1]}"
        assert launch(setup, BASA_OLLAMA_URL=url).returncode == 0
    assert not marker.exists()
