"""Routes for CSV import: preview, confirm, and undo (batch delete)."""
from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, UploadFile, File
from pydantic import BaseModel, Field

from server.db import get_connection
from server.import_service import (
    compute_fingerprint,
    parse_csv,
    partition_rows,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class TransactionRow(BaseModel):
    date: str
    description: str
    amount: float
    balance: float | None = None


class ConfirmRequest(BaseModel):
    rows: list[TransactionRow]
    skipped: int = Field(0, ge=0)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _existing_fingerprints() -> set[str]:
    """Return all fingerprints already stored in the transactions table."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT fingerprint FROM transactions WHERE fingerprint IS NOT NULL"
        ).fetchall()
    return {r["fingerprint"] for r in rows}


def _validate_columns(fieldnames: list[str], mapping: dict[str, str | None]) -> None:
    """Raise HTTPException 422 if any mapped column is absent from the CSV headers."""
    for col_name, label in mapping.items():
        if label and label not in fieldnames:
            raise HTTPException(
                status_code=422,
                detail=f"Column '{label}' (mapped as {col_name}) not found in CSV headers.",
            )


# ---------------------------------------------------------------------------
# POST /api/import/preview
# ---------------------------------------------------------------------------

@router.post("/api/import/preview")
async def preview_import(
    file: Annotated[UploadFile, File()],
    date_col: Annotated[str, Form()],
    desc_col: Annotated[str, Form()],
    amount_col: Annotated[str | None, Form()] = None,
    credit_col: Annotated[str | None, Form()] = None,
    debit_col: Annotated[str | None, Form()] = None,
    balance_col: Annotated[str | None, Form()] = None,
) -> dict:
    """Parse CSV using the provided column mapping.

    Returns two lists:
    - new: rows whose fingerprints are not already in the DB
    - duplicates: rows whose fingerprints already exist
    """
    if not amount_col and not (credit_col and debit_col):
        raise HTTPException(
            status_code=422,
            detail="Provide either amount_col or both credit_col and debit_col.",
        )

    content = await file.read()
    try:
        fieldnames, csv_rows = parse_csv(content)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    _validate_columns(fieldnames, {
        "date_col": date_col,
        "desc_col": desc_col,
        "amount_col": amount_col,
        "credit_col": credit_col,
        "debit_col": debit_col,
        "balance_col": balance_col,
    })

    new_rows, duplicate_rows = partition_rows(
        csv_rows, date_col, desc_col, amount_col, credit_col, debit_col,
        balance_col, _existing_fingerprints(),
    )
    return {"new": new_rows, "duplicates": duplicate_rows}


# ---------------------------------------------------------------------------
# POST /api/import/confirm
# ---------------------------------------------------------------------------

@router.post("/api/import/confirm")
def confirm_import(body: ConfirmRequest) -> dict:
    """Write approved rows to the database as a new import batch.

    Fingerprints are recomputed server-side — client-supplied fingerprints
    are ignored.

    Returns batch_id, imported count, and skipped count.
    """
    if not body.rows:
        raise HTTPException(status_code=422, detail="No rows to import.")

    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO import_batches (row_count, skipped) VALUES (?, ?)",
            (len(body.rows), body.skipped),
        )
        batch_id = cur.lastrowid

        conn.executemany(
            """
            INSERT INTO transactions (date, description, amount, balance, fingerprint, batch_id)
            VALUES (:date, :description, :amount, :balance, :fingerprint, :batch_id)
            """,
            [
                {
                    "date": row.date,
                    "description": row.description,
                    "amount": row.amount,
                    "balance": row.balance,
                    "fingerprint": compute_fingerprint(
                        row.date, row.description, row.amount, row.balance
                    ),
                    "batch_id": batch_id,
                }
                for row in body.rows
            ],
        )
        conn.commit()

    return {"batch_id": batch_id, "imported": len(body.rows), "skipped": body.skipped}


# ---------------------------------------------------------------------------
# DELETE /api/import/batches/{batch_id}
# ---------------------------------------------------------------------------

@router.delete("/api/import/batches/{batch_id}")
def undo_import(batch_id: int) -> dict:
    """Delete all transactions belonging to a batch, then delete the batch itself."""
    with get_connection() as conn:
        batch = conn.execute(
            "SELECT id FROM import_batches WHERE id = ?", (batch_id,)
        ).fetchone()
        if batch is None:
            raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found.")

        deleted = conn.execute(
            "DELETE FROM transactions WHERE batch_id = ?", (batch_id,)
        ).rowcount
        conn.execute("DELETE FROM import_batches WHERE id = ?", (batch_id,))
        conn.commit()

    return {"deleted": deleted, "batch_id": batch_id}
