"""Tests for PATCH /api/transactions/{id}/labels — label CRUD and validation.

These tests are written BEFORE any implementation exists (ATDD step 2).
All tests are expected to FAIL until the feature is built.
"""
import pytest

from server.db import get_connection
from tests.conftest import client, make_row, post_confirm


def _seed_one_transaction() -> int:
    """Insert a single transaction and return its id."""
    resp = post_confirm([make_row(description="WOOLWORTHS")])
    assert resp.status_code == 200
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM transactions WHERE description='WOOLWORTHS'"
        ).fetchone()
    return row["id"]


class TestLabelSet:
    def test_set_broad_label_returns_200_and_is_persisted(self):
        """Setting a valid broad label must return 200 and persist in the DB."""
        tx_id = _seed_one_transaction()
        resp = client.patch(
            f"/api/transactions/{tx_id}/labels",
            json={"layer": "broad", "category": "groceries"},
        )
        assert resp.status_code == 200

        # Verify label is persisted in the join table
        with get_connection() as conn:
            row = conn.execute(
                "SELECT category_id FROM transaction_labels "
                "WHERE transaction_id=? AND layer_id='broad'",
                (tx_id,),
            ).fetchone()
        assert row is not None
        assert row["category_id"] == "groceries"

    def test_set_label_reflected_in_transaction_list(self):
        """After setting a label, GET /api/transactions must return it under labels.broad."""
        tx_id = _seed_one_transaction()
        client.patch(
            f"/api/transactions/{tx_id}/labels",
            json={"layer": "broad", "category": "dining"},
        )
        data = client.get("/api/transactions").json()
        tx = next(t for t in data["transactions"] if t["id"] == tx_id)
        assert tx["labels"]["broad"] == "dining"

    def test_upsert_overwrites_existing_label(self):
        """PATCHing a second time replaces the first label — not duplicates it."""
        tx_id = _seed_one_transaction()
        client.patch(
            f"/api/transactions/{tx_id}/labels",
            json={"layer": "broad", "category": "groceries"},
        )
        client.patch(
            f"/api/transactions/{tx_id}/labels",
            json={"layer": "broad", "category": "transport"},
        )
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT category_id FROM transaction_labels "
                "WHERE transaction_id=? AND layer_id='broad'",
                (tx_id,),
            ).fetchall()
        assert len(rows) == 1
        assert rows[0]["category_id"] == "transport"


class TestLabelClear:
    def test_clear_label_with_null_category_removes_row(self):
        """Sending category=null must delete the label row from the join table."""
        tx_id = _seed_one_transaction()
        client.patch(
            f"/api/transactions/{tx_id}/labels",
            json={"layer": "broad", "category": "groceries"},
        )
        resp = client.patch(
            f"/api/transactions/{tx_id}/labels",
            json={"layer": "broad", "category": None},
        )
        assert resp.status_code == 200

        with get_connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM transaction_labels WHERE transaction_id=? AND layer_id='broad'",
                (tx_id,),
            ).fetchone()
        assert row is None

    def test_clear_label_reflected_in_transaction_list(self):
        """After clearing, GET /api/transactions must return labels as empty dict."""
        tx_id = _seed_one_transaction()
        client.patch(
            f"/api/transactions/{tx_id}/labels",
            json={"layer": "broad", "category": "groceries"},
        )
        client.patch(
            f"/api/transactions/{tx_id}/labels",
            json={"layer": "broad", "category": None},
        )
        data = client.get("/api/transactions").json()
        tx = next(t for t in data["transactions"] if t["id"] == tx_id)
        assert tx["labels"] == {}

    def test_clear_nonexistent_label_is_idempotent(self):
        """Sending category=null when no label exists must still return 200."""
        tx_id = _seed_one_transaction()
        resp = client.patch(
            f"/api/transactions/{tx_id}/labels",
            json={"layer": "broad", "category": None},
        )
        assert resp.status_code == 200


class TestLabelValidation:
    def test_invalid_layer_returns_422(self):
        """A layer_id that doesn't exist in categories.yaml must be rejected."""
        tx_id = _seed_one_transaction()
        resp = client.patch(
            f"/api/transactions/{tx_id}/labels",
            json={"layer": "nonexistent_layer", "category": "groceries"},
        )
        assert resp.status_code == 422

    def test_invalid_category_returns_422(self):
        """A category_id that doesn't exist in the given layer must be rejected."""
        tx_id = _seed_one_transaction()
        resp = client.patch(
            f"/api/transactions/{tx_id}/labels",
            json={"layer": "broad", "category": "nonexistent_category"},
        )
        assert resp.status_code == 422

    def test_missing_transaction_returns_404(self):
        """Patching a transaction that doesn't exist must return 404."""
        resp = client.patch(
            "/api/transactions/999999/labels",
            json={"layer": "broad", "category": "groceries"},
        )
        assert resp.status_code == 404

    def test_missing_layer_field_returns_422(self):
        """Request body without 'layer' must be rejected by FastAPI validation."""
        tx_id = _seed_one_transaction()
        resp = client.patch(
            f"/api/transactions/{tx_id}/labels",
            json={"category": "groceries"},
        )
        assert resp.status_code == 422

    def test_missing_category_field_returns_422(self):
        """Request body without 'category' key at all must be rejected."""
        tx_id = _seed_one_transaction()
        resp = client.patch(
            f"/api/transactions/{tx_id}/labels",
            json={"layer": "broad"},
        )
        assert resp.status_code == 422


class TestTransactionListLabelsShape:
    def test_unlabelled_transaction_has_empty_labels_dict(self):
        """GET /api/transactions must include labels: {} for unlabelled transactions."""
        _seed_one_transaction()
        data = client.get("/api/transactions").json()
        tx = data["transactions"][0]
        assert "labels" in tx
        assert tx["labels"] == {}

    def test_labels_key_not_label_broad(self):
        """The old label_broad key must not appear — replaced by labels dict."""
        _seed_one_transaction()
        data = client.get("/api/transactions").json()
        tx = data["transactions"][0]
        assert "label_broad" not in tx
