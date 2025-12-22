"""
Tests Ensuring Every Finding Produces Exactly One Category

Tests that fail if:
- A finding produces zero categories
- A finding produces more than one category
"""
from __future__ import annotations

import pytest

from backend.app.engines.financial_forensics.leakage.classifier import (
    ClassificationError,
    classify_finding,
)
from backend.app.engines.financial_forensics.leakage.typology import LeakageTypology


def test_finding_produces_exactly_one_category_not_zero() -> None:
    """
    Test that fails if a finding produces zero categories.
    
    Every finding must map to exactly one typology.
    """
    # Valid finding with all required fields should produce exactly one category
    finding = {
        "finding_type": "exact_match",
        "confidence": "exact",
    }
    evidence_payload = {
        "amount_comparison": {
            "diff_converted": "100.00",
        },
        "date_comparison": {
            "invoice_posted_at": "2024-01-01T00:00:00Z",
            "counterpart_posted_at": ["2024-01-05T00:00:00Z"],
            "date_diffs_days": [4],
        },
    }
    
    result = classify_finding(
        finding=finding,
        evidence_payload=evidence_payload,
        timing_inconsistency_days_threshold=30,
    )
    
    # Must produce exactly one category (not zero)
    assert result is not None, "Finding produced zero categories (result is None)"
    assert result.typology is not None, "Finding produced zero categories (typology is None)"
    assert isinstance(result.typology, LeakageTypology), "Finding produced invalid typology type"
    assert result.rationale, "Finding produced zero categories (rationale is missing)"


def test_finding_produces_exactly_one_category_not_more_than_one() -> None:
    """
    Test that fails if a finding produces more than one category.
    
    Every finding must map to exactly one typology, not multiple.
    """
    # Test that classification returns a single result, not a list or multiple results
    finding = {
        "finding_type": "partial_match",
        "confidence": "partial",
    }
    evidence_payload = {
        "amount_comparison": {
            "diff_converted": "100.00",
        },
    }
    
    result = classify_finding(finding=finding, evidence_payload=evidence_payload)
    
    # Must produce exactly one category (not a list, not multiple)
    assert not isinstance(result, list), "Finding produced multiple categories (result is a list)"
    assert result.typology is not None, "Finding produced zero categories"
    assert isinstance(result.typology, LeakageTypology), "Finding produced invalid typology type"
    
    # Verify it's a single typology value, not a set or tuple
    assert not isinstance(result.typology, (set, tuple)), "Finding produced multiple categories (typology is collection)"


def test_finding_with_missing_fields_produces_error_not_zero_categories() -> None:
    """
    Test that findings with missing required fields raise ClassificationError,
    not silently produce zero categories.
    """
    # Missing finding_type should raise error, not produce zero categories
    finding = {
        "confidence": "exact",
    }
    evidence_payload = {
        "amount_comparison": {
            "diff_converted": "100.00",
        },
    }
    
    with pytest.raises(ClassificationError, match="finding_type is required"):
        classify_finding(finding=finding, evidence_payload=evidence_payload)
    
    # Missing diff_converted should raise error, not produce zero categories
    finding = {
        "finding_type": "exact_match",
        "confidence": "exact",
    }
    evidence_payload = {
        "amount_comparison": {},
    }
    
    with pytest.raises(ClassificationError, match="diff_converted missing"):
        classify_finding(finding=finding, evidence_payload=evidence_payload)


def test_all_finding_types_produce_exactly_one_category() -> None:
    """
    Test that all finding types produce exactly one category.
    """
    finding_types = ["exact_match", "tolerance_match", "partial_match"]
    
    for finding_type in finding_types:
        finding = {
            "finding_type": finding_type,
            "confidence": "exact" if finding_type != "partial_match" else "partial",
        }
        evidence_payload = {
            "amount_comparison": {
                "diff_converted": "100.00" if finding_type != "partial_match" else "50.00",
            },
            "date_comparison": {
                "invoice_posted_at": "2024-01-01T00:00:00Z",
                "counterpart_posted_at": ["2024-01-05T00:00:00Z"],
                "date_diffs_days": [4],
            },
        }
        
        result = classify_finding(
            finding=finding,
            evidence_payload=evidence_payload,
            timing_inconsistency_days_threshold=30,
        )
        
        # Must produce exactly one category
        assert result is not None, f"Finding type {finding_type} produced zero categories"
        assert result.typology is not None, f"Finding type {finding_type} produced zero categories"
        assert isinstance(result.typology, LeakageTypology), f"Finding type {finding_type} produced invalid typology"
        assert result.rationale, f"Finding type {finding_type} produced zero categories (rationale missing)"


def test_classification_rules_are_explicit_and_ordered() -> None:
    """
    Test that classification rules are explicit and ordered (no ambiguity).
    
    Rules should be applied in order:
    1. Partial match → partial_settlement_residual
    2. Timing mismatch (if threshold provided and exceeded)
    3. Amount-based classification (overpayment/underpayment)
    Note: Balanced matches (diff == 0) raise ClassificationError as they are not leakage
    """
    # Rule 1: Partial match should always map to partial_settlement_residual
    # (even if timing mismatch or amount difference exists)
    finding = {
        "finding_type": "partial_match",
        "confidence": "partial",
    }
    evidence_payload = {
        "amount_comparison": {
            "diff_converted": "0.00",  # Balanced match (would raise error if not partial_match)
        },
        "date_comparison": {
            "invoice_posted_at": "2024-01-01T00:00:00Z",
            "counterpart_posted_at": ["2024-02-15T00:00:00Z"],
            "date_diffs_days": [45],  # Would normally trigger timing_mismatch
        },
    }
    
    result = classify_finding(
        finding=finding,
        evidence_payload=evidence_payload,
        timing_inconsistency_days_threshold=30,
    )
    
    # Rule 1 takes priority: partial_match → partial_settlement_residual
    assert result.typology == LeakageTypology.PARTIAL_SETTLEMENT_RESIDUAL
    
    # Rule 2: Timing mismatch takes priority over amount-based classification
    finding = {
        "finding_type": "exact_match",
        "confidence": "exact",
    }
    evidence_payload = {
        "amount_comparison": {
            "diff_converted": "-50.00",  # Would normally be overpayment
        },
        "date_comparison": {
            "invoice_posted_at": "2024-01-01T00:00:00Z",
            "counterpart_posted_at": ["2024-02-15T00:00:00Z"],
            "date_diffs_days": [45],
        },
    }
    
    result = classify_finding(
        finding=finding,
        evidence_payload=evidence_payload,
        timing_inconsistency_days_threshold=30,
    )
    
    # Rule 2 takes priority: timing_mismatch over overpayment
    assert result.typology == LeakageTypology.TIMING_MISMATCH
    
    # Rule 3: Amount-based classification (when no timing mismatch)
    finding = {
        "finding_type": "exact_match",
        "confidence": "exact",
    }
    evidence_payload = {
        "amount_comparison": {
            "diff_converted": "-50.00",
        },
        "date_comparison": {
            "invoice_posted_at": "2024-01-01T00:00:00Z",
            "counterpart_posted_at": ["2024-01-05T00:00:00Z"],
            "date_diffs_days": [4],  # Below threshold
        },
    }
    
    result = classify_finding(
        finding=finding,
        evidence_payload=evidence_payload,
        timing_inconsistency_days_threshold=30,
    )
    
    # Rule 3 applies: overpayment
    assert result.typology == LeakageTypology.OVERPAYMENT

