from __future__ import annotations

from enum import Enum


class ConfidenceAssignmentError(ValueError):
    pass


class Confidence(str, Enum):
    EXACT = "exact"
    WITHIN_TOLERANCE = "within_tolerance"
    PARTIAL = "partial"
    AMBIGUOUS = "ambiguous"


def validate_confidence(value: str) -> Confidence:
    if not isinstance(value, str):
        raise ConfidenceAssignmentError("CONFIDENCE_INVALID: confidence must be a string")
    normalized = value.strip().lower()
    try:
        return Confidence(normalized)
    except ValueError as exc:
        raise ConfidenceAssignmentError(f"CONFIDENCE_INVALID: '{value}' is not allowed") from exc


def assign_confidence(
    *,
    is_exact: bool,
    is_within_tolerance: bool,
    is_partial: bool,
    is_ambiguous: bool,
) -> Confidence:
    flags = [is_exact, is_within_tolerance, is_partial, is_ambiguous]
    if sum(1 for f in flags if f) != 1:
        raise ConfidenceAssignmentError("CONFIDENCE_AMBIGUOUS_LOGIC: exactly one confidence flag must be true")
    if is_exact:
        return Confidence.EXACT
    if is_within_tolerance:
        return Confidence.WITHIN_TOLERANCE
    if is_partial:
        return Confidence.PARTIAL
    return Confidence.AMBIGUOUS


__all__ = ["Confidence", "ConfidenceAssignmentError", "assign_confidence", "validate_confidence"]

