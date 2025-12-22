"""
FF-3 Evidence Completeness Enforcement

Tests that FAIL THE BUILD if evidence is incomplete.
"""
import pytest

from backend.app.engines.financial_forensics.evidence_schema_v1 import (
    AmountComparisonEvidence,
    CounterpartyEvidence,
    DateComparisonEvidence,
    EvidenceSchemaV1,
    MatchSelectionRationale,
    PrimarySourceLinks,
    ReferenceComparisonEvidence,
    RuleIdentityEvidence,
    ToleranceEvidence,
    validate_evidence_schema_v1,
)
from decimal import Decimal


def test_evidence_schema_must_be_complete() -> None:
    """
    BUILD FAILURE TEST: Evidence schema must be complete.
    
    This test will fail the build if evidence schema validation allows incomplete evidence.
    """
    from backend.app.engines.financial_forensics.evidence_schema_v1 import EvidenceSchemaViolationError
    
    # Complete evidence schema
    complete_evidence = EvidenceSchemaV1(
        rule_identity=RuleIdentityEvidence(
            rule_id="rule-1",
            rule_version="v1",
            framework_version="v1",
            executed_parameters={},
        ),
        tolerance=None,
        amount_comparison=AmountComparisonEvidence(
            invoice_amount_original=Decimal("100.00"),
            invoice_currency_original="USD",
            invoice_amount_converted=None,
            counterpart_amounts_original=[Decimal("100.00")],
            counterpart_currencies_original=["USD"],
            counterpart_amounts_converted=None,
            sum_counterpart_amount_original=Decimal("100.00"),
            sum_counterpart_amount_converted=None,
            comparison_currency="USD",
            diff_original=Decimal("0.00"),
            diff_converted=None,
        ),
        date_comparison=DateComparisonEvidence(
            invoice_posted_at="2024-01-15T00:00:00Z",
            counterpart_posted_at=["2024-01-15T00:00:00Z"],
            date_diffs_days=None,
        ),
        reference_comparison=ReferenceComparisonEvidence(
            invoice_reference_ids=["ref-1"],
            counterpart_reference_ids=[["ref-1"]],
            matched_references=[["ref-1"]],
            unmatched_references=[[]],
        ),
        counterparty=CounterpartyEvidence(
            invoice_counterparty_id="cp-1",
            counterpart_counterparty_ids=["cp-1"],
            counterparty_match=True,
            counterparty_match_logic="exact",
        ),
        match_selection=MatchSelectionRationale(
            selection_method="first_match",
            selection_criteria=["amount", "date"],
            selection_priority={"amount": 1, "date": 2},
            excluded_matches=None,
            exclusion_reasons=None,
        ),
        primary_sources=PrimarySourceLinks(
            invoice_record_id="inv-1",
            counterpart_record_ids=["pay-1"],
            source_system="test",
            source_record_ids=["inv-1", "pay-1"],
            canonical_record_ids=["inv-1", "pay-1"],
        ),
    )
    
    # Complete evidence should pass
    validate_evidence_schema_v1(complete_evidence)
    
    # Incomplete evidence should fail
    incomplete_evidence_dict = {
        "rule_identity": {
            "rule_id": "rule-1",
            # Missing rule_version, framework_version, executed_parameters
        },
    }
    
    with pytest.raises(EvidenceSchemaViolationError, match="EVIDENCE_RULE_IDENTITY_FIELD_MISSING"):
        validate_evidence_schema_v1(incomplete_evidence_dict)


def test_evidence_must_have_all_required_fields() -> None:
    """
    BUILD FAILURE TEST: Evidence must have all required fields.
    
    This test documents all required fields and ensures validation enforces them.
    """
    from backend.app.engines.financial_forensics.evidence_schema_v1 import EvidenceSchemaViolationError
    
    required_fields = [
        "rule_identity",
        "amount_comparison",
        "date_comparison",
        "reference_comparison",
        "counterparty",
        "match_selection",
        "primary_sources",
    ]
    
    # Test each required field
    for field in required_fields:
        incomplete = {f: {} for f in required_fields if f != field}
        with pytest.raises(EvidenceSchemaViolationError, match="EVIDENCE_FIELD_MISSING"):
            validate_evidence_schema_v1(incomplete)


