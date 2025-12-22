"""Tests for claims management structure."""

from datetime import datetime, timezone
import pytest

from backend.app.engines.enterprise_insurance_claim_forensics.claims_management import (
    ClaimRecord,
    ClaimTransaction,
    parse_claim_from_payload,
)


def test_claim_record_creation() -> None:
    """Test creating a valid claim record."""
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
        description="Property damage claim",
    )
    assert claim.claim_id == "claim-123"
    assert claim.claim_amount == 10000.0
    assert claim.currency == "USD"


def test_claim_record_validation_fails_missing_claim_id() -> None:
    """Test that claim record validation fails for missing claim_id."""
    with pytest.raises(ValueError, match="CLAIM_ID_REQUIRED"):
        ClaimRecord(
            claim_id="",
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


def test_claim_record_validation_fails_invalid_amount() -> None:
    """Test that claim record validation fails for negative amount."""
    with pytest.raises(ValueError, match="CLAIM_AMOUNT_INVALID"):
        ClaimRecord(
            claim_id="claim-123",
            dataset_version_id="dv-123",
            policy_number="POL-001",
            claim_number="CLM-001",
            claim_type="property",
            claim_status="open",
            reported_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            incident_date=None,
            claim_amount=-100.0,
            currency="USD",
            claimant_name="John Doe",
            claimant_type="individual",
            description="Test",
        )


def test_transaction_creation() -> None:
    """Test creating a valid transaction."""
    transaction = ClaimTransaction(
        transaction_id="tx-123",
        claim_id="claim-123",
        dataset_version_id="dv-123",
        transaction_type="payment",
        transaction_date=datetime(2024, 1, 15, tzinfo=timezone.utc),
        amount=5000.0,
        currency="USD",
        description="Initial payment",
    )
    assert transaction.transaction_id == "tx-123"
    assert transaction.amount == 5000.0


def test_parse_claim_from_payload() -> None:
    """Test parsing claim from payload."""
    payload = {
        "insurance_claim": {
            "claim_id": "claim-123",
            "policy_number": "POL-001",
            "claim_number": "CLM-001",
            "claim_type": "property",
            "claim_status": "open",
            "reported_date": "2024-01-01T00:00:00Z",
            "incident_date": "2023-12-15T00:00:00Z",
            "claim_amount": 10000.0,
            "currency": "USD",
            "claimant_name": "John Doe",
            "claimant_type": "individual",
            "description": "Property damage",
        }
    }
    claim = parse_claim_from_payload(payload, "dv-123")
    assert claim.claim_id == "claim-123"
    assert claim.policy_number == "POL-001"
    assert claim.claim_amount == 10000.0


def test_parse_claim_from_payload_missing_required_field() -> None:
    """Test that parsing fails when required fields are missing."""
    payload = {
        "insurance_claim": {
            "claim_id": "claim-123",
            # Missing policy_number
        }
    }
    with pytest.raises(ValueError, match="POLICY_NUMBER_MISSING_IN_PAYLOAD"):
        parse_claim_from_payload(payload, "dv-123")


