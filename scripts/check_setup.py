"""Report whether this laptop is ready to run Basa at Sulat offline. Used by `start.sh --check`.

Required parts stop the start when missing; Ollama only warns, because group plans fall back to
templates. Exit code: 0 when every required part is ready, 1 otherwise. Starts and changes nothing.
"""

import importlib.util
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import download_models as dm

REPO_ROOT = Path(__file__).resolve().parent.parent

ENGINE_MODULES = ["fastapi", "uvicorn", "multipart"]  # engine/requirements.txt
AI_MODULES = ["torch", "torchaudio", "soundfile", "numpy"]  # ai/requirements.txt


@dataclass
class Check:
    name: str
    probe: Callable[[], str | None]  # None when ready, otherwise what is wrong
    fix: str
    required: bool = True


def program_problem(program: str, which=shutil.which) -> str | None:
    return None if which(program) else f"'{program}' is not on the PATH"


def missing_modules(modules: list[str], find=importlib.util.find_spec) -> str | None:
    missing = [m for m in modules if find(m) is None]
    return f"missing: {', '.join(missing)}" if missing else None


def desktop_problem(root: Path = REPO_ROOT) -> str | None:
    return None if (root / "desktop" / "node_modules").is_dir() else "desktop/node_modules is not there"


def weights_problem(status: str) -> str | None:
    return None if status == dm.PRESENT else "the MMS aligner weights (about 1.2 GB) are not downloaded"


def ollama_problem(status: str) -> str | None:
    if status == dm.PRESENT:
        return None
    if status == dm.MISSING:
        return "Ollama is running but the model is not pulled (run: ollama pull <model>)"
    return "Ollama is not installed or not running"


def default_checks(root: Path = REPO_ROOT, which=shutil.which, find=importlib.util.find_spec) -> list[Check]:
    return [
        Check("ffmpeg", lambda: program_problem("ffmpeg", which), "install ffmpeg and put it on the PATH"),
        Check("npm", lambda: program_problem("npm", which), "install Node.js (it includes npm)"),
        Check(
            "Python packages",
            lambda: missing_modules(ENGINE_MODULES + AI_MODULES, find),
            "pip install -r engine/requirements.txt -r ai/requirements.txt",
        ),
        Check(
            "aligner weights",
            lambda: weights_problem(dm.Aligner().status()),
            "python scripts/download_models.py",
        ),
        Check("desktop dependencies", lambda: desktop_problem(root), "cd desktop && npm install"),
        Check(
            "Ollama",
            lambda: ollama_problem(dm.Ollama().status()),
            "install Ollama from ollama.com, start it, then python scripts/download_models.py",
            required=False,
        ),
    ]


def main(argv: list[str] | None = None, checks: list[Check] | None = None) -> int:
    checks = default_checks() if checks is None else checks
    blocked = 0
    print("Checking this laptop:")
    for check in checks:
        try:
            problem = check.probe()
        except Exception as err:  # a broken probe is a problem to report, not a crash
            problem = f"could not check: {err}"
        if problem is None:
            print(f"  [ok] {check.name}")
        elif check.required:
            print(f"  [MISSING] {check.name}: {problem}\n            fix: {check.fix}")
            blocked += 1
        else:
            print(f"  [warn] {check.name}: {problem}\n            fix: {check.fix}")
    if blocked:
        print(f"Not ready: {blocked} required item(s) missing.")
        return 1
    print("Ready.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
