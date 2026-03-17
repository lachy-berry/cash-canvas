"""Tests for GET /api/transactions and DELETE /api/test/reset."""
import pytest

from server.db import get_connection
from tests.conftest import client, post_preview, post_confirm


def _import():
    rows = post_preview().json()["new"]
    post_confirm(rows)


class TestListTransactions:
    def test_returns_200_with_shape(self):
        data = client.get("/api/transactions").json()
        assert "transactions" in data and "total" in data

    def test_empty_before_import(self):
        data = client.get("/api/transactions").json()
        assert data["transactions"] == [] and data["total"] == 0

    def test_total_matches_imported_count(self):
        _import()
        assert client.get("/api/transactions").json()["total"] == 3

    def test_transaction_has_required_fields(self):
        _import()
        tx = client.get("/api/transactions").json()["transactions"][0]
        assert {"id", "date", "description", "amount", "balance", "label_broad"}.issubset(tx)

    def test_ordered_by_date_desc(self):
        _import()
        dates = [t["date"] for t in client.get("/api/transactions").json()["transactions"]]
        assert dates == sorted(dates, reverse=True)

    @pytest.mark.parametrize("limit,offset,expected_count", [
        (2, 0, 2),
        (2, 2, 1),
        (1, 0, 1),
    ])
    def test_pagination(self, limit, offset, expected_count):
        _import()
        data = client.get(f"/api/transactions?limit={limit}&offset={offset}").json()
        assert len(data["transactions"]) == expected_count
        assert data["total"] == 3  # total never affected by pagination


class TestResetEndpoint:
    def test_reset_blocked_without_env_flag(self, monkeypatch):
        monkeypatch.delenv("CASH_CANVAS_TEST_MODE", raising=False)
        assert client.delete("/api/test/reset").status_code == 403

    def test_reset_allowed_with_env_flag(self, monkeypatch):
        monkeypatch.setenv("CASH_CANVAS_TEST_MODE", "1")
        _import()
        assert client.delete("/api/test/reset").status_code == 200
        with get_connection() as conn:
            assert conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 0
