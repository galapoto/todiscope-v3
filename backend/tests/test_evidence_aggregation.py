"""
Unit tests for evidence aggregation service.

Tests verify:
- Evidence collection by dataset version
- Evidence traceability
- Evidence grouping and aggregation
- Error handling for dataset version mismatches
"""

from __future__ import annotations

from datetime import datetime, timezone
import uuid

import pytest
from sqlalchemy import select

from backend.app.core.dataset.service import create_dataset_version_via_ingestion
from backend.app.core.db import get_sessionmaker
from backend.app.core.evidence.aggregation import (
    DatasetVersionMismatchError,
    EvidenceAggregationError,
    MissingEvidenceError,
    aggregate_evidence_by_engine,
    aggregate_evidence_by_kind,
    get_evidence_by_dataset_version,
    get_evidence_by_ids,
    get_evidence_for_findings,
    get_evidence_summary,
    get_findings_by_dataset_version,
    verify_evidence_traceability,
)
from backend.app.core.evidence.models import EvidenceRecord, FindingEvidenceLink, FindingRecord
from backend.app.core.evidence.service import (
    create_evidence,
    create_finding,
    deterministic_evidence_id,
    link_finding_to_evidence,
)
from backend.app.core.dataset.raw_models import RawRecord


@pytest.mark.anyio
async def test_get_evidence_by_dataset_version(sqlite_db: None) -> None:
    """Test retrieving evidence by dataset version."""
    now = datetime.now(timezone.utc)
    
    async with get_sessionmaker()() as db:
        dv1 = await create_dataset_version_via_ingestion(db)
        dv2 = await create_dataset_version_via_ingestion(db)
        
        # Create evidence for dv1
        evidence_id_1 = deterministic_evidence_id(
            dataset_version_id=dv1.id,
            engine_id="test_engine",
            kind="test_kind",
            stable_key="key1",
        )
        evidence_1 = await create_evidence(
            db,
            evidence_id=evidence_id_1,
            dataset_version_id=dv1.id,
            engine_id="test_engine",
            kind="test_kind",
            payload={"data": "value1"},
            created_at=now,
        )
        
        # Create evidence for dv2
        evidence_id_2 = deterministic_evidence_id(
            dataset_version_id=dv2.id,
            engine_id="test_engine",
            kind="test_kind",
            stable_key="key2",
        )
        evidence_2 = await create_evidence(
            db,
            evidence_id=evidence_id_2,
            dataset_version_id=dv2.id,
            engine_id="test_engine",
            kind="test_kind",
            payload={"data": "value2"},
            created_at=now,
        )
        
        await db.commit()
    
    async with get_sessionmaker()() as db:
        # Get evidence for dv1
        evidence_list = await get_evidence_by_dataset_version(db, dataset_version_id=dv1.id)
        assert len(evidence_list) == 1
        assert evidence_list[0].evidence_id == evidence_id_1
        assert evidence_list[0].dataset_version_id == dv1.id
        
        # Get evidence for dv2
        evidence_list = await get_evidence_by_dataset_version(db, dataset_version_id=dv2.id)
        assert len(evidence_list) == 1
        assert evidence_list[0].evidence_id == evidence_id_2
        assert evidence_list[0].dataset_version_id == dv2.id


@pytest.mark.anyio
async def test_get_evidence_by_dataset_version_with_filters(sqlite_db: None) -> None:
    """Test retrieving evidence with engine_id and kind filters."""
    now = datetime.now(timezone.utc)
    
    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)
        
        # Create evidence with different engines and kinds
        evidence_id_1 = deterministic_evidence_id(
            dataset_version_id=dv.id,
            engine_id="engine_a",
            kind="kind_1",
            stable_key="key1",
        )
        await create_evidence(
            db,
            evidence_id=evidence_id_1,
            dataset_version_id=dv.id,
            engine_id="engine_a",
            kind="kind_1",
            payload={"data": "value1"},
            created_at=now,
        )
        
        evidence_id_2 = deterministic_evidence_id(
            dataset_version_id=dv.id,
            engine_id="engine_a",
            kind="kind_2",
            stable_key="key2",
        )
        await create_evidence(
            db,
            evidence_id=evidence_id_2,
            dataset_version_id=dv.id,
            engine_id="engine_a",
            kind="kind_2",
            payload={"data": "value2"},
            created_at=now,
        )
        
        evidence_id_3 = deterministic_evidence_id(
            dataset_version_id=dv.id,
            engine_id="engine_b",
            kind="kind_1",
            stable_key="key3",
        )
        await create_evidence(
            db,
            evidence_id=evidence_id_3,
            dataset_version_id=dv.id,
            engine_id="engine_b",
            kind="kind_1",
            payload={"data": "value3"},
            created_at=now,
        )
        
        await db.commit()
    
    async with get_sessionmaker()() as db:
        # Filter by engine_id
        evidence_list = await get_evidence_by_dataset_version(
            db, dataset_version_id=dv.id, engine_id="engine_a"
        )
        assert len(evidence_list) == 2
        assert all(e.engine_id == "engine_a" for e in evidence_list)
        
        # Filter by kind
        evidence_list = await get_evidence_by_dataset_version(
            db, dataset_version_id=dv.id, kind="kind_1"
        )
        assert len(evidence_list) == 2
        assert all(e.kind == "kind_1" for e in evidence_list)
        
        # Filter by both
        evidence_list = await get_evidence_by_dataset_version(
            db, dataset_version_id=dv.id, engine_id="engine_a", kind="kind_1"
        )
        assert len(evidence_list) == 1
        assert evidence_list[0].evidence_id == evidence_id_1


@pytest.mark.anyio
async def test_get_evidence_by_ids(sqlite_db: None) -> None:
    """Test retrieving evidence by IDs with dataset version validation."""
    now = datetime.now(timezone.utc)
    
    async with get_sessionmaker()() as db:
        dv1 = await create_dataset_version_via_ingestion(db)
        dv2 = await create_dataset_version_via_ingestion(db)
        
        evidence_id_1 = deterministic_evidence_id(
            dataset_version_id=dv1.id,
            engine_id="test_engine",
            kind="test_kind",
            stable_key="key1",
        )
        await create_evidence(
            db,
            evidence_id=evidence_id_1,
            dataset_version_id=dv1.id,
            engine_id="test_engine",
            kind="test_kind",
            payload={"data": "value1"},
            created_at=now,
        )
        
        evidence_id_2 = deterministic_evidence_id(
            dataset_version_id=dv2.id,
            engine_id="test_engine",
            kind="test_kind",
            stable_key="key2",
        )
        await create_evidence(
            db,
            evidence_id=evidence_id_2,
            dataset_version_id=dv2.id,
            engine_id="test_engine",
            kind="test_kind",
            payload={"data": "value2"},
            created_at=now,
        )
        
        await db.commit()
    
    async with get_sessionmaker()() as db:
        # Get evidence for dv1
        evidence_list = await get_evidence_by_ids(
            db, evidence_ids=[evidence_id_1], dataset_version_id=dv1.id
        )
        assert len(evidence_list) == 1
        assert evidence_list[0].evidence_id == evidence_id_1
        
        # Try to get evidence from dv2 with dv1 dataset_version_id (should raise error)
        with pytest.raises(DatasetVersionMismatchError):
            await get_evidence_by_ids(
                db, evidence_ids=[evidence_id_2], dataset_version_id=dv1.id
            )
        
        # Try to get non-existent evidence
        fake_id = str(uuid.uuid4())
        with pytest.raises(MissingEvidenceError):
            await get_evidence_by_ids(
                db, evidence_ids=[fake_id], dataset_version_id=dv1.id
            )


@pytest.mark.anyio
async def test_get_findings_by_dataset_version(sqlite_db: None) -> None:
    """Test retrieving findings by dataset version."""
    now = datetime.now(timezone.utc)
    
    async with get_sessionmaker()() as db:
        dv1 = await create_dataset_version_via_ingestion(db)
        dv2 = await create_dataset_version_via_ingestion(db)
        
        # Create raw records
        raw_id_1 = str(uuid.uuid4())
        db.add(
            RawRecord(
                raw_record_id=raw_id_1,
                dataset_version_id=dv1.id,
                source_system="sys1",
                source_record_id="r1",
                payload={"data": "value1"},
                ingested_at=now,
            )
        )
        
        raw_id_2 = str(uuid.uuid4())
        db.add(
            RawRecord(
                raw_record_id=raw_id_2,
                dataset_version_id=dv2.id,
                source_system="sys2",
                source_record_id="r2",
                payload={"data": "value2"},
                ingested_at=now,
            )
        )
        
        await db.commit()
        
        # Create findings
        finding_id_1 = str(uuid.uuid4())
        finding_1 = await create_finding(
            db,
            finding_id=finding_id_1,
            dataset_version_id=dv1.id,
            raw_record_id=raw_id_1,
            kind="test_kind",
            payload={"data": "finding1"},
            created_at=now,
        )
        
        finding_id_2 = str(uuid.uuid4())
        finding_2 = await create_finding(
            db,
            finding_id=finding_id_2,
            dataset_version_id=dv2.id,
            raw_record_id=raw_id_2,
            kind="test_kind",
            payload={"data": "finding2"},
            created_at=now,
        )
        
        await db.commit()
    
    async with get_sessionmaker()() as db:
        # Get findings for dv1
        findings = await get_findings_by_dataset_version(db, dataset_version_id=dv1.id)
        assert len(findings) == 1
        assert findings[0].finding_id == finding_id_1
        
        # Get findings for dv2
        findings = await get_findings_by_dataset_version(db, dataset_version_id=dv2.id)
        assert len(findings) == 1
        assert findings[0].finding_id == finding_id_2
        
        # Filter by kind
        findings = await get_findings_by_dataset_version(
            db, dataset_version_id=dv1.id, kind="test_kind"
        )
        assert len(findings) == 1
        
        findings = await get_findings_by_dataset_version(
            db, dataset_version_id=dv1.id, kind="other_kind"
        )
        assert len(findings) == 0


@pytest.mark.anyio
async def test_get_evidence_for_findings(sqlite_db: None) -> None:
    """Test retrieving evidence linked to findings."""
    now = datetime.now(timezone.utc)
    
    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)
        
        # Create raw record
        raw_id = str(uuid.uuid4())
        db.add(
            RawRecord(
                raw_record_id=raw_id,
                dataset_version_id=dv.id,
                source_system="sys1",
                source_record_id="r1",
                payload={"data": "value1"},
                ingested_at=now,
            )
        )
        await db.commit()
        
        # Create findings
        finding_id_1 = str(uuid.uuid4())
        finding_1 = await create_finding(
            db,
            finding_id=finding_id_1,
            dataset_version_id=dv.id,
            raw_record_id=raw_id,
            kind="test_kind",
            payload={"data": "finding1"},
            created_at=now,
        )
        
        finding_id_2 = str(uuid.uuid4())
        finding_2 = await create_finding(
            db,
            finding_id=finding_id_2,
            dataset_version_id=dv.id,
            raw_record_id=raw_id,
            kind="test_kind",
            payload={"data": "finding2"},
            created_at=now,
        )
        
        # Create evidence
        evidence_id_1 = deterministic_evidence_id(
            dataset_version_id=dv.id,
            engine_id="test_engine",
            kind="evidence_kind",
            stable_key="key1",
        )
        evidence_1 = await create_evidence(
            db,
            evidence_id=evidence_id_1,
            dataset_version_id=dv.id,
            engine_id="test_engine",
            kind="evidence_kind",
            payload={"data": "evidence1"},
            created_at=now,
        )
        
        evidence_id_2 = deterministic_evidence_id(
            dataset_version_id=dv.id,
            engine_id="test_engine",
            kind="evidence_kind",
            stable_key="key2",
        )
        evidence_2 = await create_evidence(
            db,
            evidence_id=evidence_id_2,
            dataset_version_id=dv.id,
            engine_id="test_engine",
            kind="evidence_kind",
            payload={"data": "evidence2"},
            created_at=now,
        )
        
        # Link evidence to findings
        link_id_1 = str(uuid.uuid4())
        await link_finding_to_evidence(
            db, link_id=link_id_1, finding_id=finding_id_1, evidence_id=evidence_id_1
        )
        
        link_id_2 = str(uuid.uuid4())
        await link_finding_to_evidence(
            db, link_id=link_id_2, finding_id=finding_id_1, evidence_id=evidence_id_2
        )
        
        link_id_3 = str(uuid.uuid4())
        await link_finding_to_evidence(
            db, link_id=link_id_3, finding_id=finding_id_2, evidence_id=evidence_id_1
        )
        
        await db.commit()
    
    async with get_sessionmaker()() as db:
        # Get evidence for findings
        evidence_map = await get_evidence_for_findings(
            db, finding_ids=[finding_id_1, finding_id_2], dataset_version_id=dv.id
        )
        
        assert finding_id_1 in evidence_map
        assert finding_id_2 in evidence_map
        assert len(evidence_map[finding_id_1]) == 2
        assert len(evidence_map[finding_id_2]) == 1
        
        evidence_ids_finding_1 = {e.evidence_id for e in evidence_map[finding_id_1]}
        assert evidence_id_1 in evidence_ids_finding_1
        assert evidence_id_2 in evidence_ids_finding_1
        
        evidence_ids_finding_2 = {e.evidence_id for e in evidence_map[finding_id_2]}
        assert evidence_id_1 in evidence_ids_finding_2


@pytest.mark.anyio
async def test_aggregate_evidence_by_kind(sqlite_db: None) -> None:
    """Test aggregating evidence by kind."""
    now = datetime.now(timezone.utc)
    
    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)
        
        # Create evidence with different kinds
        for i, kind in enumerate(["kind_a", "kind_b", "kind_a"]):
            evidence_id = deterministic_evidence_id(
                dataset_version_id=dv.id,
                engine_id="test_engine",
                kind=kind,
                stable_key=f"key{i}",
            )
            await create_evidence(
                db,
                evidence_id=evidence_id,
                dataset_version_id=dv.id,
                engine_id="test_engine",
                kind=kind,
                payload={"data": f"value{i}"},
                created_at=now,
            )
        
        await db.commit()
    
    async with get_sessionmaker()() as db:
        grouped = await aggregate_evidence_by_kind(db, dataset_version_id=dv.id)
        
        assert "kind_a" in grouped
        assert "kind_b" in grouped
        assert len(grouped["kind_a"]) == 2
        assert len(grouped["kind_b"]) == 1


@pytest.mark.anyio
async def test_aggregate_evidence_by_engine(sqlite_db: None) -> None:
    """Test aggregating evidence by engine."""
    now = datetime.now(timezone.utc)
    
    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)
        
        # Create evidence with different engines
        for i, engine_id in enumerate(["engine_a", "engine_b", "engine_a"]):
            evidence_id = deterministic_evidence_id(
                dataset_version_id=dv.id,
                engine_id=engine_id,
                kind="test_kind",
                stable_key=f"key{i}",
            )
            await create_evidence(
                db,
                evidence_id=evidence_id,
                dataset_version_id=dv.id,
                engine_id=engine_id,
                kind="test_kind",
                payload={"data": f"value{i}"},
                created_at=now,
            )
        
        await db.commit()
    
    async with get_sessionmaker()() as db:
        grouped = await aggregate_evidence_by_engine(db, dataset_version_id=dv.id)
        
        assert "engine_a" in grouped
        assert "engine_b" in grouped
        assert len(grouped["engine_a"]) == 2
        assert len(grouped["engine_b"]) == 1


@pytest.mark.anyio
async def test_verify_evidence_traceability(sqlite_db: None) -> None:
    """Test verifying evidence traceability."""
    now = datetime.now(timezone.utc)
    
    async with get_sessionmaker()() as db:
        dv1 = await create_dataset_version_via_ingestion(db)
        dv2 = await create_dataset_version_via_ingestion(db)
        
        # Create evidence for dv1
        evidence_id_1 = deterministic_evidence_id(
            dataset_version_id=dv1.id,
            engine_id="test_engine",
            kind="test_kind",
            stable_key="key1",
        )
        await create_evidence(
            db,
            evidence_id=evidence_id_1,
            dataset_version_id=dv1.id,
            engine_id="test_engine",
            kind="test_kind",
            payload={"data": "value1"},
            created_at=now,
        )
        
        # Create evidence for dv2
        evidence_id_2 = deterministic_evidence_id(
            dataset_version_id=dv2.id,
            engine_id="test_engine",
            kind="test_kind",
            stable_key="key2",
        )
        await create_evidence(
            db,
            evidence_id=evidence_id_2,
            dataset_version_id=dv2.id,
            engine_id="test_engine",
            kind="test_kind",
            payload={"data": "value2"},
            created_at=now,
        )
        
        await db.commit()
    
    async with get_sessionmaker()() as db:
        # Verify dv1 evidence
        result = await verify_evidence_traceability(
            db, dataset_version_id=dv1.id, evidence_ids=[evidence_id_1]
        )
        assert result["valid"] is True
        assert result["total_checked"] == 1
        assert len(result["mismatches"]) == 0
        
        # Verify dv2 evidence with dv1 dataset_version_id (should fail)
        result = await verify_evidence_traceability(
            db, dataset_version_id=dv1.id, evidence_ids=[evidence_id_2]
        )
        assert result["valid"] is False
        assert len(result["mismatches"]) == 1
        
        # Verify all evidence for dv1
        result = await verify_evidence_traceability(db, dataset_version_id=dv1.id)
        assert result["valid"] is True
        assert result["total_checked"] == 1


@pytest.mark.anyio
async def test_get_evidence_summary(sqlite_db: None) -> None:
    """Test getting evidence summary."""
    now = datetime.now(timezone.utc)
    
    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)
        
        # Create evidence with different kinds and engines
        for i, (kind, engine_id) in enumerate([
            ("kind_a", "engine_1"),
            ("kind_b", "engine_1"),
            ("kind_a", "engine_2"),
        ]):
            evidence_id = deterministic_evidence_id(
                dataset_version_id=dv.id,
                engine_id=engine_id,
                kind=kind,
                stable_key=f"key{i}",
            )
            await create_evidence(
                db,
                evidence_id=evidence_id,
                dataset_version_id=dv.id,
                engine_id=engine_id,
                kind=kind,
                payload={"data": f"value{i}"},
                created_at=now,
            )
        
        await db.commit()
    
    async with get_sessionmaker()() as db:
        summary = await get_evidence_summary(db, dataset_version_id=dv.id)
        
        assert summary["dataset_version_id"] == dv.id
        assert summary["total_evidence_count"] == 3
        assert summary["evidence_by_kind"]["kind_a"] == 2
        assert summary["evidence_by_kind"]["kind_b"] == 1
        assert summary["evidence_by_engine"]["engine_1"] == 2
        assert summary["evidence_by_engine"]["engine_2"] == 1
        assert summary["earliest_evidence"] is not None
        assert summary["latest_evidence"] is not None
        
        # Test empty dataset version
        dv_empty = await create_dataset_version_via_ingestion(db)
        await db.commit()
        
        summary_empty = await get_evidence_summary(db, dataset_version_id=dv_empty.id)
        assert summary_empty["total_evidence_count"] == 0
        assert summary_empty["evidence_by_kind"] == {}
        assert summary_empty["evidence_by_engine"] == {}
        assert summary_empty["earliest_evidence"] is None
        assert summary_empty["latest_evidence"] is None






