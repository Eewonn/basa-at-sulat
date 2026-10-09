"""Bring the whole app up offline and tear it down afterwards. Run by `start.sh` once the setup check passes.

1. make sure the database exists (create and seed it on a fresh laptop; never touch an existing one)
2. start Ollama if it is installed and not already running
3. start the engine on a free port and wait until /health answers
4. run the desktop app with BASA_ENGINE_PORT set, and wait for it to close
5. stop what we started: the engine, and Ollama only if we started it

Settings (environment variables, all optional): BASA_DATA_DIR (default engine/storage),
BASA_APP_CMD (default: npm --prefix desktop run dev), BASA_OLLAMA_URL, BASA_WARM_UP (default 1),
BASA_OLLAMA_WAIT_SEC.
"""

import os
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parent.parent
ENGINE_DIR = REPO_ROOT / "engine"
DESKTOP_DIR = REPO_ROOT / "desktop"
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
HEALTH_TIMEOUT_SEC = 180  # the first start loads the aligner (about 10 s), slower laptops need longer


def say(message: str) -> None:
    print(message, flush=True)


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def is_listening(host: str, port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(1)
        return s.connect_ex((host, port)) == 0


def prepare_database(data_dir: Path) -> bool:
    """Create and seed a fresh database. An existing one is never touched."""
    db_path = data_dir / "basa.db"
    if db_path.exists():
        return True
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
    except OSError as err:
        say(f"Could not set up the data folder {data_dir}: {err}")
        return False
    for module in ("app.init_db", "app.seed"):
        result = subprocess.run(
            [sys.executable, "-m", module, "--path", str(db_path)], cwd=ENGINE_DIR, capture_output=True, text=True
        )
        if result.returncode != 0:
            say(f"Could not create the database ({module}): {(result.stderr or result.stdout).strip()}")
            db_path.unlink(missing_ok=True)  # don't leave a half-built database for the next run to trust
            return False
    say(f"Created a fresh database at {db_path}")
    return True


def start_ollama(url: str):
    """Start `ollama serve` if it is installed and nothing answers yet. Returns the process, or None."""
    if shutil.which("ollama") is None:
        say("Ollama is not installed: group plans will use templates.")
        return None
    parsed = urlparse(url)
    host, port = parsed.hostname or "127.0.0.1", parsed.port or 11434
    if is_listening(host, port):
        return None  # already running: not ours to stop
    proc = subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    deadline = time.time() + float(os.environ.get("BASA_OLLAMA_WAIT_SEC", "5"))
    while time.time() < deadline and proc.poll() is None and not is_listening(host, port):
        time.sleep(0.1)
    say("Started Ollama." if proc.poll() is None else "Ollama did not start: group plans will use templates.")
    return proc


def wait_for_health(port: int, engine: subprocess.Popen) -> bool:
    deadline = time.time() + HEALTH_TIMEOUT_SEC
    while time.time() < deadline:
        if engine.poll() is not None:
            return False
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2):
                return True
        except (urllib.error.URLError, ConnectionError, OSError):
            time.sleep(0.2)
    return False


def stop(proc, name: str) -> None:
    if proc is None or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        say(f"{name} did not stop, forcing it.")
        proc.kill()
        proc.wait()


def app_command() -> list[str]:
    raw = os.environ.get("BASA_APP_CMD")
    if raw:
        return shlex.split(raw, posix=os.name != "nt")
    return [shutil.which("npm") or "npm", "--prefix", str(DESKTOP_DIR), "run", "dev"]


def main() -> int:
    data_dir = Path(os.environ.get("BASA_DATA_DIR") or ENGINE_DIR / "storage").resolve()
    if not prepare_database(data_dir):
        return 1

    # A SIGTERM (or closing the terminal) should still stop the engine, so turn it into an exit.
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))

    ollama = engine = app = None
    try:
        ollama = start_ollama(os.environ.get("BASA_OLLAMA_URL", DEFAULT_OLLAMA_URL))
        port = free_port()
        engine_env = {**os.environ, "BASA_WARM_UP": os.environ.get("BASA_WARM_UP", "1")}
        engine = subprocess.Popen(
            [sys.executable, "-m", "app", "--port", str(port), "--data-dir", str(data_dir)],
            cwd=ENGINE_DIR, env=engine_env,
        )
        if not wait_for_health(port, engine):
            say("The engine did not come up. Its messages are above.")
            return 1
        say(f"engine on port {port}")
        app = subprocess.Popen(app_command(), env={**os.environ, "BASA_ENGINE_PORT": str(port)})
        return app.wait()
    except KeyboardInterrupt:
        return 130
    finally:
        stop(app, "The app")
        stop(engine, "The engine")
        stop(ollama, "Ollama")


if __name__ == "__main__":
    sys.exit(main())
