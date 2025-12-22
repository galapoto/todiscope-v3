"""
FF-3 Evidence Completeness Tests

Tests:
- rule_id/version required
- tolerance required when used
- comparison details required
- primary evidence links required
"""
import pytest
from decimal import Decimal

from backend.app.engines.financial_forensics.finding import (
    ComparisonDetailsMissingError,
    FindingDetails,
    PrimaryEvidenceMissingError,
    RuleIdentifierMissingError,
    ToleranceMissingError,
    validate_finding_completeness,
)


def test_rule_id_required() -> None:
    """Test: rule_id is required."""
    with pytest.raises(RuleIdentifierMissingError, match="RULE_ID_MISSING"):
        validate_finding_completeness(
            rule_id=None,
            rule_version="v1",
            framework_version="v1",
            confidence="exact",
            finding_type="match.invoice_payment",
            primary_evidence_item_id="ev-1",
            details={},
        )


def test_rule_version_required() -> None:
    """Test: rule_version is required."""
    with pytest.raises(RuleIdentifierMissingError, match="RULE_VERSION_MISSING"):
        validate_finding_completeness(
            rule_id="rule-1",
            rule_version=None,
            framework_version="v1",
            confidence="exact",
            finding_type="match.invoice_payment",
            primary_evidence_item_id="ev-1",
            details={},
        )


def test_framework_version_required() -> None:
    """Test: framework_version is required."""
    with pytest.raises(RuleIdentifierMissingError, match="FRAMEWORK_VERSION_MISSING"):
        validate_finding_completeness(
            rule_id="rule-1",
            rule_version="v1",
            framework_version=None,
            confidence="exact",
            finding_type="match.invoice_payment",
            primary_evidence_item_id="ev-1",
            details={},
        )


def test_primary_evidence_required() -> None:
    """Test: primary_evidence_item_id is required."""
    with pytest.raises(PrimaryEvidenceMissingError, match="PRIMARY_EVIDENCE_MISSING"):
        validate_finding_completeness(
            rule_id="rule-1",
            rule_version="v1",
            framework_version="v1",
            confidence="exact",
            finding_type="match.invoice_payment",
            primary_evidence_item_id=None,
            details={},
        )


def test_details_required() -> None:
    """Test: details payload is required."""
    with pytest.raises(ComparisonDetailsMissingError, match="DETAILS_MISSING"):
        validate_finding_completeness(
            rule_id="rule-1",
            rule_version="v1",
            framework_version="v1",
            confidence="exact",
            finding_type="match.invoice_payment",
            primary_evidence_item_id="ev-1",
            details=None,
        )


def test_details_fields_required() -> None:
    """Test: All required details fields must be present."""
    incomplete_details = {
        "left_record_id": "inv-1",
        # Missing other required fields
    }
    
    with pytest.raises(ComparisonDetailsMissingError, match="DETAILS_FIELD_MISSING"):
        validate_finding_completeness(
            rule_id="rule-1",
            rule_version="v1",
            framework_version="v1",
            confidence="exact",
            finding_type="match.invoice_payment",
            primary_evidence_item_id="ev-1",
            details=incomplete_details,
        )


def test_tolerance_required_when_used() -> None:
    """Test: Tolerance fields required when tolerance_required=True."""
    details = {
        "left_record_id": "inv-1",
        "right_record_ids": ["pay-1"],
        "comparison_currency": "USD",
        "amounts": {
            "invoice_amount_comparison": Decimal("100.00"),
            "counterpart_amounts_comparison": [Decimal("100.00")],
            "sum_counterpart_amount_comparison": Decimal("100.00"),
        },
        "diff": Decimal("0.00"),
        "tolerance": {},  # Empty tolerance
        "exposure": {"exposure_amount": Decimal("0.00")},
        "assumptions": {"currency_mode": "original_only"},
        "timestamps": {
            "invoice_posted_at": "2024-01-15T00:00:00Z",
            "counterpart_posted_at": ["2024-01-15T00:00:00Z"],
        },
    }
    
    with pytest.raises(ToleranceMissingError, match="DETAILS_TOLERANCE_FIELD_MISSING"):
        validate_finding_completeness(
            rule_id="rule-1",
            rule_version="v1",
            framework_version="v1",
            confidence="within_tolerance",
            finding_type="match.invoice_payment",
            primary_evidence_item_id="ev-1",
            details=details,
            tolerance_required=True,
        )


def test_complete_finding_passes() -> None:
    """Test: Complete finding with all required fields passes validation."""
    details = FindingDetails(
        left_record_id="inv-1",
        right_record_ids=["pay-1"],
        comparison_currency="USD",
        amounts={
            "invoice_amount_comparison": Decimal("100.00"),
            "counterpart_amounts_comparison": [Decimal("100.00")],
            "sum_counterpart_amount_comparison": Decimal("100.00"),
        },
        diff=Decimal("0.00"),
        tolerance={
            "tolerance_absolute": Decimal("0.01"),
            "tolerance_percent": Decimal("0.0"),
            "threshold_applied": Decimal("0.01"),
        },
        exposure={"exposure_amount": Decimal("0.00")},
        assumptions={"currency_mode": "original_only"},
        timestamps={
            "invoice_posted_at": "2024-01-15T00:00:00Z",
            "counterpart_posted_at": ["2024-01-15T00:00:00Z"],
        },
    )
    
    # Should not raise
    validate_finding_completeness(
        rule_id="rule-1",
        rule_version="v1",
        framework_version="v1",
        confidence="exact",
        finding_type="match.invoice_payment",
        primary_evidence_item_id="ev-1",
        details=details,
        tolerance_required=False,
    )


