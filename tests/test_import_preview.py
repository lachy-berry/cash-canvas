"""Tests for POST /api/import/preview."""
import pytest

from tests.conftest import client, post_preview, post_confirm, SAMPLE_MAPPING


class TestPreview:
    def test_new_and_duplicate_rows_correctly_partitioned(self):
        """Core contract: first preview returns all rows as new; after confirming,
        a second preview returns them all as duplicates."""
        first = post_preview().json()
        assert len(first["new"]) == 3 and first["duplicates"] == []

        post_confirm(first["new"])
        second = post_preview().json()
        assert second["new"] == [] and len(second["duplicates"]) == 3

    def test_row_shape_with_parsed_values(self):
        """Rows must have all required fields with correct types."""
        rows = post_preview().json()["new"]
        woolworths = next(r for r in rows if "WOOLWORTHS" in r["description"])
        assert {"date", "description", "amount", "balance", "fingerprint"}.issubset(woolworths)
        assert woolworths["amount"] == pytest.approx(-82.50)
        assert woolworths["balance"] == pytest.approx(4217.50)

    def test_credit_debit_columns(self):
        """Amount can be computed as credit − debit from two columns."""
        csv_bytes = (
            b"Date,Description,Credit,Debit,Balance\n"
            b"2026-03-01,SALARY,5200.00,0.00,5200.00\n"
            b"2026-03-02,RENT,0.00,1500.00,3700.00\n"
        )
        mapping = {
            "date_col": "Date", "desc_col": "Description",
            "credit_col": "Credit", "debit_col": "Debit", "balance_col": "Balance",
        }
        rows = post_preview(csv_bytes, mapping).json()["new"]
        assert next(r for r in rows if "SALARY" in r["description"])["amount"] == pytest.approx(5200.00)
        assert next(r for r in rows if "RENT" in r["description"])["amount"] == pytest.approx(-1500.00)

    def test_balance_col_is_optional(self):
        mapping = {k: v for k, v in SAMPLE_MAPPING.items() if k != "balance_col"}
        assert post_preview(mapping=mapping).status_code == 200

    @pytest.mark.parametrize("csv_bytes,mapping", [
        (b"", SAMPLE_MAPPING),  # empty file
        (b"Date,Description,Amount\n2026-01-01,X,1.00",
         {**SAMPLE_MAPPING, "date_col": "NoSuchCol"}),  # bad column name
    ])
    def test_invalid_input_returns_422(self, csv_bytes, mapping):
        assert post_preview(csv_bytes, mapping).status_code == 422
