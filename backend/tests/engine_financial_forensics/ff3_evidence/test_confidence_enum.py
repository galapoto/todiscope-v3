"""
FF-3 Confidence Enum Enforcement

Tests that FAIL THE BUILD if confidence is not enum.
"""
import pytest

from backend.app.engines.financial_forensics.confidence import (
    Confidence,
    ConfidenceAssignmentError,
    validate_confidence,
)


def test_confidence_must_be_enum() -> None:
    """
    BUILD FAILURE TEST: Confidence must be enum (no free text).
    
    This test will fail the build if confidence validation allows free text.
    """
    # Valid enum values
    assert validate_confidence("exact") == Confidence.EXACT
    assert validate_confidence("within_tolerance") == Confidence.WITHIN_TOLERANCE
    assert validate_confidence("partial") == Confidence.PARTIAL
    assert validate_confidence("ambiguous") == Confidence.AMBIGUOUS
    
    # Invalid (free text) should fail
    with pytest.raises(ConfidenceAssignmentError, match="CONFIDENCE_INVALID"):
        validate_confidence("high_confidence")  # Free text - should fail
    
    with pytest.raises(ConfidenceAssignmentError, match="CONFIDENCE_INVALID"):
        validate_confidence("low")  # Free text - should fail
    
    with pytest.raises(ConfidenceAssignmentError, match="CONFIDENCE_INVALID"):
        validate_confidence("custom_confidence")  # Free text - should fail


def test_confidence_enum_values_locked() -> None:
    """
    BUILD FAILURE TEST: Confidence enum values are locked.
    
    This test documents the locked enum values and ensures they cannot be extended.
    """
    # Enum values are locked
    allowed_values = {c.value for c in Confidence}
    expected_values = {"exact", "within_tolerance", "partial", "ambiguous"}
    
    assert allowed_values == expected_values, (
        f"BUILD FAILURE: Confidence enum values changed. "
        f"Expected: {expected_values}, Got: {allowed_values}"
    )


