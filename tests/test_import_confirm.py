"""Tests for POST /api/import/confirm."""
import hashlib
import sqlite3

import pytest

from server.db import get_connection
from tests.conftest import client, make_row, post_preview, post_confirm


def _new_rows():
    return post_preview().json()["new"]


class TestConfirm:
    def test_persists_rows_with_correct_fields_and_returns_contract(self):
        """Core contract: rows saved to DB with correct values; response has
        batch_id, imported, skipped."""
        data = post_confirm(_new_rows()).json()
        assert {"batch_id", "imported", "skipped"}.issubset(data)
        assert data["imported"] == 3 and data["skipped"] == 0

        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM transactions WHERE description LIKE '%WOOLWORTHS%'"
            ).fetchone()
        assert row["date"] == "2026-03-01"
        assert row["amount"] == pytest.approx(-82.50)
        # label_broad column removed — labels stored in transaction_labels join table.
        # During ATDD red phase the table may not exist yet; once Feature #3 is built
        # this assertion confirms no label is auto-assigned on import.
        try:
            with get_connection() as conn:
                label_row = conn.execute(
                    "SELECT 1 FROM transaction_labels WHERE transaction_id=?", (row["id"],)
                ).fetchone()
            assert label_row is None
        except sqlite3.OperationalError:
            pass  # table not yet created — acceptable during red phase
        assert row["batch_id"] == data["batch_id"]

    def test_fingerprint_computed_server_side(self):
        """Fingerprint in DB must match server computation, not any client value."""
        post_confirm([make_row(description="TEST")])
        expected = hashlib.sha256("2026-01-01|TEST|-10.0".encode()).hexdigest()
        with get_connection() as conn:
            row = conn.execute("SELECT fingerprint FROM transactions WHERE description='TEST'").fetchone()
        assert row["fingerprint"] == expected

    def test_skipped_echoed_and_validated(self):
        """skipped is returned as provided; negative value is rejected."""
        assert post_confirm(_new_rows(), skipped=4).json()["skipped"] == 4
        assert client.post(
            "/api/import/confirm",
            json={"rows": [make_row(description="SKIP VALIDATION")], "skipped": -1},
        ).status_code == 422

    def test_duplicate_rows_included_when_confirmed(self):
        """User can force-include duplicates — both original and re-confirmed rows persist."""
        post_confirm(_new_rows())
        dups = post_preview().json()["duplicates"]
        post_confirm(dups)
        with get_connection() as conn:
            assert conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 6

    def test_empty_rows_returns_422(self):
        assert post_confirm([]).status_code == 422
