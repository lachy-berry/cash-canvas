"""Transaction list and label endpoints."""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from server.categories import load_categories
from server.db import get_connection

router = APIRouter()


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

        # Fetch all labels for the returned page in one query
        if rows:
            tx_ids = [r["id"] for r in rows]
            placeholders = ",".join("?" * len(tx_ids))
            label_rows = conn.execute(
                f"SELECT transaction_id, layer_id, category_id "
                f"FROM transaction_labels WHERE transaction_id IN ({placeholders})",
                tx_ids,
            ).fetchall()
        else:
            label_rows = []

    # Build labels dict per transaction
    labels_by_tx: dict[int, dict[str, str]] = {}
    for lr in label_rows:
        labels_by_tx.setdefault(lr["transaction_id"], {})[lr["layer_id"]] = lr["category_id"]

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
    # Validate layer and category against the YAML config
    config = load_categories()
    layers = {layer["id"]: layer for layer in config.get("layers", [])}

    if body.layer not in layers:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown layer '{body.layer}'. Valid layers: {list(layers)}",
        )

    if body.category is not None:
        valid_categories = {c["id"] for c in layers[body.layer].get("categories", [])}
        if body.category not in valid_categories:
            raise HTTPException(
                status_code=422,
                detail=f"Unknown category '{body.category}' in layer '{body.layer}'. "
                       f"Valid categories: {sorted(valid_categories)}",
            )

    with get_connection() as conn:
        # Verify the transaction exists
        exists = conn.execute(
            "SELECT 1 FROM transactions WHERE id=?", (tx_id,)
        ).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail=f"Transaction {tx_id} not found.")

        if body.category is None:
            # Clear: delete the label row if it exists
            conn.execute(
                "DELETE FROM transaction_labels WHERE transaction_id=? AND layer_id=?",
                (tx_id, body.layer),
            )
        else:
            # Upsert: INSERT OR REPLACE handles both insert and overwrite
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
