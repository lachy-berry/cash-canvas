"""SQLite database connection and schema initialisation."""
import sqlite3
from pathlib import Path

_DB_PATH = Path(__file__).parent.parent / "data" / "cash_canvas.db"


def get_connection() -> sqlite3.Connection:
    """Return a SQLite connection with row_factory set for dict-like access."""
    _DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create tables if they don't already exist."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                date         TEXT NOT NULL,
                description  TEXT NOT NULL,
                amount       REAL NOT NULL,
                balance      REAL,
                label_broad  TEXT,
                imported_at  TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        conn.commit()
