"""Tests for POST /api/import/confirm."""
import hashlib
import pytest

from server.db import get_connection
from tests.conftest import client, post_preview, post_confirm


def _preview_new():
    return post_preview().json()["new"]


class TestConfirmBasic:
    def test_returns_200(self):
        assert post_confirm(_preview_new()).status_code == 200

    def test_response_shape(self):
        data = post_confirm(_preview_new()).json()
        assert {"batch_id", "imported", "skipped"}.issubset(data)

    def test_imported_and_skipped_counts(self):
        data = post_confirm(_preview_new()).json()
        assert data["imported"] == 3
        assert data["skipped"] == 0

    def test_skipped_echoed_from_request(self):
        data = client.post("/api/import/confirm", json={"rows": _preview_new(), "skipped": 4}).json()
        assert data["skipped"] == 4

    def test_negative_skipped_returns_422(self):
        res = client.post("/api/import/confirm", json={"rows": _preview_new(), "skipped": -1})
        assert res.status_code == 422

    def test_empty_rows_returns_422(self):
        assert post_confirm([]).status_code == 422

    def test_rows_persisted_to_db(self):
        post_confirm(_preview_new())
        with get_connection() as conn:
            assert conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 3

    def test_transaction_fields_correct(self):
        post_confirm(_preview_new())
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM transactions WHERE description LIKE '%WOOLWORTHS%'"
            ).fetchone()
        assert row["date"] == "2026-03-01"
        assert row["amount"] == pytest.approx(-82.50)
        assert row["balance"] == pytest.approx(4217.50)

    def test_label_broad_is_null_on_import(self):
        post_confirm(_preview_new())
        with get_connection() as conn:
            labels = conn.execute("SELECT label_broad FROM transactions").fetchall()
        assert all(r["label_broad"] is None for r in labels)

    def test_batch_id_set_on_all_rows(self):
        data = post_confirm(_preview_new()).json()
        with get_connection() as conn:
            txns = conn.execute("SELECT batch_id FROM transactions").fetchall()
        assert all(r["batch_id"] == data["batch_id"] for r in txns)

    def test_fingerprint_stored_and_matches_server_computation(self):
        rows = _preview_new()
        post_confirm(rows)
        with get_connection() as conn:
            stored = conn.execute("SELECT fingerprint FROM transactions").fetchall()
        assert all(r["fingerprint"] is not None for r in stored)

        # Verify server recomputes fingerprint (not copying client value)
        expected = hashlib.sha256("2026-01-01|TEST|-10.0".encode()).hexdigest()
        post_confirm([{"date": "2026-01-01", "description": "TEST", "amount": -10.00, "balance": None}])
        with get_connection() as conn:
            row = conn.execute(
                "SELECT fingerprint FROM transactions WHERE description='TEST'"
            ).fetchone()
        assert row["fingerprint"] == expected

    def test_confirming_duplicates_adds_them(self):
        post_confirm(_preview_new())
        dups = post_preview().json()["duplicates"]
        post_confirm(dups)
        with get_connection() as conn:
            assert conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 6

    def test_two_identical_rows_both_persisted(self):
        rows = [
            {"date": "2026-03-01", "description": "NETFLIX.COM", "amount": -22.99, "balance": 500.00},
            {"date": "2026-03-01", "description": "NETFLIX.COM", "amount": -22.99, "balance": 500.00},
        ]
        res = post_confirm(rows)
        assert res.status_code == 200
        assert res.json()["imported"] == 2
        with get_connection() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM transactions WHERE description = 'NETFLIX.COM'"
            ).fetchone()[0]
        assert count == 2
