"""
Tests for the PII stripping function.
server/pii_strip.py must be a pure function with no side effects.
"""
import pytest
from server.pii_strip import strip_pii


class TestCardNumbers:
    def test_strips_16_digit_card_number_with_spaces(self):
        result = strip_pii("NETFLIX.COM CARD 4512 3456 7890 1234")
        assert "[CARD]" in result
        assert "4512" not in result

    def test_strips_16_digit_card_number_no_spaces(self):
        result = strip_pii("PAYMENT REF 4512345678901234")
        assert "[CARD]" in result

    def test_strips_16_digit_card_number_with_dashes(self):
        result = strip_pii("CARD 4512-3456-7890-1234")
        assert "[CARD]" in result


class TestBSB:
    def test_strips_bsb_pattern(self):
        result = strip_pii("TRANSFER BSB 062-000")
        assert "[BSB]" in result
        assert "062-000" not in result

    def test_strips_bsb_in_longer_description(self):
        result = strip_pii("BPAY AUSGRID ELECTRICITY 062-000 12345678")
        assert "[BSB]" in result


class TestNames:
    def test_strips_name_after_transfer_to(self):
        result = strip_pii("TRANSFER TO John Smith BSB 062-123")
        assert "[NAME]" in result
        assert "John Smith" not in result


class TestPostcodes:
    def test_strips_four_digit_postcode(self):
        result = strip_pii("WOOLWORTHS SYDNEY 2000")
        assert "[POSTCODE]" in result
        assert "2000" not in result


class TestPreservation:
    def test_preserves_merchant_name(self):
        result = strip_pii("WOOLWORTHS SUPERMARKETS SYDNEY NSW")
        assert "WOOLWORTHS" in result

    def test_preserves_amount_context(self):
        result = strip_pii("EFTPOS COLES EXPRESS NEWTOWN NSW")
        assert "COLES" in result

    def test_empty_string_returns_empty(self):
        assert strip_pii("") == ""

    def test_no_pii_returns_unchanged(self):
        description = "WOOLWORTHS SUPERMARKETS"
        assert strip_pii(description) == description
