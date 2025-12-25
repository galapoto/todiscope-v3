"""
Externalization Policy for Engine #5

Code-enforced policy specifying which report sections are shareable,
which are internal-only, and redaction rules.

Platform Law Compliance:
- Law #5: Evidence and review are core-owned — evidence via core registry
- External views are safe for third-party sharing
- No transformation of numbers, only omission/redaction
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ReportSection(str, Enum):
    """Report section identifiers for Engine #5."""
    EXECUTIVE_OVERVIEW = "executive_overview"
    TRANSACTION_SCOPE_VALIDATION = "transaction_scope_validation"
    EXECUTION_SUMMARY = "execution_summary"
    READINESS_FINDINGS = "readiness_findings"
    CHECKLIST_STATUS = "checklist_status"
    EVIDENCE_INDEX = "evidence_index"
    LIMITATIONS_UNCERTAINTY = "limitations_uncertainty"
    EXPLICIT_NON_CLAIMS = "explicit_non_claims"
    INTERNAL_NOTES = "internal_notes"
    TRANSACTION_SCOPE_DETAILS = "transaction_scope_details"
    RUN_PARAMETERS = "run_parameters"
    DATASET_VERSION_DETAILS = "dataset_version_details"


class SharingLevel(str, Enum):
    """Sharing level for report sections."""
    EXTERNAL = "external"  # Shareable with third parties
    INTERNAL = "internal"  # Internal-only, not shareable


@dataclass(frozen=True)
class ExternalizationPolicy:
    """
    Code-enforced externalization policy for Engine #5.
    
    Defines which report sections are shareable and which are internal-only.
    """
    # Shareable sections (external)
    external_sections: set[ReportSection] = frozenset({
        ReportSection.EXECUTIVE_OVERVIEW,
        ReportSection.TRANSACTION_SCOPE_VALIDATION,
        ReportSection.EXECUTION_SUMMARY,
        ReportSection.READINESS_FINDINGS,
        ReportSection.CHECKLIST_STATUS,
        ReportSection.EVIDENCE_INDEX,
        ReportSection.LIMITATIONS_UNCERTAINTY,
        ReportSection.EXPLICIT_NON_CLAIMS,
    })
    
    # Internal-only sections (not shareable)
    internal_sections: set[ReportSection] = frozenset({
        ReportSection.INTERNAL_NOTES,
        ReportSection.TRANSACTION_SCOPE_DETAILS,
        ReportSection.RUN_PARAMETERS,
        ReportSection.DATASET_VERSION_DETAILS,
    })
    
    # Fields to redact in external view
    redacted_fields: set[str] = frozenset({
        "internal_notes",
        "run_parameters",
        "run_id",  # Redact run IDs (runtime metadata, not replay-stable)
        "transaction_scope",  # Redact full transaction scope details
        # Internal provenance / artifact-store linkage (must not leak in external exports)
        "artifact_key",
        "expected_sha256",
        "sha256",
        "content_type",
        "error",
        "source_system_id",
        "source_record_id",
        "canonical_record_id",
    })
    
    # Fields that can be included but must be anonymized
    anonymized_fields: set[str] = frozenset({
        "dataset_version_id",  # Anonymize dataset IDs (preserve binding without leaking raw ID)
        "result_set_id",  # Deterministic input-set ID; anonymize for external sharing
        "finding_id",  # Use anonymized reference
        "evidence_id",  # Use anonymized reference
        "checklist_item_id",  # Use anonymized reference
    })


def get_sharing_level(section: ReportSection, policy: ExternalizationPolicy) -> SharingLevel:
    """
    Get sharing level for a report section.
    
    Args:
        section: Report section
        policy: Externalization policy
    
    Returns:
        Sharing level (EXTERNAL or INTERNAL)
    """
    if section in policy.external_sections:
        return SharingLevel.EXTERNAL
    elif section in policy.internal_sections:
        return SharingLevel.INTERNAL
    else:
        # Unknown section - treat as internal (conservative)
        return SharingLevel.INTERNAL


def should_redact_field(field_name: str, policy: ExternalizationPolicy) -> bool:
    """
    Check if a field should be redacted in external view.
    
    Args:
        field_name: Field name
        policy: Externalization policy
    
    Returns:
        True if field should be redacted
    """
    return field_name in policy.redacted_fields


def should_anonymize_field(field_name: str, policy: ExternalizationPolicy) -> bool:
    """
    Check if a field should be anonymized in external view.
    
    Args:
        field_name: Field name
        policy: Externalization policy
    
    Returns:
        True if field should be anonymized
    """
    return field_name in policy.anonymized_fields


def validate_externalization_policy(policy: ExternalizationPolicy) -> None:
    """
    Validate externalization policy consistency.
    
    Raises:
        ValueError: If policy is inconsistent
    """
    # Check for overlap between external and internal sections
    overlap = policy.external_sections & policy.internal_sections
    if overlap:
        raise ValueError(f"Policy has overlapping external/internal sections: {overlap}")
    
    # Check for overlap between redacted and anonymized fields
    field_overlap = policy.redacted_fields & policy.anonymized_fields
    if field_overlap:
        raise ValueError(f"Policy has overlapping redacted/anonymized fields: {field_overlap}")


# Default policy instance
DEFAULT_POLICY = ExternalizationPolicy()

# Validate default policy
validate_externalization_policy(DEFAULT_POLICY)





