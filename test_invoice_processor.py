"""
Unit tests for invoice_processor.py
Run with: pytest test_invoice_processor.py -v
"""

import pytest
from invoice_processor import InvoiceSubmission, validate


def make_valid():
    return InvoiceSubmission(
        submission_id="T-001",
        vendor_name="Test Vendor GmbH",
        invoice_number="INV-0001",
        invoice_date="2024-10-01",
        amount_eur=1000.00,
        currency="EUR",
        material_description="Test materials",
        submitter_email="test@example.com",
    )


def test_valid_submission_is_approved():
    result = validate(make_valid())
    assert result.status == "approved"
    assert result.flags == []


def test_missing_vendor_name_is_rejected():
    s = make_valid()
    s.vendor_name = ""
    result = validate(s)
    assert result.status == "rejected"
    assert any("MISSING_FIELD:vendor_name" in f for f in result.flags)


def test_amount_above_threshold_is_flagged():
    s = make_valid()
    s.amount_eur = 99_000.00
    result = validate(s)
    assert result.status == "flagged"
    assert any("AMOUNT_EXCEEDS_THRESHOLD" in f for f in result.flags)


def test_future_date_is_flagged():
    s = make_valid()
    s.invoice_date = "2099-01-01"
    result = validate(s)
    assert result.status == "flagged"
    assert "INVOICE_DATE_FUTURE" in result.flags


def test_invalid_date_format_is_rejected():
    s = make_valid()
    s.invoice_date = "01/10/2024"      # wrong format
    result = validate(s)
    assert "INVOICE_DATE_INVALID_FORMAT" in result.flags


def test_unsupported_currency_is_flagged():
    s = make_valid()
    s.currency = "JPY"
    result = validate(s)
    assert result.status == "flagged"
    assert any("UNSUPPORTED_CURRENCY" in f for f in result.flags)


def test_zero_amount_is_rejected():
    s = make_valid()
    s.amount_eur = 0.0
    result = validate(s)
    assert result.status == "rejected"
    assert "AMOUNT_NEGATIVE_OR_ZERO" in result.flags


def test_processed_at_is_set():
    result = validate(make_valid())
    assert result.processed_at != ""
