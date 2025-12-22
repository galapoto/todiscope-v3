"""Tests for findings creation, evidence linking, and raw record linkage."""

from __future__ import annotations

from datetime import datetime, timezone
import uuid

import pytest
from sqlalchemy import select

from backend.app.core.db import get_sessionmaker
from backend.app.core.dataset.models import DatasetVersion
from backend.app.core.dataset.raw_models import RawRecord
from backend.app.core.dataset.uuidv7 import uuid7
from backend.app.core.evidence.models import EvidenceRecord, FindingEvidenceLink, FindingRecord
from backend.app.core.normalization.models import NormalizedRecord
from backend.app.engines.enterprise_insurance_claim_forensics.run import run_engine


@pytest.mark.anyio
async def test_findings_created_via_core_service(sqlite_db: None) -> None:
    """Test that findings are created using core create_finding() service."""
    dv_id = str(uuid7())
    raw_id = f"raw-{uuid.uuid4().hex}"
    claim_payload = {
        "insurance_claim": {
            "claim_id": "claim-123",
            "policy_number": "POL-001",
            "claim_number": "CLM-001",
            "claim_type": "property",
            "claim_status": "open",
            "reported_date": "2024-01-01T00:00:00Z",
            "incident_date": "2023-12-15T00:00:00Z",
            "claim_amount": 10000.0,
            "currency": "USD",
            "claimant_name": "John Doe",
            "claimant_type": "individual",
            "description": "Property damage claim",
            "transactions": [
                {
                    "transaction_id": "tx-1",
                    "transaction_type": "payment",
                    "transaction_date": "2024-01-15T00:00:00Z",
                    "amount": 5000.0,
                    "currency": "USD",
                    "description": "Partial payment",
                }
            ],
        }
    }

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        db.add(DatasetVersion(id=dv_id))
        db.add(
            RawRecord(
                raw_record_id=raw_id,
                dataset_version_id=dv_id,
                source_system="insurance",
                source_record_id="INS123",
                payload=claim_payload,
                ingested_at=datetime.now(timezone.utc),
            )
        )
        db.add(
            NormalizedRecord(
                normalized_record_id=f"norm-{uuid.uuid4().hex}",
                dataset_version_id=dv_id,
                raw_record_id=raw_id,
                payload=claim_payload,
                normalized_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()

    await run_engine(
        dataset_version_id=dv_id,
        started_at="2024-01-01T00:00:00Z",
        parameters={},
    )

    async with sessionmaker() as db:
        # Check that findings were created in core FindingRecord table
        findings = (
            await db.scalars(
                select(FindingRecord).where(
                    FindingRecord.dataset_version_id == dv_id,
                    FindingRecord.kind == "claim_forensics",
                )
            )
        ).all()
        
        assert len(findings) > 0, "No findings created in core FindingRecord table"
        
        for finding in findings:
            assert finding.dataset_version_id == dv_id
            assert finding.kind == "claim_forensics"
            assert finding.finding_id is not None
            assert finding.payload is not None


@pytest.mark.anyio
async def test_findings_include_raw_record_id(sqlite_db: None) -> None:
    """Test that findings include raw_record_id for traceability."""
    dv_id = str(uuid7())
    raw_id = f"raw-{uuid.uuid4().hex}"
    claim_payload = {
        "insurance_claim": {
            "claim_id": "claim-456",
            "policy_number": "POL-002",
            "claim_number": "CLM-002",
            "claim_type": "liability",
            "claim_status": "open",
            "reported_date": "2024-02-01T00:00:00Z",
            "incident_date": "2024-01-15T00:00:00Z",
            "claim_amount": 20000.0,
            "currency": "USD",
            "claimant_name": "Jane Smith",
            "claimant_type": "individual",
            "description": "Liability claim",
            "transactions": [],
        }
    }

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        db.add(DatasetVersion(id=dv_id))
        db.add(
            RawRecord(
                raw_record_id=raw_id,
                dataset_version_id=dv_id,
                source_system="insurance",
                source_record_id="INS456",
                payload=claim_payload,
                ingested_at=datetime.now(timezone.utc),
            )
        )
        db.add(
            NormalizedRecord(
                normalized_record_id=f"norm-{uuid.uuid4().hex}",
                dataset_version_id=dv_id,
                raw_record_id=raw_id,
                payload=claim_payload,
                normalized_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()

    await run_engine(
        dataset_version_id=dv_id,
        started_at="2024-02-01T00:00:00Z",
        parameters={},
    )

    async with sessionmaker() as db:
        findings = (
            await db.scalars(
                select(FindingRecord).where(
                    FindingRecord.dataset_version_id == dv_id,
                    FindingRecord.kind == "claim_forensics",
                )
            )
        ).all()
        
        assert len(findings) > 0
        for finding in findings:
            assert finding.raw_record_id == raw_id, f"Finding {finding.finding_id} missing raw_record_id"
            assert finding.raw_record_id is not None
            assert finding.raw_record_id != ""


@pytest.mark.anyio
async def test_findings_linked_to_evidence(sqlite_db: None) -> None:
    """Test that findings are linked to evidence via FindingEvidenceLink."""
    dv_id = str(uuid7())
    raw_id = f"raw-{uuid.uuid4().hex}"
    claim_payload = {
        "insurance_claim": {
            "claim_id": "claim-789",
            "policy_number": "POL-003",
            "claim_number": "CLM-003",
            "claim_type": "property",
            "claim_status": "open",
            "reported_date": "2024-03-01T00:00:00Z",
            "incident_date": "2024-02-15T00:00:00Z",
            "claim_amount": 15000.0,
            "currency": "USD",
            "claimant_name": "Bob Johnson",
            "claimant_type": "individual",
            "description": "Property claim",
            "transactions": [
                {
                    "transaction_id": "tx-2",
                    "transaction_type": "payment",
                    "transaction_date": "2024-03-15T00:00:00Z",
                    "amount": 15000.0,
                    "currency": "USD",
                    "description": "Full payment",
                }
            ],
        }
    }

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        db.add(DatasetVersion(id=dv_id))
        db.add(
            RawRecord(
                raw_record_id=raw_id,
                dataset_version_id=dv_id,
                source_system="insurance",
                source_record_id="INS789",
                payload=claim_payload,
                ingested_at=datetime.now(timezone.utc),
            )
        )
        db.add(
            NormalizedRecord(
                normalized_record_id=f"norm-{uuid.uuid4().hex}",
                dataset_version_id=dv_id,
                raw_record_id=raw_id,
                payload=claim_payload,
                normalized_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()

    await run_engine(
        dataset_version_id=dv_id,
        started_at="2024-03-01T00:00:00Z",
        parameters={},
    )

    async with sessionmaker() as db:
        findings = (
            await db.scalars(
                select(FindingRecord).where(
                    FindingRecord.dataset_version_id == dv_id,
                    FindingRecord.kind == "claim_forensics",
                )
            )
        ).all()
        
        assert len(findings) > 0
        
        for finding in findings:
            # Check that evidence links exist
            links = (
                await db.scalars(
                    select(FindingEvidenceLink).where(
                        FindingEvidenceLink.finding_id == finding.finding_id
                    )
                )
            ).all()
            
            assert len(links) > 0, f"Finding {finding.finding_id} has no evidence links"
            
            # Verify linked evidence exists
            for link in links:
                evidence = await db.scalar(
                    select(EvidenceRecord).where(EvidenceRecord.evidence_id == link.evidence_id)
                )
                assert evidence is not None, f"Linked evidence {link.evidence_id} does not exist"
                assert evidence.dataset_version_id == dv_id
                assert evidence.engine_id == "engine_enterprise_insurance_claim_forensics"


@pytest.mark.anyio
async def test_evidence_created_for_findings(sqlite_db: None) -> None:
    """Test that evidence records are created for findings."""
    dv_id = str(uuid7())
    raw_id = f"raw-{uuid.uuid4().hex}"
    claim_payload = {
        "insurance_claim": {
            "claim_id": "claim-evidence-test",
            "policy_number": "POL-EVID",
            "claim_number": "CLM-EVID",
            "claim_type": "property",
            "claim_status": "open",
            "reported_date": "2024-04-01T00:00:00Z",
            "incident_date": "2024-03-15T00:00:00Z",
            "claim_amount": 25000.0,
            "currency": "USD",
            "claimant_name": "Evidence Test",
            "claimant_type": "individual",
            "description": "Evidence test claim",
            "transactions": [],
        }
    }

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        db.add(DatasetVersion(id=dv_id))
        db.add(
            RawRecord(
                raw_record_id=raw_id,
                dataset_version_id=dv_id,
                source_system="insurance",
                source_record_id="INS-EVID",
                payload=claim_payload,
                ingested_at=datetime.now(timezone.utc),
            )
        )
        db.add(
            NormalizedRecord(
                normalized_record_id=f"norm-{uuid.uuid4().hex}",
                dataset_version_id=dv_id,
                raw_record_id=raw_id,
                payload=claim_payload,
                normalized_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()

    await run_engine(
        dataset_version_id=dv_id,
        started_at="2024-04-01T00:00:00Z",
        parameters={},
    )

    async with sessionmaker() as db:
        findings = (
            await db.scalars(
                select(FindingRecord).where(
                    FindingRecord.dataset_version_id == dv_id,
                    FindingRecord.kind == "claim_forensics",
                )
            )
        ).all()
        
        assert len(findings) > 0
        
        for finding in findings:
            # Get evidence linked to this finding
            links = (
                await db.scalars(
                    select(FindingEvidenceLink).where(
                        FindingEvidenceLink.finding_id == finding.finding_id
                    )
                )
            ).all()
            
            assert len(links) > 0
            
            for link in links:
                evidence = await db.scalar(
                    select(EvidenceRecord).where(EvidenceRecord.evidence_id == link.evidence_id)
                )
                assert evidence is not None
                assert evidence.kind == "loss_exposure"
                assert evidence.engine_id == "engine_enterprise_insurance_claim_forensics"
                assert evidence.dataset_version_id == dv_id
                
                # Verify evidence payload contains finding data
                assert "finding" in evidence.payload
                assert "exposure" in evidence.payload
                assert "source_raw_record_id" in evidence.payload
                assert evidence.payload["source_raw_record_id"] == raw_id


@pytest.mark.anyio
async def test_findings_traceability_to_raw_records(sqlite_db: None) -> None:
    """Test that findings can be traced back to source raw records."""
    dv_id = str(uuid7())
    raw_id_1 = f"raw-{uuid.uuid4().hex}"
    raw_id_2 = f"raw-{uuid.uuid4().hex}"
    
    claim_payload_1 = {
        "insurance_claim": {
            "claim_id": "claim-trace-1",
            "policy_number": "POL-TRACE-1",
            "claim_number": "CLM-TRACE-1",
            "claim_type": "property",
            "claim_status": "open",
            "reported_date": "2024-05-01T00:00:00Z",
            "incident_date": "2024-04-15T00:00:00Z",
            "claim_amount": 30000.0,
            "currency": "USD",
            "claimant_name": "Trace Test 1",
            "claimant_type": "individual",
            "description": "Trace test claim 1",
            "transactions": [],
        }
    }
    
    claim_payload_2 = {
        "insurance_claim": {
            "claim_id": "claim-trace-2",
            "policy_number": "POL-TRACE-2",
            "claim_number": "CLM-TRACE-2",
            "claim_type": "liability",
            "claim_status": "open",
            "reported_date": "2024-05-02T00:00:00Z",
            "incident_date": "2024-04-20T00:00:00Z",
            "claim_amount": 40000.0,
            "currency": "USD",
            "claimant_name": "Trace Test 2",
            "claimant_type": "individual",
            "description": "Trace test claim 2",
            "transactions": [],
        }
    }

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        db.add(DatasetVersion(id=dv_id))
        db.add(
            RawRecord(
                raw_record_id=raw_id_1,
                dataset_version_id=dv_id,
                source_system="insurance",
                source_record_id="INS-TRACE-1",
                payload=claim_payload_1,
                ingested_at=datetime.now(timezone.utc),
            )
        )
        db.add(
            RawRecord(
                raw_record_id=raw_id_2,
                dataset_version_id=dv_id,
                source_system="insurance",
                source_record_id="INS-TRACE-2",
                payload=claim_payload_2,
                ingested_at=datetime.now(timezone.utc),
            )
        )
        db.add(
            NormalizedRecord(
                normalized_record_id=f"norm-{uuid.uuid4().hex}",
                dataset_version_id=dv_id,
                raw_record_id=raw_id_1,
                payload=claim_payload_1,
                normalized_at=datetime.now(timezone.utc),
            )
        )
        db.add(
            NormalizedRecord(
                normalized_record_id=f"norm-{uuid.uuid4().hex}",
                dataset_version_id=dv_id,
                raw_record_id=raw_id_2,
                payload=claim_payload_2,
                normalized_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()

    await run_engine(
        dataset_version_id=dv_id,
        started_at="2024-05-01T00:00:00Z",
        parameters={},
    )

    async with sessionmaker() as db:
        findings = (
            await db.scalars(
                select(FindingRecord).where(
                    FindingRecord.dataset_version_id == dv_id,
                    FindingRecord.kind == "claim_forensics",
                )
            )
        ).all()
        
        assert len(findings) == 2
        
        # Verify each finding is linked to correct raw record
        finding_to_raw = {}
        for finding in findings:
            finding_to_raw[finding.finding_id] = finding.raw_record_id
            assert finding.raw_record_id in (raw_id_1, raw_id_2)
        
        # Verify we can trace back to raw records
        raw_records = (
            await db.scalars(
                select(RawRecord).where(
                    RawRecord.dataset_version_id == dv_id,
                    RawRecord.raw_record_id.in_([raw_id_1, raw_id_2]),
                )
            )
        ).all()
        
        assert len(raw_records) == 2
        
        # Verify finding payloads reference correct claim IDs
        for finding in findings:
            payload = finding.payload
            claim_id = payload.get("claim_id")
            assert claim_id in ("claim-trace-1", "claim-trace-2")
            
            # Verify raw_record_id matches the claim
            if claim_id == "claim-trace-1":
                assert finding.raw_record_id == raw_id_1
            elif claim_id == "claim-trace-2":
                assert finding.raw_record_id == raw_id_2


