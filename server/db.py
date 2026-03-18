"""SQLite database connection and schema initialisation."""
import sqlite3
from pathlib import Path

_DB_PATH = Path(__file__).parent.parent / "data" / "cash_canvas.db"

# ---------------------------------------------------------------------------
# Single source of truth for the schema.
# Order matters: import_batches must precede transactions (FK dependency),
# and transactions must precede transaction_labels (FK dependency).
# ---------------------------------------------------------------------------
_SCHEMA: list[tuple[str, str]] = [
    (
        "import_batches",
        """
        CREATE TABLE import_batches (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            imported_at  TEXT NOT NULL DEFAULT (datetime('now')),
            row_count    INTEGER NOT NULL,
            skipped      INTEGER NOT NULL DEFAULT 0
        )
        """,
    ),
    (
        "transactions",
        """
        CREATE TABLE transactions (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            date         TEXT NOT NULL,
            description  TEXT NOT NULL,
            amount       REAL NOT NULL,
            balance      REAL,
            fingerprint  TEXT,
            batch_id     INTEGER REFERENCES import_batches(id),
            imported_at  TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """,
    ),
    (
        "transaction_labels",
        """
        CREATE TABLE transaction_labels (
            transaction_id  INTEGER NOT NULL REFERENCES transactions(id),
            layer_id        TEXT    NOT NULL,
            category_id     TEXT    NOT NULL,
            PRIMARY KEY (transaction_id, layer_id)
        )
        """,
    ),
]

# Expected columns per table — kept in sync with _SCHEMA manually.
# Used by _schema_is_current() to detect stale DBs at startup.
_EXPECTED_COLUMNS: dict[str, set[str]] = {
    "import_batches": {"id", "imported_at", "row_count", "skipped"},
    "transactions": {
        "id", "date", "description", "amount", "balance",
        "fingerprint", "batch_id", "imported_at",
    },
    "transaction_labels": {"transaction_id", "layer_id", "category_id"},
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
    """Return True if all tables exist with at least the expected columns."""
    for table, expected in _EXPECTED_COLUMNS.items():
        if not expected.issubset(_table_columns(conn, table)):
            return False
    return True


def init_db() -> None:
    """Initialise the database schema.

    Phase 1: no migration tooling. If the schema is out of date (missing
    tables or columns), all tables are dropped and recreated from _SCHEMA.
    Data loss is acceptable for local pre-production use — per Issue #3.
    """
    with get_connection() as conn:
        if not _schema_is_current(conn):
            for table, _ in reversed(_SCHEMA):
                conn.execute(f"DROP TABLE IF EXISTS {table}")

        for _, create_sql in _SCHEMA:
            # _SCHEMA entries use CREATE TABLE; add IF NOT EXISTS for idempotency
            sql = create_sql.strip().replace("CREATE TABLE ", "CREATE TABLE IF NOT EXISTS ", 1)
            conn.execute(sql)

        conn.commit()
