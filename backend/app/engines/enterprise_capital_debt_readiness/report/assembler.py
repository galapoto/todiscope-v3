"""
Report Assembler for Enterprise Capital & Debt Readiness Engine

Assembles comprehensive reports from engine evidence records.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.evidence.models import EvidenceRecord


class ReportAssemblyError(RuntimeError):
    """Base error for report assembly"""
    pass


class EvidenceNotFoundError(ReportAssemblyError):
    """Evidence record not found"""
    pass


class DatasetVersionMismatchError(ReportAssemblyError):
    """Evidence dataset_version_id mismatch"""
    pass


async def assemble_report(
    db: AsyncSession,
    *,
    dataset_version_id: str,
) -> dict:
    """
    Assemble comprehensive report from evidence records.
    
    Args:
        db: Database session
        dataset_version_id: Dataset version ID
    
    Returns:
        Complete report dictionary with all sections
    
    Raises:
        EvidenceNotFoundError: If required evidence is missing
        DatasetVersionMismatchError: If evidence dataset_version_id doesn't match
    """
    engine_id = "engine_enterprise_capital_debt_readiness"
    
    # Load evidence records
    evidence_records = (
        await db.execute(
            select(EvidenceRecord)
            .where(
                EvidenceRecord.dataset_version_id == dataset_version_id,
                EvidenceRecord.engine_id == engine_id,
            )
            .order_by(EvidenceRecord.kind.asc(), EvidenceRecord.created_at.asc())
        )
    ).scalars().all()
    
    if not evidence_records:
        raise EvidenceNotFoundError(f"NO_EVIDENCE_FOUND: dataset_version_id={dataset_version_id}")
    
    # Verify all evidence belongs to the same dataset_version_id
    for ev in evidence_records:
        if ev.dataset_version_id != dataset_version_id:
            raise DatasetVersionMismatchError(
                f"EVIDENCE_DATASET_MISMATCH: evidence_id={ev.evidence_id} "
                f"dataset_version_id={ev.dataset_version_id} != {dataset_version_id}"
            )
    
    # Organize evidence by kind
    evidence_by_kind: dict[str, EvidenceRecord] = {}
    for ev in evidence_records:
        if ev.kind not in evidence_by_kind:
            evidence_by_kind[ev.kind] = ev
    
    # Extract payloads
    summary_evidence = evidence_by_kind.get("summary")
    if not summary_evidence:
        raise EvidenceNotFoundError("SUMMARY_EVIDENCE_NOT_FOUND")
    
    summary_payload = summary_evidence.payload.get("summary", {})
    
    capital_evidence = evidence_by_kind.get("capital_adequacy")
    debt_evidence = evidence_by_kind.get("debt_service")
    readiness_evidence = evidence_by_kind.get("readiness_score")
    scenario_evidence = evidence_by_kind.get("scenario_analysis")
    
    # Build report sections
    from backend.app.engines.enterprise_capital_debt_readiness.report.sections import (
        section_capital_adequacy,
        section_debt_service,
        section_readiness_score,
        section_scenario_analysis,
        section_executive_summary,
    )
    
    report = {
        "dataset_version_id": dataset_version_id,
        "analysis_date": summary_payload.get("analysis_date"),
        "sections": {
            "executive_summary": section_executive_summary(
                summary_payload=summary_payload,
            ),
            "capital_adequacy": section_capital_adequacy(
                capital_payload=capital_evidence.payload if capital_evidence else {},
            ) if capital_evidence else None,
            "debt_service": section_debt_service(
                debt_payload=debt_evidence.payload if debt_evidence else {},
            ) if debt_evidence else None,
            "readiness_score": section_readiness_score(
                readiness_payload=readiness_evidence.payload if readiness_evidence else {},
            ) if readiness_evidence else None,
            "scenario_analysis": section_scenario_analysis(
                scenario_payload=scenario_evidence.payload if scenario_evidence else {},
            ) if scenario_evidence else None,
        },
        "evidence_ids": {
            "summary": summary_evidence.evidence_id,
            "capital_adequacy": capital_evidence.evidence_id if capital_evidence else None,
            "debt_service": debt_evidence.evidence_id if debt_evidence else None,
            "readiness_score": readiness_evidence.evidence_id if readiness_evidence else None,
            "scenario_analysis": scenario_evidence.evidence_id if scenario_evidence else None,
        },
    }
    
    return report






