"""
Externalization Policy for Engine #2

FF-5: Code-enforced policy specifying which report sections are shareable,
which are internal-only, and redaction rules.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ReportSection(str, Enum):
    """Report section identifiers."""
    FINDINGS_OVERVIEW = "findings_overview"
    EXPOSURE_ESTIMATES = "exposure_estimates"
    CONTROL_SIGNALS = "control_signals"
    LIMITATIONS_UNCERTAINTY = "limitations_uncertainty"
    ASSUMPTIONS = "assumptions"
    EVIDENCE_INDEX = "evidence_index"
    INTERNAL_NOTES = "internal_notes"
    COUNTERPARTY_DETAILS = "counterparty_details"
    SOURCE_SYSTEM_IDS = "source_system_ids"
    RUN_PARAMETERS = "run_parameters"


class SharingLevel(str, Enum):
    """Sharing level for report sections."""
    EXTERNAL = "external"  # Shareable with third parties
    INTERNAL = "internal"  # Internal-only, not shareable


@dataclass(frozen=True)
class ExternalizationPolicy:
    """
    Code-enforced externalization policy.
    
    Defines which report sections are shareable and which are internal-only.
    """
    # Shareable sections (external)
    external_sections: set[ReportSection] = frozenset({
        ReportSection.FINDINGS_OVERVIEW,
        ReportSection.EXPOSURE_ESTIMATES,
        ReportSection.CONTROL_SIGNALS,
        ReportSection.LIMITATIONS_UNCERTAINTY,
        ReportSection.ASSUMPTIONS,
        ReportSection.EVIDENCE_INDEX,
    })
    
    # Internal-only sections (not shareable)
    internal_sections: set[ReportSection] = frozenset({
        ReportSection.INTERNAL_NOTES,
        ReportSection.COUNTERPARTY_DETAILS,
        ReportSection.SOURCE_SYSTEM_IDS,
        ReportSection.RUN_PARAMETERS,
    })
    
    # Fields to redact in external view
    redacted_fields: set[str] = frozenset({
        "internal_notes",
        "counterparty_id",
        "counterparty_name",
        "source_system_id",
        "source_record_id",
        "canonical_record_id",
        "run_parameters",
        "engine_version",
        "dataset_version_id",  # Redact dataset IDs for privacy
        "run_id",  # Redact run IDs
        # finding_id / evidence_id are anonymized (not redacted)
    })
    
    # Fields that can be included but must be anonymized
    anonymized_fields: set[str] = frozenset({
        "finding_id",  # Use anonymized reference
        "evidence_id",  # Use anonymized reference
        "record_id",  # Use anonymized reference
    })


# Default policy instance
DEFAULT_POLICY = ExternalizationPolicy()


def is_section_shareable(section: ReportSection, policy: ExternalizationPolicy = DEFAULT_POLICY) -> bool:
    """
    Check if a report section is shareable externally.
    
    Args:
        section: Report section identifier
        policy: Externalization policy (defaults to DEFAULT_POLICY)
    
    Returns:
        True if section is shareable externally, False if internal-only
    """
    return section in policy.external_sections


def get_sharing_level(section: ReportSection, policy: ExternalizationPolicy = DEFAULT_POLICY) -> SharingLevel:
    """
    Get sharing level for a report section.
    
    Args:
        section: Report section identifier
        policy: Externalization policy (defaults to DEFAULT_POLICY)
    
    Returns:
        SharingLevel.EXTERNAL if shareable, SharingLevel.INTERNAL if not
    """
    if section in policy.external_sections:
        return SharingLevel.EXTERNAL
    return SharingLevel.INTERNAL


def should_redact_field(field_name: str, policy: ExternalizationPolicy = DEFAULT_POLICY) -> bool:
    """
    Check if a field should be redacted in external view.
    
    Args:
        field_name: Field name to check
        policy: Externalization policy (defaults to DEFAULT_POLICY)
    
    Returns:
        True if field should be redacted, False otherwise
    """
    return field_name in policy.redacted_fields


def should_anonymize_field(field_name: str, policy: ExternalizationPolicy = DEFAULT_POLICY) -> bool:
    """
    Check if a field should be anonymized in external view.
    
    Args:
        field_name: Field name to check
        policy: Externalization policy (defaults to DEFAULT_POLICY)
    
    Returns:
        True if field should be anonymized, False otherwise
    """
    return field_name in policy.anonymized_fields


def validate_externalization_policy(policy: ExternalizationPolicy) -> None:
    """
    Validate that externalization policy is consistent.
    
    Raises:
        ValueError: If policy is inconsistent (e.g., section in both external and internal)
    """
    overlap = policy.external_sections & policy.internal_sections
    if overlap:
        raise ValueError(
            f"Externalization policy inconsistent: sections in both external and internal sets: {overlap}"
        )
    
    all_sections = policy.external_sections | policy.internal_sections
    all_defined_sections = set(ReportSection)
    missing = all_defined_sections - all_sections
    if missing:
        raise ValueError(
            f"Externalization policy incomplete: missing sections: {missing}"
        )

