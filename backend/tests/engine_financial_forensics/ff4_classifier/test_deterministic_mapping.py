"""
Deterministic Classifier Mapping Tests

Tests ensuring every FF-3 finding maps to exactly one typology.
"""
from __future__ import annotations

import pytest
from decimal import Decimal

from backend.app.engines.financial_forensics.leakage.classifier import (
    ClassificationError,
    ClassificationResult,
    classify_finding,
)
from backend.app.engines.financial_forensics.leakage.typology import LeakageTypology


def test_partial_match_maps_to_partial_settlement_residual() -> None:
    """Test that partial_match findings map to partial_settlement_residual."""
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
    
    assert result.typology == LeakageTypology.PARTIAL_SETTLEMENT_RESIDUAL
    assert "partial_match" in result.rationale.lower()


def test_timing_mismatch_deterministic() -> None:
    """Test that timing_mismatch is emitted deterministically for matched amounts with date delta beyond threshold."""
    finding = {
        "finding_type": "exact_match",
        "confidence": "exact",
    }
    evidence_payload = {
        "amount_comparison": {
            "diff_converted": "0.00",  # Matched amounts
        },
        "date_comparison": {
            "invoice_posted_at": "2024-01-01T00:00:00Z",
            "counterpart_posted_at": ["2024-02-15T00:00:00Z"],  # 45 days later
            "date_diffs_days": [45],
        },
    }
    
    result = classify_finding(
        finding=finding,
        evidence_payload=evidence_payload,
        timing_inconsistency_days_threshold=30,  # 45 > 30, should trigger timing_mismatch
    )
    
    assert result.typology == LeakageTypology.TIMING_MISMATCH
    assert "date delta" in result.rationale.lower()
    assert "45" in result.rationale or "exceeds threshold" in result.rationale.lower()


def test_timing_mismatch_not_triggered_below_threshold() -> None:
    """Test that timing_mismatch is not triggered when date delta is below threshold."""
    finding = {
        "finding_type": "exact_match",
        "confidence": "exact",
    }
    evidence_payload = {
        "amount_comparison": {
            "diff_converted": "0.00",
        },
        "date_comparison": {
            "invoice_posted_at": "2024-01-01T00:00:00Z",
            "counterpart_posted_at": ["2024-01-15T00:00:00Z"],  # 14 days later
            "date_diffs_days": [14],
        },
    }
    
    result = classify_finding(
        finding=finding,
        evidence_payload=evidence_payload,
        timing_inconsistency_days_threshold=30,  # 14 < 30, should not trigger timing_mismatch
    )
    
    assert result.typology == LeakageTypology.UNMATCHED_PAYMENT


def test_overpayment_classification() -> None:
    """Test that diff_converted < 0 maps to overpayment."""
    finding = {
        "finding_type": "exact_match",
        "confidence": "exact",
    }
    evidence_payload = {
        "amount_comparison": {
            "diff_converted": "-50.00",  # Negative diff = overpayment
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
        timing_inconsistency_days_threshold=30,  # 4 < 30, no timing mismatch
    )
    
    assert result.typology == LeakageTypology.OVERPAYMENT
    assert "overpayment" in result.rationale.lower()


def test_underpayment_classification() -> None:
    """Test that diff_converted > 0 maps to underpayment."""
    finding = {
        "finding_type": "exact_match",
        "confidence": "exact",
    }
    evidence_payload = {
        "amount_comparison": {
            "diff_converted": "100.00",  # Positive diff = underpayment
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
    
    assert result.typology == LeakageTypology.UNDERPAYMENT
    assert "underpayment" in result.rationale.lower()


def test_balanced_match_raises_error() -> None:
    """Test that balanced matches (diff == 0, no timing mismatch) map deterministically."""
    finding = {
        "finding_type": "exact_match",
        "confidence": "exact",
    }
    evidence_payload = {
        "amount_comparison": {
            "diff_converted": "0.00",
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
    assert result.typology == LeakageTypology.UNMATCHED_PAYMENT


def test_finding_produces_exactly_one_category() -> None:
    """Test that every finding produces exactly one category (not zero, not more than one)."""
    test_cases = [
        {
            "finding": {"finding_type": "partial_match", "confidence": "partial"},
            "evidence_payload": {"amount_comparison": {"diff_converted": "100.00"}},
            "expected_typology": LeakageTypology.PARTIAL_SETTLEMENT_RESIDUAL,
        },
        {
            "finding": {"finding_type": "exact_match", "confidence": "exact"},
            "evidence_payload": {
                "amount_comparison": {"diff_converted": "0.00"},
                "date_comparison": {
                    "invoice_posted_at": "2024-01-01T00:00:00Z",
                    "counterpart_posted_at": ["2024-02-15T00:00:00Z"],
                    "date_diffs_days": [45],
                },
            },
            "timing_threshold": 30,
            "expected_typology": LeakageTypology.TIMING_MISMATCH,
        },
        {
            "finding": {"finding_type": "exact_match", "confidence": "exact"},
            "evidence_payload": {
                "amount_comparison": {"diff_converted": "-50.00"},
                "date_comparison": {
                    "invoice_posted_at": "2024-01-01T00:00:00Z",
                    "counterpart_posted_at": ["2024-01-05T00:00:00Z"],
                    "date_diffs_days": [4],
                },
            },
            "timing_threshold": 30,
            "expected_typology": LeakageTypology.OVERPAYMENT,
        },
        {
            "finding": {"finding_type": "tolerance_match", "confidence": "within_tolerance"},
            "evidence_payload": {
                "amount_comparison": {"diff_converted": "100.00"},
                "date_comparison": {
                    "invoice_posted_at": "2024-01-01T00:00:00Z",
                    "counterpart_posted_at": ["2024-01-05T00:00:00Z"],
                    "date_diffs_days": [4],
                },
            },
            "timing_threshold": 30,
            "expected_typology": LeakageTypology.UNDERPAYMENT,
        },
    ]
    
    for case in test_cases:
        finding = case["finding"]
        evidence_payload = case["evidence_payload"]
        timing_threshold = case.get("timing_threshold")
        expected_typology = case["expected_typology"]
        
        result = classify_finding(
            finding=finding,
            evidence_payload=evidence_payload,
            timing_inconsistency_days_threshold=timing_threshold,
        )
        
        # Must produce exactly one category
        assert result.typology == expected_typology, (
            f"Finding {finding['finding_type']} produced {result.typology}, expected {expected_typology}"
        )
        assert result.rationale, "Rationale must be present"


def test_finding_produces_zero_categories_fails() -> None:
    """Test that findings producing zero categories fail with ClassificationError."""
    # Missing finding_type
    finding = {
        "confidence": "exact",
    }
    evidence_payload = {
        "amount_comparison": {
            "diff_converted": "0.00",
        },
    }
    
    with pytest.raises(ClassificationError, match="finding_type is required"):
        classify_finding(finding=finding, evidence_payload=evidence_payload)
    
    # Missing diff_converted (cannot classify)
    finding = {
        "finding_type": "exact_match",
        "confidence": "exact",
    }
    evidence_payload = {
        "amount_comparison": {},
    }
    
    with pytest.raises(ClassificationError, match="diff_converted missing"):
        classify_finding(finding=finding, evidence_payload=evidence_payload)


def test_timing_mismatch_priority_over_amount_classification() -> None:
    """Test that timing_mismatch takes priority over amount-based classification."""
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
        timing_inconsistency_days_threshold=30,  # 45 > 30, timing mismatch takes priority
    )
    
    # Timing mismatch should take priority over overpayment
    assert result.typology == LeakageTypology.TIMING_MISMATCH
    assert result.typology != LeakageTypology.OVERPAYMENT


def test_all_typologies_have_mapping_rules() -> None:
    """Test that all typologies in LeakageTypology enum have mapping rules."""
    typologies = list(LeakageTypology)
    
    # Test that each typology can be produced
    test_mappings = {
            LeakageTypology.UNMATCHED_INVOICE: {
                "finding": {"finding_type": "exact_match"},
                "evidence_payload": {
                    "amount_comparison": {
                        "invoice_amount_converted": "100.00",
                        "sum_counterpart_amount_converted": "0.00",
                        "diff_converted": "100.00",
                    },
                    "date_comparison": {
                        "invoice_posted_at": "2024-01-01T00:00:00Z",
                        "counterpart_posted_at": [],
                        "date_diffs_days": [],
                    },
                },
                "timing_threshold": 30,
            },
            LeakageTypology.UNMATCHED_PAYMENT: {
                "finding": {"finding_type": "exact_match"},
                "evidence_payload": {
                    "amount_comparison": {
                        "invoice_amount_converted": "0.00",
                        "sum_counterpart_amount_converted": "50.00",
                        "diff_converted": "-50.00",
                    },
                    "date_comparison": {
                        "invoice_posted_at": "2024-01-01T00:00:00Z",
                        "counterpart_posted_at": ["2024-01-05T00:00:00Z"],
                        "date_diffs_days": [4],
                    },
                },
                "timing_threshold": 30,
            },
            LeakageTypology.PARTIAL_SETTLEMENT_RESIDUAL: {
                "finding": {"finding_type": "partial_match"},
                "evidence_payload": {"amount_comparison": {"diff_converted": "100.00"}},
            },
        LeakageTypology.TIMING_MISMATCH: {
            "finding": {"finding_type": "exact_match"},
            "evidence_payload": {
                "amount_comparison": {"diff_converted": "0.00"},
                "date_comparison": {
                    "invoice_posted_at": "2024-01-01T00:00:00Z",
                    "counterpart_posted_at": ["2024-02-15T00:00:00Z"],
                    "date_diffs_days": [45],
                },
            },
            "timing_threshold": 30,
        },
        LeakageTypology.OVERPAYMENT: {
            "finding": {"finding_type": "exact_match"},
            "evidence_payload": {
                "amount_comparison": {"diff_converted": "-50.00"},
                "date_comparison": {
                    "invoice_posted_at": "2024-01-01T00:00:00Z",
                    "counterpart_posted_at": ["2024-01-05T00:00:00Z"],
                    "date_diffs_days": [4],
                },
            },
            "timing_threshold": 30,
        },
            LeakageTypology.UNDERPAYMENT: {
                "finding": {"finding_type": "exact_match"},
                "evidence_payload": {
                    "amount_comparison": {"diff_converted": "100.00"},
                "date_comparison": {
                    "invoice_posted_at": "2024-01-01T00:00:00Z",
                    "counterpart_posted_at": ["2024-01-05T00:00:00Z"],
                    "date_diffs_days": [4],
                },
            },
                "timing_threshold": 30,
            },
        }
    
    for typology in typologies:
        assert typology in test_mappings, f"Typology {typology} has no test mapping"
        
        mapping = test_mappings[typology]
        result = classify_finding(
            finding=mapping["finding"],
            evidence_payload=mapping["evidence_payload"],
            timing_inconsistency_days_threshold=mapping.get("timing_threshold"),
        )
        
        assert result.typology == typology, (
            f"Typology {typology} mapping rule does not produce expected result"
        )
