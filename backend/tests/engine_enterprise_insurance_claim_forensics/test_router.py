"""HTTP-level tests for the Enterprise Insurance Claim Forensics engine router."""

from __future__ import annotations

from datetime import datetime, timezone
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from backend.app.core.db import get_sessionmaker
from backend.app.core.dataset.models import DatasetVersion
from backend.app.core.dataset.raw_models import RawRecord
from backend.app.core.dataset.uuidv7 import uuid7
from backend.app.core.normalization.models import NormalizedRecord
from backend.app.engines.enterprise_insurance_claim_forensics.constants import ENGINE_ID
from backend.app.engines.enterprise_insurance_claim_forensics.models import (
    EnterpriseInsuranceClaimForensicsRun,
)
from backend.app.main import create_app


async def _seed_claim_records(sessionmaker, dv_id: str, raw_id: str, payload: dict) -> None:
    """Seed a minimal claim RawRecord + NormalizedRecord for HTTP tests."""
    async with sessionmaker() as db:
        db.add(DatasetVersion(id=dv_id))
        db.add(
            RawRecord(
                raw_record_id=raw_id,
                dataset_version_id=dv_id,
                source_system="insurance",
                source_record_id="INS-HTTP-001",
                payload=payload,
                ingested_at=datetime.now(timezone.utc),
            )
        )
        db.add(
            NormalizedRecord(
                normalized_record_id=f"norm-{uuid.uuid4().hex}",
                dataset_version_id=dv_id,
                raw_record_id=raw_id,
                payload=payload,
                normalized_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()


@pytest.mark.anyio
async def test_run_endpoint_success(monkeypatch: pytest.MonkeyPatch, sqlite_db: None) -> None:
    """End-to-end test: HTTP run endpoint returns 200 and expected fields."""
    monkeypatch.setenv("TODISCOPE_ENABLED_ENGINES", ENGINE_ID)
    dv_id = str(uuid7())
    raw_id = f"raw-{uuid.uuid4().hex}"
    claim_payload = {
        "insurance_claim": {
            "claim_id": "CLAIM-HTTP-OK",
            "policy_number": "POL-HTTP-OK",
            "claim_number": "CLM-HTTP-OK",
            "claim_type": "property",
            "claim_status": "open",
            "reported_date": "2024-01-01T00:00:00Z",
            "incident_date": "2023-12-15T00:00:00Z",
            "claim_amount": 10000.0,
            "currency": "USD",
            "claimant_name": "HTTP Success",
            "claimant_type": "individual",
            "description": "HTTP success path claim",
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
    await _seed_claim_records(sessionmaker, dv_id, raw_id, claim_payload)

    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v3/engines/enterprise-insurance-claim-forensics/run",
            json={
                "dataset_version_id": dv_id,
                "started_at": "2024-01-01T00:00:00Z",
                "parameters": {},
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["dataset_version_id"] == dv_id
    assert "run_id" in data
    assert "loss_exposures" in data
    assert "validation_results" in data
    assert "audit_trail_summary" in data
    # Enterprise features
    assert "readiness_scores" in data
    assert "remediation_tasks" in data

    # Verify a run record was persisted
    async with sessionmaker() as db:
        run_record = await db.scalar(
            select(EnterpriseInsuranceClaimForensicsRun).where(
                EnterpriseInsuranceClaimForensicsRun.run_id == data["run_id"]
            )
        )
        assert run_record is not None
        assert run_record.dataset_version_id == dv_id


@pytest.mark.anyio
async def test_run_endpoint_not_enabled(monkeypatch: pytest.MonkeyPatch, sqlite_db: None) -> None:
    """Engine router should not be mounted when engine is disabled."""
    monkeypatch.setenv("TODISCOPE_ENABLED_ENGINES", "")
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v3/engines/enterprise-insurance-claim-forensics/run",
            json={},
        )
    assert response.status_code == 404


@pytest.mark.anyio
async def test_run_endpoint_missing_dataset_version(monkeypatch: pytest.MonkeyPatch, sqlite_db: None) -> None:
    """Missing dataset_version_id should result in HTTP 400 from the endpoint."""
    monkeypatch.setenv("TODISCOPE_ENABLED_ENGINES", ENGINE_ID)
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v3/engines/enterprise-insurance-claim-forensics/run",
            json={
                # dataset_version_id intentionally omitted
                "started_at": "2024-01-01T00:00:00Z",
                "parameters": {},
            },
        )
    assert response.status_code == 400


@pytest.mark.anyio
async def test_run_endpoint_unexpected_error_returns_500(monkeypatch: pytest.MonkeyPatch, sqlite_db: None) -> None:
    """Unexpected errors inside run_engine are surfaced as HTTP 500."""
    monkeypatch.setenv("TODISCOPE_ENABLED_ENGINES", ENGINE_ID)

    # Monkeypatch the engine's run_engine used by the endpoint to raise a generic error
    from backend.app.engines import enterprise_insurance_claim_forensics as engine_pkg

    def _boom(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("boom")

    monkeypatch.setattr(
        "backend.app.engines.enterprise_insurance_claim_forensics.run.run_engine", _boom, raising=True
    )

    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v3/engines/enterprise-insurance-claim-forensics/run",
            json={
                "dataset_version_id": str(uuid7()),
                "started_at": "2024-01-01T00:00:00Z",
                "parameters": {},
            },
        )

    assert response.status_code == 500
    body = response.json()
    # Endpoint wraps unexpected errors as ENGINE_RUN_FAILED with type information
    assert isinstance(body.get("detail"), str)
    assert "ENGINE_RUN_FAILED" in body["detail"], body["detail"]
