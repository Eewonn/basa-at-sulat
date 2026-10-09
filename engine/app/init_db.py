"""Create a fresh SQLite database. Run from engine/: python -m app.init_db [--reset]"""

import argparse
import sqlite3
import sys

from app.db import DatabaseExistsError, get_db_path, init_db


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a fresh Basa at Sulat database.")
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
        db_path = init_db(args.path, reset=args.reset)
    except DatabaseExistsError as err:
        print(f"Error: {err}", file=sys.stderr)
        return 1
    except (sqlite3.Error, OSError) as err:
        print(f"Error: could not create the database: {err}", file=sys.stderr)
        return 1

    print(f"Created database at {db_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
