"""Tests for server/db.py — schema initialisation and stale-schema migration."""
import sqlite3
from pathlib import Path

import pytest

from server.db import _schema_is_current, _table_columns, init_db


def _make_conn(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


STALE_SCHEMA = """
    CREATE TABLE import_batches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        imported_at TEXT NOT NULL DEFAULT (datetime('now')),
        row_count INTEGER NOT NULL
    );
    CREATE TABLE transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL, description TEXT NOT NULL,
        amount REAL NOT NULL, balance REAL, label_broad TEXT,
        fingerprint TEXT, batch_id INTEGER,
        imported_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
"""
# NOTE: stale schema has label_broad (old) and is missing transaction_labels table.
# init_db() must detect this as stale and recreate from _SCHEMA.


def _make_stale_db(path: str) -> None:
    with _make_conn(path) as conn:
        conn.executescript(STALE_SCHEMA)


class TestInitDb:
    def test_all_expected_columns_present_after_init(self, tmp_path, monkeypatch):
        """init_db() must create all tables with all required columns.

        label_broad must NOT appear — it is replaced by the transaction_labels table.
        """
        db_file = str(tmp_path / "test.db")
        monkeypatch.setattr("server.db._DB_PATH", Path(db_file))
        init_db()
        with _make_conn(db_file) as conn:
            assert {"id", "imported_at", "row_count", "skipped"}.issubset(
                _table_columns(conn, "import_batches")
            )
            tx_cols = _table_columns(conn, "transactions")
            assert {"id", "date", "description", "amount", "balance",
                    "fingerprint", "batch_id", "imported_at"}.issubset(tx_cols)
            assert "label_broad" not in tx_cols
            # transaction_labels join table must exist
            assert {"transaction_id", "layer_id", "category_id"}.issubset(
                _table_columns(conn, "transaction_labels")
            )


class TestSchemaMigration:
    def test_stale_db_is_recreated_with_correct_schema(self, tmp_path, monkeypatch):
        """A stale DB (missing skipped column) must be detected, dropped, and
        recreated so runtime inserts work and any old data is cleared."""
        db_file = str(tmp_path / "stale.db")
        monkeypatch.setattr("server.db._DB_PATH", Path(db_file))
        _make_stale_db(db_file)

        # Seed a row to confirm data is cleared
        with _make_conn(db_file) as conn:
            conn.execute("INSERT INTO import_batches (row_count) VALUES (5)")
            conn.commit()
            assert _schema_is_current(conn) is False

        init_db()

        with _make_conn(db_file) as conn:
            assert "skipped" in _table_columns(conn, "import_batches")
            assert conn.execute("SELECT COUNT(*) FROM import_batches").fetchone()[0] == 0
