"""
Finding Type Enum for Engine #2

FF-3: Finding types are constrained enums, derived deterministically from rule_id.
"""
from __future__ import annotations

from enum import Enum


class FindingType(Enum):
    """
    Controlled finding type enum for findings.
    
    Values (v1, locked):
    - exact_match: Exact match finding
    - tolerance_match: Tolerance-based match finding
    - partial_match: Partial match finding
    """
    EXACT_MATCH = "exact_match"
    TOLERANCE_MATCH = "tolerance_match"
    PARTIAL_MATCH = "partial_match"


class FindingTypeAssignmentError(ValueError):
    """Raised when finding type assignment violates rules."""
    pass


def validate_finding_type(finding_type: str | FindingType) -> FindingType:
    """
    Validate and normalize finding type value.
    
    Args:
        finding_type: Finding type value (string or FindingType enum)
    
    Returns:
        FindingType enum value
    
    Raises:
        FindingTypeAssignmentError: If finding_type is not in allowed enum
    """
    if isinstance(finding_type, FindingType):
        return finding_type
    
    if not isinstance(finding_type, str):
        raise FindingTypeAssignmentError(
            f"FINDING_TYPE_INVALID_TYPE: finding_type must be str or FindingType enum, got {type(finding_type).__name__}"
        )
    
    finding_type_lower = finding_type.lower().strip()
    
    try:
        return FindingType(finding_type_lower)
    except ValueError:
        allowed = [ft.value for ft in FindingType]
        raise FindingTypeAssignmentError(
            f"FINDING_TYPE_INVALID: finding_type '{finding_type}' is not in allowed enum: {allowed}"
        )


def derive_finding_type_from_rule_id(rule_id: str) -> FindingType:
    """
    Derive finding type deterministically from rule_id.
    
    Args:
        rule_id: Rule identifier
    
    Returns:
        FindingType enum value
    
    Raises:
        FindingTypeAssignmentError: If rule_id cannot be mapped to finding type
    """
    rule_id_lower = rule_id.lower().strip()
    
    # Deterministic mapping from rule_id to finding_type
    if "exact" in rule_id_lower or rule_id_lower.startswith("exact"):
        return FindingType.EXACT_MATCH
    elif "tolerance" in rule_id_lower or rule_id_lower.startswith("tolerance"):
        return FindingType.TOLERANCE_MATCH
    elif "partial" in rule_id_lower or rule_id_lower.startswith("partial"):
        return FindingType.PARTIAL_MATCH
    else:
        # Default to tolerance_match if cannot determine
        # This should be explicit in rule definitions
        raise FindingTypeAssignmentError(
            f"FINDING_TYPE_CANNOT_DERIVE: Cannot derive finding_type from rule_id '{rule_id}'. "
            f"Rule ID must contain 'exact', 'tolerance', or 'partial'."
        )


