"""
Report Assembler for Engine #5

Assembles transaction readiness reports from run data and findings.
Deterministic and replay-stable.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.evidence.models import EvidenceRecord
from backend.app.engines.enterprise_deal_transaction_readiness.ids import hash_run_parameters
from backend.app.engines.enterprise_deal_transaction_readiness.models.findings import (
    EnterpriseDealTransactionReadinessFinding,
)
from backend.app.engines.enterprise_deal_transaction_readiness.models.runs import (
    EnterpriseDealTransactionReadinessRun,
)
from backend.app.engines.enterprise_deal_transaction_readiness.report.sections import (
    section_checklist_status,
    section_evidence_index,
    section_explicit_non_claims,
    section_executive_overview,
    section_execution_summary,
    section_limitations_uncertainty,
    section_readiness_findings,
    section_transaction_scope_validation,
    section_run_parameters,
)


class ReportAssemblyError(RuntimeError):
    """Base error for report assembly failures."""
    pass


class RunNotFoundError(ReportAssemblyError):
    """Raised when run is not found."""
    pass


class DatasetVersionMismatchError(ReportAssemblyError):
    """Raised when run dataset_version_id doesn't match requested dataset_version_id."""
    pass


async def assemble_report(
    db: AsyncSession,
    *,
    dataset_version_id: str,
    run_id: str,
) -> dict:
    """
    Assemble transaction readiness report from run data.
    
    Args:
        db: Database session
        dataset_version_id: Dataset version ID
        run_id: Run ID
    
    Returns:
        Complete report dictionary
    
    Raises:
        RunNotFoundError: If run is not found
        DatasetVersionMismatchError: If run dataset_version_id doesn't match
    """
    # Fetch run
    run = await db.scalar(
        select(EnterpriseDealTransactionReadinessRun).where(
            EnterpriseDealTransactionReadinessRun.run_id == run_id
        )
    )
    if run is None:
        raise RunNotFoundError(f"RUN_NOT_FOUND: run_id '{run_id}' does not exist")
    
    if run.dataset_version_id != dataset_version_id:
        raise DatasetVersionMismatchError(
            f"RUN_DATASET_MISMATCH: run dataset_version_id '{run.dataset_version_id}' "
            f"does not match requested '{dataset_version_id}'"
        )
    
    findings_rows = (
        await db.execute(
            select(EnterpriseDealTransactionReadinessFinding)
            .where(EnterpriseDealTransactionReadinessFinding.result_set_id == run.result_set_id)
            .order_by(EnterpriseDealTransactionReadinessFinding.finding_id.asc())
        )
    ).scalars().all()

    findings: list[dict] = [
        {
            "finding_id": f.finding_id,
            "kind": f.kind,
            "severity": f.severity,
            "title": f.title,
            "detail": f.detail,
            "evidence_id": f.evidence_id,
        }
        for f in findings_rows
    ]
    checklist_items: list[dict] = []  # Will be populated when checklist is implemented
    
    # Build readiness summary
    high_count = sum(1 for f in findings_rows if f.severity == "high")
    findings_by_kind: dict[str, int] = {}
    findings_by_severity: dict[str, int] = {}
    for f in findings_rows:
        findings_by_kind[f.kind] = findings_by_kind.get(f.kind, 0) + 1
        findings_by_severity[f.severity] = findings_by_severity.get(f.severity, 0) + 1
    readiness_summary = {
        "total_findings": len(findings),
        "high_findings": high_count,
        "readiness_status": "ready" if high_count == 0 else "gaps_present",
        "checklist_completion": 0,  # Will be computed from checklist
    }
    
    evidence_ids = sorted({f.evidence_id for f in findings_rows})
    evidence_rows: list[EvidenceRecord] = []
    if evidence_ids:
        evidence_rows = (
            await db.execute(
                select(EvidenceRecord)
                .where(EvidenceRecord.evidence_id.in_(evidence_ids))
                .order_by(EvidenceRecord.evidence_id.asc())
            )
        ).scalars().all()

    evidence_index: list[dict] = [
        {
            "evidence_id": e.evidence_id,
            "kind": e.kind,
            "payload": e.payload,
        }
        for e in evidence_rows
    ]
    
    # Build limitations and assumptions from parameters
    limitations = [
        "Readiness assessment is limited to provided DatasetVersion",
        "Readiness assessment is limited to declared transaction scope (runtime parameter)",
        "Readiness assessment does not include external data enrichment",
    ]
    assumption_keys: list[str] = []
    if isinstance(run.parameters, dict):
        assumptions_dict = run.parameters.get("assumptions", {})
        if isinstance(assumptions_dict, dict):
            assumption_keys = sorted([str(k) for k in assumptions_dict.keys()])

    run_parameters_hash = hash_run_parameters(
        {
            "transaction_scope": run.transaction_scope,
            "parameters": run.parameters,
            "optional_inputs": run.optional_inputs,
        }
    )
    transaction_scope_summary = {
        "scope_kind": run.transaction_scope.get("scope_kind") if isinstance(run.transaction_scope, dict) else None,
        "transaction_scope_hash": hash_run_parameters(run.transaction_scope if isinstance(run.transaction_scope, dict) else {}),
    }
    run_parameters_summary = {
        "run_parameters_hash": run_parameters_hash,
        "parameter_keys": sorted([str(k) for k in (run.parameters or {}).keys()]) if isinstance(run.parameters, dict) else [],
        "optional_input_names": sorted([str(k) for k in (run.optional_inputs or {}).keys()]) if isinstance(run.optional_inputs, dict) else [],
    }

    # Transaction scope validation summary (explicit)
    scope_errors: list[str] = []
    scope_kind: str | None = None
    if isinstance(run.transaction_scope, dict):
        sk = run.transaction_scope.get("scope_kind")
        if isinstance(sk, str) and sk.strip():
            scope_kind = sk.strip()
        else:
            scope_errors.append("SCOPE_KIND_REQUIRED")
    else:
        scope_errors.append("TRANSACTION_SCOPE_INVALID_TYPE")
    scope_validation_status = "validated" if not scope_errors else "invalid"

    optional_inputs_summary = {
        "declared": len(run_parameters_summary["optional_input_names"]),
        "missing_prerequisite_findings": findings_by_kind.get("missing_prerequisite", 0),
        "checksum_mismatch_findings": findings_by_kind.get("prerequisite_checksum_mismatch", 0),
        "invalid_prerequisite_findings": findings_by_kind.get("prerequisite_invalid", 0),
    }
    
    # Assemble report sections
    sections = [
        section_executive_overview(
            dataset_version_id=dataset_version_id,
            run_id=run_id,
            transaction_scope=run.transaction_scope,
            readiness_summary=readiness_summary,
            transaction_scope_summary=transaction_scope_summary,
            run_parameters_summary=run_parameters_summary,
        ),
        section_transaction_scope_validation(
            validation_status=scope_validation_status,
            scope_kind=scope_kind,
            errors=scope_errors,
            transaction_scope_hash=transaction_scope_summary["transaction_scope_hash"],
        ),
        section_execution_summary(
            result_set_id=run.result_set_id,
            findings_by_kind={k: findings_by_kind[k] for k in sorted(findings_by_kind.keys())},
            findings_by_severity={k: findings_by_severity[k] for k in sorted(findings_by_severity.keys())},
            optional_inputs_summary=optional_inputs_summary,
        ),
        section_readiness_findings(findings=findings),
        section_checklist_status(checklist_items=checklist_items),
        section_evidence_index(evidence_index=evidence_index),
        section_limitations_uncertainty(limitations=limitations, assumption_keys=assumption_keys),
        section_run_parameters(
            transaction_scope=run.transaction_scope,
            parameters=run.parameters,
            optional_inputs=run.optional_inputs,
            run_parameters_hash=run_parameters_hash,
        ),
        section_explicit_non_claims(),
    ]
    
    return {
        "engine_id": "engine_enterprise_deal_transaction_readiness",
        "engine_version": run.engine_version,
        "dataset_version_id": dataset_version_id,
        "run_id": run_id,
        "result_set_id": run.result_set_id,
        "sections": sections,
    }





