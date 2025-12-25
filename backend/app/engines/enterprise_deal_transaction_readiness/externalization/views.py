"""
External Report Views for Engine #5

Internal view (full) and external view (policy-filtered).
No transformation of numbers, only omission/redaction.

Platform Law Compliance:
- Law #5: Evidence and review are core-owned
- External views are safe for third-party sharing
- No transformation of numeric values
"""
from __future__ import annotations

import hashlib
from typing import Any

from backend.app.engines.enterprise_deal_transaction_readiness.externalization.policy import (
    DEFAULT_POLICY,
    ExternalizationPolicy,
    ReportSection,
    SharingLevel,
    get_sharing_level,
    should_anonymize_field,
    should_redact_field,
)


def anonymize_id(identifier: str, salt: str = "") -> str:
    """
    Anonymize an identifier for external view.
    
    Uses deterministic hashing to create anonymized references.
    
    Args:
        identifier: Original identifier
        salt: Optional salt for additional privacy
    
    Returns:
        Anonymized identifier (e.g., "REF-abc123")
    """
    hash_input = f"{identifier}{salt}".encode("utf-8")
    hash_value = hashlib.sha256(hash_input).hexdigest()[:8]
    return f"REF-{hash_value}"


def create_internal_view(report: dict[str, Any]) -> dict[str, Any]:
    """
    Create internal view of report (full, unredacted).
    
    Args:
        report: Full report data
    
    Returns:
        Internal view (unchanged, full data)
    """
    return report.copy()


def create_external_view(
    report: dict[str, Any],
    policy: ExternalizationPolicy = DEFAULT_POLICY,
    anonymization_salt: str = "",
) -> dict[str, Any]:
    """
    Create external view of report (policy-filtered, redacted).
    
    No transformation of numbers, only omission/redaction.
    
    Args:
        report: Full report data
        policy: Externalization policy (defaults to DEFAULT_POLICY)
        anonymization_salt: Salt for anonymization (optional)
    
    Returns:
        External view (filtered, redacted, anonymized)
    """
    external_view = {}
    omitted_internal_sections: list[str] = []
    
    # Handle sections array if present
    if "sections" in report:
        external_sections = []
        for section in report["sections"]:
            section_id = section.get("section_id") or section.get("section_type", "")
            section_enum = _identify_section(section_id)
            
            if section_enum is None:
                # Unknown section - exclude from external view (conservative)
                continue
            
            sharing_level = get_sharing_level(section_enum, policy)
            
            if sharing_level == SharingLevel.EXTERNAL:
                # Include section, but redact/anonymize fields
                external_sections.append(
                    _redact_section(
                        section,
                        policy=policy,
                        anonymization_salt=anonymization_salt,
                    )
                )
            else:
                omitted_internal_sections.append(section_id)
        
        external_view["sections"] = external_sections
        # Copy top-level metadata (redacted)
        for key in ["engine_id", "engine_version", "dataset_version_id", "run_id"]:
            if key in report:
                if should_redact_field(key, policy):
                    continue
                elif should_anonymize_field(key, policy):
                    external_view[key] = anonymize_id(str(report[key]), salt=anonymization_salt)
                else:
                    external_view[key] = report[key]
    else:
        # Handle flat report structure
        for section_key, section_data in report.items():
            section_enum = _identify_section(section_key)
            
            if section_enum is None:
                # Unknown section - exclude from external view (conservative)
                continue
            
            sharing_level = get_sharing_level(section_enum, policy)
            
            if sharing_level == SharingLevel.EXTERNAL:
                external_view[section_key] = _redact_section(
                    section_data,
                    policy=policy,
                    anonymization_salt=anonymization_salt,
                )
            else:
                omitted_internal_sections.append(section_key)
    
    if omitted_internal_sections:
        external_view["__omitted_internal_sections__"] = sorted(omitted_internal_sections)
    
    return external_view


def _identify_section(section_key: str) -> ReportSection | None:
    """
    Identify report section from key.
    
    Args:
        section_key: Section key/name
    
    Returns:
        ReportSection if identified, None otherwise
    """
    section_key_lower = section_key.lower()
    
    section_map = {
        "executive_overview": ReportSection.EXECUTIVE_OVERVIEW,
        "transaction_scope_validation": ReportSection.TRANSACTION_SCOPE_VALIDATION,
        "execution_summary": ReportSection.EXECUTION_SUMMARY,
        "readiness_findings": ReportSection.READINESS_FINDINGS,
        "checklist_status": ReportSection.CHECKLIST_STATUS,
        "evidence_index": ReportSection.EVIDENCE_INDEX,
        "limitations_uncertainty": ReportSection.LIMITATIONS_UNCERTAINTY,
        "explicit_non_claims": ReportSection.EXPLICIT_NON_CLAIMS,
        "internal_notes": ReportSection.INTERNAL_NOTES,
        "transaction_scope_details": ReportSection.TRANSACTION_SCOPE_DETAILS,
        "run_parameters": ReportSection.RUN_PARAMETERS,
        "dataset_version_details": ReportSection.DATASET_VERSION_DETAILS,
    }
    
    return section_map.get(section_key_lower)


def _redact_section(
    section_data: Any,
    policy: ExternalizationPolicy,
    anonymization_salt: str,
) -> Any:
    """
    Redact and anonymize section data for external view.
    
    Args:
        section_data: Section data (dict, list, or primitive)
        policy: Externalization policy
        anonymization_salt: Salt for anonymization
    
    Returns:
        Redacted/anonymized section data
    """
    if isinstance(section_data, dict):
        redacted = {}
        for key, value in section_data.items():
            if should_redact_field(key, policy):
                # Omit redacted fields
                continue
            elif should_anonymize_field(key, policy):
                # Anonymize field value
                if isinstance(value, str):
                    redacted[key] = anonymize_id(value, salt=anonymization_salt)
                elif isinstance(value, list):
                    redacted[key] = [
                        anonymize_id(item, salt=anonymization_salt) if isinstance(item, str) else item
                        for item in value
                    ]
                else:
                    # Non-string anonymizable field - omit to be safe
                    continue
            else:
                # Recursively redact nested structures
                redacted[key] = _redact_section(value, policy=policy, anonymization_salt=anonymization_salt)
        return redacted
    elif isinstance(section_data, list):
        return [
            _redact_section(item, policy=policy, anonymization_salt=anonymization_salt)
            for item in section_data
        ]
    else:
        # Primitive value - return as-is (no transformation of numbers)
        return section_data


def validate_external_view(external_view: dict[str, Any], policy: ExternalizationPolicy = DEFAULT_POLICY) -> None:
    """
    Validate that external view does not expose internal-only fields.
    
    Raises:
        ValueError: If external view contains internal-only sections or redacted fields
    """
    # Check for internal-only sections
    if "__omitted_internal_sections__" in external_view:
        # This is metadata, not an error
        pass
    
    # Check sections array
    if "sections" in external_view:
        for section in external_view["sections"]:
            section_id = section.get("section_id") or section.get("section_type", "")
            section_enum = _identify_section(section_id)
            if section_enum and section_enum in policy.internal_sections:
                raise ValueError(f"External view contains internal-only section: {section_id}")
    
    # Check for redacted fields (recursive)
    _validate_no_redacted_fields(external_view, policy=policy)


def _validate_no_redacted_fields(data: Any, policy: ExternalizationPolicy, path: str = "") -> None:
    """
    Recursively validate that no redacted fields are present.
    
    Args:
        data: Data to validate
        policy: Externalization policy
        path: Current path in data structure (for error messages)
    
    Raises:
        ValueError: If redacted field is found
    """
    if isinstance(data, dict):
        for key, value in data.items():
            current_path = f"{path}.{key}" if path else key
            if should_redact_field(key, policy):
                raise ValueError(f"External view contains redacted field: {current_path}")
            _validate_no_redacted_fields(value, policy=policy, path=current_path)
    elif isinstance(data, list):
        for i, item in enumerate(data):
            current_path = f"{path}[{i}]" if path else f"[{i}]"
            _validate_no_redacted_fields(item, policy=policy, path=current_path)





