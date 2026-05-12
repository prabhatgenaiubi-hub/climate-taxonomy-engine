"""
backend/db/database.py
=======================
SQLite database setup for user credentials.
Creates the `users` table on first run.
DB file stored at: data/auth/users.db
"""

import sqlite3
from pathlib import Path

DB_DIR  = Path(__file__).resolve().parent.parent.parent / "data" / "auth"
DB_PATH = DB_DIR / "users.db"


def get_connection() -> sqlite3.Connection:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row          # results as dict-like rows
    return conn


def init_db() -> None:
    """Create tables if they don't exist. Called on app startup."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                username    TEXT    UNIQUE NOT NULL,
                email       TEXT    UNIQUE NOT NULL,
                full_name   TEXT    NOT NULL,
                hashed_password TEXT NOT NULL,
                role        TEXT    NOT NULL DEFAULT 'analyst',
                is_active   INTEGER NOT NULL DEFAULT 1,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
            )
        """)
        conn.commit()
    print("✅ Database initialised:", DB_PATH)
