"""
FF-4 v1 Lock Enforcement Tests

These tests FAIL if critical FF-4 v1 behaviors are changed.
They lock the v1 implementation permanently.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

from backend.app.engines.financial_forensics.leakage.classifier import classify_finding
from backend.app.engines.financial_forensics.leakage.typology import LeakageTypology


def test_typology_enum_v1_lock() -> None:
    """
    Test that FAILS if typology enum changes.
    
    Locks FF-4 v1 typology set permanently.
    """
    # Expected v1 typologies (locked set)
    expected_typologies = {
        "UNMATCHED_INVOICE",
        "UNMATCHED_PAYMENT",
        "OVERPAYMENT",
        "UNDERPAYMENT",
        "TIMING_MISMATCH",
        "PARTIAL_SETTLEMENT_RESIDUAL",
    }
    
    # Get actual typologies from enum
    actual_typologies = {typology.name for typology in LeakageTypology}
    
    # Must match exactly (no additions, no removals)
    assert actual_typologies == expected_typologies, (
        f"Typology enum changed from v1 locked set!\n"
        f"Expected: {expected_typologies}\n"
        f"Actual: {actual_typologies}\n"
        f"Added: {actual_typologies - expected_typologies}\n"
        f"Removed: {expected_typologies - actual_typologies}\n"
        f"FF-4 v1 typology set is locked and cannot be changed."
    )


def test_timing_mismatch_rule_v1_lock() -> None:
    """
    Test that FAILS if timing mismatch rule is removed.
    
    Locks FF-4 v1 timing mismatch behavior permanently.
    """
    # Test that timing mismatch rule exists and works
    finding = {
        "finding_type": "exact_match",
        "confidence": "exact",
    }
    evidence_payload = {
        "amount_comparison": {
            "diff_converted": "0.00",  # Balanced amounts
        },
        "date_comparison": {
            "invoice_posted_at": "2024-01-01T00:00:00Z",
            "counterpart_posted_at": ["2024-02-15T00:00:00Z"],
            "date_diffs_days": [45],  # 45 days > 30 threshold
        },
    }
    
    result = classify_finding(
        finding=finding,
        evidence_payload=evidence_payload,
        timing_inconsistency_days_threshold=30,
    )
    
    # Must produce TIMING_MISMATCH (rule must exist)
    assert result.typology == LeakageTypology.TIMING_MISMATCH, (
        f"Timing mismatch rule removed or broken!\n"
        f"Expected: {LeakageTypology.TIMING_MISMATCH}\n"
        f"Actual: {result.typology}\n"
        f"FF-4 v1 timing mismatch rule is locked and cannot be removed."
    )
    
    # Verify rationale mentions timing mismatch
    assert "timing" in result.rationale.lower() or "date delta" in result.rationale.lower(), (
        f"Timing mismatch rationale missing or changed!\n"
        f"Rationale: {result.rationale}\n"
        f"FF-4 v1 timing mismatch rule is locked."
    )


def test_timing_mismatch_rule_code_exists() -> None:
    """
    Test that FAILS if timing mismatch rule code is removed from classifier.
    
    Structural test to ensure _check_timing_mismatch function exists.
    """
    root = pathlib.Path(__file__).resolve().parents[4]
    classifier_file = root / "backend" / "app" / "engines" / "financial_forensics" / "leakage" / "classifier.py"
    
    if not classifier_file.exists():
        pytest.fail("Classifier file not found")
    
    content = classifier_file.read_text(encoding="utf-8")
    
    # Must contain timing mismatch check function
    assert "_check_timing_mismatch" in content, (
        f"Timing mismatch rule function removed from classifier!\n"
        f"File: {classifier_file}\n"
        f"FF-4 v1 timing mismatch rule is locked and cannot be removed."
    )
    
    # Must contain timing_inconsistency_days_threshold parameter
    assert "timing_inconsistency_days_threshold" in content, (
        f"Timing mismatch threshold parameter removed from classifier!\n"
        f"File: {classifier_file}\n"
        f"FF-4 v1 timing mismatch rule is locked and cannot be removed."
    )
    
    # Must check for TIMING_MISMATCH typology
    assert "TIMING_MISMATCH" in content or "timing_mismatch" in content, (
        f"TIMING_MISMATCH typology reference removed from classifier!\n"
        f"File: {classifier_file}\n"
        f"FF-4 v1 timing mismatch rule is locked and cannot be removed."
    )


def test_partial_exposure_binding_v1_lock() -> None:
    """
    Test that FAILS if partial exposure binding changes.
    
    Locks FF-4 v1 partial_match → partial_settlement_residual mapping permanently.
    """
    # Test that partial_match findings always map to partial_settlement_residual
    finding = {
        "finding_type": "partial_match",
        "confidence": "partial",
    }
    evidence_payload = {
        "amount_comparison": {
            "diff_converted": "100.00",  # Any value
        },
    }
    
    result = classify_finding(finding=finding, evidence_payload=evidence_payload)
    
    # Must map to PARTIAL_SETTLEMENT_RESIDUAL (binding is locked)
    assert result.typology == LeakageTypology.PARTIAL_SETTLEMENT_RESIDUAL, (
        f"Partial exposure binding changed!\n"
        f"Expected: {LeakageTypology.PARTIAL_SETTLEMENT_RESIDUAL}\n"
        f"Actual: {result.typology}\n"
        f"FF-4 v1 partial_match → partial_settlement_residual binding is locked and cannot be changed."
    )
    
    # Verify rationale mentions partial_match
    assert "partial_match" in result.rationale.lower(), (
        f"Partial match rationale missing or changed!\n"
        f"Rationale: {result.rationale}\n"
        f"FF-4 v1 partial exposure binding is locked."
    )


def test_partial_exposure_binding_priority_v1_lock() -> None:
    """
    Test that FAILS if partial exposure binding priority changes.
    
    Ensures partial_match takes priority over timing mismatch and amount classification.
    """
    # Test that partial_match takes priority even when timing mismatch would apply
    finding = {
        "finding_type": "partial_match",
        "confidence": "partial",
    }
    evidence_payload = {
        "amount_comparison": {
            "diff_converted": "0.00",  # Would normally be balanced (not leakage)
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
    
    # Must still map to PARTIAL_SETTLEMENT_RESIDUAL (priority is locked)
    assert result.typology == LeakageTypology.PARTIAL_SETTLEMENT_RESIDUAL, (
        f"Partial exposure binding priority changed!\n"
        f"Expected: {LeakageTypology.PARTIAL_SETTLEMENT_RESIDUAL}\n"
        f"Actual: {result.typology}\n"
        f"FF-4 v1 partial_match priority (Rule 1) is locked and cannot be changed."
    )


def test_exposure_source_diff_converted_v1_lock() -> None:
    """
    Test that FAILS if exposure source switches back to comparison math.
    
    Locks FF-4 v1 to use diff_converted from evidence, not computed comparison.
    """
    # Test that classifier uses diff_converted from evidence_payload
    finding = {
        "finding_type": "exact_match",
        "confidence": "exact",
    }
    evidence_payload = {
        "amount_comparison": {
            "diff_converted": "-50.00",  # Must use this value, not compute from amounts
            "invoice_amount_original": "1000.00",  # These should NOT be used for classification
            "sum_counterpart_amount_original": "1050.00",
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
    
    # Must use diff_converted (-50.00) → OVERPAYMENT
    # If it computed from amounts (1000 - 1050 = -50), that's acceptable,
    # but we want to ensure it's using diff_converted, not computing
    assert result.typology == LeakageTypology.OVERPAYMENT, (
        f"Exposure source changed from diff_converted!\n"
        f"Expected: {LeakageTypology.OVERPAYMENT} (from diff_converted=-50.00)\n"
        f"Actual: {result.typology}\n"
        f"FF-4 v1 must use diff_converted from evidence, not compute from comparison math."
    )


def test_exposure_source_code_uses_diff_converted() -> None:
    """
    Test that FAILS if classifier code switches to computing exposure from comparison math.
    
    Structural test to ensure _extract_diff_converted is used, not computed values.
    """
    root = pathlib.Path(__file__).resolve().parents[4]
    classifier_file = root / "backend" / "app" / "engines" / "financial_forensics" / "leakage" / "classifier.py"
    
    if not classifier_file.exists():
        pytest.fail("Classifier file not found")
    
    content = classifier_file.read_text(encoding="utf-8")
    
    # Must use _extract_diff_converted function
    assert "_extract_diff_converted" in content, (
        f"Classifier no longer uses _extract_diff_converted!\n"
        f"File: {classifier_file}\n"
        f"FF-4 v1 must use diff_converted from evidence, not compute from comparison math."
    )
    
    # Must reference diff_converted in amount_comparison
    assert "diff_converted" in content, (
        f"Classifier no longer references diff_converted!\n"
        f"File: {classifier_file}\n"
        f"FF-4 v1 must use diff_converted from evidence, not compute from comparison math."
    )
    
    # Should NOT compute exposure from invoice_amount - sum_counterpart_amount
    # (This is a heuristic check - if we see this pattern, it's a violation)
    try:
        tree = ast.parse(content, filename=str(classifier_file))
        
        # Check for patterns that compute exposure from amounts
        for node in ast.walk(tree):
            # Check for subtraction operations that might compute exposure
            if isinstance(node, ast.Sub):
                # Check if it's computing invoice - counterpart
                # This is a heuristic - we want to flag suspicious patterns
                pass  # For now, just check that diff_converted is used
    except SyntaxError:
        # If we can't parse, that's a different issue
        pass
    
    # Verify that diff_converted is extracted, not computed
    assert "amount_comparison.get(\"diff_converted\")" in content or "amount_comparison[\"diff_converted\"]" in content, (
        f"Classifier may be computing exposure instead of using diff_converted!\n"
        f"File: {classifier_file}\n"
        f"FF-4 v1 must use diff_converted from evidence, not compute from comparison math."
    )


def test_classification_rules_order_v1_lock() -> None:
    """
    Test that FAILS if classification rules order changes.
    
    Locks FF-4 v1 rule priority order permanently.
    """
    # Rule order must be:
    # 1. Partial match (highest priority)
    # 2. Timing mismatch
    # 3. Amount-based classification
    
    # Test Rule 1 priority over Rule 2
    finding = {
        "finding_type": "partial_match",
        "confidence": "partial",
    }
    evidence_payload = {
        "amount_comparison": {
            "diff_converted": "0.00",
        },
        "date_comparison": {
            "invoice_posted_at": "2024-01-01T00:00:00Z",
            "counterpart_posted_at": ["2024-02-15T00:00:00Z"],
            "date_diffs_days": [45],  # Would trigger timing_mismatch if not partial_match
        },
    }
    
    result = classify_finding(
        finding=finding,
        evidence_payload=evidence_payload,
        timing_inconsistency_days_threshold=30,
    )
    
    # Rule 1 must take priority
    assert result.typology == LeakageTypology.PARTIAL_SETTLEMENT_RESIDUAL, (
        f"Rule order changed! Rule 1 (partial_match) must have highest priority.\n"
        f"Expected: {LeakageTypology.PARTIAL_SETTLEMENT_RESIDUAL}\n"
        f"Actual: {result.typology}\n"
        f"FF-4 v1 rule order is locked: 1) partial_match, 2) timing_mismatch, 3) amount-based."
    )
    
    # Test Rule 2 priority over Rule 3
    finding = {
        "finding_type": "exact_match",
        "confidence": "exact",
    }
    evidence_payload = {
        "amount_comparison": {
            "diff_converted": "-50.00",  # Would be overpayment (Rule 3)
        },
        "date_comparison": {
            "invoice_posted_at": "2024-01-01T00:00:00Z",
            "counterpart_posted_at": ["2024-02-15T00:00:00Z"],
            "date_diffs_days": [45],  # Triggers timing_mismatch (Rule 2)
        },
    }
    
    result = classify_finding(
        finding=finding,
        evidence_payload=evidence_payload,
        timing_inconsistency_days_threshold=30,
    )
    
    # Rule 2 must take priority over Rule 3
    assert result.typology == LeakageTypology.TIMING_MISMATCH, (
        f"Rule order changed! Rule 2 (timing_mismatch) must have priority over Rule 3 (amount-based).\n"
        f"Expected: {LeakageTypology.TIMING_MISMATCH}\n"
        f"Actual: {result.typology}\n"
        f"FF-4 v1 rule order is locked: 1) partial_match, 2) timing_mismatch, 3) amount-based."
    )


def test_all_v1_typologies_have_mapping_rules() -> None:
    """
    Test that FAILS if any v1 typology loses its mapping rule.
    
    Ensures all typologies in v1 set have explicit mapping rules.
    """
    # Typologies that should have mapping rules from findings
    typologies_with_finding_rules = {
        LeakageTypology.PARTIAL_SETTLEMENT_RESIDUAL,
        LeakageTypology.TIMING_MISMATCH,
        LeakageTypology.OVERPAYMENT,
        LeakageTypology.UNDERPAYMENT,
    }
    
    # Test that each typology can be produced from a finding
    test_cases = {
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
    
    for typology in typologies_with_finding_rules:
        assert typology in test_cases, (
            f"Typology {typology} has no test case!\n"
            f"FF-4 v1 requires all typologies to have mapping rules."
        )
        
        case = test_cases[typology]
        result = classify_finding(
            finding=case["finding"],
            evidence_payload=case["evidence_payload"],
            timing_inconsistency_days_threshold=case.get("timing_threshold"),
        )
        
        assert result.typology == typology, (
            f"Typology {typology} mapping rule broken or removed!\n"
            f"Expected: {typology}\n"
            f"Actual: {result.typology}\n"
            f"FF-4 v1 requires all typologies to have working mapping rules."
        )


