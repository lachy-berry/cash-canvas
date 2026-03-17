"""Shared fixtures and helpers for all pytest tests."""
import io
import pytest
from fastapi.testclient import TestClient

from server.main import app
from server.db import get_connection, init_db

init_db()

client = TestClient(app)

SAMPLE_CSV = b"""Date,Description,Amount,Balance
2026-03-01,WOOLWORTHS SUPERMARKETS SYDNEY NSW,-82.50,4217.50
2026-03-02,EFTPOS COLES EXPRESS NEWTOWN NSW,-45.00,4172.50
2026-03-03,DIRECT CREDIT EMPLOYER PTY LTD SALARY,5200.00,9372.50
"""

SAMPLE_MAPPING = {
    "date_col": "Date",
    "desc_col": "Description",
    "amount_col": "Amount",
    "balance_col": "Balance",
}


def post_preview(csv_bytes: bytes = SAMPLE_CSV, mapping: dict | None = None):
    m = mapping or SAMPLE_MAPPING
    return client.post(
        "/api/import/preview",
        data=m,
        files={"file": ("bank.csv", io.BytesIO(csv_bytes), "text/csv")},
    )


def post_confirm(rows: list, skipped: int = 0):
    return client.post("/api/import/confirm", json={"rows": rows, "skipped": skipped})


def _wipe_db():
    with get_connection() as conn:
        conn.execute("DELETE FROM transactions")
        conn.execute("DELETE FROM import_batches")
        conn.commit()


@pytest.fixture(autouse=True)
def clean_db():
    """Wipe transactions and import_batches before and after each test."""
    _wipe_db()
    yield
    _wipe_db()
