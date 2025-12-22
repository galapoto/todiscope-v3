from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.evidence.models import EvidenceRecord, FindingEvidenceLink, FindingRecord
from backend.app.core.evidence.service import create_evidence, create_finding, deterministic_evidence_id, link_finding_to_evidence
from backend.app.engines.construction_cost_intelligence.errors import DatasetVersionMismatchError
from backend.app.engines.construction_cost_intelligence.models import ComparisonConfig, ComparisonResult, CostLine


ENGINE_ID = "engine_construction_cost_intelligence_core"


_FINDING_NAMESPACE = uuid.UUID("00000000-0000-0000-0000-000000000043")


def deterministic_finding_id(*, dataset_version_id: str, engine_id: str, kind: str, stable_key: str) -> str:
    return str(uuid.uuid5(_FINDING_NAMESPACE, f"{dataset_version_id}|{engine_id}|{kind}|{stable_key}"))


def deterministic_link_id(*, finding_id: str, evidence_id: str) -> str:
    namespace = uuid.UUID("00000000-0000-0000-0000-000000000044")
    return str(uuid.uuid5(namespace, f"{finding_id}|{evidence_id}"))


def _stable_json_sha256(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _line_ids(lines: tuple[CostLine, ...]) -> list[str]:
    return [ln.line_id for ln in lines]


def build_core_assumptions(*, dataset_version_id: str, config: ComparisonConfig) -> list[dict[str, Any]]:
    return [
        {
            "id": "dataset_version_binding",
            "description": "All inputs/outputs are bound to an explicit DatasetVersion identifier.",
            "source": "core",
            "impact": "Traceability; prevents cross-version mixing.",
            "dataset_version_id": dataset_version_id,
        },
        {
            "id": "identity_alignment",
            "description": "BOQ lines are aligned to Actual lines by exact match on configured identity_fields.",
            "source": "core",
            "impact": "Determines which lines are considered comparable.",
            "identity_fields": list(config.identity_fields),
        },
        {
            "id": "cost_basis",
            "description": "Effective cost is computed from total_cost and/or quantity*unit_cost depending on cost_basis.",
            "source": "core",
            "impact": "Controls how costs are derived for summation.",
            "cost_basis": config.cost_basis,
        },
        {
            "id": "incomplete_cost_handling",
            "description": (
                "When a line lacks the fields needed to compute an effective cost, it is excluded from the sum "
                "and counted as incomplete_cost_count."
            ),
            "source": "core",
            "impact": "Totals may be partial; incomplete counts indicate missing inputs.",
        },
        {
            "id": "breakdown_dimensions",
            "description": "Optional breakdown aggregates costs by configured breakdown_fields (no inference).",
            "source": "core",
            "impact": "Produces grouped totals without changing match semantics.",
            "breakdown_fields": list(config.breakdown_fields),
        },
    ]


@dataclass(frozen=True, slots=True)
class CoreMaterializationResult:
    dataset_version_id: str
    assumptions_evidence_id: str
    inputs_evidence_ids: tuple[str, ...]
    finding_ids: tuple[str, ...]


async def _strict_create_evidence(
    db: AsyncSession,
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
            raise DatasetVersionMismatchError("EVIDENCE_ID_COLLISION")
        if existing.payload != payload:
            raise DatasetVersionMismatchError("IMMUTABLE_EVIDENCE_MISMATCH")
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
    db: AsyncSession,
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
            raise DatasetVersionMismatchError("FINDING_ID_COLLISION")
        if existing.payload != payload:
            raise DatasetVersionMismatchError("IMMUTABLE_FINDING_MISMATCH")
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
    db: AsyncSession,
    *,
    finding_id: str,
    evidence_id: str,
) -> FindingEvidenceLink:
    link_id = deterministic_link_id(finding_id=finding_id, evidence_id=evidence_id)
    existing = await db.scalar(select(FindingEvidenceLink).where(FindingEvidenceLink.link_id == link_id))
    if existing is not None:
        if existing.finding_id != finding_id or existing.evidence_id != evidence_id:
            raise DatasetVersionMismatchError("IMMUTABLE_LINK_MISMATCH")
        return existing
    return await link_finding_to_evidence(db, link_id=link_id, finding_id=finding_id, evidence_id=evidence_id)


def _decimal_to_str(d: Decimal) -> str:
    return str(d.normalize()) if d != d.to_integral() else str(d.to_integral())


async def materialize_core_traceability(
    db: AsyncSession,
    *,
    dataset_version_id: str,
    created_at: datetime,
    config: ComparisonConfig,
    comparison_result: ComparisonResult,
    boq_raw_record_id: str,
    actual_raw_record_id: str,
) -> CoreMaterializationResult:
    """
    Persist evidence and data-quality findings for a core comparison result.

    This function does not change comparison semantics. It only:
    - records explicit assumptions
    - records input provenance evidence
    - emits deterministic findings for missing/partial inputs
    - links all findings to evidence (inputs + assumptions)
    """
    if comparison_result.dataset_version_id != dataset_version_id:
        raise DatasetVersionMismatchError("COMPARISON_RESULT_DATASET_VERSION_MISMATCH")

    assumptions = build_core_assumptions(dataset_version_id=dataset_version_id, config=config)
    assumptions_payload = {
        "dataset_version_id": dataset_version_id,
        "engine_id": ENGINE_ID,
        "assumptions": assumptions,
        "config": {
            "identity_fields": list(config.identity_fields),
            "cost_basis": config.cost_basis,
            "breakdown_fields": list(config.breakdown_fields),
        },
    }
    assumptions_key = _stable_json_sha256(assumptions_payload)
    assumptions_evidence_id = deterministic_evidence_id(
        dataset_version_id=dataset_version_id,
        engine_id=ENGINE_ID,
        kind="assumptions",
        stable_key=assumptions_key,
    )
    await _strict_create_evidence(
        db,
        evidence_id=assumptions_evidence_id,
        dataset_version_id=dataset_version_id,
        engine_id=ENGINE_ID,
        kind="assumptions",
        payload=assumptions_payload,
        created_at=created_at,
    )

    inputs_evidence_ids: list[str] = []
    for kind, raw_record_id in (("inputs_boq", boq_raw_record_id), ("inputs_actual", actual_raw_record_id)):
        payload = {"dataset_version_id": dataset_version_id, "raw_record_id": raw_record_id, "kind": kind}
        evidence_id = deterministic_evidence_id(
            dataset_version_id=dataset_version_id,
            engine_id=ENGINE_ID,
            kind=kind,
            stable_key=raw_record_id,
        )
        await _strict_create_evidence(
            db,
            evidence_id=evidence_id,
            dataset_version_id=dataset_version_id,
            engine_id=ENGINE_ID,
            kind=kind,
            payload=payload,
            created_at=created_at,
        )
        inputs_evidence_ids.append(evidence_id)

    finding_ids: list[str] = []

    if comparison_result.unmatched_boq:
        payload = {
            "dataset_version_id": dataset_version_id,
            "kind": "data_quality_unmatched_boq",
            "count": len(comparison_result.unmatched_boq),
            "line_ids": _line_ids(comparison_result.unmatched_boq),
        }
        stable_key = _stable_json_sha256(payload)
        finding_id = deterministic_finding_id(
            dataset_version_id=dataset_version_id, engine_id=ENGINE_ID, kind="data_quality_unmatched_boq", stable_key=stable_key
        )
        await _strict_create_finding(
            db,
            finding_id=finding_id,
            dataset_version_id=dataset_version_id,
            raw_record_id=boq_raw_record_id,
            kind="data_quality_unmatched_boq",
            payload=payload,
            created_at=created_at,
        )
        for evidence_id in (assumptions_evidence_id, *inputs_evidence_ids):
            await _strict_link(db, finding_id=finding_id, evidence_id=evidence_id)
        finding_ids.append(finding_id)

    if comparison_result.unmatched_actual:
        payload = {
            "dataset_version_id": dataset_version_id,
            "kind": "data_quality_unmatched_actual",
            "count": len(comparison_result.unmatched_actual),
            "line_ids": _line_ids(comparison_result.unmatched_actual),
        }
        stable_key = _stable_json_sha256(payload)
        finding_id = deterministic_finding_id(
            dataset_version_id=dataset_version_id,
            engine_id=ENGINE_ID,
            kind="data_quality_unmatched_actual",
            stable_key=stable_key,
        )
        await _strict_create_finding(
            db,
            finding_id=finding_id,
            dataset_version_id=dataset_version_id,
            raw_record_id=actual_raw_record_id,
            kind="data_quality_unmatched_actual",
            payload=payload,
            created_at=created_at,
        )
        for evidence_id in (assumptions_evidence_id, *inputs_evidence_ids):
            await _strict_link(db, finding_id=finding_id, evidence_id=evidence_id)
        finding_ids.append(finding_id)

    for match in comparison_result.matched:
        if match.boq_incomplete_cost_count == 0 and match.actual_incomplete_cost_count == 0:
            continue
        payload = {
            "dataset_version_id": dataset_version_id,
            "kind": "data_quality_incomplete_costs",
            "match_key": match.match_key,
            "boq_incomplete_cost_count": match.boq_incomplete_cost_count,
            "actual_incomplete_cost_count": match.actual_incomplete_cost_count,
            "boq_total_cost": _decimal_to_str(match.boq_total_cost),
            "actual_total_cost": _decimal_to_str(match.actual_total_cost),
            "boq_line_ids": _line_ids(match.boq_lines),
            "actual_line_ids": _line_ids(match.actual_lines),
        }
        stable_key = _stable_json_sha256(payload)
        finding_id = deterministic_finding_id(
            dataset_version_id=dataset_version_id,
            engine_id=ENGINE_ID,
            kind="data_quality_incomplete_costs",
            stable_key=stable_key,
        )
        raw_record_id = boq_raw_record_id if match.boq_incomplete_cost_count > 0 else actual_raw_record_id
        await _strict_create_finding(
            db,
            finding_id=finding_id,
            dataset_version_id=dataset_version_id,
            raw_record_id=raw_record_id,
            kind="data_quality_incomplete_costs",
            payload=payload,
            created_at=created_at,
        )
        for evidence_id in (assumptions_evidence_id, *inputs_evidence_ids):
            await _strict_link(db, finding_id=finding_id, evidence_id=evidence_id)
        finding_ids.append(finding_id)

    return CoreMaterializationResult(
        dataset_version_id=dataset_version_id,
        assumptions_evidence_id=assumptions_evidence_id,
        inputs_evidence_ids=tuple(inputs_evidence_ids),
        finding_ids=tuple(finding_ids),
    )

