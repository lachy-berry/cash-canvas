"""Tests for GET /api/transactions and DELETE /api/test/reset."""
import pytest

from server.db import get_connection
from tests.conftest import client, post_preview, post_confirm


def _import():
    post_confirm(post_preview().json()["new"])


class TestTransactionsList:
    def test_returns_transactions_ordered_desc_with_total(self):
        """Core contract: ordered by date DESC, total unaffected by pagination."""
        _import()
        data = client.get("/api/transactions").json()
        assert data["total"] == 3
        dates = [t["date"] for t in data["transactions"]]
        assert dates == sorted(dates, reverse=True)
        assert {"id", "date", "description", "amount", "balance", "labels"}.issubset(data["transactions"][0])

    def test_empty_before_import(self):
        data = client.get("/api/transactions").json()
        assert data["transactions"] == [] and data["total"] == 0

    @pytest.mark.parametrize("limit,offset,expected", [(2, 0, 2), (2, 2, 1)])
    def test_pagination(self, limit, offset, expected):
        _import()
        data = client.get(f"/api/transactions?limit={limit}&offset={offset}").json()
        assert len(data["transactions"]) == expected
        assert data["total"] == 3


class TestResetEndpoint:
    def test_blocked_without_flag_allowed_with_flag(self, monkeypatch):
        monkeypatch.delenv("CASH_CANVAS_TEST_MODE", raising=False)
        assert client.delete("/api/test/reset").status_code == 403

        monkeypatch.setenv("CASH_CANVAS_TEST_MODE", "1")
        _import()
        assert client.delete("/api/test/reset").status_code == 200
        with get_connection() as conn:
            assert conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 0
