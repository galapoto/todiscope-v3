"""
Report Sections for Engine #5

Deterministic report section generation for transaction readiness reports.
All sections are deterministic and replay-stable.
"""
from __future__ import annotations

from typing import Any


def section_executive_overview(
    *,
    dataset_version_id: str,
    run_id: str,
    transaction_scope: dict,
    readiness_summary: dict,
    transaction_scope_summary: dict,
    run_parameters_summary: dict,
) -> dict[str, Any]:
    """
    Executive overview section.
    
    Contains high-level readiness status and summary metrics.
    """
    return {
        "section_id": "executive_overview",
        "section_type": "executive_overview",
        "dataset_version_id": dataset_version_id,
        "run_id": run_id,
        "transaction_scope": transaction_scope,
        "transaction_scope_summary": transaction_scope_summary,
        "run_parameters_summary": run_parameters_summary,
        "readiness_summary": readiness_summary,
    }


def section_transaction_scope_validation(
    *,
    validation_status: str,
    scope_kind: str | None,
    errors: list[str],
    transaction_scope_hash: str,
) -> dict[str, Any]:
    """
    External-shareable transaction scope validation summary.
    """
    return {
        "section_id": "transaction_scope_validation",
        "section_type": "transaction_scope_validation",
        "validation_status": validation_status,
        "scope_kind": scope_kind,
        "errors": errors,
        "transaction_scope_hash": transaction_scope_hash,
    }


def section_execution_summary(
    *,
    result_set_id: str,
    findings_by_kind: dict[str, int],
    findings_by_severity: dict[str, int],
    optional_inputs_summary: dict[str, int],
) -> dict[str, Any]:
    """
    External-shareable execution summary (no internal provenance details).
    """
    return {
        "section_id": "execution_summary",
        "section_type": "execution_summary",
        "result_set_id": result_set_id,
        "findings_by_kind": findings_by_kind,
        "findings_by_severity": findings_by_severity,
        "optional_inputs_summary": optional_inputs_summary,
    }


def section_readiness_findings(
    *,
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Readiness findings section.
    
    Contains detailed readiness findings with evidence references.
    """
    return {
        "section_id": "readiness_findings",
        "section_type": "readiness_findings",
        "findings": findings,
        "finding_count": len(findings),
    }


def section_checklist_status(
    *,
    checklist_items: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Checklist status section.
    
    Contains readiness checklist items and their status.
    """
    return {
        "section_id": "checklist_status",
        "section_type": "checklist_status",
        "checklist_items": checklist_items,
        "total_items": len(checklist_items),
    }


def section_evidence_index(
    *,
    evidence_index: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Evidence index section.
    
    Contains references to all evidence bundles used in the report.
    """
    return {
        "section_id": "evidence_index",
        "section_type": "evidence_index",
        "evidence_index": evidence_index,
        "evidence_count": len(evidence_index),
    }


def section_limitations_uncertainty(
    *,
    limitations: list[str],
    assumption_keys: list[str],
) -> dict[str, Any]:
    """
    Limitations and uncertainty section.
    
    Contains explicit limitations and assumptions for the readiness assessment.
    """
    return {
        "section_id": "limitations_uncertainty",
        "section_type": "limitations_uncertainty",
        "limitations": limitations,
        "assumption_keys": assumption_keys,
    }


def section_run_parameters(
    *,
    transaction_scope: dict,
    parameters: dict,
    optional_inputs: dict,
    run_parameters_hash: str,
) -> dict[str, Any]:
    """
    Internal-only run parameter section.
    """
    return {
        "section_id": "run_parameters",
        "section_type": "run_parameters",
        "run_parameters_hash": run_parameters_hash,
        "transaction_scope": transaction_scope,
        "parameters": parameters,
        "optional_inputs": optional_inputs,
    }


def section_explicit_non_claims() -> dict[str, Any]:
    """
    Explicit non-claims section.
    
    Documents what the engine does NOT claim or assert.
    """
    return {
        "section_id": "explicit_non_claims",
        "section_type": "explicit_non_claims",
        "non_claims": [
            "No assertions of transaction readiness correctness",
            "No assertions of deal success probability",
            "No scoring, grading, or ranking of readiness",
            "No compliance assertions (legal, regulatory, accounting)",
            "No recommendations or decisioning",
            "No assertions of business outcome correctness",
        ],
    }

