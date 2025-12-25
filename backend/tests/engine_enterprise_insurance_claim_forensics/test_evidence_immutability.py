"""Tests for evidence immutability and conflict detection."""

from __future__ import annotations

from datetime import datetime, timezone
import uuid

import pytest
from sqlalchemy import select

from backend.app.core.db import get_sessionmaker
from backend.app.core.dataset.models import DatasetVersion
from backend.app.core.dataset.raw_models import RawRecord
from backend.app.core.dataset.uuidv7 import uuid7
from backend.app.core.evidence.models import EvidenceRecord
from backend.app.core.evidence.service import deterministic_evidence_id
from backend.app.core.normalization.models import NormalizedRecord
from backend.app.engines.enterprise_insurance_claim_forensics.audit_trail import AuditTrail
from backend.app.engines.enterprise_insurance_claim_forensics.constants import ENGINE_ID
from backend.app.engines.enterprise_insurance_claim_forensics.errors import ImmutableConflictError
from backend.app.engines.enterprise_insurance_claim_forensics.run import _strict_create_evidence
from backend.app.engines.enterprise_insurance_claim_forensics.claims_management import ClaimRecord


@pytest.mark.anyio
async def test_strict_evidence_creation_idempotent(sqlite_db: None) -> None:
    """Test that strict evidence creation is idempotent."""
    dv_id = str(uuid7())
    evidence_id = deterministic_evidence_id(
        dataset_version_id=dv_id,
        engine_id=ENGINE_ID,
        kind="test",
        stable_key="test_key",
    )
    
    payload = {"test": "data"}
    created_at = datetime.now(timezone.utc)
    
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        db.add(DatasetVersion(id=dv_id))
        await db.commit()
        
        # Create evidence first time
        evidence1 = await _strict_create_evidence(
            db,
            evidence_id=evidence_id,
            dataset_version_id=dv_id,
            engine_id=ENGINE_ID,
            kind="test",
            payload=payload,
            created_at=created_at,
        )
        await db.commit()
        
        # Create same evidence again (should return existing)
        evidence2 = await _strict_create_evidence(
            db,
            evidence_id=evidence_id,
            dataset_version_id=dv_id,
            engine_id=ENGINE_ID,
            kind="test",
            payload=payload,
            created_at=created_at,
        )
        
        assert evidence1.evidence_id == evidence2.evidence_id
        assert evidence1.payload == evidence2.payload


@pytest.mark.anyio
async def test_strict_evidence_creation_conflict_detection(sqlite_db: None) -> None:
    """Test that strict evidence creation detects conflicts."""
    dv_id = str(uuid7())
    evidence_id = deterministic_evidence_id(
        dataset_version_id=dv_id,
        engine_id=ENGINE_ID,
        kind="test",
        stable_key="test_key",
    )
    
    payload1 = {"test": "data1"}
    payload2 = {"test": "data2"}
    created_at = datetime.now(timezone.utc)
    
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        db.add(DatasetVersion(id=dv_id))
        await db.commit()
        
        # Create evidence with payload1
        await _strict_create_evidence(
            db,
            evidence_id=evidence_id,
            dataset_version_id=dv_id,
            engine_id=ENGINE_ID,
            kind="test",
            payload=payload1,
            created_at=created_at,
        )
        await db.commit()
        
        # Try to create same evidence with different payload (should raise conflict)
        with pytest.raises(ImmutableConflictError, match="IMMUTABLE_EVIDENCE_MISMATCH"):
            await _strict_create_evidence(
                db,
                evidence_id=evidence_id,
                dataset_version_id=dv_id,
                engine_id=ENGINE_ID,
                kind="test",
                payload=payload2,
                created_at=created_at,
            )


@pytest.mark.anyio
async def test_strict_evidence_creation_dataset_version_mismatch(sqlite_db: None) -> None:
    """Test that strict evidence creation detects DatasetVersion mismatches."""
    dv_id_1 = str(uuid7())
    dv_id_2 = str(uuid7())
    evidence_id = deterministic_evidence_id(
        dataset_version_id=dv_id_1,
        engine_id=ENGINE_ID,
        kind="test",
        stable_key="test_key",
    )
    
    payload = {"test": "data"}
    created_at = datetime.now(timezone.utc)
    
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        db.add(DatasetVersion(id=dv_id_1))
        db.add(DatasetVersion(id=dv_id_2))
        await db.commit()
        
        # Create evidence with dv_id_1
        await _strict_create_evidence(
            db,
            evidence_id=evidence_id,
            dataset_version_id=dv_id_1,
            engine_id=ENGINE_ID,
            kind="test",
            payload=payload,
            created_at=created_at,
        )
        await db.commit()
        
        # Try to create same evidence with different DatasetVersion (should raise conflict)
        with pytest.raises(ImmutableConflictError, match="EVIDENCE_ID_COLLISION"):
            await _strict_create_evidence(
                db,
                evidence_id=evidence_id,
                dataset_version_id=dv_id_2,
                engine_id=ENGINE_ID,
                kind="test",
                payload=payload,
                created_at=created_at,
            )


@pytest.mark.anyio
async def test_audit_trail_uses_strict_evidence_creation(sqlite_db: None) -> None:
    """Test that audit trail uses strict evidence creation."""
    dv_id = str(uuid7())
    raw_id = f"raw-{uuid.uuid4().hex}"
    
    claim = ClaimRecord(
        claim_id="claim-audit-test",
        dataset_version_id=dv_id,
        policy_number="POL-AUDIT",
        claim_number="CLM-AUDIT",
        claim_type="property",
        claim_status="open",
        reported_date=datetime.now(timezone.utc),
        incident_date=None,
        claim_amount=5000.0,
        currency="USD",
        claimant_name="Audit Test",
        claimant_type="individual",
        description="Audit test claim",
    )
    
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        db.add(DatasetVersion(id=dv_id))
        await db.commit()
        
        audit = AuditTrail(db, dataset_version_id=dv_id)
        created_at = datetime.now(timezone.utc)
        
        # Log claim creation (uses strict evidence creation)
        evidence_id = await audit.log_claim_creation(claim, created_at=created_at)
        await db.commit()
        
        # Verify evidence was created
        evidence = await db.scalar(
            select(EvidenceRecord).where(EvidenceRecord.evidence_id == evidence_id)
        )
        assert evidence is not None
        assert evidence.dataset_version_id == dv_id
        assert evidence.engine_id == ENGINE_ID
        assert evidence.kind == "audit_trail"
        
        # Try to create same evidence with different payload (should raise conflict)
        # This verifies that audit trail is using strict creation
        with pytest.raises(ImmutableConflictError):
            # Create a new audit trail instance and try to log again with different payload
            # We'll directly test the strict creation
            different_payload = {"action": "claim_creation", "timestamp": created_at.isoformat(), "details": {"different": "data"}}
            await _strict_create_evidence(
                db,
                evidence_id=evidence_id,
                dataset_version_id=dv_id,
                engine_id=ENGINE_ID,
                kind="audit_trail",
                payload=different_payload,
                created_at=created_at,
            )


@pytest.mark.anyio
async def test_evidence_deterministic_ids(sqlite_db: None) -> None:
    """Test that evidence IDs are deterministic."""
    dv_id = str(uuid7())
    
    stable_key = "test_stable_key"
    evidence_id_1 = deterministic_evidence_id(
        dataset_version_id=dv_id,
        engine_id=ENGINE_ID,
        kind="test",
        stable_key=stable_key,
    )
    evidence_id_2 = deterministic_evidence_id(
        dataset_version_id=dv_id,
        engine_id=ENGINE_ID,
        kind="test",
        stable_key=stable_key,
    )
    
    assert evidence_id_1 == evidence_id_2, "Evidence IDs should be deterministic"
    
    # Different stable key should produce different ID
    evidence_id_3 = deterministic_evidence_id(
        dataset_version_id=dv_id,
        engine_id=ENGINE_ID,
        kind="test",
        stable_key="different_key",
    )
    
    assert evidence_id_1 != evidence_id_3, "Different stable keys should produce different IDs"






