"""Shared fixtures and helpers for all pytest tests."""
import io
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from server.main import app
from server.db import get_connection, init_db

init_db()

client = TestClient(app)

_sample_lines = (Path(__file__).parent / "fixtures" / "sample.csv").read_text().splitlines()
SAMPLE_CSV = ("\n".join(_sample_lines[:4]) + "\n").encode()

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


def make_row(**overrides):
    row = {
        "date": "2026-01-01",
        "description": "TEST TXN",
        "amount": -10.0,
        "balance": None,
    }
    row.update(overrides)
    return row


def _wipe_db():
    with get_connection() as conn:
        # Feature #3 introduces transaction_labels. During the ATDD red phase,
        # this table may not exist yet — gracefully skip if so.
        try:
            conn.execute("DELETE FROM transaction_labels")
        except sqlite3.OperationalError:
            pass
        conn.execute("DELETE FROM transactions")
        conn.execute("DELETE FROM import_batches")
        conn.commit()


@pytest.fixture(autouse=True)
def clean_db():
    """Wipe all tables before and after each test."""
    _wipe_db()
    yield
    _wipe_db()
