"""
Semantic Guard Tests for FF-4

Tests ensuring no fraud/blame language, descriptive typologies, advisory exposure.
"""
from __future__ import annotations

import pytest

from backend.app.engines.financial_forensics.leakage.semantic_guards import (
    SemanticViolationError,
    validate_exposure_language,
    validate_leakage_evidence_semantics,
    validate_typology_language,
)


def test_validate_typology_language_forbidden_fraud_words() -> None:
    """Test that forbidden fraud words are detected."""
    # Test forbidden words
    forbidden_words = [
        "fraud",
        "fraudulent",
        "theft",
        "wrongdoing",
        "negligent",
        "breach",
        "illegal",
        "intent",
        "blame",
        "fault",
        "recovery",
        "damages",
    ]
    
    for word in forbidden_words:
        with pytest.raises(SemanticViolationError, match="SEMANTIC_VIOLATION_FRAUD_WORD"):
            validate_typology_language(f"leakage_{word}_type", f"Description with {word}")


def test_validate_typology_language_forbidden_decision_phrases() -> None:
    """Test that forbidden decision phrases are detected."""
    forbidden_phrases = [
        "must be paid",
        "should be collected",
        "is required",
        "is unpaid",
        "is uncollected",
        "is delinquent",
        "is overdue",
        "has been paid",
        "has not been paid",
    ]
    
    for phrase in forbidden_phrases:
        with pytest.raises(SemanticViolationError, match="SEMANTIC_VIOLATION_DECISION_PHRASE"):
            validate_typology_language("leakage_type", f"Description: {phrase}")


def test_validate_typology_language_allowed_descriptive() -> None:
    """Test that allowed descriptive phrases pass validation."""
    allowed_descriptions = [
        "unmatched under declared rules",
        "not matched under declared constraints",
        "pattern consistent with duplicate settlement",
        "signal indicating unmatched state",
        "remains unmatched",
        "no match found",
        "partial match",
        "within tolerance",
    ]
    
    for desc in allowed_descriptions:
        # Should not raise
        validate_typology_language("unmatched_payable_exposure", desc)


def test_validate_exposure_language_forbidden_words() -> None:
    """Test that exposure language with forbidden words is rejected."""
    forbidden_exposures = [
        "fraudulent exposure amount",
        "theft-related exposure",
        "wrongdoing exposure",
        "recoverable damages",
    ]
    
    for exposure in forbidden_exposures:
        with pytest.raises(SemanticViolationError, match="SEMANTIC_VIOLATION_FRAUD_WORD"):
            validate_exposure_language(exposure)


def test_validate_exposure_language_allowed_advisory() -> None:
    """Test that advisory exposure language passes validation."""
    allowed_exposures = [
        "advisory exposure estimate",
        "estimated exposure under declared constraints",
        "potential exposure based on unmatched amount",
        "exposure range according to matching rules",
        "remaining unmatched amount under declared rules",
    ]
    
    for exposure in allowed_exposures:
        # Should not raise
        validate_exposure_language(exposure)


def test_validate_leakage_evidence_semantics_complete() -> None:
    """Test that complete leakage evidence is validated for semantics."""
    valid_evidence = {
        "typology_assignment": {
            "leakage_type": "unmatched_payable_exposure",
            "assignment_rule_id": "rule_001",
            "assignment_rule_version": "v1",
            "assignment_criteria": ["no_match_found", "invoice_direction=payable"],
            "assignment_confidence": "exact",
            "direction_convention": "debit=payable",
            "direction_source": "run_parameters",
        },
        "exposure_derivation": {
            "exposure_amount": "1000.00",
            "exposure_currency": "USD",
            "exposure_basis": "remaining unmatched amount under declared constraints",
            "exposure_currency_mode": "original_only",
            "derivation_method": "direct_amount",
            "derivation_inputs": {"invoice_amount": "1000.00"},
            "derivation_confidence": "exact",
        },
        "finding_references": {
            "related_finding_ids": [],
            "finding_rule_ids": [],
            "finding_rule_versions": [],
            "finding_confidences": [],
            "finding_evidence_ids": [],
            "match_outcome": "no_match",
            "match_search_scope": {},
        },
        "primary_records": {
            "invoice_record_id": "inv_001",
            "invoice_source_system": "erp",
            "invoice_source_record_id": "erp_001",
            "counterpart_record_ids": [],
            "counterpart_source_systems": [],
            "counterpart_source_record_ids": [],
            "is_intercompany": False,
        },
    }
    
    # Should not raise
    validate_leakage_evidence_semantics(valid_evidence)


def test_validate_leakage_evidence_semantics_violation() -> None:
    """Test that evidence with forbidden language is rejected."""
    invalid_evidence = {
        "typology_assignment": {
            "leakage_type": "fraudulent_exposure",  # Forbidden word
            "assignment_rule_id": "rule_001",
            "assignment_rule_version": "v1",
            "assignment_criteria": ["fraud detected"],  # Forbidden word
            "assignment_confidence": "exact",
            "direction_convention": "debit=payable",
            "direction_source": "run_parameters",
        },
        "exposure_derivation": {
            "exposure_amount": "1000.00",
            "exposure_currency": "USD",
            "exposure_basis": "recoverable damages",  # Forbidden phrase
            "exposure_currency_mode": "original_only",
            "derivation_method": "direct_amount",
            "derivation_inputs": {},
            "derivation_confidence": "exact",
        },
        "finding_references": {
            "related_finding_ids": [],
            "finding_rule_ids": [],
            "finding_rule_versions": [],
            "finding_confidences": [],
            "finding_evidence_ids": [],
            "match_outcome": "no_match",
            "match_search_scope": {},
        },
        "primary_records": {
            "invoice_record_id": "inv_001",
            "invoice_source_system": "erp",
            "invoice_source_record_id": "erp_001",
            "counterpart_record_ids": [],
            "counterpart_source_systems": [],
            "counterpart_source_record_ids": [],
            "is_intercompany": False,
        },
    }
    
    # Should raise on typology language
    with pytest.raises(SemanticViolationError, match="SEMANTIC_VIOLATION_FRAUD_WORD"):
        validate_leakage_evidence_semantics(invalid_evidence)


