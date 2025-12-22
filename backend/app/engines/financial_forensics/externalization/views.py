"""
External Report Views for Engine #2

FF-5: Internal view (full) and external view (policy-filtered).
No transformation of numbers, only omission/redaction.
"""
from __future__ import annotations

import hashlib
from typing import Any

from backend.app.engines.financial_forensics.externalization.policy import (
    DEFAULT_POLICY,
    ExternalizationPolicy,
    ReportSection,
    SharingLevel,
    get_sharing_level,
    should_anonymize_field,
    should_redact_field,
)
from backend.app.engines.financial_forensics.leakage.semantic_guards import (
    FORBIDDEN_DECISION_PHRASES,
    FORBIDDEN_FRAUD_WORDS,
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
    # Create deterministic hash
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
    # Internal view is the full report, no filtering
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
    
    # Filter sections by sharing level
    for section_key, section_data in report.items():
        # Try to identify section
        section = _identify_section(section_key)
        
        if section is None:
            # Unknown section - exclude from external view (conservative)
            continue
        
        sharing_level = get_sharing_level(section, policy)
        
        if sharing_level == SharingLevel.EXTERNAL:
            # Include section, but redact/anonymize fields
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
    
    # Map common section names to ReportSection enum
    section_map = {
        "findings_overview": ReportSection.FINDINGS_OVERVIEW,
        "exposure_estimates": ReportSection.EXPOSURE_ESTIMATES,
        "control_signals": ReportSection.CONTROL_SIGNALS,
        "limitations_uncertainty": ReportSection.LIMITATIONS_UNCERTAINTY,
        "assumptions": ReportSection.ASSUMPTIONS,
        "evidence_index": ReportSection.EVIDENCE_INDEX,
        "internal_notes": ReportSection.INTERNAL_NOTES,
        "counterparty_details": ReportSection.COUNTERPARTY_DETAILS,
        "source_system_ids": ReportSection.SOURCE_SYSTEM_IDS,
        "run_parameters": ReportSection.RUN_PARAMETERS,
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
        # Primitive value - return as-is (no transformation of numbers).
        if isinstance(section_data, str):
            return _sanitize_text(section_data)
        return section_data


def _sanitize_text(text: str) -> str:
    lowered = text.lower()
    for word in FORBIDDEN_FRAUD_WORDS:
        if word in lowered:
            return "[redacted]"
    for phrase in FORBIDDEN_DECISION_PHRASES:
        if phrase.lower() in lowered:
            return "[redacted]"
    return text


def validate_external_view(external_view: dict[str, Any], policy: ExternalizationPolicy = DEFAULT_POLICY) -> None:
    """
    Validate that external view does not expose internal-only fields.
    
    Raises:
        ValueError: If external view contains internal-only sections or redacted fields
    """
    # Check for internal-only sections
    for section_key in external_view.keys():
        if section_key == "__omitted_internal_sections__":
            raise ValueError("External view derived from report containing internal-only section(s)")
        section = _identify_section(section_key)
        if section and section in policy.internal_sections:
            raise ValueError(
                f"External view contains internal-only section: {section_key}"
            )
    
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
                raise ValueError(
                    f"External view contains redacted field: {current_path}"
                )
            _validate_no_redacted_fields(value, policy=policy, path=current_path)
    elif isinstance(data, list):
        for i, item in enumerate(data):
            current_path = f"{path}[{i}]" if path else f"[{i}]"
            _validate_no_redacted_fields(item, policy=policy, path=current_path)

