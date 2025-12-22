from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Iterable

from sqlalchemy import select

from backend.app.core.db import get_sessionmaker
from backend.app.core.dataset.immutability import install_immutability_guards
from backend.app.core.dataset.models import DatasetVersion
from backend.app.core.dataset.raw_models import RawRecord
from backend.app.core.evidence.models import EvidenceRecord, FindingEvidenceLink, FindingRecord
from backend.app.core.evidence.service import (
    create_evidence,
    create_finding,
    deterministic_evidence_id,
    link_finding_to_evidence,
)
from backend.app.engines.regulatory_readiness.catalog import ControlCatalog
from backend.app.engines.regulatory_readiness.checks import ControlEvaluation, evaluate_controls
from backend.app.engines.regulatory_readiness.controls import (
    ControlCategory,
    ControlDefinition,
    ControlStatus,
    RiskType,
)
from backend.app.engines.regulatory_readiness.constants import (
    CONTROL_EVIDENCE_KIND,
    ENGINE_ID,
    FINDING_KIND,
    SYSTEM_EVIDENCE_KIND,
)
from backend.app.engines.regulatory_readiness.errors import (
    DatasetVersionInvalidError,
    DatasetVersionMissingError,
    DatasetVersionNotFoundError,
    ImmutableConflictError,
    RawRecordsMissingError,
    StartedAtInvalidError,
    StartedAtMissingError,
)
from backend.app.engines.regulatory_readiness.frameworks import (
    FrameworkCatalog,
    RegulatoryFramework,
    build_default_frameworks,
)
from backend.app.engines.regulatory_readiness.ids import deterministic_id
from backend.app.engines.regulatory_readiness.mapping import (
    ComplianceMapping,
    map_controls_to_frameworks,
)
from backend.app.engines.regulatory_readiness.models import (
    RegulatoryControl,
    RegulatoryGap,
    RegulatoryRemediationTask,
)

logger = logging.getLogger(__name__)


def _parse_started_at(value: object) -> datetime:
    if value is None:
        raise StartedAtMissingError("STARTED_AT_REQUIRED")
    if not isinstance(value, str) or not value.strip():
        raise StartedAtInvalidError("STARTED_AT_INVALID")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise StartedAtInvalidError("STARTED_AT_INVALID") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _validate_dataset_version_id(value: object) -> str:
    if value is None:
        raise DatasetVersionMissingError("DATASET_VERSION_ID_REQUIRED")
    if not isinstance(value, str):
        raise DatasetVersionInvalidError("DATASET_VERSION_ID_INVALID")
    trimmed = value.strip()
    if not trimmed:
        raise DatasetVersionInvalidError("DATASET_VERSION_ID_INVALID")
    return trimmed


def _extract_regulatory_payload(payload: dict) -> dict:
    if not isinstance(payload, dict):
        return {}
    candidate = payload.get("regulatory") or payload.get("regulatory_readiness")
    if isinstance(candidate, dict):
        return candidate
    return {}


def _extract_control_hints(*sources: Iterable[object]) -> dict[str, str]:
    hints: dict[str, str] = {}
    for source in sources:
        if not isinstance(source, dict):
            continue
        for key, value in source.items():
            if key is None or value is None:
                continue
            key_str = str(key).strip()
            val_str = str(value).strip()
            if key_str and val_str:
                hints[key_str] = val_str
    return hints


def _ensure_catalog_has_controls(
    catalog: ControlCatalog,
    frameworks: Iterable[RegulatoryFramework],
) -> None:
    if catalog.list_controls():
        return
    for framework in frameworks:
        catalog.register(
            ControlDefinition(
                control_id=f"default:{framework.framework_id}",
                title=f"Baseline coverage for {framework.name}",
                description="Auto-generated placeholder control to ensure mapping coverage.",
                category=ControlCategory.RISK_MANAGEMENT,
                risk_type=RiskType.COMPLIANCE,
                ownership=("regulatory_team",),
                status=ControlStatus.UNKNOWN,
                frameworks=(framework.framework_id,),
                tags=(framework.framework_id,),
            )
        )


def _severity_for_status(status: ControlStatus) -> str:
    if status == ControlStatus.NOT_IMPLEMENTED:
        return "high"
    if status == ControlStatus.PARTIAL:
        return "medium"
    return "low"


def _readiness_score_for_status(status: ControlStatus) -> float:
    return {
        ControlStatus.IMPLEMENTED: 1.0,
        ControlStatus.MONITORED: 0.75,
        ControlStatus.PARTIAL: 0.5,
        ControlStatus.NOT_IMPLEMENTED: 0.2,
        ControlStatus.UNKNOWN: 0.4,
    }.get(status, 0.5)


async def _persist_control_record(
    db,
    *,
    dataset_version_id: str,
    control_record_id: str,
    control: ControlDefinition,
    evaluation: ControlEvaluation,
    created_at: datetime,
) -> RegulatoryControl:
    existing = await db.scalar(
        select(RegulatoryControl).where(RegulatoryControl.control_record_id == control_record_id)
    )
    if existing is not None:
        return existing
    record = RegulatoryControl(
        control_record_id=control_record_id,
        dataset_version_id=dataset_version_id,
        control_id=control.control_id,
        title=control.title,
        description=control.description,
        category=control.category.value,
        risk_type=control.risk_type.value,
        control_status=evaluation.status.value,
        ownership=list(control.ownership),
        frameworks=list(control.frameworks),
        evaluation=evaluation.as_dict(),
        created_at=created_at,
    )
    db.add(record)
    return record


async def _persist_gap_and_task(
    db,
    *,
    dataset_version_id: str,
    control: ControlDefinition,
    control_record_id: str,
    evaluation: ControlEvaluation,
    mapping: ComplianceMapping,
    created_at: datetime,
) -> tuple[dict, dict]:
    gap_id = deterministic_id(dataset_version_id, "gap", control.control_id, mapping.framework_id)
    existing_gap = await db.scalar(select(RegulatoryGap).where(RegulatoryGap.gap_id == gap_id))
    severity = _severity_for_status(evaluation.status)
    gap_payload = {
        "gap_id": gap_id,
        "control_id": control.control_id,
        "framework_id": mapping.framework_id,
        "framework_name": mapping.framework_name,
        "severity": severity,
        "alignment_score": mapping.alignment_score,
        "notes": mapping.notes,
        "status": evaluation.status.value,
    }
    if existing_gap is None:
        gap = RegulatoryGap(
            gap_id=gap_id,
            dataset_version_id=dataset_version_id,
            control_record_id=control_record_id,
            control_id=control.control_id,
            framework_id=mapping.framework_id,
            framework_name=mapping.framework_name,
            severity=severity,
            alignment_score=mapping.alignment_score,
            notes=mapping.notes,
            status=evaluation.status.value,
            created_at=created_at,
        )
        db.add(gap)
    task_id = deterministic_id(dataset_version_id, "task", gap_id)
    existing_task = await db.scalar(
        select(RegulatoryRemediationTask).where(RegulatoryRemediationTask.task_id == task_id)
    )
    owner = control.ownership[0] if control.ownership else "regulatory_team"
    task_payload = {
        "task_id": task_id,
        "gap_id": gap_id,
        "control_id": control.control_id,
        "description": (
            f"Remediate {control.control_id} for {mapping.framework_name}: {mapping.notes}"
        ),
        "owner": owner,
        "status": "open",
    }
    if existing_task is None:
        task = RegulatoryRemediationTask(
            task_id=task_id,
            dataset_version_id=dataset_version_id,
            gap_id=gap_id,
            control_id=control.control_id,
            description=task_payload["description"],
            owner=owner,
            status="open",
            created_at=created_at,
        )
        db.add(task)
    return gap_payload, task_payload


async def _strict_create_evidence(
    db,
    *,
    evidence_id: str,
    dataset_version_id: str,
    engine_id: str,
    kind: str,
    payload: dict,
    created_at: datetime,
) -> EvidenceRecord:
    existing = await db.scalar(select(EvidenceRecord).where(EvidenceRecord.evidence_id == evidence_id))
    if existing is not None:
        if existing.dataset_version_id != dataset_version_id or existing.engine_id != engine_id or existing.kind != kind:
            logger.warning(
                "REGULATORY_IMMUTABLE_CONFLICT evidence_id_collision evidence_id=%s dataset_version_id=%s",
                evidence_id,
                dataset_version_id,
            )
            raise ImmutableConflictError("EVIDENCE_ID_COLLISION")
        existing_created_at = existing.created_at
        if existing_created_at.tzinfo is None:
            existing_created_at = existing_created_at.replace(tzinfo=timezone.utc)
        created_at_norm = created_at if created_at.tzinfo is not None else created_at.replace(tzinfo=timezone.utc)
        if existing_created_at != created_at_norm:
            logger.warning(
                "REGULATORY_IMMUTABLE_CONFLICT evidence_created_at_mismatch evidence_id=%s dataset_version_id=%s",
                evidence_id,
                dataset_version_id,
            )
            raise ImmutableConflictError("IMMUTABLE_EVIDENCE_CREATED_AT_MISMATCH")
        if existing.payload != payload:
            logger.warning(
                "REGULATORY_IMMUTABLE_CONFLICT evidence_payload_mismatch evidence_id=%s dataset_version_id=%s",
                evidence_id,
                dataset_version_id,
            )
            raise ImmutableConflictError("IMMUTABLE_EVIDENCE_MISMATCH")
        return existing
    return await create_evidence(
        db,
        evidence_id=evidence_id,
        dataset_version_id=dataset_version_id,
        engine_id=engine_id,
        kind=kind,
        payload=payload,
        created_at=created_at,
    )


async def _strict_create_finding(
    db,
    *,
    finding_id: str,
    dataset_version_id: str,
    raw_record_id: str,
    kind: str,
    payload: dict,
    created_at: datetime,
) -> FindingRecord:
    existing = await db.scalar(select(FindingRecord).where(FindingRecord.finding_id == finding_id))
    if existing is not None:
        if existing.dataset_version_id != dataset_version_id or existing.raw_record_id != raw_record_id or existing.kind != kind:
            logger.warning(
                "REGULATORY_IMMUTABLE_CONFLICT finding_id_collision finding_id=%s dataset_version_id=%s",
                finding_id,
                dataset_version_id,
            )
            raise ImmutableConflictError("FINDING_ID_COLLISION")
        if existing.payload != payload:
            logger.warning(
                "REGULATORY_IMMUTABLE_CONFLICT finding_payload_mismatch finding_id=%s dataset_version_id=%s",
                finding_id,
                dataset_version_id,
            )
            raise ImmutableConflictError("IMMUTABLE_FINDING_MISMATCH")
        return existing
    return await create_finding(
        db,
        finding_id=finding_id,
        dataset_version_id=dataset_version_id,
        raw_record_id=raw_record_id,
        kind=kind,
        payload=payload,
        created_at=created_at,
    )


async def _strict_link(
    db,
    *,
    link_id: str,
    finding_id: str,
    evidence_id: str,
) -> FindingEvidenceLink:
    existing = await db.scalar(select(FindingEvidenceLink).where(FindingEvidenceLink.link_id == link_id))
    if existing is not None:
        if existing.finding_id != finding_id or existing.evidence_id != evidence_id:
            logger.warning(
                "REGULATORY_IMMUTABLE_CONFLICT link_mismatch link_id=%s dataset_version_id=%s",
                link_id,
                "unknown",
            )
            raise ImmutableConflictError("IMMUTABLE_LINK_MISMATCH")
        return existing
    return await link_finding_to_evidence(db, link_id=link_id, finding_id=finding_id, evidence_id=evidence_id)


def _group_mappings_by_control(mappings: Iterable[ComplianceMapping]) -> dict[str, list[ComplianceMapping]]:
    grouped: dict[str, list[ComplianceMapping]] = {}
    for mapping in mappings:
        grouped.setdefault(mapping.control_id, []).append(mapping)
    return grouped


async def run_engine(*, dataset_version_id: object, started_at: object, parameters: dict | None = None) -> dict:
    install_immutability_guards()
    dv_id = _validate_dataset_version_id(dataset_version_id)
    started = _parse_started_at(started_at)
    params = parameters if isinstance(parameters, dict) else {}

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        dv = await db.scalar(select(DatasetVersion).where(DatasetVersion.id == dv_id))
        if dv is None:
            raise DatasetVersionNotFoundError("DATASET_VERSION_NOT_FOUND")

        raw_records = (await db.scalars(select(RawRecord).where(RawRecord.dataset_version_id == dv_id))).all()
        if not raw_records:
            raise RawRecordsMissingError("RAW_RECORDS_REQUIRED")

        primary_raw = raw_records[0]
        regulatory_payload = _extract_regulatory_payload(primary_raw.payload)
        warnings: list[str] = []
        if not regulatory_payload:
            warnings.append("REGULATORY_PAYLOAD_MISSING")

        catalog = ControlCatalog()
        control_payloads = regulatory_payload.get("controls")
        if isinstance(control_payloads, dict):
            control_payloads = [control_payloads]
        catalog.load_from_payloads(control_payloads)
        frameworks = build_default_frameworks()
        framework_catalog = FrameworkCatalog(frameworks)
        _ensure_catalog_has_controls(catalog, framework_catalog.list_frameworks())
        if not control_payloads:
            warnings.append("CONTROL_INVENTORY_MISSING")

        hints = _extract_control_hints(
            params.get("control_status_hints"),
            regulatory_payload.get("control_status_hints"),
        )

        controls = tuple(catalog.list_controls())
        evaluations = evaluate_controls(controls, evidence_hints=hints)
        evaluation_by_control = {evaluation.control_id: evaluation for evaluation in evaluations}
        evaluation_map = {evaluation.control_id: evaluation.status for evaluation in evaluations}
        readiness_scores = [_readiness_score_for_status(evaluation.status) for evaluation in evaluations]
        readiness_score = sum(readiness_scores) / len(readiness_scores) if readiness_scores else 0.0
        control_record_ids: dict[str, str] = {}
        for control in controls:
            control_record_id = deterministic_id(dv_id, "control", control.control_id)
            control_record_ids[control.control_id] = control_record_id
            evaluation = evaluation_by_control.get(control.control_id)
            if evaluation is None:
                continue
            await _persist_control_record(
                db,
                dataset_version_id=dv_id,
                control_record_id=control_record_id,
                control=control,
                evaluation=evaluation,
                created_at=started,
            )
        compliance_mappings = map_controls_to_frameworks(
            controls,
            framework_catalog.list_frameworks(),
            evaluations=evaluation_map,
        )

        mapping_index = _group_mappings_by_control(compliance_mappings)
        findings: list[dict] = []
        gaps: list[dict] = []
        remediation_tasks: list[dict] = []

        for evaluation in evaluations:
            if evaluation.status not in (ControlStatus.NOT_IMPLEMENTED, ControlStatus.PARTIAL):
                continue
            control = catalog.find(evaluation.control_id)
            if control is None:
                continue
            control_mapping_items = list(mapping_index.get(control.control_id, []))
            if not control_mapping_items:
                fallback_frameworks = control.frameworks or ("unmapped_framework",)
                control_mapping_items = [
                    ComplianceMapping(
                        control_id=control.control_id,
                        framework_id=framework,
                        framework_name=framework,
                        status=evaluation.status,
                        alignment_score=_readiness_score_for_status(evaluation.status),
                        notes="Framework inferred from control catalog.",
                    )
                    for framework in fallback_frameworks
                ]
            control_mapping = [mapping.as_dict() for mapping in control_mapping_items]
            control_record_id = control_record_ids.get(control.control_id)
            for mapping in control_mapping_items:
                gap_payload, task_payload = await _persist_gap_and_task(
                    db,
                    dataset_version_id=dv_id,
                    control=control,
                    control_record_id=control_record_id or deterministic_id(
                        dv_id,
                        "control",
                        control.control_id,
                    ),
                    evaluation=evaluation,
                    mapping=mapping,
                    created_at=started,
                )
                gaps.append(gap_payload)
                remediation_tasks.append(task_payload)
            finding_payload = {
                "control": control.as_dict(),
                "evaluation": evaluation.as_dict(),
                "framework_mappings": control_mapping,
                "recommendation": (
                    "Elevate control implementation plan and evidence capture." if evaluation.status == ControlStatus.NOT_IMPLEMENTED else "Strengthen existing control instrumentation."
                ),
                "data_flow": regulatory_payload.get("data_flow"),
            }
            finding_id = deterministic_id(dv_id, "finding", control.control_id)
            await _strict_create_finding(
                db,
                finding_id=finding_id,
                dataset_version_id=dv_id,
                raw_record_id=primary_raw.raw_record_id,
                kind=FINDING_KIND,
                payload=finding_payload,
                created_at=started,
            )
            evidence_id = deterministic_evidence_id(
                dataset_version_id=dv_id,
                engine_id=ENGINE_ID,
                kind=CONTROL_EVIDENCE_KIND,
                stable_key=control.control_id,
            )
            await _strict_create_evidence(
                db,
                evidence_id=evidence_id,
                dataset_version_id=dv_id,
                engine_id=ENGINE_ID,
                kind=CONTROL_EVIDENCE_KIND,
                payload={
                    "control": control.as_dict(),
                    "evaluation": evaluation.as_dict(),
                    "framework_mappings": control_mapping,
                    "source_raw_record_id": primary_raw.raw_record_id,
                },
                created_at=started,
            )
            link_id = deterministic_id(dv_id, "link", finding_id, evidence_id)
            await _strict_link(db, link_id=link_id, finding_id=finding_id, evidence_id=evidence_id)
            findings.append(
                {
                    "finding_id": finding_id,
                    "control_id": control.control_id,
                    "status": evaluation.status.value,
                    "rationale": evaluation.rationale,
                    "confidence": evaluation.confidence,
                }
            )

        control_summary = {
            "total_controls": len(controls),
            "status_distribution": catalog.status_distribution(),
            "gaps_detected": len(gaps),
            "open_remediation_tasks": len(remediation_tasks),
            "readiness_score": readiness_score,
        }

        compliance_snapshot_payload = {
            "dataset_version_id": dv_id,
            "control_summary": control_summary,
            "framework_mappings": [mapping.as_dict() for mapping in compliance_mappings],
            "control_evaluations": [evaluation.as_dict() for evaluation in evaluations],
            "findings": findings,
            "readiness_score": readiness_score,
            "regulatory_controls": [control.as_dict() for control in controls],
            "gaps": gaps,
            "remediation_tasks": remediation_tasks,
            "parameters": params,
            "regulatory_payload": regulatory_payload,
            "warnings": warnings,
            "source": {
                "raw_record_id": primary_raw.raw_record_id,
                "source_system": primary_raw.source_system,
            },
        }

        compliance_evidence_id = deterministic_evidence_id(
            dataset_version_id=dv_id,
            engine_id=ENGINE_ID,
            kind=SYSTEM_EVIDENCE_KIND,
            stable_key="compliance_snapshot",
        )
        await _strict_create_evidence(
            db,
            evidence_id=compliance_evidence_id,
            dataset_version_id=dv_id,
            engine_id=ENGINE_ID,
            kind=SYSTEM_EVIDENCE_KIND,
            payload=compliance_snapshot_payload,
            created_at=started,
        )

        await db.commit()

    return {
        "dataset_version_id": dv_id,
        "started_at": started.isoformat(),
        "control_summary": control_summary,
        "framework_mappings": [mapping.as_dict() for mapping in compliance_mappings],
        "control_evaluations": [evaluation.as_dict() for evaluation in evaluations],
        "findings": findings,
        "readiness_score": readiness_score,
        "gaps": gaps,
        "remediation_tasks": remediation_tasks,
        "compliance_evidence_id": compliance_evidence_id,
        "warnings": warnings,
    }
