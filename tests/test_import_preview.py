"""Tests for POST /api/import/preview."""
import pytest

from tests.conftest import client, post_preview, post_confirm, SAMPLE_CSV, SAMPLE_MAPPING


class TestPreviewBasic:
    def test_returns_200_with_new_and_duplicates_keys(self):
        data = post_preview().json()
        assert "new" in data and "duplicates" in data

    def test_new_rows_count_matches_csv(self):
        assert len(post_preview().json()["new"]) == 3

    def test_no_duplicates_on_first_preview(self):
        assert post_preview().json()["duplicates"] == []

    def test_row_has_required_fields(self):
        row = post_preview().json()["new"][0]
        assert {"date", "description", "amount", "balance", "fingerprint"}.issubset(row)

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
        assert data["new"] == [] and len(data["duplicates"]) == 3

    def test_balance_col_is_optional(self):
        mapping = {k: v for k, v in SAMPLE_MAPPING.items() if k != "balance_col"}
        res = post_preview(mapping=mapping)
        assert res.status_code == 200 and len(res.json()["new"]) == 3


class TestPreviewAmountModes:
    def test_credit_debit_columns(self):
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
        salary = next(r for r in rows if "SALARY" in r["description"])
        rent = next(r for r in rows if "RENT" in r["description"])
        assert salary["amount"] == pytest.approx(5200.00)
        assert rent["amount"] == pytest.approx(-1500.00)


@pytest.mark.parametrize("bad_mapping,expected_status", [
    (
        {"date_col": "NoSuchCol", "desc_col": "Description", "amount_col": "Amount"},
        422,
    ),
    (
        {},  # missing required form fields → FastAPI 422
        422,
    ),
])
def test_invalid_mapping_returns_422(bad_mapping, expected_status):
    res = post_preview(mapping=bad_mapping) if bad_mapping else client.post(
        "/api/import/preview", data={}, files={"file": ("f.csv", b"Date\n2026", "text/csv")}
    )
    assert res.status_code == expected_status


def test_empty_file_returns_422():
    assert post_preview(csv_bytes=b"").status_code == 422
