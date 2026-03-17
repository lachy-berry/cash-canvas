"""
Tests for server/db.py — schema initialisation and stale-schema migration.
"""
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from server.db import _schema_is_current, _table_columns, init_db, get_connection


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_conn(path: str) -> sqlite3.Connection:
    """Open a connection with row_factory at an arbitrary path."""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# Schema correctness after init_db()
# ---------------------------------------------------------------------------

class TestInitDb:
    def test_import_batches_has_all_columns(self, tmp_path, monkeypatch):
        db_file = str(tmp_path / "test.db")
        monkeypatch.setattr("server.db._DB_PATH", Path(db_file))
        init_db()
        with _make_conn(db_file) as conn:
            cols = _table_columns(conn, "import_batches")
        assert {"id", "imported_at", "row_count", "skipped"}.issubset(cols)

    def test_transactions_has_all_columns(self, tmp_path, monkeypatch):
        db_file = str(tmp_path / "test.db")
        monkeypatch.setattr("server.db._DB_PATH", Path(db_file))
        init_db()
        with _make_conn(db_file) as conn:
            cols = _table_columns(conn, "transactions")
        expected = {
            "id", "date", "description", "amount", "balance",
            "label_broad", "fingerprint", "batch_id", "imported_at",
        }
        assert expected.issubset(cols)

    def test_idempotent_on_clean_db(self, tmp_path, monkeypatch):
        """Calling init_db() twice on a fresh DB must not raise."""
        db_file = str(tmp_path / "test.db")
        monkeypatch.setattr("server.db._DB_PATH", Path(db_file))
        init_db()
        init_db()  # should not raise


# ---------------------------------------------------------------------------
# Stale-schema migration
# ---------------------------------------------------------------------------

class TestSchemaMigration:
    def test_stale_db_missing_skipped_column_is_recreated(self, tmp_path, monkeypatch):
        """A DB with import_batches missing the skipped column (pre-migration)
        must be dropped and recreated by init_db() so runtime inserts succeed."""
        db_file = str(tmp_path / "stale.db")
        monkeypatch.setattr("server.db._DB_PATH", Path(db_file))

        # Create a stale schema without the skipped column
        with _make_conn(db_file) as conn:
            conn.execute("""
                CREATE TABLE import_batches (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    imported_at TEXT NOT NULL DEFAULT (datetime('now')),
                    row_count   INTEGER NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE transactions (
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

        # init_db() must detect the mismatch and recreate
        init_db()

        # Verify the skipped column now exists
        with _make_conn(db_file) as conn:
            cols = _table_columns(conn, "import_batches")
        assert "skipped" in cols

    def test_stale_db_data_cleared_after_migration(self, tmp_path, monkeypatch):
        """Data in stale tables is dropped during migration — consistent with
        Issue #3's phase-1 policy of drop+recreate over migration tooling."""
        db_file = str(tmp_path / "stale.db")
        monkeypatch.setattr("server.db._DB_PATH", Path(db_file))

        # Create stale schema and insert a row
        with _make_conn(db_file) as conn:
            conn.execute("""
                CREATE TABLE import_batches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    imported_at TEXT NOT NULL DEFAULT (datetime('now')),
                    row_count INTEGER NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    description TEXT NOT NULL,
                    amount REAL NOT NULL,
                    balance REAL,
                    label_broad TEXT,
                    fingerprint TEXT,
                    batch_id INTEGER,
                    imported_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)
            conn.execute("INSERT INTO import_batches (row_count) VALUES (5)")
            conn.commit()

        init_db()

        with _make_conn(db_file) as conn:
            count = conn.execute("SELECT COUNT(*) FROM import_batches").fetchone()[0]
        assert count == 0

    def test_schema_is_current_returns_false_for_stale(self, tmp_path):
        """_schema_is_current() must return False when a column is missing."""
        db_file = str(tmp_path / "stale.db")
        with _make_conn(db_file) as conn:
            conn.execute("""
                CREATE TABLE import_batches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    imported_at TEXT NOT NULL DEFAULT (datetime('now')),
                    row_count INTEGER NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    description TEXT NOT NULL,
                    amount REAL NOT NULL,
                    balance REAL,
                    label_broad TEXT,
                    fingerprint TEXT,
                    batch_id INTEGER,
                    imported_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)
            conn.commit()
            assert _schema_is_current(conn) is False

    def test_schema_is_current_returns_true_after_init(self, tmp_path, monkeypatch):
        """_schema_is_current() must return True after init_db() runs."""
        db_file = str(tmp_path / "fresh.db")
        monkeypatch.setattr("server.db._DB_PATH", Path(db_file))
        init_db()
        with _make_conn(db_file) as conn:
            assert _schema_is_current(conn) is True
