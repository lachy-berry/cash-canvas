"""Transaction list endpoint."""
from fastapi import APIRouter, Query

from server.db import get_connection

router = APIRouter()


@router.get("/api/transactions")
def list_transactions(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> dict:
    """Return a paginated list of transactions ordered by date descending."""
    with get_connection() as conn:
        total = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        rows = conn.execute(
            """
            SELECT id, date, description, amount, balance, label_broad
            FROM transactions
            ORDER BY date DESC, id DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()

    transactions = [dict(row) for row in rows]
    return {"transactions": transactions, "total": total}
