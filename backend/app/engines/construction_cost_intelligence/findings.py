"""
Finding Persistence for Construction Cost Intelligence Engine

Persists variance and time-phased findings as FindingRecords with full traceability.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.evidence.models import FindingEvidenceLink, FindingRecord
from backend.app.core.evidence.service import create_finding, link_finding_to_evidence
from backend.app.engines.construction_cost_intelligence.errors import DatasetVersionMismatchError
from backend.app.engines.construction_cost_intelligence.variance.detector import CostVariance


ENGINE_ID = "engine_construction_cost_intelligence"

_FINDING_NAMESPACE = uuid.UUID("00000000-0000-0000-0000-000000000045")


def deterministic_finding_id(*, dataset_version_id: str, engine_id: str, kind: str, stable_key: str) -> str:
    """Generate deterministic finding ID."""
    return str(uuid.uuid5(_FINDING_NAMESPACE, f"{dataset_version_id}|{engine_id}|{kind}|{stable_key}"))


def deterministic_link_id(*, finding_id: str, evidence_id: str) -> str:
    """Generate deterministic link ID."""
    namespace = uuid.UUID("00000000-0000-0000-0000-000000000046")
    return str(uuid.uuid5(namespace, f"{finding_id}|{evidence_id}"))


def _stable_json_sha256(payload: dict) -> str:
    """Generate stable hash for payload."""
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _decimal_to_str(d: Decimal) -> str:
    """Convert Decimal to normalized string."""
    return str(d.normalize()) if d != d.to_integral() else str(d.to_integral())


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
    """Create finding with idempotency and immutability checks."""
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
    """Create finding-evidence link with idempotency."""
    link_id = deterministic_link_id(finding_id=finding_id, evidence_id=evidence_id)
    existing = await db.scalar(select(FindingEvidenceLink).where(FindingEvidenceLink.link_id == link_id))
    if existing is not None:
        if existing.finding_id != finding_id or existing.evidence_id != evidence_id:
            raise DatasetVersionMismatchError("IMMUTABLE_LINK_MISMATCH")
        return existing
    return await link_finding_to_evidence(db, link_id=link_id, finding_id=finding_id, evidence_id=evidence_id)


async def persist_variance_findings(
    db: AsyncSession,
    *,
    dataset_version_id: str,
    variances: list[CostVariance],
    raw_record_id: str,
    evidence_id: str,
    created_at: datetime,
) -> list[str]:
    """
    Persist variance findings as FindingRecords.
    
    Args:
        db: Database session
        dataset_version_id: DatasetVersion identifier
        variances: List of CostVariance objects to persist
        raw_record_id: Raw record ID to associate findings with (typically BOQ raw_record_id)
        evidence_id: Evidence ID to link findings to
        created_at: Deterministic timestamp
    
    Returns:
        List of finding IDs created
    """
    finding_ids: list[str] = []
    
    for variance in variances:
        # Determine finding kind based on scope_creep flag
        finding_kind = "scope_creep" if getattr(variance, "scope_creep", False) else "cost_variance"
        
        # Create finding payload
        payload = {
            "dataset_version_id": dataset_version_id,
            "kind": finding_kind,
            "match_key": variance.match_key,
            "category": variance.category,
            "estimated_cost": _decimal_to_str(variance.estimated_cost),
            "actual_cost": _decimal_to_str(variance.actual_cost),
            "variance_amount": _decimal_to_str(variance.variance_amount),
            "variance_percentage": _decimal_to_str(variance.variance_percentage),
            "severity": variance.severity.value,
            "direction": variance.direction.value,
            "line_ids_boq": list(variance.line_ids_boq),
            "line_ids_actual": list(variance.line_ids_actual),
            "identity": variance.identity or {},
            "attributes": variance.attributes or {},
        }
        
        # Generate stable key for deterministic finding ID
        stable_key = _stable_json_sha256(payload)
        finding_id = deterministic_finding_id(
            dataset_version_id=dataset_version_id,
            engine_id=ENGINE_ID,
            kind=finding_kind,
            stable_key=stable_key,
        )
        
        # Create finding
        await _strict_create_finding(
            db,
            finding_id=finding_id,
            dataset_version_id=dataset_version_id,
            raw_record_id=raw_record_id,
            kind=finding_kind,
            payload=payload,
            created_at=created_at,
        )
        
        # Link to evidence
        await _strict_link(db, finding_id=finding_id, evidence_id=evidence_id)
        
        finding_ids.append(finding_id)
    
    return finding_ids


async def persist_scope_creep_finding(
    db: AsyncSession,
    *,
    dataset_version_id: str,
    unmatched_actual_count: int,
    unmatched_line_ids: list[str],
    raw_record_id: str,
    evidence_id: str,
    created_at: datetime,
) -> str | None:
    """
    Persist scope creep finding for unmatched actual lines.
    
    Args:
        db: Database session
        dataset_version_id: DatasetVersion identifier
        unmatched_actual_count: Number of unmatched actual lines
        unmatched_line_ids: List of unmatched actual line IDs
        raw_record_id: Raw record ID to associate finding with (typically actual raw_record_id)
        evidence_id: Evidence ID to link finding to
        created_at: Deterministic timestamp
    
    Returns:
        Finding ID if scope creep detected, None otherwise
    """
    if unmatched_actual_count == 0:
        return None
    
    payload = {
        "dataset_version_id": dataset_version_id,
        "kind": "scope_creep",
        "count": unmatched_actual_count,
        "line_ids": unmatched_line_ids,
    }
    
    stable_key = _stable_json_sha256(payload)
    finding_id = deterministic_finding_id(
        dataset_version_id=dataset_version_id,
        engine_id=ENGINE_ID,
        kind="scope_creep",
        stable_key=stable_key,
    )
    
    await _strict_create_finding(
        db,
        finding_id=finding_id,
        dataset_version_id=dataset_version_id,
        raw_record_id=raw_record_id,
        kind="scope_creep",
        payload=payload,
        created_at=created_at,
    )
    
    await _strict_link(db, finding_id=finding_id, evidence_id=evidence_id)
    
    return finding_id


async def persist_time_phased_findings(
    db: AsyncSession,
    *,
    dataset_version_id: str,
    periods_with_variance: list[dict],
    raw_record_id: str,
    evidence_id: str,
    created_at: datetime,
) -> list[str]:
    """
    Persist time-phased findings for periods with significant variance.
    
    Args:
        db: Database session
        dataset_version_id: DatasetVersion identifier
        periods_with_variance: List of period dicts with variance information
        raw_record_id: Raw record ID to associate findings with
        evidence_id: Evidence ID to link findings to
        created_at: Deterministic timestamp
    
    Returns:
        List of finding IDs created
    """
    finding_ids: list[str] = []
    
    for period in periods_with_variance:
        payload = {
            "dataset_version_id": dataset_version_id,
            "kind": "time_phased_variance",
            "period": period.get("period"),
            "period_type": period.get("period_type"),
            "start_date": period.get("start_date"),
            "end_date": period.get("end_date"),
            "estimated_cost": period.get("estimated_cost"),
            "actual_cost": period.get("actual_cost"),
            "variance_amount": period.get("variance_amount"),
            "variance_percentage": period.get("variance_percentage"),
        }
        
        stable_key = _stable_json_sha256(payload)
        finding_id = deterministic_finding_id(
            dataset_version_id=dataset_version_id,
            engine_id=ENGINE_ID,
            kind="time_phased_variance",
            stable_key=stable_key,
        )
        
        await _strict_create_finding(
            db,
            finding_id=finding_id,
            dataset_version_id=dataset_version_id,
            raw_record_id=raw_record_id,
            kind="time_phased_variance",
            payload=payload,
            created_at=created_at,
        )
        
        await _strict_link(db, finding_id=finding_id, evidence_id=evidence_id)
        
        finding_ids.append(finding_id)
    
    return finding_ids

