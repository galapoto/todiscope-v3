"""Tests for validation rules."""

from datetime import datetime, timezone
import pytest

from backend.app.engines.enterprise_insurance_claim_forensics.claims_management import (
    ClaimRecord,
    ClaimTransaction,
)
from backend.app.engines.enterprise_insurance_claim_forensics.validation import (
    validate_claim,
    ClaimAmountConsistencyRule,
    ClaimDateConsistencyRule,
    CurrencyConsistencyRule,
)


def test_claim_amount_consistency_rule_valid() -> None:
    """Test amount consistency rule with matching amounts."""
    claim = ClaimRecord(
        claim_id="claim-123",
        dataset_version_id="dv-123",
        policy_number="POL-001",
        claim_number="CLM-001",
        claim_type="property",
        claim_status="open",
        reported_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        incident_date=None,
        claim_amount=10000.0,
        currency="USD",
        claimant_name="John Doe",
        claimant_type="individual",
        description="Test",
    )
    transactions = [
        ClaimTransaction(
            transaction_id="tx-1",
            claim_id="claim-123",
            dataset_version_id="dv-123",
            transaction_type="payment",
            transaction_date=datetime(2024, 1, 15, tzinfo=timezone.utc),
            amount=10000.0,
            currency="USD",
            description="Full payment",
        )
    ]
    rule = ClaimAmountConsistencyRule()
    result = rule.validate(claim, transactions)
    assert result["is_valid"] is True
    assert result["difference"] == 0.0


def test_claim_amount_consistency_rule_invalid() -> None:
    """Test amount consistency rule with mismatched amounts."""
    claim = ClaimRecord(
        claim_id="claim-123",
        dataset_version_id="dv-123",
        policy_number="POL-001",
        claim_number="CLM-001",
        claim_type="property",
        claim_status="open",
        reported_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        incident_date=None,
        claim_amount=10000.0,
        currency="USD",
        claimant_name="John Doe",
        claimant_type="individual",
        description="Test",
    )
    transactions = [
        ClaimTransaction(
            transaction_id="tx-1",
            claim_id="claim-123",
            dataset_version_id="dv-123",
            transaction_type="payment",
            transaction_date=datetime(2024, 1, 15, tzinfo=timezone.utc),
            amount=5000.0,
            currency="USD",
            description="Partial payment",
        )
    ]
    rule = ClaimAmountConsistencyRule()
    result = rule.validate(claim, transactions)
    assert result["is_valid"] is False
    assert result["difference"] == 5000.0


def test_claim_date_consistency_rule_valid() -> None:
    """Test date consistency rule with valid dates."""
    claim = ClaimRecord(
        claim_id="claim-123",
        dataset_version_id="dv-123",
        policy_number="POL-001",
        claim_number="CLM-001",
        claim_type="property",
        claim_status="open",
        reported_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        incident_date=datetime(2023, 12, 15, tzinfo=timezone.utc),
        claim_amount=10000.0,
        currency="USD",
        claimant_name="John Doe",
        claimant_type="individual",
        description="Test",
    )
    rule = ClaimDateConsistencyRule()
    result = rule.validate(claim, [])
    assert result["is_valid"] is True


def test_claim_date_consistency_rule_invalid() -> None:
    """Test date consistency rule with invalid dates."""
    claim = ClaimRecord(
        claim_id="claim-123",
        dataset_version_id="dv-123",
        policy_number="POL-001",
        claim_number="CLM-001",
        claim_type="property",
        claim_status="open",
        reported_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        incident_date=datetime(2024, 1, 15, tzinfo=timezone.utc),  # After reported date
        claim_amount=10000.0,
        currency="USD",
        claimant_name="John Doe",
        claimant_type="individual",
        description="Test",
    )
    rule = ClaimDateConsistencyRule()
    result = rule.validate(claim, [])
    assert result["is_valid"] is False


def test_currency_consistency_rule_valid() -> None:
    """Test currency consistency rule with matching currencies."""
    claim = ClaimRecord(
        claim_id="claim-123",
        dataset_version_id="dv-123",
        policy_number="POL-001",
        claim_number="CLM-001",
        claim_type="property",
        claim_status="open",
        reported_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        incident_date=None,
        claim_amount=10000.0,
        currency="USD",
        claimant_name="John Doe",
        claimant_type="individual",
        description="Test",
    )
    transactions = [
        ClaimTransaction(
            transaction_id="tx-1",
            claim_id="claim-123",
            dataset_version_id="dv-123",
            transaction_type="payment",
            transaction_date=datetime(2024, 1, 15, tzinfo=timezone.utc),
            amount=5000.0,
            currency="USD",
            description="Payment",
        )
    ]
    rule = CurrencyConsistencyRule()
    result = rule.validate(claim, transactions)
    assert result["is_valid"] is True


def test_currency_consistency_rule_invalid() -> None:
    """Test currency consistency rule with mismatched currencies."""
    claim = ClaimRecord(
        claim_id="claim-123",
        dataset_version_id="dv-123",
        policy_number="POL-001",
        claim_number="CLM-001",
        claim_type="property",
        claim_status="open",
        reported_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        incident_date=None,
        claim_amount=10000.0,
        currency="USD",
        claimant_name="John Doe",
        claimant_type="individual",
        description="Test",
    )
    transactions = [
        ClaimTransaction(
            transaction_id="tx-1",
            claim_id="claim-123",
            dataset_version_id="dv-123",
            transaction_type="payment",
            transaction_date=datetime(2024, 1, 15, tzinfo=timezone.utc),
            amount=5000.0,
            currency="EUR",  # Different currency
            description="Payment",
        )
    ]
    rule = CurrencyConsistencyRule()
    result = rule.validate(claim, transactions)
    assert result["is_valid"] is False
    assert len(result["mismatched_transactions"]) == 1


def test_validate_claim_comprehensive() -> None:
    """Test comprehensive claim validation."""
    claim = ClaimRecord(
        claim_id="claim-123",
        dataset_version_id="dv-123",
        policy_number="POL-001",
        claim_number="CLM-001",
        claim_type="property",
        claim_status="open",
        reported_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        incident_date=datetime(2023, 12, 15, tzinfo=timezone.utc),
        claim_amount=10000.0,
        currency="USD",
        claimant_name="John Doe",
        claimant_type="individual",
        description="Test",
    )
    transactions = [
        ClaimTransaction(
            transaction_id="tx-1",
            claim_id="claim-123",
            dataset_version_id="dv-123",
            transaction_type="payment",
            transaction_date=datetime(2024, 1, 15, tzinfo=timezone.utc),
            amount=10000.0,
            currency="USD",
            description="Full payment",
        )
    ]
    result = validate_claim(claim, transactions)
    assert "is_valid" in result
    assert "errors" in result
    assert "warnings" in result
    assert "rule_results" in result
    assert "summary" in result


