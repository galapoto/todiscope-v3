"""Integration tests covering the regulatory readiness engine endpoint, persistence, and linked artifacts."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from backend.app.core.db import get_sessionmaker
from backend.app.core.dataset.models import DatasetVersion
from backend.app.core.dataset.raw_models import RawRecord
from backend.app.core.evidence.models import FindingEvidenceLink, FindingRecord
from backend.app.engines.regulatory_readiness.engine import ENGINE_ID, router
from backend.app.engines.regulatory_readiness.models import (
    RegulatoryControl,
    RegulatoryGap,
    RegulatoryRemediationTask,
)
from backend.app.engines.regulatory_readiness.run import run_engine


@pytest.fixture(autouse=True)
def enable_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure the regulatory readiness engine is enabled during tests."""
    monkeypatch.setenv("TODISCOPE_ENABLED_ENGINES", ENGINE_ID)


@pytest.fixture
def regulatory_payload() -> dict:
    """Standardized regulatory payload for integration testing."""
    return {
        "regulatory": {
            "controls": [
                {
                    "id": "ctrl-iso-governance",
                    "title": "ISO governance control",
                    "description": "Implements ISO 27001 controls.",
                    "category": "data_governance",
                    "risk_type": "compliance",
                    "ownership": ["ops_team"],
                    "status": "implemented",
                    "frameworks": ["iso27001"],
                },
                {
                    "id": "ctrl-gap",
                    "title": "Risk management gap",
                    "description": "Control awaiting implementation.",
                    "category": "risk_management",
                    "risk_type": "operational",
                    "ownership": ["risk_team"],
                    "status": "not_implemented",
                    "frameworks": ["internal_controls"],
                },
            ],
            "control_status_hints": {"ctrl-gap": "not_implemented"},
            "data_flow": {"source": "erp_system"},
        }
    }


@pytest.fixture
async def seeded_dataset(sqlite_db, regulatory_payload: dict) -> str:
    """Seed a DatasetVersion and RawRecord containing regulatory inputs."""
    dataset_version_id = "reg-readiness-dv"
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        db.add(DatasetVersion(id=dataset_version_id))
        db.add(
            RawRecord(
                raw_record_id="raw-reg-1",
                dataset_version_id=dataset_version_id,
                source_system="integration-test",
                source_record_id="raw-reg-1",
                payload=regulatory_payload,
                ingested_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()
    return dataset_version_id


@pytest.mark.anyio
async def test_regulatory_endpoint_returns_readiness(seeded_dataset: str) -> None:
    """Endpoint should run the engine, return readiness, and detect gaps."""
    payload = {
        "dataset_version_id": seeded_dataset,
        "started_at": "2024-01-01T00:00:00Z",
        "parameters": {"control_status_hints": {"ctrl-gap": "not_implemented"}},
    }
    response = await router.routes[0].endpoint(payload)
    assert response["dataset_version_id"] == seeded_dataset
    assert 0.0 <= response["readiness_score"] <= 1.0
    assert response["control_summary"]["gaps_detected"] >= 1
    assert response["gaps"]


@pytest.mark.anyio
async def test_regulatory_records_persist(seeded_dataset: str) -> None:
    """Controls, gaps, and remediation tasks should be persisted in the database."""
    await run_engine(
        dataset_version_id=seeded_dataset,
        started_at="2024-01-01T00:00:00Z",
        parameters={},
    )
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        controls = (
            await db.scalars(
                select(RegulatoryControl).where(RegulatoryControl.dataset_version_id == seeded_dataset)
            )
        ).all()
        gaps = (
            await db.scalars(
                select(RegulatoryGap).where(RegulatoryGap.dataset_version_id == seeded_dataset)
            )
        ).all()
        tasks = (
            await db.scalars(
                select(RegulatoryRemediationTask).where(RegulatoryRemediationTask.dataset_version_id == seeded_dataset)
            )
        ).all()
    assert len(controls) >= 2
    assert gaps, "Gaps should be detected for incomplete controls"
    assert tasks, "Remediation tasks should be created for each gap"


@pytest.mark.anyio
async def test_evidence_linking_created(seeded_dataset: str) -> None:
    """Findings must link to evidence so the regulatory gaps remain traceable."""
    await run_engine(
        dataset_version_id=seeded_dataset,
        started_at="2024-01-01T00:00:00Z",
        parameters={},
    )
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        linked = (
            await db.scalars(
                select(FindingEvidenceLink)
                .join(FindingRecord, FindingEvidenceLink.finding_id == FindingRecord.finding_id)
                .where(FindingRecord.dataset_version_id == seeded_dataset)
            )
        ).all()
    assert linked, "At least one finding should link to evidence for traceability"
