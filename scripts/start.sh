#!/usr/bin/env bash
# Basa at Sulat: start everything offline.   scripts/start.sh [--check]
#   (no option)  check this laptop, then start Ollama, the engine and the app
#   --check      report what is ready or missing, start nothing
# On Windows run it from Git Bash or WSL. Set BASA_PYTHON to pick the Python to use.
ROOT="$(cd "${BASH_SOURCE[0]%/*}/.." && pwd)"

find_python() {
  if [ -n "$BASA_PYTHON" ]; then echo "$BASA_PYTHON"; return; fi
  for candidate in "$ROOT/engine/.venv/bin/python" "$ROOT/engine/.venv/Scripts/python.exe"; do
    if [ -x "$candidate" ]; then echo "$candidate"; return; fi
  done
  command -v python3 || command -v python
}

PYTHON="$(find_python)"
if [ -z "$PYTHON" ]; then
  echo "start.sh: Python 3 was not found. Install it, or set BASA_PYTHON to its path." >&2
  exit 1
fi

case "$1" in
  "")
    "$PYTHON" "$ROOT/scripts/check_setup.py" || {
      echo "Fix the items above, then run scripts/start.sh again." >&2
      exit 1
    }
    exec "$PYTHON" "$ROOT/scripts/launch.py"
    ;;
  --check)
    exec "$PYTHON" "$ROOT/scripts/check_setup.py"
    ;;
  *)
    echo "usage: scripts/start.sh [--check]" >&2
    exit 2
    ;;
esac
