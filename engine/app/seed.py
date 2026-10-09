"""Load synthetic learners and sample passages into the database (P0-BE2-2).

Run from engine/: python -m app.seed [--path PATH] [--reset]

Re-running is safe: rows are inserted or updated from the JSON files. The one
exception is a passage whose text changed while assessments already point at
it. Word results are stored by word index, so new text would silently break
saved results, and the seed stops instead. See docs/SCHEMA.md.
"""

import argparse
import json
import re
import sqlite3
import sys
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from app.db import ENGINE_DIR, connect, get_db_path, init_db

DATA_DIR = ENGINE_DIR.parent / "data"
DEFAULT_LEARNERS_PATH = DATA_DIR / "learners" / "learners.json"
DEFAULT_PASSAGES_PATH = DATA_DIR / "passages" / "passages.json"

# ISO 639 codes (fil, eng, ilo, ceb, pam...), so a regional passage can be
# added without touching this file.
LANGUAGE_PATTERN = re.compile(r"[a-z]{2,3}")

LEARNER_FIELDS = ("id", "display_name", "grade")
PASSAGE_FIELDS = ("id", "title", "language", "grade", "text")


class SeedError(Exception):
    """Raised when seed data is invalid or can't be applied safely."""


@dataclass
class SeedResult:
    """How many rows each table gained or changed. Unchanged rows aren't counted."""

    learners_added: int = 0
    learners_updated: int = 0
    passages_added: int = 0
    passages_updated: int = 0


# --- Reading and checking the JSON files -----------------------------------

def load_entries(path: Path) -> list[dict]:
    """Read a JSON file that must hold a list of objects."""
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise SeedError(f"{path}: file not found") from None
    except OSError as err:
        raise SeedError(f"{path}: could not read file: {err}") from None

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as err:
        raise SeedError(f"{path}: invalid JSON: {err}") from None

    if not isinstance(data, list):
        raise SeedError(f"{path}: expected a list of entries, got {type(data).__name__}")
    for index, entry in enumerate(data):
        if not isinstance(entry, dict):
            raise SeedError(f"{path}: entry {index} is not an object")
    return data


def _check_text(entry: dict, field: str, where: str) -> str:
    value = entry[field]
    if not isinstance(value, str) or not value.strip():
        raise SeedError(f"{where}: '{field}' must be non-empty text")
    return value


def _check_grade(entry: dict, where: str) -> int:
    grade = entry["grade"]
    # bool is a subclass of int, so `true` would otherwise pass as grade 1.
    if isinstance(grade, bool) or not isinstance(grade, int) or not 1 <= grade <= 12:
        raise SeedError(f"{where}: 'grade' must be a whole number from 1 to 12")
    return grade


def _check_entries(entries: list[dict], fields: tuple[str, ...], path: Path) -> None:
    """Shared checks: required fields present, ids are non-empty and unique.

    Extra fields are allowed and ignored, e.g. a credit line on a passage.
    """
    seen = set()
    for index, entry in enumerate(entries):
        where = f"{path}: entry {index}"
        missing = [field for field in fields if field not in entry]
        if missing:
            raise SeedError(f"{where}: missing {', '.join(missing)}")

        entry_id = _check_text(entry, "id", where)
        if entry_id in seen:
            raise SeedError(f"{path}: duplicate id '{entry_id}'")
        seen.add(entry_id)


def validate_learners(entries: list[dict], path: Path) -> list[tuple]:
    """Return learner rows in LEARNER_FIELDS order, or raise SeedError."""
    _check_entries(entries, LEARNER_FIELDS, path)
    rows = []
    for entry in entries:
        where = f"{path}: learner '{entry['id']}'"
        rows.append((
            entry["id"],
            _check_text(entry, "display_name", where),
            _check_grade(entry, where),
        ))
    return rows


def validate_passages(entries: list[dict], path: Path) -> list[tuple]:
    """Return passage rows in PASSAGE_FIELDS order, or raise SeedError."""
    _check_entries(entries, PASSAGE_FIELDS, path)
    rows = []
    for entry in entries:
        where = f"{path}: passage '{entry['id']}'"
        language = _check_text(entry, "language", where)
        if not LANGUAGE_PATTERN.fullmatch(language):
            raise SeedError(f"{where}: 'language' must be a 2-3 letter lowercase code")
        rows.append((
            entry["id"],
            _check_text(entry, "title", where),
            language,
            _check_grade(entry, where),
            _check_text(entry, "text", where),
        ))
    return rows


# --- Writing to the database -----------------------------------------------

def _existing_rows(conn: sqlite3.Connection, table: str, fields: tuple[str, ...]) -> dict:
    # table and fields come from the constants above, never from user input.
    query = f"SELECT {', '.join(fields)} FROM {table}"
    return {row[0]: tuple(row) for row in conn.execute(query)}


def _find_text_conflicts(conn: sqlite3.Connection, passages: list[tuple],
                         existing: dict) -> list[str]:
    """Passage ids whose text would change while assessments still use them."""
    text_index = PASSAGE_FIELDS.index("text")
    conflicts = []
    for row in passages:
        old = existing.get(row[0])
        if old is None or old[text_index] == row[text_index]:
            continue
        in_use = conn.execute(
            "SELECT 1 FROM assessments WHERE passage_id = ? LIMIT 1", (row[0],)
        ).fetchone()
        if in_use:
            conflicts.append(row[0])
    return conflicts


def _upsert(conn: sqlite3.Connection, table: str, fields: tuple[str, ...],
            rows: list[tuple], existing: dict) -> tuple[int, int]:
    """Insert new rows, update changed ones, and return (added, updated)."""
    columns = ", ".join(fields)
    placeholders = ", ".join("?" for _ in fields)
    updates = ", ".join(f"{field} = excluded.{field}" for field in fields[1:])
    sql = (
        f"INSERT INTO {table} ({columns}) VALUES ({placeholders}) "
        f"ON CONFLICT (id) DO UPDATE SET {updates}"
    )

    added = updated = 0
    for row in rows:
        old = existing.get(row[0])
        if old == row:
            continue
        conn.execute(sql, row)
        if old is None:
            added += 1
        else:
            updated += 1
    return added, updated


def apply_seed(conn: sqlite3.Connection, learners: list[tuple],
               passages: list[tuple]) -> SeedResult:
    """Write validated rows in one transaction: everything lands or nothing does."""
    existing_learners = _existing_rows(conn, "learners", LEARNER_FIELDS)
    existing_passages = _existing_rows(conn, "passages", PASSAGE_FIELDS)

    conflicts = _find_text_conflicts(conn, passages, existing_passages)
    if conflicts:
        raise SeedError(
            "passage text changed but saved assessments use it: "
            f"{', '.join(conflicts)}. Add the new text under a new id instead, "
            "or run with --reset to start over (all results are lost)."
        )

    result = SeedResult()
    with conn:  # commits on success, rolls back if any insert fails
        result.learners_added, result.learners_updated = _upsert(
            conn, "learners", LEARNER_FIELDS, learners, existing_learners
        )
        result.passages_added, result.passages_updated = _upsert(
            conn, "passages", PASSAGE_FIELDS, passages, existing_passages
        )
    return result


def seed_db(path: Path | str | None = None, reset: bool = False,
            learners_path: Path | None = None,
            passages_path: Path | None = None) -> SeedResult:
    """Validate the seed files, create the database if needed, then seed it."""
    learners_path = learners_path or DEFAULT_LEARNERS_PATH
    passages_path = passages_path or DEFAULT_PASSAGES_PATH

    # Validate first, so a typo in the JSON never costs a --reset its data.
    learners = validate_learners(load_entries(learners_path), learners_path)
    passages = validate_passages(load_entries(passages_path), passages_path)

    db_path = Path(path) if path else get_db_path()
    if reset or not db_path.exists():
        init_db(db_path, reset=reset)

    with closing(connect(db_path)) as conn:
        return apply_seed(conn, learners, passages)


# --- Command line ----------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Load synthetic learners and sample passages into the database."
    )
    parser.add_argument(
        "--path",
        help=f"database file (default: BASA_DB_PATH or {get_db_path()})",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="delete the existing database first (all data is lost)",
    )
    args = parser.parse_args(argv)

    try:
        result = seed_db(args.path, reset=args.reset)
    except SeedError as err:
        print(f"Error: {err}", file=sys.stderr)
        return 1
    except (sqlite3.Error, OSError) as err:
        print(f"Error: could not seed the database: {err}", file=sys.stderr)
        return 1

    print(
        f"Learners: {result.learners_added} added, {result.learners_updated} updated. "
        f"Passages: {result.passages_added} added, {result.passages_updated} updated."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
