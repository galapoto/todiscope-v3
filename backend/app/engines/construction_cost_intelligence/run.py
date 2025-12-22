from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from sqlalchemy import select

from backend.app.core.dataset.immutability import install_immutability_guards
from backend.app.core.dataset.models import DatasetVersion
from backend.app.core.dataset.raw_models import RawRecord
from backend.app.core.db import get_sessionmaker
from backend.app.engines.construction_cost_intelligence.compare import compare_boq_to_actuals
from backend.app.engines.construction_cost_intelligence.errors import (
    DatasetVersionMismatchError,
    RawRecordInvalidError,
    RawRecordMissingError,
    StartedAtInvalidError,
    StartedAtMissingError,
)
from backend.app.engines.construction_cost_intelligence.models import (
    ComparisonConfig,
    NormalizationMapping,
    normalize_cost_lines,
    validate_dataset_version_id,
)
from backend.app.engines.construction_cost_intelligence.traceability import (
    ENGINE_ID,
    build_core_assumptions,
    materialize_core_traceability,
)


def _parse_started_at(value: object) -> datetime:
    if value is None:
        raise StartedAtMissingError("STARTED_AT_REQUIRED")
    if not isinstance(value, str) or not value.strip():
        raise StartedAtInvalidError("STARTED_AT_INVALID")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as e:
        raise StartedAtInvalidError("STARTED_AT_INVALID") from e
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _validate_raw_record_id(value: object, *, code: str) -> str:
    if value is None:
        raise RawRecordMissingError(code)
    if not isinstance(value, str) or not value.strip():
        raise RawRecordInvalidError(f"{code}_INVALID")
    return value.strip()


def _require_lines_payload(payload: Mapping[str, Any], *, code: str) -> list[Mapping[str, Any]]:
    lines = payload.get("lines")
    if not isinstance(lines, list):
        raise RawRecordInvalidError(code)
    if any(not isinstance(x, Mapping) for x in lines):
        raise RawRecordInvalidError(f"{code}_LINE_INVALID")
    return lines  # type: ignore[return-value]


def _parse_normalization_mapping(value: object) -> NormalizationMapping:
    if not isinstance(value, dict):
        raise RawRecordInvalidError("NORMALIZATION_MAPPING_REQUIRED")
    identity = value.get("identity")
    extras = value.get("extras", [])
    if extras is None:
        extras = []
    if not isinstance(extras, list) or any(not isinstance(x, str) for x in extras):
        raise RawRecordInvalidError("NORMALIZATION_MAPPING_EXTRAS_INVALID")
    return NormalizationMapping(
        line_id=value.get("line_id") or "line_id",
        identity=identity if isinstance(identity, dict) else {},
        quantity=value.get("quantity"),
        unit_cost=value.get("unit_cost"),
        total_cost=value.get("total_cost"),
        currency=value.get("currency"),
        extras=tuple(extras),
    )


def _parse_comparison_config(value: object) -> ComparisonConfig:
    if not isinstance(value, dict):
        raise RawRecordInvalidError("COMPARISON_CONFIG_REQUIRED")
    identity_fields = value.get("identity_fields")
    if not isinstance(identity_fields, list) or any(not isinstance(x, str) for x in identity_fields):
        raise RawRecordInvalidError("IDENTITY_FIELDS_REQUIRED")
    breakdown_fields = value.get("breakdown_fields", [])
    if breakdown_fields is None:
        breakdown_fields = []
    if not isinstance(breakdown_fields, list) or any(not isinstance(x, str) for x in breakdown_fields):
        raise RawRecordInvalidError("BREAKDOWN_FIELDS_INVALID")
    cost_basis = value.get("cost_basis", "prefer_total_cost")
    return ComparisonConfig(
        identity_fields=tuple(identity_fields),
        cost_basis=cost_basis,
        breakdown_fields=tuple(breakdown_fields),
    )


async def run_engine(
    *,
    dataset_version_id: object,
    started_at: object,
    boq_raw_record_id: object,
    actual_raw_record_id: object,
    normalization_mapping: object,
    comparison_config: object,
) -> dict:
    """
    Core-only engine run: loads BOQ + Actual inputs from RawRecords and emits traceability artifacts.

    Inputs:
    - `boq_raw_record_id` and `actual_raw_record_id` must reference RawRecords in the same DatasetVersion.
    - Each RawRecord payload must contain a `lines` array (list of dicts).
    """
    install_immutability_guards()
    dv_id = validate_dataset_version_id(dataset_version_id)
    started = _parse_started_at(started_at)
    boq_rr_id = _validate_raw_record_id(boq_raw_record_id, code="BOQ_RAW_RECORD_ID_REQUIRED")
    actual_rr_id = _validate_raw_record_id(actual_raw_record_id, code="ACTUAL_RAW_RECORD_ID_REQUIRED")

    mapping = _parse_normalization_mapping(normalization_mapping)
    cfg = _parse_comparison_config(comparison_config)

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        dv = await db.scalar(select(DatasetVersion).where(DatasetVersion.id == dv_id))
        if dv is None:
            raise DatasetVersionMismatchError("DATASET_VERSION_NOT_FOUND")

        boq_raw = await db.scalar(select(RawRecord).where(RawRecord.raw_record_id == boq_rr_id))
        if boq_raw is None:
            raise RawRecordMissingError("BOQ_RAW_RECORD_NOT_FOUND")
        actual_raw = await db.scalar(select(RawRecord).where(RawRecord.raw_record_id == actual_rr_id))
        if actual_raw is None:
            raise RawRecordMissingError("ACTUAL_RAW_RECORD_NOT_FOUND")

        if boq_raw.dataset_version_id != dv_id or actual_raw.dataset_version_id != dv_id:
            raise DatasetVersionMismatchError("RAW_RECORD_DATASET_VERSION_MISMATCH")

        boq_lines_raw = _require_lines_payload(boq_raw.payload, code="BOQ_LINES_REQUIRED")
        actual_lines_raw = _require_lines_payload(actual_raw.payload, code="ACTUAL_LINES_REQUIRED")

        boq_lines = normalize_cost_lines(dataset_version_id=dv_id, kind="boq", raw_lines=boq_lines_raw, mapping=mapping)
        actual_lines = normalize_cost_lines(
            dataset_version_id=dv_id, kind="actual", raw_lines=actual_lines_raw, mapping=mapping
        )
        comparison = compare_boq_to_actuals(dataset_version_id=dv_id, boq_lines=boq_lines, actual_lines=actual_lines, config=cfg)

        materialization = await materialize_core_traceability(
            db,
            dataset_version_id=dv_id,
            created_at=started,
            config=cfg,
            comparison_result=comparison,
            boq_raw_record_id=boq_rr_id,
            actual_raw_record_id=actual_rr_id,
        )
        await db.commit()

    assumptions = build_core_assumptions(dataset_version_id=dv_id, config=cfg)

    return {
        "engine_id": ENGINE_ID,
        "dataset_version_id": dv_id,
        "started_at": started.isoformat(),
        "assumptions": assumptions,
        "traceability": {
            "assumptions_evidence_id": materialization.assumptions_evidence_id,
            "inputs_evidence_ids": list(materialization.inputs_evidence_ids),
            "finding_ids": list(materialization.finding_ids),
        },
        "comparison": {
            "identity_fields": list(comparison.identity_fields),
            "breakdown_fields": list(comparison.breakdown_fields),
            "cost_basis": comparison.cost_basis,
            "matched_count": len(comparison.matched),
            "unmatched_boq_count": len(comparison.unmatched_boq),
            "unmatched_actual_count": len(comparison.unmatched_actual),
            "breakdown_count": len(comparison.breakdowns),
        },
    }
