"""
Tests for DatasetVersion enforcement and immutability compliance.

Verifies that the engine correctly enforces DatasetVersion requirements
and maintains immutability of all data structures.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from backend.app.core.dataset.immutability import ImmutableViolation, install_immutability_guards
from backend.app.core.dataset.models import DatasetVersion
from backend.app.core.dataset.service import create_dataset_version_via_ingestion
from backend.app.core.evidence.models import EvidenceRecord, FindingRecord
from backend.app.core.normalization.models import NormalizedRecord
from backend.app.core.db import get_sessionmaker
from backend.app.engines.enterprise_distressed_asset_debt_stress.errors import (
    DatasetVersionInvalidError,
    DatasetVersionMissingError,
    DatasetVersionNotFoundError,
    ImmutableConflictError,
    NormalizedRecordMissingError,
)
from backend.app.engines.enterprise_distressed_asset_debt_stress.run import run_engine


@pytest.mark.anyio
async def test_dataset_version_mandatory(sqlite_db: None) -> None:
    """Test that DatasetVersion is mandatory for engine execution."""
    install_immutability_guards()
    
    # Missing dataset_version_id
    with pytest.raises(DatasetVersionMissingError):
        await run_engine(dataset_version_id=None, started_at=datetime.now(timezone.utc).isoformat())
    
    # Invalid dataset_version_id (empty string)
    with pytest.raises(DatasetVersionInvalidError):
        await run_engine(dataset_version_id="", started_at=datetime.now(timezone.utc).isoformat())
    
    # Non-existent DatasetVersion
    with pytest.raises(DatasetVersionNotFoundError):
        await run_engine(
            dataset_version_id="nonexistent-dv-id",
            started_at=datetime.now(timezone.utc).isoformat(),
        )


@pytest.mark.anyio
async def test_normalized_record_required(sqlite_db: None) -> None:
    """Test that normalized record is required for engine execution."""
    install_immutability_guards()
    
    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)
        await db.commit()
    
    # Should fail without normalized record
    with pytest.raises(NormalizedRecordMissingError):
        await run_engine(
            dataset_version_id=dv.id,
            started_at=datetime.now(timezone.utc).isoformat(),
        )


@pytest.mark.anyio
async def test_evidence_immutability(sqlite_db: None) -> None:
    """Test that evidence records are stored immutably."""
    install_immutability_guards()
    
    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)
        
        # Create normalized record
        import uuid
        from backend.app.core.dataset.raw_models import RawRecord
        
        raw_id = str(uuid.uuid4())
        db.add(
            RawRecord(
                raw_record_id=raw_id,
                dataset_version_id=dv.id,
                source_system="test",
                source_record_id="test-1",
                payload={
                    "financial": {
                        "debt": {
                            "total_outstanding": 1_000_000,
                            "interest_rate_pct": 5.0,
                            "collateral_value": 750_000,
                        },
                        "assets": {"total": 2_000_000},
                    },
                    "distressed_assets": [
                        {"value": 200_000, "recovery_rate_pct": 35},
                    ],
                },
                ingested_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()
        
        norm_id = str(uuid.uuid4())
        db.add(
            NormalizedRecord(
                normalized_record_id=norm_id,
                dataset_version_id=dv.id,
                raw_record_id=raw_id,
                payload={
                    "financial": {
                        "debt": {
                            "total_outstanding": 1_000_000,
                            "interest_rate_pct": 5.0,
                            "collateral_value": 750_000,
                        },
                        "assets": {"total": 2_000_000},
                    },
                    "distressed_assets": [
                        {"value": 200_000, "recovery_rate_pct": 35},
                    ],
                },
                normalized_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()
    
    # Run engine
    started = datetime.now(timezone.utc)
    result1 = await run_engine(
        dataset_version_id=dv.id,
        started_at=started.isoformat(),
    )
    
    # Run again with same parameters - should be idempotent
    result2 = await run_engine(
        dataset_version_id=dv.id,
        started_at=started.isoformat(),
    )
    
    # Evidence IDs should be the same (idempotent)
    assert result1["debt_exposure_evidence_id"] == result2["debt_exposure_evidence_id"]
    assert result1["stress_test_evidence_ids"] == result2["stress_test_evidence_ids"]
    
    # Verify evidence is stored
    async with get_sessionmaker()() as db:
        evidence = await db.scalar(
            select(EvidenceRecord).where(EvidenceRecord.evidence_id == result1["debt_exposure_evidence_id"])
        )
        assert evidence is not None
        assert evidence.dataset_version_id == dv.id
        
        # Try to modify evidence (should fail due to immutability guards)
        evidence.payload = {"modified": True}
        with pytest.raises(ImmutableViolation):
            await db.commit()


@pytest.mark.anyio
async def test_findings_immutability(sqlite_db: None) -> None:
    """Test that findings are stored immutably."""
    install_immutability_guards()
    
    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)
        
        import uuid
        from backend.app.core.dataset.raw_models import RawRecord
        
        raw_id = str(uuid.uuid4())
        db.add(
            RawRecord(
                raw_record_id=raw_id,
                dataset_version_id=dv.id,
                source_system="test",
                source_record_id="test-1",
                payload={
                    "financial": {
                        "debt": {"total_outstanding": 1_000_000, "interest_rate_pct": 5.0},
                        "assets": {"total": 2_000_000},
                    },
                },
                ingested_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()
        
        norm_id = str(uuid.uuid4())
        db.add(
            NormalizedRecord(
                normalized_record_id=norm_id,
                dataset_version_id=dv.id,
                raw_record_id=raw_id,
                payload={
                    "financial": {
                        "debt": {"total_outstanding": 1_000_000, "interest_rate_pct": 5.0},
                        "assets": {"total": 2_000_000},
                    },
                },
                normalized_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()
    
    # Run engine
    result = await run_engine(
        dataset_version_id=dv.id,
        started_at=datetime.now(timezone.utc).isoformat(),
    )
    
    # Verify findings are stored
    async with get_sessionmaker()() as db:
        finding_ids = [f["id"] for f in result["material_findings"]]
        findings = (
            await db.scalars(select(FindingRecord).where(FindingRecord.finding_id.in_(finding_ids)))
        ).all()
        
        assert len(findings) == len(finding_ids)
        
        # All findings should be bound to the same DatasetVersion
        for finding in findings:
            assert finding.dataset_version_id == dv.id
            
            # Try to modify finding (should fail)
            finding.payload = {"modified": True}
            with pytest.raises(ImmutableViolation):
                await db.commit()
                break  # Only need to test once


@pytest.mark.anyio
async def test_immutable_conflict_detection(sqlite_db: None) -> None:
    """Test that immutable conflicts are detected and raised."""
    install_immutability_guards()
    
    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)
        
        import uuid
        from backend.app.core.dataset.raw_models import RawRecord
        
        raw_id = str(uuid.uuid4())
        db.add(
            RawRecord(
                raw_record_id=raw_id,
                dataset_version_id=dv.id,
                source_system="test",
                source_record_id="test-1",
                payload={
                    "financial": {
                        "debt": {"total_outstanding": 1_000_000, "interest_rate_pct": 5.0},
                        "assets": {"total": 2_000_000},
                    },
                },
                ingested_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()
        
        norm_id = str(uuid.uuid4())
        db.add(
            NormalizedRecord(
                normalized_record_id=norm_id,
                dataset_version_id=dv.id,
                raw_record_id=raw_id,
                payload={
                    "financial": {
                        "debt": {"total_outstanding": 1_000_000, "interest_rate_pct": 5.0},
                        "assets": {"total": 2_000_000},
                    },
                },
                normalized_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()
    
    started = datetime.now(timezone.utc)
    
    # First run - should succeed
    result1 = await run_engine(
        dataset_version_id=dv.id,
        started_at=started.isoformat(),
    )
    
    # Second run with same parameters - should be idempotent (no conflict)
    result2 = await run_engine(
        dataset_version_id=dv.id,
        started_at=started.isoformat(),
    )
    
    # Results should be identical
    assert result1["debt_exposure_evidence_id"] == result2["debt_exposure_evidence_id"]


@pytest.mark.anyio
async def test_dataset_version_isolation(sqlite_db: None) -> None:
    """Test that different DatasetVersions are properly isolated."""
    install_immutability_guards()
    
    async with get_sessionmaker()() as db:
        dv1 = await create_dataset_version_via_ingestion(db)
        dv2 = await create_dataset_version_via_ingestion(db)
        
        import uuid
        from backend.app.core.dataset.raw_models import RawRecord
        
        # Create records for dv1
        raw_id1 = str(uuid.uuid4())
        db.add(
            RawRecord(
                raw_record_id=raw_id1,
                dataset_version_id=dv1.id,
                source_system="test",
                source_record_id="test-1",
                payload={
                    "financial": {
                        "debt": {"total_outstanding": 1_000_000, "interest_rate_pct": 5.0},
                        "assets": {"total": 2_000_000},
                    },
                },
                ingested_at=datetime.now(timezone.utc),
            )
        )
        
        # Create records for dv2
        raw_id2 = str(uuid.uuid4())
        db.add(
            RawRecord(
                raw_record_id=raw_id2,
                dataset_version_id=dv2.id,
                source_system="test",
                source_record_id="test-2",
                payload={
                    "financial": {
                        "debt": {"total_outstanding": 500_000, "interest_rate_pct": 4.0},
                        "assets": {"total": 1_000_000},
                    },
                },
                ingested_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()
        
        norm_id1 = str(uuid.uuid4())
        db.add(
            NormalizedRecord(
                normalized_record_id=norm_id1,
                dataset_version_id=dv1.id,
                raw_record_id=raw_id1,
                payload={
                    "financial": {
                        "debt": {"total_outstanding": 1_000_000, "interest_rate_pct": 5.0},
                        "assets": {"total": 2_000_000},
                    },
                },
                normalized_at=datetime.now(timezone.utc),
            )
        )
        
        norm_id2 = str(uuid.uuid4())
        db.add(
            NormalizedRecord(
                normalized_record_id=norm_id2,
                dataset_version_id=dv2.id,
                raw_record_id=raw_id2,
                payload={
                    "financial": {
                        "debt": {"total_outstanding": 500_000, "interest_rate_pct": 4.0},
                        "assets": {"total": 1_000_000},
                    },
                },
                normalized_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()
    
    # Run engine for each DatasetVersion
    started = datetime.now(timezone.utc)
    result1 = await run_engine(
        dataset_version_id=dv1.id,
        started_at=started.isoformat(),
    )
    
    result2 = await run_engine(
        dataset_version_id=dv2.id,
        started_at=started.isoformat(),
    )
    
    # Verify they produce different results
    assert result1["dataset_version_id"] == dv1.id
    assert result2["dataset_version_id"] == dv2.id
    assert result1["debt_exposure_evidence_id"] != result2["debt_exposure_evidence_id"]
    
    # Verify exposure values are different
    assert result1["report"]["debt_exposure"]["total_outstanding"] == pytest.approx(1_000_000)
    assert result2["report"]["debt_exposure"]["total_outstanding"] == pytest.approx(500_000)

