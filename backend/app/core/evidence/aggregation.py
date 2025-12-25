"""
Evidence Aggregation Service

Provides functions to collect, aggregate, and verify evidence for litigation scenarios.
All evidence operations are bound to DatasetVersion for traceability.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.evidence.models import EvidenceRecord, FindingEvidenceLink, FindingRecord


class EvidenceAggregationError(Exception):
    """Base exception for evidence aggregation errors."""


class DatasetVersionMismatchError(EvidenceAggregationError):
    """Raised when evidence belongs to a different dataset version."""


class MissingEvidenceError(EvidenceAggregationError):
    """Raised when required evidence is missing."""


async def get_evidence_by_dataset_version(
    db: AsyncSession,
    *,
    dataset_version_id: str,
    engine_id: str | None = None,
    kind: str | None = None,
) -> list[EvidenceRecord]:
    """
    Retrieve all evidence records for a specific dataset version.
    
    Args:
        db: Database session
        dataset_version_id: The dataset version ID (required)
        engine_id: Optional filter by engine ID
        kind: Optional filter by evidence kind
        
    Returns:
        List of EvidenceRecord instances
        
    Raises:
        DatasetVersionMismatchError: If any evidence belongs to a different dataset version
    """
    query = select(EvidenceRecord).where(EvidenceRecord.dataset_version_id == dataset_version_id)
    
    if engine_id is not None:
        query = query.where(EvidenceRecord.engine_id == engine_id)
    
    if kind is not None:
        query = query.where(EvidenceRecord.kind == kind)
    
    query = query.order_by(EvidenceRecord.created_at.asc(), EvidenceRecord.evidence_id.asc())
    
    result = await db.execute(query)
    evidence_records = result.scalars().all()
    
    # Verify all evidence belongs to the same dataset version
    for record in evidence_records:
        if record.dataset_version_id != dataset_version_id:
            raise DatasetVersionMismatchError(
                f"Evidence {record.evidence_id} belongs to dataset_version_id {record.dataset_version_id}, "
                f"expected {dataset_version_id}"
            )
    
    return list(evidence_records)


async def get_evidence_by_ids(
    db: AsyncSession,
    *,
    evidence_ids: list[str],
    dataset_version_id: str,
) -> list[EvidenceRecord]:
    """
    Retrieve evidence records by their IDs, ensuring they belong to the specified dataset version.
    
    Args:
        db: Database session
        evidence_ids: List of evidence IDs to retrieve
        dataset_version_id: Expected dataset version ID (for validation)
        
    Returns:
        List of EvidenceRecord instances
        
    Raises:
        MissingEvidenceError: If any evidence ID is not found
        DatasetVersionMismatchError: If any evidence belongs to a different dataset version
    """
    if not evidence_ids:
        return []
    
    result = await db.execute(
        select(EvidenceRecord).where(EvidenceRecord.evidence_id.in_(evidence_ids))
    )
    evidence_records = result.scalars().all()
    
    found_ids = {record.evidence_id for record in evidence_records}
    missing_ids = set(evidence_ids) - found_ids
    
    if missing_ids:
        raise MissingEvidenceError(f"Missing evidence IDs: {sorted(missing_ids)}")
    
    # Verify all evidence belongs to the same dataset version
    for record in evidence_records:
        if record.dataset_version_id != dataset_version_id:
            raise DatasetVersionMismatchError(
                f"Evidence {record.evidence_id} belongs to dataset_version_id {record.dataset_version_id}, "
                f"expected {dataset_version_id}"
            )
    
    return list(evidence_records)


async def get_findings_by_dataset_version(
    db: AsyncSession,
    *,
    dataset_version_id: str,
    kind: str | None = None,
) -> list[FindingRecord]:
    """
    Retrieve all findings for a specific dataset version.
    
    Args:
        db: Database session
        dataset_version_id: The dataset version ID (required)
        kind: Optional filter by finding kind
        
    Returns:
        List of FindingRecord instances
    """
    query = select(FindingRecord).where(FindingRecord.dataset_version_id == dataset_version_id)
    
    if kind is not None:
        query = query.where(FindingRecord.kind == kind)
    
    query = query.order_by(FindingRecord.created_at.asc(), FindingRecord.finding_id.asc())
    
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_evidence_for_findings(
    db: AsyncSession,
    *,
    finding_ids: list[str],
    dataset_version_id: str,
) -> dict[str, list[EvidenceRecord]]:
    """
    Retrieve all evidence linked to specific findings.
    
    Args:
        db: Database session
        finding_ids: List of finding IDs
        dataset_version_id: Expected dataset version ID (for validation)
        
    Returns:
        Dictionary mapping finding_id to list of EvidenceRecord instances
        
    Raises:
        DatasetVersionMismatchError: If any finding or evidence belongs to a different dataset version
    """
    if not finding_ids:
        return {}
    
    # First, verify all findings belong to the correct dataset version
    findings_result = await db.execute(
        select(FindingRecord).where(FindingRecord.finding_id.in_(finding_ids))
    )
    findings = findings_result.scalars().all()
    
    for finding in findings:
        if finding.dataset_version_id != dataset_version_id:
            raise DatasetVersionMismatchError(
                f"Finding {finding.finding_id} belongs to dataset_version_id {finding.dataset_version_id}, "
                f"expected {dataset_version_id}"
            )
    
    # Get all links for these findings
    links_result = await db.execute(
        select(FindingEvidenceLink).where(FindingEvidenceLink.finding_id.in_(finding_ids))
    )
    links = links_result.scalars().all()
    
    # Collect evidence IDs
    evidence_ids = {link.evidence_id for link in links}
    
    if not evidence_ids:
        return {finding_id: [] for finding_id in finding_ids}
    
    # Retrieve evidence records
    evidence_result = await db.execute(
        select(EvidenceRecord).where(EvidenceRecord.evidence_id.in_(evidence_ids))
    )
    evidence_records = evidence_result.scalars().all()
    
    # Verify evidence belongs to the correct dataset version
    for record in evidence_records:
        if record.dataset_version_id != dataset_version_id:
            raise DatasetVersionMismatchError(
                f"Evidence {record.evidence_id} belongs to dataset_version_id {record.dataset_version_id}, "
                f"expected {dataset_version_id}"
            )
    
    # Build mapping: finding_id -> list of evidence
    evidence_by_id = {record.evidence_id: record for record in evidence_records}
    result: dict[str, list[EvidenceRecord]] = defaultdict(list)
    
    for link in links:
        if link.evidence_id in evidence_by_id:
            result[link.finding_id].append(evidence_by_id[link.evidence_id])
    
    # Ensure all findings are in the result (even if they have no evidence)
    for finding_id in finding_ids:
        if finding_id not in result:
            result[finding_id] = []
    
    return dict(result)


async def aggregate_evidence_by_kind(
    db: AsyncSession,
    *,
    dataset_version_id: str,
    engine_id: str | None = None,
) -> dict[str, list[EvidenceRecord]]:
    """
    Aggregate evidence records grouped by kind.
    
    Args:
        db: Database session
        dataset_version_id: The dataset version ID
        engine_id: Optional filter by engine ID
        
    Returns:
        Dictionary mapping evidence kind to list of EvidenceRecord instances
    """
    evidence_records = await get_evidence_by_dataset_version(
        db, dataset_version_id=dataset_version_id, engine_id=engine_id
    )
    
    grouped: dict[str, list[EvidenceRecord]] = defaultdict(list)
    for record in evidence_records:
        grouped[record.kind].append(record)
    
    return dict(grouped)


async def aggregate_evidence_by_engine(
    db: AsyncSession,
    *,
    dataset_version_id: str,
) -> dict[str, list[EvidenceRecord]]:
    """
    Aggregate evidence records grouped by engine ID.
    
    Args:
        db: Database session
        dataset_version_id: The dataset version ID
        
    Returns:
        Dictionary mapping engine_id to list of EvidenceRecord instances
    """
    evidence_records = await get_evidence_by_dataset_version(
        db, dataset_version_id=dataset_version_id
    )
    
    grouped: dict[str, list[EvidenceRecord]] = defaultdict(list)
    for record in evidence_records:
        grouped[record.engine_id].append(record)
    
    return dict(grouped)


async def verify_evidence_traceability(
    db: AsyncSession,
    *,
    dataset_version_id: str,
    evidence_ids: list[str] | None = None,
) -> dict[str, Any]:
    """
    Verify that all evidence is properly traceable to the dataset version.
    
    Args:
        db: Database session
        dataset_version_id: The dataset version ID to verify against
        evidence_ids: Optional list of specific evidence IDs to verify.
                      If None, verifies all evidence for the dataset version.
        
    Returns:
        Dictionary with verification results:
        - valid: bool
        - total_checked: int
        - mismatches: list of dicts with evidence_id and expected/actual dataset_version_id
        - missing: list of evidence IDs that were not found
        
    Raises:
        MissingEvidenceError: If any evidence ID is not found (when evidence_ids is provided)
    """
    if evidence_ids is None:
        # Verify all evidence for this dataset version
        evidence_records = await get_evidence_by_dataset_version(
            db, dataset_version_id=dataset_version_id
        )
        evidence_ids_to_check = [record.evidence_id for record in evidence_records]
    else:
        # Verify specific evidence IDs
        evidence_ids_to_check = evidence_ids
        result = await db.execute(
            select(EvidenceRecord).where(EvidenceRecord.evidence_id.in_(evidence_ids_to_check))
        )
        found_records = result.scalars().all()
        found_ids = {record.evidence_id for record in found_records}
        missing_ids = set(evidence_ids_to_check) - found_ids
        
        if missing_ids:
            raise MissingEvidenceError(f"Missing evidence IDs: {sorted(missing_ids)}")
    
    mismatches: list[dict[str, str]] = []
    
    if evidence_ids_to_check:
        result = await db.execute(
            select(EvidenceRecord).where(EvidenceRecord.evidence_id.in_(evidence_ids_to_check))
        )
        records = result.scalars().all()
        
        for record in records:
            if record.dataset_version_id != dataset_version_id:
                mismatches.append({
                    "evidence_id": record.evidence_id,
                    "expected_dataset_version_id": dataset_version_id,
                    "actual_dataset_version_id": record.dataset_version_id,
                })
    
    return {
        "valid": len(mismatches) == 0,
        "total_checked": len(evidence_ids_to_check),
        "mismatches": mismatches,
        "missing": [],
    }


async def get_evidence_summary(
    db: AsyncSession,
    *,
    dataset_version_id: str,
) -> dict[str, Any]:
    """
    Get a summary of all evidence for a dataset version.
    
    Args:
        db: Database session
        dataset_version_id: The dataset version ID
        
    Returns:
        Dictionary with summary statistics:
        - dataset_version_id: str
        - total_evidence_count: int
        - evidence_by_kind: dict mapping kind to count
        - evidence_by_engine: dict mapping engine_id to count
        - earliest_evidence: ISO datetime string or None
        - latest_evidence: ISO datetime string or None
    """
    evidence_records = await get_evidence_by_dataset_version(
        db, dataset_version_id=dataset_version_id
    )
    
    if not evidence_records:
        return {
            "dataset_version_id": dataset_version_id,
            "total_evidence_count": 0,
            "evidence_by_kind": {},
            "evidence_by_engine": {},
            "earliest_evidence": None,
            "latest_evidence": None,
        }
    
    by_kind: dict[str, int] = defaultdict(int)
    by_engine: dict[str, int] = defaultdict(int)
    
    timestamps: list[datetime] = []
    
    for record in evidence_records:
        by_kind[record.kind] += 1
        by_engine[record.engine_id] += 1
        timestamps.append(record.created_at)
    
    return {
        "dataset_version_id": dataset_version_id,
        "total_evidence_count": len(evidence_records),
        "evidence_by_kind": dict(by_kind),
        "evidence_by_engine": dict(by_engine),
        "earliest_evidence": min(timestamps).isoformat() if timestamps else None,
        "latest_evidence": max(timestamps).isoformat() if timestamps else None,
    }






