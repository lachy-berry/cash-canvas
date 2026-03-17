"""Routes for CSV import: preview, confirm, and undo (batch delete)."""
import csv
import hashlib
import io
from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, UploadFile, File
from pydantic import BaseModel

from server.db import get_connection

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_csv(content: bytes) -> tuple[list[str], list[dict]]:
    """Decode CSV bytes and return (fieldnames, rows_as_dicts).

    Raises HTTPException 422 on empty file or parse failure.
    """
    if not content:
        raise HTTPException(status_code=422, detail="Uploaded file is empty.")
    try:
        text = content.decode("utf-8-sig")  # strip BOM if present
    except UnicodeDecodeError:
        raise HTTPException(status_code=422, detail="File must be UTF-8 encoded.")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(status_code=422, detail="CSV has no headers.")
    return list(reader.fieldnames), list(reader)


def _resolve_column(row: dict, col_name: str | None, label: str) -> str | None:
    """Return the value for col_name from row, or None if col_name is falsy."""
    if not col_name:
        return None
    if col_name not in row:
        raise HTTPException(
            status_code=422,
            detail=f"Column '{col_name}' not found in CSV (expected for {label}).",
        )
    return row[col_name].strip()


def _compute_fingerprint(date: str, description: str, amount: float, balance: float | None) -> str:
    """Produce a stable SHA-256 fingerprint for a transaction row."""
    parts = [date, description, str(amount)]
    if balance is not None:
        parts.append(str(balance))
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode()).hexdigest()


def _existing_fingerprints() -> set[str]:
    """Return the set of all fingerprints already in the transactions table."""
    with get_connection() as conn:
        rows = conn.execute("SELECT fingerprint FROM transactions WHERE fingerprint IS NOT NULL").fetchall()
    return {r["fingerprint"] for r in rows}


def _build_row(
    csv_row: dict,
    date_col: str,
    desc_col: str,
    amount_col: str | None,
    credit_col: str | None,
    debit_col: str | None,
    balance_col: str | None,
) -> dict | None:
    """Parse a single CSV row into a transaction dict, or return None to skip."""
    date = _resolve_column(csv_row, date_col, "date")
    description = _resolve_column(csv_row, desc_col, "description")
    if not date or not description:
        return None

    # Amount: single column or credit−debit
    if amount_col:
        raw = _resolve_column(csv_row, amount_col, "amount") or ""
        try:
            amount = float(raw.replace(",", ""))
        except ValueError:
            return None  # skip malformed rows
    elif credit_col and debit_col:
        raw_credit = _resolve_column(csv_row, credit_col, "credit") or "0"
        raw_debit = _resolve_column(csv_row, debit_col, "debit") or "0"
        try:
            amount = float(raw_credit.replace(",", "")) - float(raw_debit.replace(",", ""))
        except ValueError:
            return None
    else:
        return None  # no amount column configured

    balance = None
    if balance_col:
        raw_balance = _resolve_column(csv_row, balance_col, "balance") or ""
        try:
            balance = float(raw_balance.replace(",", ""))
        except ValueError:
            pass

    fingerprint = _compute_fingerprint(date, description, amount, balance)
    return {
        "date": date,
        "description": description,
        "amount": amount,
        "balance": balance,
        "fingerprint": fingerprint,
    }


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
    fieldnames, csv_rows = _parse_csv(content)

    # Validate that the mapped columns actually exist in the CSV
    for col_name, label in [
        (date_col, "date_col"),
        (desc_col, "desc_col"),
        (amount_col, "amount_col") if amount_col else (None, None),
        (credit_col, "credit_col") if credit_col else (None, None),
        (debit_col, "debit_col") if debit_col else (None, None),
        (balance_col, "balance_col") if balance_col else (None, None),
    ]:
        if col_name and col_name not in fieldnames:
            raise HTTPException(
                status_code=422,
                detail=f"Column '{col_name}' (mapped as {label}) not found in CSV headers.",
            )

    existing = _existing_fingerprints()

    new_rows = []
    duplicate_rows = []

    for csv_row in csv_rows:
        row = _build_row(csv_row, date_col, desc_col, amount_col, credit_col, debit_col, balance_col)
        if row is None:
            continue
        if row["fingerprint"] in existing:
            duplicate_rows.append(row)
        else:
            new_rows.append(row)

    return {"new": new_rows, "duplicates": duplicate_rows}


# ---------------------------------------------------------------------------
# POST /api/import/confirm
# ---------------------------------------------------------------------------

class TransactionRow(BaseModel):
    date: str
    description: str
    amount: float
    balance: float | None = None


class ConfirmRequest(BaseModel):
    rows: list[TransactionRow]
    skipped: int = 0  # number of detected duplicates the user chose not to include


@router.post("/api/import/confirm")
def confirm_import(body: ConfirmRequest) -> dict:
    """Write approved rows to the database as a new import batch.

    Fingerprints are recomputed server-side from canonical field values —
    client-supplied fingerprints are ignored.

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

        params = [
            {
                "date": row.date,
                "description": row.description,
                "amount": row.amount,
                "balance": row.balance,
                "fingerprint": _compute_fingerprint(row.date, row.description, row.amount, row.balance),
                "batch_id": batch_id,
            }
            for row in body.rows
        ]
        conn.executemany(
            """
            INSERT INTO transactions (date, description, amount, balance, fingerprint, batch_id)
            VALUES (:date, :description, :amount, :balance, :fingerprint, :batch_id)
            """,
            params,
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

        cur = conn.execute(
            "DELETE FROM transactions WHERE batch_id = ?", (batch_id,)
        )
        deleted = cur.rowcount
        conn.execute("DELETE FROM import_batches WHERE id = ?", (batch_id,))
        conn.commit()

    return {"deleted": deleted, "batch_id": batch_id}
