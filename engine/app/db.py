"""SQLite access for the engine: connections and database creation (P0-BE2-1)."""

import os
import sqlite3
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parent.parent
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"
# engine/storage/ is git-ignored, so the database never ends up in a commit.
DEFAULT_DB_PATH = ENGINE_DIR / "storage" / "basa.db"


class DatabaseExistsError(Exception):
    """Raised when init_db would overwrite an existing database without reset."""


def get_db_path() -> Path:
    """Return the database path, letting BASA_DB_PATH override the default."""
    override = os.environ.get("BASA_DB_PATH")
    return Path(override) if override else DEFAULT_DB_PATH


def connect(path: Path | str | None = None) -> sqlite3.Connection:
    """Open a connection with foreign keys enforced and rows readable by name.

    SQLite turns foreign keys off by default, per connection, so every
    connection must go through here or cascades and references silently stop
    working.
    """
    # Each caller opens its own connection and never shares it. FastAPI may still open a request's
    # connection in one worker thread and use it in another, which SQLite refuses by default.
    conn = sqlite3.connect(path or get_db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(path: Path | str | None = None, reset: bool = False) -> Path:
    """Create a fresh database from schema.sql and return its path.

    Refuses to touch an existing database unless reset is True, so running the
    script twice can't wipe real results by accident.
    """
    db_path = Path(path) if path else get_db_path()

    if db_path.exists():
        if not reset:
            raise DatabaseExistsError(
                f"{db_path} already exists. Pass reset=True (--reset) to replace it."
            )
        db_path.unlink()

    db_path.parent.mkdir(parents=True, exist_ok=True)
    schema = SCHEMA_PATH.read_text(encoding="utf-8")

    conn = connect(db_path)
    try:
        conn.executescript(schema)
        conn.commit()
    except sqlite3.Error:
        # Don't leave a half-built database behind for the next run to trip on.
        conn.close()
        db_path.unlink(missing_ok=True)
        raise
    conn.close()
    return db_path
