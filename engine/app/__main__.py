"""Start the engine: python -m app [--port N] [--data-dir D] (run from engine/).

Listens on 127.0.0.1. The port is --port, else $PORT, else 8000. --data-dir D keeps the database at
D/basa.db and the audio under D, and overrides BASA_DB_PATH and BASA_STORAGE_DIR.
"""

import argparse
import os
import sys
from pathlib import Path

import uvicorn

DEFAULT_PORT = 8000


def parse_port(value: str) -> int:
    try:
        port = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"port must be a whole number from 1 to 65535, not '{value}'") from None
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError(f"port must be from 1 to 65535, not {port}")
    return port


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app", description="Start the Basa at Sulat engine.")
    parser.add_argument("--port", type=parse_port, help="port to listen on (default: $PORT, else 8000)")
    parser.add_argument("--data-dir", type=Path, help="folder for the database (basa.db) and the audio")
    args = parser.parse_args(argv)

    port = args.port
    if port is None:
        try:
            port = parse_port(os.environ.get("PORT", str(DEFAULT_PORT)))
        except argparse.ArgumentTypeError as err:
            parser.error(f"$PORT: {err}")
    if args.data_dir is not None:
        data_dir = args.data_dir.resolve()
        os.environ["BASA_DB_PATH"] = str(data_dir / "basa.db")
        os.environ["BASA_STORAGE_DIR"] = str(data_dir)

    uvicorn.run("app.main:app", host="127.0.0.1", port=port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
