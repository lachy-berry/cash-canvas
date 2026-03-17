"""Pure domain logic for CSV import — no FastAPI or HTTP concerns."""
import csv
import hashlib
import io


def parse_csv(content: bytes) -> tuple[list[str], list[dict]]:
    """Decode CSV bytes and return (fieldnames, rows_as_dicts).

    Raises ValueError on empty file or parse failure.
    """
    if not content:
        raise ValueError("Uploaded file is empty.")
    try:
        text = content.decode("utf-8-sig")  # strip BOM if present
    except UnicodeDecodeError:
        raise ValueError("File must be UTF-8 encoded.")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError("CSV has no headers.")
    return list(reader.fieldnames), list(reader)


def compute_fingerprint(date: str, description: str, amount: float, balance: float | None) -> str:
    """Produce a stable SHA-256 fingerprint for a transaction row."""
    parts = [date, description, str(amount)]
    if balance is not None:
        parts.append(str(balance))
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


def resolve_amount(
    row: dict,
    amount_col: str | None,
    credit_col: str | None,
    debit_col: str | None,
) -> float | None:
    """Return parsed amount from a single column or credit−debit pair.

    Returns None if parsing fails or no column configured.
    """
    if amount_col:
        raw = (row.get(amount_col) or "").strip()
        try:
            return float(raw.replace(",", ""))
        except ValueError:
            return None
    if credit_col and debit_col:
        raw_credit = (row.get(credit_col) or "0").strip()
        raw_debit = (row.get(debit_col) or "0").strip()
        try:
            return float(raw_credit.replace(",", "")) - float(raw_debit.replace(",", ""))
        except ValueError:
            return None
    return None


def build_row(
    csv_row: dict,
    date_col: str,
    desc_col: str,
    amount_col: str | None,
    credit_col: str | None,
    debit_col: str | None,
    balance_col: str | None,
) -> dict | None:
    """Parse a single CSV row into a transaction dict, or return None to skip."""
    date = (csv_row.get(date_col) or "").strip()
    description = (csv_row.get(desc_col) or "").strip()
    if not date or not description:
        return None

    amount = resolve_amount(csv_row, amount_col, credit_col, debit_col)
    if amount is None:
        return None

    balance = None
    if balance_col:
        raw_balance = (csv_row.get(balance_col) or "").strip()
        try:
            balance = float(raw_balance.replace(",", ""))
        except ValueError:
            pass

    fingerprint = compute_fingerprint(date, description, amount, balance)
    return {
        "date": date,
        "description": description,
        "amount": amount,
        "balance": balance,
        "fingerprint": fingerprint,
    }


def partition_rows(
    csv_rows: list[dict],
    date_col: str,
    desc_col: str,
    amount_col: str | None,
    credit_col: str | None,
    debit_col: str | None,
    balance_col: str | None,
    existing_fingerprints: set[str],
) -> tuple[list[dict], list[dict]]:
    """Split parsed CSV rows into new rows and duplicates.

    Returns (new_rows, duplicate_rows).
    """
    new_rows: list[dict] = []
    duplicate_rows: list[dict] = []

    for csv_row in csv_rows:
        row = build_row(csv_row, date_col, desc_col, amount_col, credit_col, debit_col, balance_col)
        if row is None:
            continue
        if row["fingerprint"] in existing_fingerprints:
            duplicate_rows.append(row)
        else:
            new_rows.append(row)

    return new_rows, duplicate_rows
