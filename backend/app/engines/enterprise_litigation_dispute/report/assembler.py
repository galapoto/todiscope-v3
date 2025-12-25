"""Report assembler for Enterprise Litigation & Dispute Analysis Engine."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.evidence.aggregation import (
    get_evidence_by_dataset_version,
    get_evidence_for_findings,
    get_findings_by_dataset_version,
    verify_evidence_traceability,
)
from backend.app.core.evidence.models import EvidenceRecord, FindingRecord
from backend.app.engines.enterprise_litigation_dispute.constants import ENGINE_ID, ENGINE_VERSION


class ReportAssemblyError(Exception):
    """Base exception for report assembly errors."""


class FindingsNotFoundError(ReportAssemblyError):
    """Raised when no findings are found for the dataset version."""


class EvidenceNotFoundError(ReportAssemblyError):
    """Raised when required evidence is not found."""


async def assemble_report(
    db: AsyncSession,
    *,
    dataset_version_id: str,
) -> dict[str, Any]:
    """
    Assemble litigation dispute analysis report from findings and evidence.
    
    Args:
        db: Database session
        dataset_version_id: Dataset version ID
        
    Returns:
        Complete report dictionary with:
        - metadata: Report metadata
        - executive_summary: High-level summary
        - damage_assessment: Damage quantification results
        - liability_assessment: Liability assessment results
        - scenario_comparison: Scenario comparison results
        - legal_consistency: Legal consistency check results
        - findings: Detailed findings
        - evidence_index: Evidence references
        - assumptions: Documented assumptions
        - limitations: Report limitations
        
    Raises:
        FindingsNotFoundError: If no findings found for dataset version
        EvidenceNotFoundError: If required evidence is missing
    """
    # Verify evidence traceability
    traceability_result = await verify_evidence_traceability(
        db, dataset_version_id=dataset_version_id
    )
    
    if not traceability_result["valid"]:
        raise ReportAssemblyError(
            f"Evidence traceability verification failed: {traceability_result['mismatches']}"
        )
    
    # Get all findings for this dataset version and engine
    findings = await get_findings_by_dataset_version(db, dataset_version_id=dataset_version_id)
    
    # Filter findings to this engine only
    engine_findings = [
        f for f in findings
        if f.kind in ("legal_damage", "liability", "scenario_analysis", "legal_consistency")
    ]
    
    if not engine_findings:
        raise FindingsNotFoundError(
            f"No findings found for dataset_version_id '{dataset_version_id}' and engine '{ENGINE_ID}'"
        )
    
    # Get evidence for findings
    finding_ids = [f.finding_id for f in engine_findings]
    evidence_by_finding = await get_evidence_for_findings(
        db, finding_ids=finding_ids, dataset_version_id=dataset_version_id
    )
    
    # Get all evidence for this dataset version and engine
    all_evidence = await get_evidence_by_dataset_version(
        db, dataset_version_id=dataset_version_id
    )
    engine_evidence = [e for e in all_evidence if e.engine_id == ENGINE_ID]
    
    if not engine_evidence:
        raise EvidenceNotFoundError(
            f"No evidence found for dataset_version_id '{dataset_version_id}' and engine '{ENGINE_ID}'"
        )
    
    # Organize evidence by kind
    evidence_by_kind: dict[str, list[EvidenceRecord]] = {}
    for evidence in engine_evidence:
        if evidence.kind not in evidence_by_kind:
            evidence_by_kind[evidence.kind] = []
        evidence_by_kind[evidence.kind].append(evidence)
    
    # Extract analysis results from evidence
    damage_assessment: dict[str, Any] | None = None
    liability_assessment: dict[str, Any] | None = None
    scenario_comparison: dict[str, Any] | None = None
    legal_consistency: dict[str, Any] | None = None
    
    for evidence in engine_evidence:
        payload = evidence.payload
        if isinstance(payload, dict):
            if evidence.kind == "damage" and "damage" in payload:
                damage_assessment = payload["damage"]
            elif evidence.kind == "liability" and "liability" in payload:
                liability_assessment = payload["liability"]
            elif evidence.kind == "scenario" and "scenario" in payload:
                scenario_comparison = payload["scenario"]
            elif evidence.kind == "legal_consistency" and "legal_consistency" in payload:
                legal_consistency = payload["legal_consistency"]
    
    # Build findings details
    findings_details: list[dict[str, Any]] = []
    for finding in engine_findings:
        evidence_records = evidence_by_finding.get(finding.finding_id, [])
        finding_detail = {
            "finding_id": finding.finding_id,
            "kind": finding.kind,
            "category": finding.kind,
            "title": finding.payload.get("title") if isinstance(finding.payload, dict) else None,
            "description": finding.payload.get("description") if isinstance(finding.payload, dict) else None,
            "value": finding.payload.get("value") if isinstance(finding.payload, dict) else None,
            "status": finding.payload.get("status") if isinstance(finding.payload, dict) else None,
            "confidence": finding.payload.get("confidence") if isinstance(finding.payload, dict) else None,
            "details": finding.payload.get("details") if isinstance(finding.payload, dict) else None,
            "evidence_ids": [e.evidence_id for e in evidence_records],
            "created_at": finding.created_at.isoformat(),
        }
        findings_details.append(finding_detail)
    
    # Build evidence index
    evidence_index: list[dict[str, Any]] = []
    for evidence in sorted(engine_evidence, key=lambda e: (e.kind, e.created_at)):
        evidence_index.append({
            "evidence_id": evidence.evidence_id,
            "kind": evidence.kind,
            "engine_id": evidence.engine_id,
            "dataset_version_id": evidence.dataset_version_id,
            "created_at": evidence.created_at.isoformat(),
        })
    
    # Collect all assumptions
    all_assumptions: list[dict[str, str]] = []
    for evidence in engine_evidence:
        payload = evidence.payload
        if isinstance(payload, dict):
            assumptions = payload.get("assumptions")
            if isinstance(assumptions, list):
                for assumption in assumptions:
                    if isinstance(assumption, dict) and assumption not in all_assumptions:
                        all_assumptions.append(assumption)
    
    # Build executive summary
    total_findings = len(engine_findings)
    findings_by_kind: dict[str, int] = {}
    for finding in engine_findings:
        findings_by_kind[finding.kind] = findings_by_kind.get(finding.kind, 0) + 1
    
    executive_summary = {
        "total_findings": total_findings,
        "findings_by_kind": findings_by_kind,
        "total_evidence_items": len(engine_evidence),
        "evidence_kinds": sorted(set(e.kind for e in engine_evidence)),
    }
    
    if damage_assessment:
        executive_summary["net_damage"] = damage_assessment.get("net_damage")
        executive_summary["damage_severity"] = damage_assessment.get("severity")
    
    if liability_assessment:
        executive_summary["responsible_party"] = liability_assessment.get("responsible_party")
        executive_summary["liability_strength"] = liability_assessment.get("liability_strength")
    
    if scenario_comparison:
        executive_summary["scenario_count"] = len(scenario_comparison.get("scenarios", []))
        if scenario_comparison.get("best_case"):
            executive_summary["best_case_expected_loss"] = scenario_comparison["best_case"].get("expected_loss")
        if scenario_comparison.get("worst_case"):
            executive_summary["worst_case_expected_loss"] = scenario_comparison["worst_case"].get("expected_loss")
    
    if legal_consistency:
        executive_summary["legal_consistency_status"] = "consistent" if legal_consistency.get("consistent") else "inconsistent"
        executive_summary["legal_issues_count"] = len(legal_consistency.get("issues", []))
    
    # Build limitations
    limitations = [
        "This report is generated from findings and evidence bound to a specific DatasetVersion.",
        "Findings are presented as scenarios or ranges, not definitive conclusions.",
        "All findings are immutable once created and bound to DatasetVersion.",
        "Evidence traceability is verified for all findings.",
        "Assumptions are explicitly documented and may affect findings.",
        "This report is for litigation support purposes and does not constitute legal advice.",
        "Report does not assert data correctness, completeness, suitability, or compliance.",
    ]
    
    # Assemble report
    report: dict[str, Any] = {
        "metadata": {
            "engine_id": ENGINE_ID,
            "engine_version": ENGINE_VERSION,
            "dataset_version_id": dataset_version_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "report_type": "litigation_dispute_analysis",
        },
        "executive_summary": executive_summary,
        "findings": findings_details,
        "evidence_index": evidence_index,
        "assumptions": all_assumptions,
        "limitations": limitations,
    }
    
    # Add analysis results if available
    if damage_assessment:
        report["damage_assessment"] = damage_assessment
    
    if liability_assessment:
        report["liability_assessment"] = liability_assessment
    
    if scenario_comparison:
        report["scenario_comparison"] = scenario_comparison
    
    if legal_consistency:
        report["legal_consistency"] = legal_consistency
    
    return report






