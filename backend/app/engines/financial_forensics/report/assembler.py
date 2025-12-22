from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.evidence.models import EvidenceRecord
from backend.app.engines.financial_forensics.failures import MissingArtifactError, InconsistentReferenceError, RuntimeLimitError
from backend.app.engines.financial_forensics.models.findings import FinancialForensicsFinding
from backend.app.engines.financial_forensics.models.leakage import FinancialForensicsLeakageItem
from backend.app.engines.financial_forensics.models.runs import FinancialForensicsRun
from backend.app.engines.financial_forensics.report.sections import (
    section_evidence_index,
    section_executive_overview,
    section_exposure_summary,
    section_findings_table,
    section_leakage_breakdown,
)
from backend.app.engines.financial_forensics.runtime_limits import limits_from_parameters


async def assemble_report(
    db: AsyncSession,
    *,
    dataset_version_id: str,
    run_id: str,
    parameters: dict,
) -> dict:
    limits = limits_from_parameters(parameters or {})

    run = await db.scalar(select(FinancialForensicsRun).where(FinancialForensicsRun.run_id == run_id))
    if run is None:
        raise MissingArtifactError("RUN_NOT_FOUND")
    if run.dataset_version_id != dataset_version_id:
        raise InconsistentReferenceError("RUN_DATASET_MISMATCH")

    findings = (
        await db.execute(
            select(FinancialForensicsFinding)
            .where(FinancialForensicsFinding.run_id == run_id)
            .order_by(FinancialForensicsFinding.rule_id.asc(), FinancialForensicsFinding.finding_id.asc())
        )
    ).scalars().all()

    if len(findings) > limits.max_report_findings:
        raise RuntimeLimitError("RUNTIME_LIMIT_EXCEEDED: max_report_findings")

    leakage_items = (
        await db.execute(
            select(FinancialForensicsLeakageItem)
            .where(FinancialForensicsLeakageItem.run_id == run_id)
            .order_by(FinancialForensicsLeakageItem.typology.asc(), FinancialForensicsLeakageItem.finding_id.asc())
        )
    ).scalars().all()
    if len(leakage_items) != len(findings):
        raise MissingArtifactError("MISSING_LEAKAGE_ITEMS_FOR_RUN")

    # Evidence index: collect primary evidence ids from findings.
    evidence_ids = sorted({f.primary_evidence_item_id for f in findings})
    evidences = (
        await db.execute(
            select(EvidenceRecord)
            .where(EvidenceRecord.evidence_id.in_(evidence_ids))
            .order_by(EvidenceRecord.evidence_id.asc())
        )
    ).scalars().all()
    if len(evidences) != len(evidence_ids):
        raise MissingArtifactError("MISSING_EVIDENCE_FOR_RUN")

    # Build deterministic leakage rollups
    buckets: dict[str, tuple[int, Decimal]] = {}
    total_exposure = Decimal("0")
    for li in leakage_items:
        count, total = buckets.get(li.typology, (0, Decimal("0")))
        buckets[li.typology] = (count + 1, total + Decimal(li.exposure_abs))
        total_exposure += Decimal(li.exposure_abs)

    leakage_breakdown = [
        {"typology": t, "finding_count": buckets[t][0], "total_exposure_abs": str(buckets[t][1])}
        for t in sorted(buckets.keys())
    ]

    findings_rows = []
    leakage_by_finding = {li.finding_id: li for li in leakage_items}
    for f in findings:
        li = leakage_by_finding[f.finding_id]
        findings_rows.append(
            {
                "finding_id": f.finding_id,
                "rule_id": f.rule_id,
                "rule_version": f.rule_version,
                "framework_version": f.framework_version,
                "confidence": f.confidence,
                "finding_type": f.finding_type,
                "matched_record_ids": list(f.matched_record_ids),
                "unmatched_amount": f.unmatched_amount,
                "typology": li.typology,
                "exposure_abs": str(li.exposure_abs),
                "exposure_signed": str(li.exposure_signed),
                "primary_evidence_item_id": f.primary_evidence_item_id,
            }
        )

    evidence_index = [
        {"evidence_id": e.evidence_id, "kind": e.kind, "engine_id": e.engine_id, "created_at": e.created_at.isoformat()}
        for e in evidences
    ]

    totals = {"finding_count": len(findings), "total_exposure_abs": str(total_exposure)}

    return {
        "engine_id": "engine_financial_forensics",
        "engine_version": run.engine_version,
        "dataset_version_id": dataset_version_id,
        "run_id": run_id,
        "sections": [
            section_executive_overview(dataset_version_id=dataset_version_id, run_id=run_id, totals=totals),
            section_leakage_breakdown(rows=leakage_breakdown),
            section_exposure_summary(total_exposure_abs=str(total_exposure)),
            section_findings_table(findings=findings_rows),
            section_evidence_index(evidence_index=evidence_index),
        ],
    }

