"""Tests for DELETE /api/import/batches/{batch_id}."""
from server.db import get_connection
from tests.conftest import client, post_preview, post_confirm


def _import_batch():
    return post_confirm(post_preview().json()["new"]).json()["batch_id"]


class TestUndo:
    def test_undo_removes_only_target_batch(self):
        """Undo deletes all transactions for that batch and only that batch."""
        batch1 = _import_batch()
        batch2 = post_confirm(post_preview().json()["duplicates"]).json()["batch_id"]

        res = client.delete(f"/api/import/batches/{batch1}")
        assert res.status_code == 200
        assert "deleted" in res.json()

        with get_connection() as conn:
            remaining = conn.execute(
                "SELECT COUNT(*) FROM transactions WHERE batch_id = ?", (batch2,)
            ).fetchone()[0]
        assert remaining == 3

    def test_undo_nonexistent_batch_returns_404(self):
        assert client.delete("/api/import/batches/99999").status_code == 404
