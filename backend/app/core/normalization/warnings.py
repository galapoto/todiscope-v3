"""
Structured warning system for normalization workflow.

Warnings are generated during normalization preview and validation to inform users
about data quality issues, missing values, fuzzy matches, and other anomalies.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class WarningSeverity(str, Enum):
    """Severity levels for normalization warnings."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class NormalizationWarning:
    """
    Structured warning for normalization issues.
    
    Attributes:
        code: Unique warning code (e.g., "MISSING_VALUE", "FUZZY_MATCH")
        severity: Warning severity level
        message: Human-readable warning message
        affected_fields: List of field names affected by this warning
        raw_record_id: ID of the raw record that triggered this warning
        explanation: Detailed explanation of the issue
        recommendation: Suggested action to resolve the issue
    """

    code: str
    severity: WarningSeverity
    message: str
    affected_fields: list[str]
    raw_record_id: str
    explanation: str
    recommendation: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert warning to dictionary for serialization."""
        return {
            "code": self.code,
            "severity": self.severity.value,
            "message": self.message,
            "affected_fields": self.affected_fields,
            "raw_record_id": self.raw_record_id,
            "explanation": self.explanation,
            "recommendation": self.recommendation,
        }


def create_missing_value_warning(
    raw_record_id: str,
    field_name: str,
    explanation: str | None = None,
) -> NormalizationWarning:
    """Create a warning for missing required values."""
    return NormalizationWarning(
        code="MISSING_VALUE",
        severity=WarningSeverity.WARNING,
        message=f"Missing value for field: {field_name}",
        affected_fields=[field_name],
        raw_record_id=raw_record_id,
        explanation=explanation or f"Field '{field_name}' is required but not present in the raw record.",
        recommendation=f"Provide a value for '{field_name}' or mark it as optional in the normalization rules.",
    )


def create_fuzzy_match_warning(
    raw_record_id: str,
    field_name: str,
    original_value: str,
    suggested_value: str,
    confidence: float | None = None,
) -> NormalizationWarning:
    """Create a warning for fuzzy matches that may need review."""
    confidence_str = f" ({confidence:.0%} confidence)" if confidence is not None else ""
    return NormalizationWarning(
        code="FUZZY_MATCH",
        severity=WarningSeverity.INFO,
        message=f"Fuzzy match detected for field: {field_name}",
        affected_fields=[field_name],
        raw_record_id=raw_record_id,
        explanation=f"Value '{original_value}' was matched to '{suggested_value}'{confidence_str}. Review recommended.",
        recommendation=f"Verify that '{suggested_value}' is the correct normalization for '{original_value}'.",
    )


def create_conversion_issue_warning(
    raw_record_id: str,
    field_name: str,
    original_value: Any,
    target_type: str,
    explanation: str | None = None,
) -> NormalizationWarning:
    """Create a warning for type conversion issues."""
    return NormalizationWarning(
        code="CONVERSION_ISSUE",
        severity=WarningSeverity.WARNING,
        message=f"Type conversion issue for field: {field_name}",
        affected_fields=[field_name],
        raw_record_id=raw_record_id,
        explanation=explanation or f"Cannot convert value '{original_value}' to {target_type}.",
        recommendation=f"Review the value for '{field_name}' and ensure it can be converted to {target_type}.",
    )


def create_unit_discrepancy_warning(
    raw_record_id: str,
    field_name: str,
    detected_unit: str,
    expected_unit: str | None = None,
) -> NormalizationWarning:
    """Create a warning for unit discrepancies."""
    expected_str = f" (expected: {expected_unit})" if expected_unit else ""
    return NormalizationWarning(
        code="UNIT_DISCREPANCY",
        severity=WarningSeverity.WARNING,
        message=f"Unit discrepancy detected for field: {field_name}",
        affected_fields=[field_name],
        raw_record_id=raw_record_id,
        explanation=f"Detected unit '{detected_unit}'{expected_str}. Unit normalization may be required.",
        recommendation=f"Verify unit '{detected_unit}' is correct or provide unit conversion rules.",
    )


def create_data_quality_warning(
    raw_record_id: str,
    code: str,
    message: str,
    affected_fields: list[str],
    explanation: str,
    recommendation: str | None = None,
    severity: WarningSeverity = WarningSeverity.WARNING,
) -> NormalizationWarning:
    """Create a custom data quality warning."""
    return NormalizationWarning(
        code=code,
        severity=severity,
        message=message,
        affected_fields=affected_fields,
        raw_record_id=raw_record_id,
        explanation=explanation,
        recommendation=recommendation,
    )





