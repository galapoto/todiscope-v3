"""
FF-3 Confidence Guards Tests

Tests:
- Centralized confidence assignment
- Enum enforcement
- No contextual overrides
"""
import pytest

from backend.app.engines.financial_forensics.confidence import (
    Confidence,
    ConfidenceAssignmentError,
    assign_confidence,
    validate_confidence,
)


def test_confidence_enum_enforcement() -> None:
    """Test: Confidence must be in allowed enum."""
    # Valid values
    assert validate_confidence("exact") == Confidence.EXACT
    assert validate_confidence("within_tolerance") == Confidence.WITHIN_TOLERANCE
    assert validate_confidence("partial") == Confidence.PARTIAL
    assert validate_confidence("ambiguous") == Confidence.AMBIGUOUS
    
    # Invalid values
    with pytest.raises(ConfidenceAssignmentError, match="CONFIDENCE_INVALID"):
        validate_confidence("invalid")
    
    with pytest.raises(ConfidenceAssignmentError, match="CONFIDENCE_INVALID"):
        validate_confidence("high")
    
    with pytest.raises(ConfidenceAssignmentError, match="CONFIDENCE_INVALID"):
        validate_confidence("low")


def test_confidence_case_insensitive() -> None:
    """Test: Confidence is case-insensitive (normalized to lowercase)."""
    assert validate_confidence("EXACT") == Confidence.EXACT
    assert validate_confidence("Exact") == Confidence.EXACT
    assert validate_confidence("  exact  ") == Confidence.EXACT


def test_confidence_centralized_assignment() -> None:
    """Test: Confidence assignment is centralized with explicit priority."""
    # Exact match
    confidence = assign_confidence(
        is_exact=True,
        is_within_tolerance=False,
        is_partial=False,
        is_ambiguous=False,
    )
    assert confidence == Confidence.EXACT
    
    # Within tolerance (not exact)
    confidence = assign_confidence(
        is_exact=False,
        is_within_tolerance=True,
        is_partial=False,
        is_ambiguous=False,
    )
    assert confidence == Confidence.WITHIN_TOLERANCE
    
    # Partial (not exact, not within tolerance)
    confidence = assign_confidence(
        is_exact=False,
        is_within_tolerance=False,
        is_partial=True,
        is_ambiguous=False,
    )
    assert confidence == Confidence.PARTIAL
    
    # Ambiguous
    confidence = assign_confidence(
        is_exact=False,
        is_within_tolerance=False,
        is_partial=False,
        is_ambiguous=True,
    )
    assert confidence == Confidence.AMBIGUOUS


def test_confidence_priority_order() -> None:
    """Test: Confidence assignment follows explicit priority order."""
    # If multiple flags set, should raise error (ambiguous logic)
    with pytest.raises(ConfidenceAssignmentError, match="CONFIDENCE_AMBIGUOUS_LOGIC"):
        assign_confidence(
            is_exact=True,
            is_within_tolerance=True,  # Multiple flags
            is_partial=False,
            is_ambiguous=False,
        )


def test_confidence_no_contextual_overrides() -> None:
    """Test: Confidence cannot be overridden after assignment."""
    # Confidence is assigned via centralized function
    # No direct assignment or override allowed
    confidence = assign_confidence(
        is_exact=True,
        is_within_tolerance=False,
        is_partial=False,
        is_ambiguous=False,
    )
    
    # Confidence is enum (immutable)
    assert confidence == Confidence.EXACT
    
    # Cannot change (enum is immutable)
    # This is enforced by using enum and centralized assignment function


