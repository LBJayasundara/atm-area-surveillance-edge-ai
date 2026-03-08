"""
Database initialisation script.

Creates (or re-creates) the SQLite database using database/schema.sql.

Usage::

    python database/init_db.py
    python database/init_db.py --db database/alerts.db
    python database/init_db.py --reset   # drop and recreate
"""

from __future__ import annotations

import argparse
import os
import sqlite3
from pathlib import Path


def init_db(db_path: str = "database/alerts.db", schema_path: str = "database/schema.sql") -> None:
    """
    Initialise the database from the SQL schema file.

    Args:
        db_path: Path to the SQLite database file (created if absent).
        schema_path: Path to the SQL schema file.
    """
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    schema_sql = Path(schema_path).read_text(encoding="utf-8")

    with sqlite3.connect(db_path) as conn:
        conn.executescript(schema_sql)

    print(f"Database initialised: {db_path}")


def reset_db(db_path: str) -> None:
    """Delete the database file and re-initialise."""
    if os.path.isfile(db_path):
        os.remove(db_path)
        print(f"Existing database removed: {db_path}")
    init_db(db_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialise ATM surveillance database")
    parser.add_argument("--db", default="database/alerts.db", help="Database file path")
    parser.add_argument(
        "--schema", default="database/schema.sql", help="SQL schema file path"
    )
    parser.add_argument(
        "--reset", action="store_true", help="Drop existing database and recreate"
    )
    args = parser.parse_args()

    if args.reset:
        reset_db(args.db)
    else:
        init_db(args.db, args.schema)


if __name__ == "__main__":
    main()
