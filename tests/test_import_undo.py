"""Tests for DELETE /api/import/batches/{batch_id}."""
from server.db import get_connection
from tests.conftest import client, post_preview, post_confirm


def _import_batch():
    rows = post_preview().json()["new"]
    return post_confirm(rows).json()["batch_id"]


class TestUndoImport:
    def test_undo_removes_transactions(self):
        batch_id = _import_batch()
        assert client.delete(f"/api/import/batches/{batch_id}").status_code == 200
        with get_connection() as conn:
            assert conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 0

    def test_undo_removes_only_target_batch(self):
        batch1 = _import_batch()
        dups = post_preview().json()["duplicates"]
        batch2 = post_confirm(dups).json()["batch_id"]
        client.delete(f"/api/import/batches/{batch1}")
        with get_connection() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM transactions WHERE batch_id = ?", (batch2,)
            ).fetchone()[0]
        assert count == 3

    def test_undo_nonexistent_batch_returns_404(self):
        assert client.delete("/api/import/batches/99999").status_code == 404

    def test_undo_response_has_deleted_count(self):
        batch_id = _import_batch()
        assert "deleted" in client.delete(f"/api/import/batches/{batch_id}").json()
