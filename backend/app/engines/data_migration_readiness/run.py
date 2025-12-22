from __future__ import annotations

import inspect
import logging
from contextlib import asynccontextmanager
from dataclasses import fields, is_dataclass
from datetime import datetime, timezone
from decimal import Decimal
from types import MappingProxyType
from typing import AsyncContextManager, Mapping

from sqlalchemy import select

from backend.app.core.db import get_sessionmaker
from backend.app.core.dataset import immutability as dataset_immutability
from backend.app.core.dataset.models import DatasetVersion
from backend.app.core.dataset.raw_models import RawRecord
from backend.app.core.evidence.models import EvidenceRecord, FindingEvidenceLink, FindingRecord
from backend.app.core.evidence.service import (
    create_evidence,
    create_finding,
    deterministic_evidence_id,
    link_finding_to_evidence,
)
from backend.app.engines.data_migration_readiness.checks import (
    IntegrityCheck,
    MappingCheck,
    QualityCheck,
    RawRecordSnapshot,
    RiskSignal,
    StructuralCheck,
    assess_risks,
    build_collection_index,
    evaluate_mapping,
    evaluate_quality,
    evaluate_structure,
    load_default_config,
    snapshot_raw_records,
    verify_integrity,
)
from backend.app.engines.data_migration_readiness.errors import (
    DatasetVersionInvalidError,
    DatasetVersionMissingError,
    DatasetVersionNotFoundError,
    RawRecordsMissingError,
    StartedAtInvalidError,
    StartedAtMissingError,
)
from backend.app.engines.data_migration_readiness.ids import deterministic_id
from backend.app.engines.data_migration_readiness.models import (
    DataMigrationReadinessFinding,
    DataMigrationReadinessRun,
)

ENGINE_ID = "engine_data_migration_readiness"
ENGINE_VERSION = "v1"

logger = logging.getLogger(__name__)


def _safe_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _parse_started_at(value: object) -> datetime:
    if value is None:
        raise StartedAtMissingError("STARTED_AT_REQUIRED")
    if not isinstance(value, str) or not value.strip():
        raise StartedAtInvalidError("STARTED_AT_INVALID")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise StartedAtInvalidError("STARTED_AT_INVALID") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _validate_dataset_version_id(value: object) -> str:
    if value is None:
        raise DatasetVersionMissingError("DATASET_VERSION_ID_REQUIRED")
    if not isinstance(value, str) or not value.strip():
        raise DatasetVersionInvalidError("DATASET_VERSION_ID_INVALID")
    return value.strip()


def _normalize_value(value: object) -> object:
    if isinstance(value, Mapping):
        return {k: _normalize_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalize_value(v) for v in value]
    if isinstance(value, (int, float, str, bool)) or value is None:
        return value
    return float(value) if hasattr(value, "__float__") else value


def _serialize_result(data: object) -> object:
    if is_dataclass(data):
        return {field.name: _serialize_result(getattr(data, field.name)) for field in fields(data)}
    return _normalize_value(data)


def _ensure_async_context(session: object) -> AsyncContextManager:
    if hasattr(session, "__aenter__"):
        return session  # type: ignore[return-value]

    @asynccontextmanager
    async def _wrapped():
        try:
            yield session
        finally:
            close = getattr(session, "close", None)
            if close:
                result = close()
                if inspect.isawaitable(result):
                    await result

    return _wrapped()


async def _strict_create_evidence(
    db,
    *,
    evidence_id: str,
    dataset_version_id: str,
    kind: str,
    payload: dict,
    created_at: datetime,
) -> EvidenceRecord:
    existing = await db.scalar(select(EvidenceRecord).where(EvidenceRecord.evidence_id == evidence_id))
    if existing is not None:
        return existing
    return await create_evidence(
        db,
        evidence_id=evidence_id,
        dataset_version_id=dataset_version_id,
        engine_id=ENGINE_ID,
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


async def _strict_link(db, *, link_id: str, finding_id: str, evidence_id: str) -> FindingEvidenceLink:
    existing = await db.scalar(select(FindingEvidenceLink).where(FindingEvidenceLink.link_id == link_id))
    if existing is not None:
        return existing
    return await link_finding_to_evidence(db, link_id=link_id, finding_id=finding_id, evidence_id=evidence_id)


def _readiness_level(score: float) -> str:
    if score >= 90.0:
        return "optimal"
    if score >= 70.0:
        return "caution"
    return "critical"


def _component_scores(
    *,
    structure: StructuralCheck,
    quality: QualityCheck,
    mapping: MappingCheck,
    integrity: IntegrityCheck,
) -> dict[str, float]:
    comps = {
        "structure": 1.0 if structure.compliant else 0.0,
        "quality": float(min(quality.completeness_score, Decimal("1"))),
        "mapping": 1.0 if mapping.compliant else 0.0,
        "integrity": 1.0 if integrity.compliant else 0.0,
    }
    return {k: max(0.0, min(1.0, v)) for k, v in comps.items()}


def _build_remediation_tasks(
    *,
    dataset_version_id: str,
    structure: StructuralCheck,
    quality: QualityCheck,
    mapping: MappingCheck,
    integrity: IntegrityCheck,
    config: Mapping[str, object],
) -> list[dict[str, object]]:
    tasks: list[dict[str, object]] = []
    quality_thresholds = config.get("quality_thresholds", {})

    if structure.missing_collections or structure.metadata_issues:
        tasks.append(
            {
                "id": deterministic_id(dataset_version_id, "remediation", "structure"),
                "category": "structure",
                "severity": "high",
                "description": "Ensure all required collections and metadata keys are ingested.",
                "details": {
                    "missing_collections": structure.missing_collections,
                    "metadata_issues": structure.metadata_issues,
                },
                "status": "pending",
            }
        )

    critical_completeness = _safe_decimal(quality_thresholds.get("completeness", Decimal("1")))
    if quality.completeness_score < critical_completeness:
        tasks.append(
            {
                "id": deterministic_id(dataset_version_id, "remediation", "quality"),
                "category": "quality",
                "severity": "medium",
                "description": "Improve completeness of required fields across collections.",
                "details": {
                    "completeness_score": float(quality.completeness_score),
                    "target": float(critical_completeness),
                },
                "status": "pending",
            }
        )

    if mapping.missing_mappings:
        tasks.append(
            {
                "id": deterministic_id(dataset_version_id, "remediation", "mapping"),
                "category": "mapping",
                "severity": "medium",
                "description": "Add missing field mappings so the target schema can be satisfied.",
                "details": {"missing_mappings": mapping.missing_mappings},
                "status": "pending",
            }
        )

    if not integrity.compliant:
        tasks.append(
            {
                "id": deterministic_id(dataset_version_id, "remediation", "integrity"),
                "category": "integrity",
                "severity": "high",
                "description": "Resolve duplicate source identifiers or inconsistent records.",
                "details": {"duplicate_ratio": float(integrity.duplicate_ratio)},
                "status": "pending",
            }
        )

    if not tasks:
        tasks.append(
            {
                "id": deterministic_id(dataset_version_id, "remediation", "monitor"),
                "category": "monitoring",
                "severity": "low",
                "description": "Continue monitoring data quality and keep ingestion pipelines stable.",
                "details": {},
                "status": "completed",
            }
        )

    return tasks


async def run_readiness_check(
    *,
    dataset_version_id: object,
    started_at: object,
    parameters: dict | None = None,
) -> dict:
    dataset_immutability.install_immutability_guards()
    dv_id = _validate_dataset_version_id(dataset_version_id)
    started = _parse_started_at(started_at)
    params = parameters or {}
    config = load_default_config()
    overrides = params.get("config_overrides")
    if isinstance(overrides, dict):
        mutable = dict(config)
        mutable.update(overrides)
        config = MappingProxyType(mutable)

    sessionmaker = get_sessionmaker()
    session_candidate = sessionmaker()
    if inspect.isawaitable(session_candidate):
        session_candidate = await session_candidate  # type: ignore[assignment]
    session_context = _ensure_async_context(session_candidate)
    async with session_context as db:
        dv = await db.scalar(select(DatasetVersion).where(DatasetVersion.id == dv_id))
        if dv is None:
            raise DatasetVersionNotFoundError("DATASET_VERSION_NOT_FOUND")

        raw_records = (await db.scalars(select(RawRecord).where(RawRecord.dataset_version_id == dv_id))).all()
        if inspect.isawaitable(raw_records):
            raw_records = await raw_records  # type: ignore[assignment]
        if not raw_records:
            raise RawRecordsMissingError("RAW_RECORDS_REQUIRED")

        source_raw_id = raw_records[0].raw_record_id
        snapshots = snapshot_raw_records(dv_id, raw_records)
        collections = build_collection_index(snapshots)
        structure_result = evaluate_structure(dv_id, snapshots, collections, config)
        integrity_result = verify_integrity(dv_id, snapshots)
        quality_result = evaluate_quality(dv_id, collections, config, integrity_result.duplicate_ratio)
        mapping_result = evaluate_mapping(dv_id, collections, config)
        source_systems = tuple(sorted({snap.source_system for snap in snapshots if snap.source_system}))
        risks = assess_risks(
            dv_id,
            structure=structure_result,
            quality=quality_result,
            mapping=mapping_result,
            integrity=integrity_result,
            config=config,
            source_systems=source_systems,
        )

        component_scores = _component_scores(
            structure=structure_result,
            quality=quality_result,
            mapping=mapping_result,
            integrity=integrity_result,
        )
        readiness_score = round(sum(component_scores.values()) / len(component_scores) * 100, 2)
        readiness_level = _readiness_level(readiness_score)
        remediation_tasks = _build_remediation_tasks(
            dataset_version_id=dv_id,
            structure=structure_result,
            quality=quality_result,
            mapping=mapping_result,
            integrity=integrity_result,
            config=config,
        )

        run_id = deterministic_id(dv_id, "run", started.isoformat())
        run_record = DataMigrationReadinessRun(
            run_id=run_id,
            dataset_version_id=dv_id,
            started_at=started,
            status="issues" if risks else "ready",
            readiness_score=readiness_score,
            readiness_level=readiness_level,
            component_scores=component_scores,
            remediation_tasks=remediation_tasks,
            source_systems=list(source_systems),
            risk_count=len(risks),
            engine_version=ENGINE_VERSION,
        )
        db.add(run_record)
        await db.flush()

        finding_records: list[DataMigrationReadinessFinding] = []
        for risk in risks:
            risk_payload = {
                "risk": {
                    "category": risk.category,
                    "severity": risk.severity,
                    "description": risk.description,
                },
                "metadata": dict(risk.metadata),
                "source_systems": source_systems,
            }
            finding_id = risk.id
            evidence_id = deterministic_evidence_id(
                dataset_version_id=dv_id,
                engine_id=ENGINE_ID,
                kind="readiness_risk",
                stable_key=finding_id,
            )
            await _strict_create_evidence(
                db,
                evidence_id=evidence_id,
                dataset_version_id=dv_id,
                kind="readiness_risk",
                payload=risk_payload,
                created_at=started,
            )
            await _strict_create_finding(
                db,
                finding_id=finding_id,
                dataset_version_id=dv_id,
                raw_record_id=source_raw_id,
                kind="readiness_risk",
                payload=risk_payload,
                created_at=started,
            )
            link_id = deterministic_id(dv_id, "link", finding_id, evidence_id)
            await _strict_link(db, link_id=link_id, finding_id=finding_id, evidence_id=evidence_id)

            record = DataMigrationReadinessFinding(
                finding_id=finding_id,
                run_id=run_id,
                dataset_version_id=dv_id,
                category=risk.category,
                severity=risk.severity,
                description=risk.description,
                details=dict(risk.metadata),
                evidence_id=evidence_id,
                engine_version=ENGINE_VERSION,
            )
            db.add(record)
            finding_records.append(record)

        summary_payload = {
            "dataset_version_id": dv_id,
            "structure": _serialize_result(structure_result),
            "quality": _serialize_result(quality_result),
            "mapping": _serialize_result(mapping_result),
            "integrity": _serialize_result(integrity_result),
            "component_scores": component_scores,
            "readiness_score": readiness_score,
            "readiness_level": readiness_level,
            "remediation_tasks": remediation_tasks,
            "source_systems": source_systems,
            "assumptions": config.get("assumptions", {}),
        }
        summary_evidence_id = deterministic_evidence_id(
            dataset_version_id=dv_id,
            engine_id=ENGINE_ID,
            kind="readiness_summary",
            stable_key="v1",
        )
        await _strict_create_evidence(
            db,
            evidence_id=summary_evidence_id,
            dataset_version_id=dv_id,
            kind="readiness_summary",
            payload=summary_payload,
            created_at=started,
        )

        if risks:
            logger.warning(
                "DATA_MIGRATION_READINESS_RISKS dataset_version_id=%s source_systems=%s risks=%s",
                dv_id,
                source_systems,
                [risk.description for risk in risks],
            )

        await db.commit()

    return {
        "dataset_version_id": dv_id,
        "started_at": started.isoformat(),
        "run_id": run_id,
        "readiness_score": readiness_score,
        "readiness_level": readiness_level,
        "component_scores": component_scores,
        "remediation_tasks": remediation_tasks,
        "structure": _serialize_result(structure_result),
        "quality": _serialize_result(quality_result),
        "mapping": _serialize_result(mapping_result),
        "integrity": _serialize_result(integrity_result),
        "source_systems": source_systems,
        "risks": [_serialize_result(risk) for risk in risks],
        "assumptions": config.get("assumptions", {}),
        "summary_evidence_id": summary_evidence_id,
        "risk_evidence_ids": [deterministic_evidence_id(
            dataset_version_id=dv_id,
            engine_id=ENGINE_ID,
            kind="readiness_risk",
            stable_key=risk.id,
        ) for risk in risks],
    }
