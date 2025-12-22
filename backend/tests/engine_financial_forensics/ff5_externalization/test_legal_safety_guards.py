"""
Legal Safety Guards for FF-5

Tests that fail if:
- Fraud/blame language appears in reports
- Decisioning language appears
- External view exposes internal-only fields
"""
from __future__ import annotations

import re

import pytest

from backend.app.engines.financial_forensics.externalization.policy import (
    DEFAULT_POLICY,
    ReportSection,
    SharingLevel,
)
from backend.app.engines.financial_forensics.externalization.views import (
    create_external_view,
    validate_external_view,
)
from backend.app.engines.financial_forensics.leakage.semantic_guards import (
    FORBIDDEN_DECISION_PHRASES,
    FORBIDDEN_FRAUD_WORDS,
)


def test_external_view_no_fraud_language() -> None:
    """Test that external view does not contain fraud/blame language."""
    report = {
        "findings_overview": {
            "summary": "No fraud detected in the dataset",
            "findings": [
                {
                    "description": "Potential fraudulent activity identified",
                    "amount": "1000.00",
                },
            ],
        },
        "exposure_estimates": {
            "total_exposure": "5000.00",
        },
    }
    
    external_view = create_external_view(report)
    
    # Check for forbidden fraud words in external view
    external_view_str = str(external_view).lower()
    
    violations = []
    for word in FORBIDDEN_FRAUD_WORDS:
        if re.search(rf"\b{word}\b", external_view_str):
            violations.append(word)
    
    assert len(violations) == 0, (
        f"External view contains forbidden fraud/blame language: {violations}\n"
        f"External view: {external_view}\n"
        f"FF-5 requires external views to be free of fraud/blame language."
    )


def test_external_view_no_decisioning_language() -> None:
    """Test that external view does not contain decisioning language."""
    report = {
        "findings_overview": {
            "summary": "Items must be paid immediately",
            "recommendations": [
                "Should collect outstanding amounts",
                "Is required to investigate further",
            ],
        },
        "exposure_estimates": {
            "total_exposure": "5000.00",
        },
    }
    
    external_view = create_external_view(report)
    
    # Check for forbidden decision phrases in external view
    external_view_str = str(external_view).lower()
    
    violations = []
    for phrase in FORBIDDEN_DECISION_PHRASES:
        if phrase.lower() in external_view_str:
            violations.append(phrase)
    
    assert len(violations) == 0, (
        f"External view contains forbidden decisioning language: {violations}\n"
        f"External view: {external_view}\n"
        f"FF-5 requires external views to be free of decisioning language."
    )


def test_external_view_no_internal_only_fields() -> None:
    """Test that external view does not expose internal-only fields."""
    report = {
        "findings_overview": {
            "summary": "Findings summary",
            "findings": [
                {
                    "finding_id": "finding_123",
                    "counterparty_id": "cp_456",
                    "source_system_id": "erp_001",
                    "amount": "1000.00",
                },
            ],
        },
        "internal_notes": {
            "note": "Internal note",
        },
        "counterparty_details": {
            "counterparty_id": "cp_456",
            "name": "Counterparty Name",
        },
        "run_parameters": {
            "tolerance": "0.01",
            "engine_version": "v1.0",
        },
    }
    
    external_view = create_external_view(report)
    
    # Validate that external view does not contain internal-only sections
    with pytest.raises(ValueError, match="internal-only section"):
        validate_external_view(external_view)
    
    # Check that internal-only sections are omitted
    assert "internal_notes" not in external_view, "External view contains internal_notes section"
    assert "counterparty_details" not in external_view, "External view contains counterparty_details section"
    assert "run_parameters" not in external_view, "External view contains run_parameters section"
    
    # Check that redacted fields are omitted from included sections
    if "findings_overview" in external_view:
        findings = external_view["findings_overview"].get("findings", [])
        for finding in findings:
            assert "counterparty_id" not in finding, "External view contains counterparty_id"
            assert "source_system_id" not in finding, "External view contains source_system_id"
            # finding_id should be anonymized, not present as-is
            if "finding_id" in finding:
                assert finding["finding_id"].startswith("REF-"), "finding_id not anonymized"


def test_external_view_redacts_sensitive_fields() -> None:
    """Test that external view redacts sensitive fields."""
    report = {
        "findings_overview": {
            "findings": [
                {
                    "finding_id": "finding_123",
                    "evidence_id": "evidence_456",
                    "dataset_version_id": "dv_789",
                    "run_id": "run_012",
                    "amount": "1000.00",
                    "description": "Finding description",
                },
            ],
        },
    }
    
    external_view = create_external_view(report)
    
    # Check that sensitive fields are redacted or anonymized
    if "findings_overview" in external_view:
        findings = external_view["findings_overview"].get("findings", [])
        for finding in findings:
            # Redacted fields should be omitted
            assert "dataset_version_id" not in finding, "dataset_version_id not redacted"
            assert "run_id" not in finding, "run_id not redacted"
            
            # Anonymized fields should be anonymized (start with REF-)
            if "finding_id" in finding:
                assert finding["finding_id"].startswith("REF-"), "finding_id not anonymized"
            if "evidence_id" in finding:
                assert finding["evidence_id"].startswith("REF-"), "evidence_id not anonymized"
            
            # Non-sensitive fields should be present
            assert "amount" in finding, "amount should be present"
            assert "description" in finding, "description should be present"


def test_external_view_no_number_transformation() -> None:
    """Test that external view does not transform numbers, only omits/redacts."""
    report = {
        "exposure_estimates": {
            "total_exposure": "5000.00",
            "exposure_by_type": {
                "overpayment": "2000.00",
                "underpayment": "3000.00",
            },
            "exposure_range": {
                "min": "4500.00",
                "max": "5500.00",
            },
        },
    }
    
    external_view = create_external_view(report)
    
    # Numbers should be unchanged (no transformation)
    if "exposure_estimates" in external_view:
        assert external_view["exposure_estimates"]["total_exposure"] == "5000.00", (
            "Numbers should not be transformed in external view"
        )
        assert external_view["exposure_estimates"]["exposure_by_type"]["overpayment"] == "2000.00", (
            "Numbers should not be transformed in external view"
        )
        assert external_view["exposure_estimates"]["exposure_range"]["min"] == "4500.00", (
            "Numbers should not be transformed in external view"
        )


def test_external_view_includes_required_sections() -> None:
    """Test that external view includes all required shareable sections."""
    report = {
        "findings_overview": {"summary": "Findings"},
        "exposure_estimates": {"total": "1000.00"},
        "control_signals": {"signals": []},
        "limitations_uncertainty": {"limitations": []},
        "assumptions": {"assumptions": []},
        "evidence_index": {"evidence": []},
    }
    
    external_view = create_external_view(report)
    
    # All shareable sections should be present
    assert "findings_overview" in external_view, "findings_overview should be in external view"
    assert "exposure_estimates" in external_view, "exposure_estimates should be in external view"
    assert "control_signals" in external_view, "control_signals should be in external view"
    assert "limitations_uncertainty" in external_view, "limitations_uncertainty should be in external view"
    assert "assumptions" in external_view, "assumptions should be in external view"
    assert "evidence_index" in external_view, "evidence_index should be in external view"


def test_internal_view_is_full() -> None:
    """Test that internal view contains full, unredacted data."""
    from backend.app.engines.financial_forensics.externalization.views import create_internal_view
    
    report = {
        "findings_overview": {
            "findings": [
                {
                    "finding_id": "finding_123",
                    "counterparty_id": "cp_456",
                    "amount": "1000.00",
                },
            ],
        },
        "internal_notes": {
            "note": "Internal note",
        },
    }
    
    internal_view = create_internal_view(report)
    
    # Internal view should be identical to original
    assert internal_view == report, "Internal view should be full, unredacted"
    assert "internal_notes" in internal_view, "Internal view should include internal sections"
    assert internal_view["findings_overview"]["findings"][0]["counterparty_id"] == "cp_456", (
        "Internal view should include redacted fields"
    )


