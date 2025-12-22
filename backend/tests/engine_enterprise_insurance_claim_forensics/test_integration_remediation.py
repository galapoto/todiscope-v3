"""Integration tests for remediation: findings, evidence linking, and raw record traceability."""

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
async def test_end_to_end_findings_and_evidence_linking(sqlite_db: None) -> None:
    """End-to-end test: findings creation, evidence linking, and raw record traceability."""
    dv_id = str(uuid7())
    raw_id = f"raw-{uuid.uuid4().hex}"
    claim_payload = {
        "insurance_claim": {
            "claim_id": "claim-e2e",
            "policy_number": "POL-E2E",
            "claim_number": "CLM-E2E",
            "claim_type": "property",
            "claim_status": "open",
            "reported_date": "2024-06-01T00:00:00Z",
            "incident_date": "2024-05-15T00:00:00Z",
            "claim_amount": 35000.0,
            "currency": "USD",
            "claimant_name": "E2E Test",
            "claimant_type": "individual",
            "description": "End-to-end test claim",
            "transactions": [
                {
                    "transaction_id": "tx-e2e",
                    "transaction_type": "payment",
                    "transaction_date": "2024-06-15T00:00:00Z",
                    "amount": 20000.0,
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
                source_record_id="INS-E2E",
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

    result = await run_engine(
        dataset_version_id=dv_id,
        started_at="2024-06-01T00:00:00Z",
        parameters={},
    )

    # Verify engine returns expected structure
    assert "run_id" in result
    assert "dataset_version_id" in result
    assert result["dataset_version_id"] == dv_id
    assert "loss_exposures" in result
    assert "validation_results" in result

    async with sessionmaker() as db:
        # 1. Verify findings were created in core FindingRecord table
        findings = (
            await db.scalars(
                select(FindingRecord).where(
                    FindingRecord.dataset_version_id == dv_id,
                    FindingRecord.kind == "claim_forensics",
                )
            )
        ).all()
        
        assert len(findings) > 0, "Findings should be created in core FindingRecord table"
        
        # 2. Verify each finding has raw_record_id
        for finding in findings:
            assert finding.raw_record_id == raw_id, f"Finding {finding.finding_id} should have raw_record_id"
            assert finding.dataset_version_id == dv_id
            
            # 3. Verify finding is linked to evidence
            links = (
                await db.scalars(
                    select(FindingEvidenceLink).where(
                        FindingEvidenceLink.finding_id == finding.finding_id
                    )
                )
            ).all()
            
            assert len(links) > 0, f"Finding {finding.finding_id} should be linked to evidence"
            
            # 4. Verify linked evidence exists and is correct
            for link in links:
                evidence = await db.scalar(
                    select(EvidenceRecord).where(EvidenceRecord.evidence_id == link.evidence_id)
                )
                assert evidence is not None, f"Evidence {link.evidence_id} should exist"
                assert evidence.dataset_version_id == dv_id
                assert evidence.engine_id == "engine_enterprise_insurance_claim_forensics"
                assert evidence.kind == "loss_exposure"
                
                # 5. Verify evidence payload contains raw_record_id
                assert "source_raw_record_id" in evidence.payload
                assert evidence.payload["source_raw_record_id"] == raw_id
                
                # 6. Verify evidence payload contains finding data
                assert "finding" in evidence.payload
                assert "exposure" in evidence.payload
                assert "validation" in evidence.payload


@pytest.mark.anyio
async def test_dataset_version_enforcement(sqlite_db: None) -> None:
    """Test that DatasetVersion is enforced throughout the process."""
    dv_id = str(uuid7())
    raw_id = f"raw-{uuid.uuid4().hex}"
    claim_payload = {
        "insurance_claim": {
            "claim_id": "claim-dv-test",
            "policy_number": "POL-DV",
            "claim_number": "CLM-DV",
            "claim_type": "property",
            "claim_status": "open",
            "reported_date": "2024-07-01T00:00:00Z",
            "incident_date": "2024-06-15T00:00:00Z",
            "claim_amount": 40000.0,
            "currency": "USD",
            "claimant_name": "DV Test",
            "claimant_type": "individual",
            "description": "DatasetVersion test claim",
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
                source_record_id="INS-DV",
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
        started_at="2024-07-01T00:00:00Z",
        parameters={},
    )

    async with sessionmaker() as db:
        # Verify all findings have correct DatasetVersion
        findings = (
            await db.scalars(
                select(FindingRecord).where(
                    FindingRecord.dataset_version_id == dv_id,
                )
            )
        ).all()
        
        for finding in findings:
            assert finding.dataset_version_id == dv_id
            
            # Verify all linked evidence has correct DatasetVersion
            links = (
                await db.scalars(
                    select(FindingEvidenceLink).where(
                        FindingEvidenceLink.finding_id == finding.finding_id
                    )
                )
            ).all()
            
            for link in links:
                evidence = await db.scalar(
                    select(EvidenceRecord).where(EvidenceRecord.evidence_id == link.evidence_id)
                )
                assert evidence.dataset_version_id == dv_id


@pytest.mark.anyio
async def test_multiple_claims_traceability(sqlite_db: None) -> None:
    """Test traceability with multiple claims from different raw records."""
    dv_id = str(uuid7())
    raw_id_1 = f"raw-{uuid.uuid4().hex}"
    raw_id_2 = f"raw-{uuid.uuid4().hex}"
    
    claim_payload_1 = {
        "insurance_claim": {
            "claim_id": "claim-multi-1",
            "policy_number": "POL-MULTI-1",
            "claim_number": "CLM-MULTI-1",
            "claim_type": "property",
            "claim_status": "open",
            "reported_date": "2024-08-01T00:00:00Z",
            "incident_date": "2024-07-15T00:00:00Z",
            "claim_amount": 50000.0,
            "currency": "USD",
            "claimant_name": "Multi Test 1",
            "claimant_type": "individual",
            "description": "Multi test claim 1",
            "transactions": [],
        }
    }
    
    claim_payload_2 = {
        "insurance_claim": {
            "claim_id": "claim-multi-2",
            "policy_number": "POL-MULTI-2",
            "claim_number": "CLM-MULTI-2",
            "claim_type": "liability",
            "claim_status": "open",
            "reported_date": "2024-08-02T00:00:00Z",
            "incident_date": "2024-07-20T00:00:00Z",
            "claim_amount": 60000.0,
            "currency": "USD",
            "claimant_name": "Multi Test 2",
            "claimant_type": "individual",
            "description": "Multi test claim 2",
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
                source_record_id="INS-MULTI-1",
                payload=claim_payload_1,
                ingested_at=datetime.now(timezone.utc),
            )
        )
        db.add(
            RawRecord(
                raw_record_id=raw_id_2,
                dataset_version_id=dv_id,
                source_system="insurance",
                source_record_id="INS-MULTI-2",
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
        started_at="2024-08-01T00:00:00Z",
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
        
        # Verify each finding is correctly mapped to its raw record
        claim_to_raw = {
            "claim-multi-1": raw_id_1,
            "claim-multi-2": raw_id_2,
        }
        
        for finding in findings:
            payload = finding.payload
            claim_id = payload.get("claim_id")
            expected_raw_id = claim_to_raw.get(claim_id)
            
            assert expected_raw_id is not None, f"Unexpected claim_id: {claim_id}"
            assert finding.raw_record_id == expected_raw_id, (
                f"Finding for claim {claim_id} should have raw_record_id {expected_raw_id}, "
                f"but got {finding.raw_record_id}"
            )
            
            # Verify evidence also references correct raw_record_id
            links = (
                await db.scalars(
                    select(FindingEvidenceLink).where(
                        FindingEvidenceLink.finding_id == finding.finding_id
                    )
                )
            ).all()
            
            for link in links:
                evidence = await db.scalar(
                    select(EvidenceRecord).where(EvidenceRecord.evidence_id == link.evidence_id)
                )
                assert evidence.payload["source_raw_record_id"] == expected_raw_id


