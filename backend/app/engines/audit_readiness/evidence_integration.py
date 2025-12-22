"""
Evidence Storage Integration for Audit Readiness Engine

Integrates with core evidence storage mechanisms to link evidence to
DatasetVersion and regulatory check results.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.evidence.models import EvidenceRecord, FindingEvidenceLink, FindingRecord
from backend.app.core.evidence.service import (
    create_evidence,
    create_finding,
    deterministic_evidence_id,
    link_finding_to_evidence,
)
from backend.app.engines.audit_readiness.errors import EvidenceStorageError, ImmutableConflictError
from backend.app.engines.audit_readiness.ids import deterministic_id


async def get_evidence_for_dataset_version(
    db: AsyncSession,
    dataset_version_id: str,
    engine_id: str | None = None,
    kind: str | None = None,
) -> list[EvidenceRecord]:
    """
    Retrieve evidence records for a dataset version.
    
    Args:
        db: Database session
        dataset_version_id: Dataset version ID
        engine_id: Optional engine ID filter
        kind: Optional evidence kind filter
    
    Returns:
        List of evidence records
    """
    query = select(EvidenceRecord).where(EvidenceRecord.dataset_version_id == dataset_version_id)
    
    if engine_id:
        query = query.where(EvidenceRecord.engine_id == engine_id)
    
    if kind:
        query = query.where(EvidenceRecord.kind == kind)
    
    result = await db.scalars(query)
    return list(result.all())


async def map_evidence_to_controls(
    db: AsyncSession,
    dataset_version_id: str,
    control_catalog: dict[str, Any],
) -> dict[str, list[str]]:
    """
    Map available evidence to controls based on evidence metadata.
    
    This function examines evidence records and maps them to control IDs
    based on evidence kind and payload metadata.
    
    Args:
        db: Database session
        dataset_version_id: Dataset version ID
        control_catalog: Control catalog structure
    
    Returns:
        Map of control_id to list of evidence_ids
    """
    evidence_records = await get_evidence_for_dataset_version(db, dataset_version_id)
    
    evidence_map: dict[str, list[str]] = {}
    
    # Extract control-to-evidence mappings from evidence payloads
    for evidence in evidence_records:
        payload = evidence.payload or {}
        
        # Check for control_id references in payload
        control_ids = payload.get("control_ids", [])
        if not control_ids:
            # Try alternative field names
            control_ids = payload.get("controls", [])
        if not control_ids and isinstance(payload.get("control_id"), str):
            control_ids = [payload["control_id"]]
        
        # Map evidence to controls
        for control_id in control_ids:
            if control_id not in evidence_map:
                evidence_map[control_id] = []
            evidence_map[control_id].append(evidence.evidence_id)
        
        # Also check evidence kind for control mapping
        if evidence.kind.startswith("control_"):
            # Extract control ID from kind (e.g., "control_access_control_001")
            parts = evidence.kind.split("_")
            if len(parts) >= 3:
                potential_control_id = "_".join(parts[1:])
                if potential_control_id not in evidence_map:
                    evidence_map[potential_control_id] = []
                evidence_map[potential_control_id].append(evidence.evidence_id)
    
    return evidence_map


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
    """
    Create evidence with immutability conflict detection.
    
    Similar to CSRD engine's _strict_create_evidence for consistency.
    """
    from datetime import timezone
    import logging
    
    logger = logging.getLogger(__name__)
    
    existing = await db.scalar(select(EvidenceRecord).where(EvidenceRecord.evidence_id == evidence_id))
    if existing is not None:
        if existing.dataset_version_id != dataset_version_id or existing.engine_id != engine_id or existing.kind != kind:
            logger.warning(
                "AUDIT_READINESS_IMMUTABLE_CONFLICT evidence_id_collision evidence_id=%s dataset_version_id=%s",
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
                "AUDIT_READINESS_IMMUTABLE_CONFLICT evidence_created_at_mismatch evidence_id=%s dataset_version_id=%s",
                evidence_id,
                dataset_version_id,
            )
            raise ImmutableConflictError("IMMUTABLE_EVIDENCE_CREATED_AT_MISMATCH")
        if existing.payload != payload:
            logger.warning(
                "AUDIT_READINESS_IMMUTABLE_CONFLICT evidence_payload_mismatch evidence_id=%s dataset_version_id=%s",
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


async def store_regulatory_check_evidence(
    db: AsyncSession,
    dataset_version_id: str,
    framework_id: str,
    check_result: dict[str, Any],
    created_at: datetime,
) -> str:
    """
    Store regulatory check result as evidence.
    
    Args:
        db: Database session
        dataset_version_id: Dataset version ID
        framework_id: Regulatory framework ID
        check_result: Regulatory check result data
        created_at: Creation timestamp
    
    Returns:
        Evidence ID
    """
    evidence_id = deterministic_evidence_id(
        dataset_version_id=dataset_version_id,
        engine_id="engine_audit_readiness",
        kind="regulatory_check",
        stable_key=f"{framework_id}_{check_result.get('check_status', 'unknown')}",
    )
    
    payload = {
        "framework_id": framework_id,
        "check_result": check_result,
        "dataset_version_id": dataset_version_id,
    }
    
    await _strict_create_evidence(
        db,
        evidence_id=evidence_id,
        dataset_version_id=dataset_version_id,
        engine_id="engine_audit_readiness",
        kind="regulatory_check",
        payload=payload,
        created_at=created_at,
    )
    
    return evidence_id


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
    """
    Create finding with immutability conflict detection.
    
    Similar to CSRD engine's _strict_create_finding for consistency.
    """
    import logging
    
    logger = logging.getLogger(__name__)
    
    existing = await db.scalar(select(FindingRecord).where(FindingRecord.finding_id == finding_id))
    if existing is not None:
        if existing.dataset_version_id != dataset_version_id or existing.raw_record_id != raw_record_id or existing.kind != kind:
            logger.warning(
                "AUDIT_READINESS_IMMUTABLE_CONFLICT finding_id_collision finding_id=%s dataset_version_id=%s",
                finding_id,
                dataset_version_id,
            )
            raise ImmutableConflictError("FINDING_ID_COLLISION")
        if existing.payload != payload:
            logger.warning(
                "AUDIT_READINESS_IMMUTABLE_CONFLICT finding_payload_mismatch finding_id=%s dataset_version_id=%s",
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


async def store_control_gap_finding(
    db: AsyncSession,
    dataset_version_id: str,
    raw_record_id: str,
    framework_id: str,
    control_gap: dict[str, Any],
    created_at: datetime,
) -> tuple[str, str]:
    """
    Store control gap as a finding and link to evidence.
    
    Args:
        db: Database session
        dataset_version_id: Dataset version ID
        raw_record_id: Raw record ID (source)
        framework_id: Regulatory framework ID
        control_gap: Control gap data
        created_at: Creation timestamp
    
    Returns:
        Tuple of (finding_id, evidence_id)
    """
    finding_id = deterministic_id(
        dataset_version_id,
        "finding",
        framework_id,
        control_gap.get("control_id", "unknown"),
    )
    
    finding_payload = {
        "framework_id": framework_id,
        "control_gap": control_gap,
        "dataset_version_id": dataset_version_id,
    }
    
    await _strict_create_finding(
        db,
        finding_id=finding_id,
        dataset_version_id=dataset_version_id,
        raw_record_id=raw_record_id,
        kind="control_gap",
        payload=finding_payload,
        created_at=created_at,
    )
    
    # Create evidence for the gap
    evidence_id = deterministic_evidence_id(
        dataset_version_id=dataset_version_id,
        engine_id="engine_audit_readiness",
        kind="control_gap",
        stable_key=f"{framework_id}_{control_gap.get('control_id', 'unknown')}",
    )
    
    evidence_payload = {
        "framework_id": framework_id,
        "control_gap": control_gap,
        "finding_id": finding_id,
        "dataset_version_id": dataset_version_id,
    }
    
    await _strict_create_evidence(
        db,
        evidence_id=evidence_id,
        dataset_version_id=dataset_version_id,
        engine_id="engine_audit_readiness",
        kind="control_gap",
        payload=evidence_payload,
        created_at=created_at,
    )
    
    # Link finding to evidence
    link_id = deterministic_id(dataset_version_id, "link", finding_id, evidence_id)
    await link_finding_to_evidence(db, link_id=link_id, finding_id=finding_id, evidence_id=evidence_id)
    
    return finding_id, evidence_id


async def create_audit_trail_entry(
    db: AsyncSession,
    dataset_version_id: str,
    action_type: str,
    action_details: dict[str, Any],
    created_at: datetime,
) -> str:
    """
    Create an audit trail entry for compliance mapping and control assessments.
    
    Args:
        db: Database session
        dataset_version_id: Dataset version ID
        action_type: Type of action (e.g., "compliance_mapping", "control_assessment")
        action_details: Action details dictionary
        created_at: Creation timestamp
    
    Returns:
        Evidence ID of audit trail entry
    """
    evidence_id = deterministic_evidence_id(
        dataset_version_id=dataset_version_id,
        engine_id="engine_audit_readiness",
        kind="audit_trail",
        stable_key=f"{action_type}_{created_at.isoformat()}",
    )
    
    payload = {
        "action_type": action_type,
        "action_details": action_details,
        "dataset_version_id": dataset_version_id,
        "timestamp": created_at.isoformat(),
    }
    
    await _strict_create_evidence(
        db,
        evidence_id=evidence_id,
        dataset_version_id=dataset_version_id,
        engine_id="engine_audit_readiness",
        kind="audit_trail",
        payload=payload,
        created_at=created_at,
    )
    
    return evidence_id

