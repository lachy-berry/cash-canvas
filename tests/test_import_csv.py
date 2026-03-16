"""
Tests for the CSV import endpoints:
  POST /api/import/preview
  POST /api/import/confirm
  DELETE /api/import/batches/{batch_id}
  GET /api/transactions
"""
import io
import pytest
from fastapi.testclient import TestClient

from server.main import app
from server.db import get_connection, init_db

# Ensure schema is created before any test fixture runs
init_db()

client = TestClient(app)

# ---------------------------------------------------------------------------
# Shared fixtures / helpers
# ---------------------------------------------------------------------------

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


def post_confirm(rows: list):
    return client.post("/api/import/confirm", json={"rows": rows})


@pytest.fixture(autouse=True)
def clean_db():
    """Wipe transactions and import_batches before and after each test."""
    with get_connection() as conn:
        conn.execute("DELETE FROM transactions")
        conn.execute("DELETE FROM import_batches")
        conn.commit()
    yield
    with get_connection() as conn:
        conn.execute("DELETE FROM transactions")
        conn.execute("DELETE FROM import_batches")
        conn.commit()


# ---------------------------------------------------------------------------
# POST /api/import/preview
# ---------------------------------------------------------------------------

class TestImportPreview:
    def test_returns_200_on_valid_csv(self):
        res = post_preview()
        assert res.status_code == 200

    def test_response_has_new_and_duplicates_keys(self):
        data = post_preview().json()
        assert "new" in data
        assert "duplicates" in data

    def test_new_rows_count_matches_csv(self):
        data = post_preview().json()
        assert len(data["new"]) == 3

    def test_no_duplicates_on_first_preview(self):
        data = post_preview().json()
        assert data["duplicates"] == []

    def test_row_shape_has_required_fields(self):
        row = post_preview().json()["new"][0]
        for field in ("date", "description", "amount", "balance", "fingerprint"):
            assert field in row, f"Missing field: {field}"

    def test_amount_parsed_as_float(self):
        rows = post_preview().json()["new"]
        woolworths = next(r for r in rows if "WOOLWORTHS" in r["description"])
        assert woolworths["amount"] == pytest.approx(-82.50)

    def test_balance_parsed_as_float(self):
        rows = post_preview().json()["new"]
        woolworths = next(r for r in rows if "WOOLWORTHS" in r["description"])
        assert woolworths["balance"] == pytest.approx(4217.50)

    def test_second_preview_after_confirm_returns_all_as_duplicates(self):
        rows = post_preview().json()["new"]
        post_confirm(rows)

        data = post_preview().json()
        assert len(data["duplicates"]) == 3
        assert data["new"] == []

    def test_credit_debit_columns_combined(self):
        csv_bytes = (
            b"Date,Description,Credit,Debit,Balance\n"
            b"2026-03-01,SALARY,5200.00,0.00,5200.00\n"
            b"2026-03-02,RENT,0.00,1500.00,3700.00\n"
        )
        mapping = {
            "date_col": "Date",
            "desc_col": "Description",
            "credit_col": "Credit",
            "debit_col": "Debit",
            "balance_col": "Balance",
        }
        res = post_preview(csv_bytes, mapping)
        assert res.status_code == 200
        rows = res.json()["new"]
        salary = next(r for r in rows if "SALARY" in r["description"])
        rent = next(r for r in rows if "RENT" in r["description"])
        assert salary["amount"] == pytest.approx(5200.00)
        assert rent["amount"] == pytest.approx(-1500.00)

    def test_missing_required_column_mapping_returns_422(self):
        # Send a mapping that points to a column that doesn't exist in the CSV
        bad_mapping = {
            "date_col": "NonExistentDate",
            "desc_col": "Description",
            "amount_col": "Amount",
        }
        res = post_preview(SAMPLE_CSV, bad_mapping)
        assert res.status_code == 422

    def test_empty_file_returns_422(self):
        res = post_preview(b"")
        assert res.status_code == 422

    def test_balance_col_is_optional(self):
        mapping = {
            "date_col": "Date",
            "desc_col": "Description",
            "amount_col": "Amount",
        }
        res = post_preview(SAMPLE_CSV, mapping)
        assert res.status_code == 200
        assert len(res.json()["new"]) == 3


# ---------------------------------------------------------------------------
# POST /api/import/confirm
# ---------------------------------------------------------------------------

class TestImportConfirm:
    def test_returns_200(self):
        rows = post_preview().json()["new"]
        res = post_confirm(rows)
        assert res.status_code == 200

    def test_response_has_batch_id_imported_skipped(self):
        rows = post_preview().json()["new"]
        data = post_confirm(rows).json()
        assert "batch_id" in data
        assert "imported" in data
        assert "skipped" in data

    def test_imported_count_matches_rows(self):
        rows = post_preview().json()["new"]
        data = post_confirm(rows).json()
        assert data["imported"] == 3
        assert data["skipped"] == 0

    def test_rows_persisted_to_db(self):
        rows = post_preview().json()["new"]
        post_confirm(rows)
        with get_connection() as conn:
            count = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        assert count == 3

    def test_transaction_fields_correct(self):
        rows = post_preview().json()["new"]
        post_confirm(rows)
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM transactions WHERE description LIKE '%WOOLWORTHS%'"
            ).fetchone()
        assert row["date"] == "2026-03-01"
        assert row["amount"] == pytest.approx(-82.50)
        assert row["balance"] == pytest.approx(4217.50)

    def test_label_broad_is_null_on_import(self):
        rows = post_preview().json()["new"]
        post_confirm(rows)
        with get_connection() as conn:
            labels = conn.execute("SELECT label_broad FROM transactions").fetchall()
        assert all(r["label_broad"] is None for r in labels)

    def test_batch_id_set_on_all_rows(self):
        rows = post_preview().json()["new"]
        data = post_confirm(rows).json()
        batch_id = data["batch_id"]
        with get_connection() as conn:
            txns = conn.execute("SELECT batch_id FROM transactions").fetchall()
        assert all(r["batch_id"] == batch_id for r in txns)

    def test_fingerprint_stored_on_rows(self):
        rows = post_preview().json()["new"]
        post_confirm(rows)
        with get_connection() as conn:
            txns = conn.execute("SELECT fingerprint FROM transactions").fetchall()
        assert all(r["fingerprint"] is not None for r in txns)

    def test_confirming_duplicate_rows_adds_them(self):
        # Import once
        rows = post_preview().json()["new"]
        post_confirm(rows)

        # Second preview — all duplicates; confirm them anyway
        dups = post_preview().json()["duplicates"]
        post_confirm(dups)

        with get_connection() as conn:
            count = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        assert count == 6

    def test_empty_rows_returns_422(self):
        res = post_confirm([])
        assert res.status_code == 422


# ---------------------------------------------------------------------------
# DELETE /api/import/batches/{batch_id}
# ---------------------------------------------------------------------------

class TestUndoImport:
    def test_undo_removes_transactions(self):
        rows = post_preview().json()["new"]
        batch_id = post_confirm(rows).json()["batch_id"]

        res = client.delete(f"/api/import/batches/{batch_id}")
        assert res.status_code == 200

        with get_connection() as conn:
            count = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        assert count == 0

    def test_undo_removes_only_target_batch(self):
        # First import
        rows1 = post_preview().json()["new"]
        batch1 = post_confirm(rows1).json()["batch_id"]

        # Second import (confirm the duplicates to create a second batch)
        dups = post_preview().json()["duplicates"]
        batch2 = post_confirm(dups).json()["batch_id"]

        # Undo only batch 1
        client.delete(f"/api/import/batches/{batch1}")

        with get_connection() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM transactions WHERE batch_id = ?", (batch2,)
            ).fetchone()[0]
        assert count == 3

    def test_undo_nonexistent_batch_returns_404(self):
        res = client.delete("/api/import/batches/99999")
        assert res.status_code == 404

    def test_undo_response_has_deleted_count(self):
        rows = post_preview().json()["new"]
        batch_id = post_confirm(rows).json()["batch_id"]
        res = client.delete(f"/api/import/batches/{batch_id}")
        assert "deleted" in res.json()


# ---------------------------------------------------------------------------
# GET /api/transactions
# ---------------------------------------------------------------------------

class TestListTransactions:
    def _import(self):
        rows = post_preview().json()["new"]
        post_confirm(rows)

    def test_returns_200(self):
        assert client.get("/api/transactions").status_code == 200

    def test_response_shape(self):
        data = client.get("/api/transactions").json()
        assert "transactions" in data
        assert "total" in data

    def test_empty_before_import(self):
        data = client.get("/api/transactions").json()
        assert data["transactions"] == []
        assert data["total"] == 0

    def test_total_matches_imported_count(self):
        self._import()
        assert client.get("/api/transactions").json()["total"] == 3

    def test_transaction_shape(self):
        self._import()
        tx = client.get("/api/transactions").json()["transactions"][0]
        for field in ("id", "date", "description", "amount", "balance", "label_broad"):
            assert field in tx

    def test_ordered_by_date_desc(self):
        self._import()
        txns = client.get("/api/transactions").json()["transactions"]
        dates = [t["date"] for t in txns]
        assert dates == sorted(dates, reverse=True)

    def test_pagination_limit(self):
        self._import()
        data = client.get("/api/transactions?limit=2&offset=0").json()
        assert len(data["transactions"]) == 2

    def test_pagination_offset(self):
        self._import()
        data = client.get("/api/transactions?limit=2&offset=2").json()
        assert len(data["transactions"]) == 1

    def test_total_unaffected_by_pagination(self):
        self._import()
        data = client.get("/api/transactions?limit=1&offset=0").json()
        assert data["total"] == 3
