"""Integration tests for the litigation/dispute engine run logic."""

from datetime import datetime, timezone
import uuid

import pytest
from sqlalchemy import select

from backend.app.core.db import get_sessionmaker
from backend.app.core.dataset.models import DatasetVersion
from backend.app.core.dataset.raw_models import RawRecord
from backend.app.core.dataset.uuidv7 import uuid7
from backend.app.core.normalization.models import NormalizedRecord
from backend.app.engines.enterprise_litigation_dispute.errors import (
    DatasetVersionMissingError,
    NormalizedRecordMissingError,
    StartedAtMissingError,
)
from backend.app.engines.enterprise_litigation_dispute.models import (
    EnterpriseLitigationDisputeFinding,
    EnterpriseLitigationDisputeRun,
)
from backend.app.engines.enterprise_litigation_dispute.run import run_engine


@pytest.mark.anyio
async def test_run_engine_requires_dataset_version() -> None:
    with pytest.raises(DatasetVersionMissingError):
        await run_engine(dataset_version_id=None, started_at="2024-01-01T00:00:00Z", parameters={})


@pytest.mark.anyio
async def test_run_engine_requires_started_at() -> None:
    with pytest.raises(StartedAtMissingError):
        await run_engine(dataset_version_id=str(uuid7()), started_at=None, parameters={})


@pytest.mark.anyio
async def test_run_engine_requires_normalized_record(sqlite_db: None) -> None:
    dv_id = str(uuid7())
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        db.add(DatasetVersion(id=dv_id))
        await db.commit()

    with pytest.raises(NormalizedRecordMissingError):
        await run_engine(dataset_version_id=dv_id, started_at="2024-01-01T00:00:00Z", parameters={"assumptions": {}})


@pytest.mark.anyio
async def test_run_engine_generates_findings_and_evidence(sqlite_db: None) -> None:
    dv_id = str(uuid7())
    raw_id = f"raw-{uuid.uuid4().hex}"
    scenario_payload = {
        "claims": [{"amount": 1_000_000}],
        "damages": {"compensatory": 2_000_000, "punitive": 400_000, "mitigation": 200_000},
        "liability": {
            "parties": [{"party": "Vendor", "percent": 80, "evidence_strength": 0.9}],
            "admissions": True,
        },
        "scenarios": [
            {"name": "low", "probability": 0.75, "expected_damages": 400_000, "liability_multiplier": 0.9},
            {"name": "high", "probability": 0.25, "expected_damages": 1_500_000, "liability_multiplier": 1.2},
        ],
        "legal_consistency": {"conflicts": ["regulation overlap"], "missing_support": []},
    }

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        db.add(DatasetVersion(id=dv_id))
        db.add(
            RawRecord(
                raw_record_id=raw_id,
                dataset_version_id=dv_id,
                source_system="litigation",
                source_record_id="LIT123",
                payload={"legal_dispute": scenario_payload},
                ingested_at=datetime.now(timezone.utc),
            )
        )
        db.add(
            NormalizedRecord(
                normalized_record_id=f"norm-{uuid.uuid4().hex}",
                dataset_version_id=dv_id,
                raw_record_id=raw_id,
                payload={"legal_dispute": scenario_payload},
                normalized_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()

    parameters = {
        "assumptions": {
            "damage": {"severity_thresholds": {"high": 1_000_000, "medium": 500_000}, "recovery_rate": 0.6},
            "liability": {"evidence_strength_thresholds": {"strong": 0.7, "weak": 0.3}},
            "scenario": {"probabilities": 1.0},
            "legal_consistency": {"completeness_requirements": ["statutes", "evidence"]},
        }
    }
    result = await run_engine(dataset_version_id=dv_id, started_at="2024-01-01T00:00:00Z", parameters=parameters)

    assert result["damage_assessment"]["net_damage"] > 0
    assert len(result["findings"]) == 4
    assert "summary" in result["evidence"]
    assert set(result["evidence"]) == {"damage", "liability", "scenario", "legal_consistency", "summary"}
    assert result["legal_consistency"]["consistent"] is False
    assert any(assump["id"].startswith("assumption_") for assump in result["assumptions"])

    async with sessionmaker() as db:
        run_record = await db.scalar(
            select(EnterpriseLitigationDisputeRun).where(
                EnterpriseLitigationDisputeRun.dataset_version_id == dv_id
            )
        )
        assert run_record is not None
        assert run_record.status == "completed"
        assert run_record.damage_payload == result["damage_assessment"]
        record_start_time = (
            run_record.run_start_time
            if run_record.run_start_time.tzinfo is not None
            else run_record.run_start_time.replace(tzinfo=timezone.utc)
        )
        assert record_start_time == datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
        assert run_record.run_end_time is not None

        finding_records = (
            await db.scalars(
                select(EnterpriseLitigationDisputeFinding).where(
                    EnterpriseLitigationDisputeFinding.dataset_version_id == dv_id
                )
            )
        ).all()
        assert len(finding_records) == 4
        assert all(record.run_id == run_record.run_id for record in finding_records)
        assert all(record.payload["dataset_version_id"] == dv_id for record in finding_records)
