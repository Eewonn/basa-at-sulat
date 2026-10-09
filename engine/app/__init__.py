import sys
from pathlib import Path

# `ai` is a sibling package at the repo root, not under engine/.
_REPO_ROOT = str(Path(__file__).resolve().parents[2])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
