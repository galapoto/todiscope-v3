"""
Evidence Emission for Construction Cost Intelligence Engine

Emits evidence bundles for variance detection and time-phased reporting.
All evidence is immutable, DatasetVersion-bound, and replay-stable.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.evidence.service import create_evidence, deterministic_evidence_id
from backend.app.engines.construction_cost_intelligence.assumptions import AssumptionRegistry


ENGINE_ID = "engine_construction_cost_intelligence"


async def emit_variance_analysis_evidence(
    db: AsyncSession,
    *,
    dataset_version_id: str,
    comparison_result_id: str,
    variance_count: int,
    scope_creep_count: int = 0,
    scope_creep_line_ids: list[str] | None = None,
    assumptions: AssumptionRegistry,
    created_at: datetime,
) -> str:
    """
    Emit evidence bundle for variance analysis.
    
    Args:
        db: Database session
        dataset_version_id: DatasetVersion identifier
        comparison_result_id: Identifier for the comparison result (stable key)
        variance_count: Number of variances detected
        assumptions: Assumption registry for variance analysis
        created_at: Deterministic timestamp
    
    Returns:
        Evidence ID
    """
    evidence_id = deterministic_evidence_id(
        dataset_version_id=dataset_version_id,
        engine_id=ENGINE_ID,
        kind="variance_analysis",
        stable_key=comparison_result_id,
    )
    
    payload = {
        "comparison_result_id": comparison_result_id,
        "variance_count": variance_count,
        "scope_creep": {
            "count": scope_creep_count,
            "line_ids": list(scope_creep_line_ids or []),
        },
        "assumptions": assumptions.to_dict(),
    }
    
    await create_evidence(
        db,
        evidence_id=evidence_id,
        dataset_version_id=dataset_version_id,
        engine_id=ENGINE_ID,
        kind="variance_analysis",
        payload=payload,
        created_at=created_at,
    )
    
    return evidence_id


async def emit_time_phased_report_evidence(
    db: AsyncSession,
    *,
    dataset_version_id: str,
    report_id: str,
    period_type: str,
    period_count: int,
    assumptions: AssumptionRegistry,
    created_at: datetime,
) -> str:
    """
    Emit evidence bundle for time-phased cost report.
    
    Args:
        db: Database session
        dataset_version_id: DatasetVersion identifier
        report_id: Identifier for the time-phased report (stable key)
        period_type: Type of time period aggregation
        period_count: Number of periods in the report
        assumptions: Assumption registry for time-phased reporting
        created_at: Deterministic timestamp
    
    Returns:
        Evidence ID
    """
    evidence_id = deterministic_evidence_id(
        dataset_version_id=dataset_version_id,
        engine_id=ENGINE_ID,
        kind="time_phased_report",
        stable_key=report_id,
    )
    
    payload = {
        "report_id": report_id,
        "period_type": period_type,
        "period_count": period_count,
        "assumptions": assumptions.to_dict(),
    }
    
    await create_evidence(
        db,
        evidence_id=evidence_id,
        dataset_version_id=dataset_version_id,
        engine_id=ENGINE_ID,
        kind="time_phased_report",
        payload=payload,
        created_at=created_at,
    )
    
    return evidence_id

