"""Transaction list and label endpoints."""
import sqlite3
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from server.categories import validate_category
from server.db import get_connection

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_labels_for_transactions(
    conn: sqlite3.Connection, tx_ids: list[int]
) -> dict[int, dict[str, str]]:
    """Return a mapping of transaction_id → {layer_id: category_id} for the given ids.

    Issues a single query regardless of page size. Returns an empty dict for
    transactions that have no labels.
    """
    if not tx_ids:
        return {}
    placeholders = ",".join("?" * len(tx_ids))
    rows = conn.execute(
        f"SELECT transaction_id, layer_id, category_id "
        f"FROM transaction_labels WHERE transaction_id IN ({placeholders})",
        tx_ids,
    ).fetchall()
    result: dict[int, dict[str, str]] = {}
    for row in rows:
        result.setdefault(row["transaction_id"], {})[row["layer_id"]] = row["category_id"]
    return result


# ---------------------------------------------------------------------------
# GET /api/transactions
# ---------------------------------------------------------------------------

@router.get("/api/transactions")
def list_transactions(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> dict:
    """Return a paginated list of transactions ordered by date descending.

    Each transaction includes a ``labels`` dict keyed by layer_id, e.g.
    ``{"broad": "groceries"}``. Empty dict if no labels assigned.
    """
    with get_connection() as conn:
        total = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        rows = conn.execute(
            """
            SELECT id, date, description, amount, balance
            FROM transactions
            ORDER BY date DESC, id DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()

        tx_ids = [r["id"] for r in rows]
        labels_by_tx = _load_labels_for_transactions(conn, tx_ids)

    transactions = [
        {**dict(row), "labels": labels_by_tx.get(row["id"], {})}
        for row in rows
    ]
    return {"transactions": transactions, "total": total}


# ---------------------------------------------------------------------------
# PATCH /api/transactions/{id}/labels
# ---------------------------------------------------------------------------

class LabelRequest(BaseModel):
    layer: str
    category: Optional[str]  # None means clear the label


@router.patch("/api/transactions/{tx_id}/labels")
def set_label(tx_id: int, body: LabelRequest) -> dict:
    """Assign or clear a category label for a single transaction.

    - ``category`` set to a valid category_id: upserts the label.
    - ``category`` set to ``null``: removes the label (idempotent).

    Returns 404 if the transaction doesn't exist.
    Returns 422 if the layer or category is not in categories.yaml.
    """
    validate_category(body.layer, body.category)

    with get_connection() as conn:
        if not conn.execute(
            "SELECT 1 FROM transactions WHERE id=?", (tx_id,)
        ).fetchone():
            raise HTTPException(status_code=404, detail=f"Transaction {tx_id} not found.")

        if body.category is None:
            conn.execute(
                "DELETE FROM transaction_labels WHERE transaction_id=? AND layer_id=?",
                (tx_id, body.layer),
            )
        else:
            conn.execute(
                """
                INSERT INTO transaction_labels (transaction_id, layer_id, category_id)
                VALUES (?, ?, ?)
                ON CONFLICT(transaction_id, layer_id) DO UPDATE SET category_id=excluded.category_id
                """,
                (tx_id, body.layer, body.category),
            )

        conn.commit()

    return {"ok": True}
