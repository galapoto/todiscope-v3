"""Integration tests for the Enterprise Insurance Claim Forensics engine."""

from datetime import datetime, timezone
import uuid

import pytest
from sqlalchemy import select

from backend.app.core.db import get_sessionmaker
from backend.app.core.dataset.models import DatasetVersion
from backend.app.core.dataset.raw_models import RawRecord
from backend.app.core.dataset.uuidv7 import uuid7
from backend.app.core.normalization.models import NormalizedRecord
from backend.app.engines.enterprise_insurance_claim_forensics.errors import (
    DatasetVersionMissingError,
    NormalizedRecordMissingError,
    StartedAtMissingError,
)
from backend.app.engines.enterprise_insurance_claim_forensics.models import (
    EnterpriseInsuranceClaimForensicsFinding,
    EnterpriseInsuranceClaimForensicsRun,
)
from backend.app.engines.enterprise_insurance_claim_forensics.run import run_engine


@pytest.mark.anyio
async def test_run_engine_requires_dataset_version() -> None:
    """Test that engine requires dataset_version_id."""
    with pytest.raises(DatasetVersionMissingError):
        await run_engine(dataset_version_id=None, started_at="2024-01-01T00:00:00Z", parameters={})


@pytest.mark.anyio
async def test_run_engine_requires_started_at() -> None:
    """Test that engine requires started_at."""
    with pytest.raises(StartedAtMissingError):
        await run_engine(dataset_version_id=str(uuid7()), started_at=None, parameters={})


@pytest.mark.anyio
async def test_run_engine_requires_normalized_record(sqlite_db: None) -> None:
    """Test that engine requires normalized record."""
    dv_id = str(uuid7())
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        db.add(DatasetVersion(id=dv_id))
        await db.commit()

    with pytest.raises(NormalizedRecordMissingError):
        await run_engine(dataset_version_id=dv_id, started_at="2024-01-01T00:00:00Z", parameters={})


@pytest.mark.anyio
async def test_run_engine_generates_findings_and_evidence(sqlite_db: None) -> None:
    """Test that engine generates findings and evidence."""
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
                    "amount": 10000.0,
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

    result = await run_engine(
        dataset_version_id=dv_id,
        started_at="2024-01-01T00:00:00Z",
        parameters={},
    )

    assert "run_id" in result
    assert result["dataset_version_id"] == dv_id
    assert "loss_exposures" in result
    assert "validation_results" in result
    assert "audit_trail_summary" in result

    async with sessionmaker() as db:
        run_record = await db.scalar(
            select(EnterpriseInsuranceClaimForensicsRun).where(
                EnterpriseInsuranceClaimForensicsRun.dataset_version_id == dv_id
            )
        )
        assert run_record is not None
        assert run_record.status == "completed"
        assert "total_claims" in run_record.claim_summary
        record_start_time = (
            run_record.run_start_time
            if run_record.run_start_time.tzinfo is not None
            else run_record.run_start_time.replace(tzinfo=timezone.utc)
        )
        assert record_start_time == datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
        assert run_record.run_end_time is not None


@pytest.mark.anyio
async def test_run_engine_with_validation_errors(sqlite_db: None) -> None:
    """Test that engine handles validation errors correctly."""
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
            "incident_date": "2024-01-15T00:00:00Z",  # After reported date - invalid
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
                    "amount": 5000.0,  # Mismatched amount
                    "currency": "EUR",  # Mismatched currency
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

    result = await run_engine(
        dataset_version_id=dv_id,
        started_at="2024-01-01T00:00:00Z",
        parameters={},
    )

    assert "validation_results" in result
    validation_results = result["validation_results"]
    assert isinstance(validation_results, dict)
    
    # Check that at least one validation result exists
    assert len(validation_results) > 0
    
    # Check validation summary
    assert "validation_summary" in result
    validation_summary = result["validation_summary"]
    assert "total_claims" in validation_summary
    assert validation_summary["errors"] > 0  # Should have validation errors

    async with sessionmaker() as db:
        finding_records = (
            await db.scalars(
                select(EnterpriseInsuranceClaimForensicsFinding).where(
                    EnterpriseInsuranceClaimForensicsFinding.dataset_version_id == dv_id
                )
            )
        ).all()
        assert len(finding_records) > 0
        assert all(record.category == "claim_forensics" for record in finding_records)

