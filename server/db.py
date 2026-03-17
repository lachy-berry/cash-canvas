"""SQLite database connection and schema initialisation."""
import sqlite3
from pathlib import Path

_DB_PATH = Path(__file__).parent.parent / "data" / "cash_canvas.db"

# Expected columns per table. Used by _check_schema() to detect stale DBs.
_EXPECTED_COLUMNS: dict[str, set[str]] = {
    "import_batches": {"id", "imported_at", "row_count", "skipped"},
    "transactions": {
        "id", "date", "description", "amount", "balance",
        "label_broad", "fingerprint", "batch_id", "imported_at",
    },
}


def get_connection() -> sqlite3.Connection:
    """Return a SQLite connection with row_factory set for dict-like access."""
    _DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    """Return the set of column names for an existing table."""
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {r["name"] for r in rows}


def _schema_is_current(conn: sqlite3.Connection) -> bool:
    """Return True if all tables exist with the correct columns."""
    for table, expected in _EXPECTED_COLUMNS.items():
        actual = _table_columns(conn, table)
        if not actual:
            return False  # table doesn't exist yet
        if not expected.issubset(actual):
            return False  # missing one or more columns
    return True


def init_db() -> None:
    """Initialise the database schema.

    Phase 1: no migration tooling. If the schema is out of date (missing
    tables or columns), both tables are dropped and recreated. All data
    is local and pre-production, so data loss during development is
    acceptable — as agreed in Issue #3.
    """
    with get_connection() as conn:
        if not _schema_is_current(conn):
            # Drop in reverse dependency order so FK constraints don't block
            conn.execute("DROP TABLE IF EXISTS transactions")
            conn.execute("DROP TABLE IF EXISTS import_batches")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS import_batches (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                imported_at  TEXT NOT NULL DEFAULT (datetime('now')),
                row_count    INTEGER NOT NULL,
                skipped      INTEGER NOT NULL DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                date         TEXT NOT NULL,
                description  TEXT NOT NULL,
                amount       REAL NOT NULL,
                balance      REAL,
                label_broad  TEXT,
                fingerprint  TEXT,
                batch_id     INTEGER REFERENCES import_batches(id),
                imported_at  TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        conn.commit()
