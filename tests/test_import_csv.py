"""
Tests for CSV import parsing logic.
Uses the sample fixture at tests/fixtures/sample.csv.
"""
import pytest
import io
from pathlib import Path

FIXTURE_CSV = Path(__file__).parent / "fixtures" / "sample.csv"


class TestCSVParsing:
    """Placeholder — expand once server/routes/import_csv.py is implemented."""

    def test_fixture_file_exists(self):
        assert FIXTURE_CSV.exists(), "Sample fixture CSV is missing"

    def test_fixture_has_expected_columns(self):
        import csv
        with open(FIXTURE_CSV) as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
        assert "Date" in headers
        assert "Description" in headers
        assert "Amount" in headers

    def test_fixture_has_rows(self):
        import csv
        with open(FIXTURE_CSV) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) > 0
