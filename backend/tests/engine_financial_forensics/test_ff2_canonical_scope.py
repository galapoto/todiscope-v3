"""
Canonical Normalization Scope Guards

Tests:
- No enrichment imports
- No accounting assumptions
- No aggregation logic
"""
import pytest
from datetime import datetime, timezone
from decimal import Decimal

from backend.app.engines.financial_forensics.normalization import (
    CanonicalCurrencyInvalidError,
    CanonicalDirectionInvalidError,
    CanonicalTypeInvalidError,
    normalize_canonical_record,
)


def test_canonical_normalization_no_enrichment() -> None:
    """Test: Normalization does not require enrichment data."""
    raw_record = {
        "source_system": "test",
        "source_record_id": "inv-001",
        "record_type": "invoice",
        "posted_at": "2024-01-15T00:00:00Z",
        "counterparty_id": "vendor-123",
        "amount_original": "1000.00",
        "currency_original": "USD",
        "direction": "debit",
    }
    
    canonical = normalize_canonical_record(
        raw_record=raw_record,
        dataset_version_id="dv-123",
        ingested_at=datetime.now(timezone.utc),
    )
    
    # Verify no enrichment fields present
    assert "vendor_name" not in canonical
    assert "contract_id" not in canonical
    assert "gl_account" not in canonical
    assert "cost_center" not in canonical


def test_canonical_normalization_no_accounting_assumptions() -> None:
    """Test: Normalization does not make accounting policy assumptions."""
    # Normalization should not compute direction from amounts
    # Direction must be explicit in raw record
    
    raw_record = {
        "source_system": "test",
        "source_record_id": "inv-001",
        "record_type": "invoice",
        "posted_at": "2024-01-15T00:00:00Z",
        "counterparty_id": "vendor-123",
        "amount_original": "1000.00",
        "currency_original": "USD",
        "direction": "debit",  # Explicit, not computed
    }
    
    canonical = normalize_canonical_record(
        raw_record=raw_record,
        dataset_version_id="dv-123",
        ingested_at=datetime.now(timezone.utc),
    )
    
    # Verify direction is normalized, not computed
    assert canonical["direction"] == "debit"
    assert canonical["amount_original"] == Decimal("1000.00")


def test_canonical_normalization_no_aggregation() -> None:
    """Test: Normalization does not perform aggregation."""
    # Normalization should process one record at a time
    # No summing, no grouping, no aggregation logic
    
    raw_record = {
        "source_system": "test",
        "source_record_id": "inv-001",
        "record_type": "invoice",
        "posted_at": "2024-01-15T00:00:00Z",
        "counterparty_id": "vendor-123",
        "amount_original": "1000.00",
        "currency_original": "USD",
        "direction": "debit",
    }
    
    canonical = normalize_canonical_record(
        raw_record=raw_record,
        dataset_version_id="dv-123",
        ingested_at=datetime.now(timezone.utc),
    )
    
    # Verify single record output (no aggregation)
    assert isinstance(canonical, dict)
    assert "total_amount" not in canonical
    assert "record_count" not in canonical
    assert "aggregated" not in canonical


def test_canonical_invalid_type_hard_fails() -> None:
    """Test: Invalid record_type raises explicit error."""
    raw_record = {
        "source_system": "test",
        "source_record_id": "inv-001",
        "record_type": "invalid_type",  # Invalid
        "posted_at": "2024-01-15T00:00:00Z",
        "counterparty_id": "vendor-123",
        "amount_original": "1000.00",
        "currency_original": "USD",
        "direction": "debit",
    }
    
    with pytest.raises(CanonicalTypeInvalidError):
        normalize_canonical_record(
            raw_record=raw_record,
            dataset_version_id="dv-123",
            ingested_at=datetime.now(timezone.utc),
        )


def test_canonical_invalid_currency_hard_fails() -> None:
    """Test: Invalid currency raises explicit error."""
    raw_record = {
        "source_system": "test",
        "source_record_id": "inv-001",
        "record_type": "invoice",
        "posted_at": "2024-01-15T00:00:00Z",
        "counterparty_id": "vendor-123",
        "amount_original": "1000.00",
        "currency_original": "INVALID",  # Invalid currency
        "direction": "debit",
    }
    
    with pytest.raises(CanonicalCurrencyInvalidError):
        normalize_canonical_record(
            raw_record=raw_record,
            dataset_version_id="dv-123",
            ingested_at=datetime.now(timezone.utc),
        )


def test_canonical_invalid_direction_hard_fails() -> None:
    """Test: Invalid direction raises explicit error."""
    raw_record = {
        "source_system": "test",
        "source_record_id": "inv-001",
        "record_type": "invoice",
        "posted_at": "2024-01-15T00:00:00Z",
        "counterparty_id": "vendor-123",
        "amount_original": "1000.00",
        "currency_original": "USD",
        "direction": "invalid",  # Invalid direction
    }
    
    with pytest.raises(CanonicalDirectionInvalidError):
        normalize_canonical_record(
            raw_record=raw_record,
            dataset_version_id="dv-123",
            ingested_at=datetime.now(timezone.utc),
        )


def test_canonical_uses_decimal_not_float() -> None:
    """Test: Amount normalization uses Decimal, not float."""
    raw_record = {
        "source_system": "test",
        "source_record_id": "inv-001",
        "record_type": "invoice",
        "posted_at": "2024-01-15T00:00:00Z",
        "counterparty_id": "vendor-123",
        "amount_original": "1000.123456",  # High precision
        "currency_original": "USD",
        "direction": "debit",
    }
    
    canonical = normalize_canonical_record(
        raw_record=raw_record,
        dataset_version_id="dv-123",
        ingested_at=datetime.now(timezone.utc),
    )
    
    # Verify Decimal type (not float)
    assert isinstance(canonical["amount_original"], Decimal)
    assert canonical["amount_original"] == Decimal("1000.123456")  # Precision preserved


