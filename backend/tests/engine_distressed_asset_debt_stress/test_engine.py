from __future__ import annotations

import os
from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from backend.app.core.db import get_sessionmaker
from backend.app.core.dataset.raw_models import RawRecord
from backend.app.core.evidence.models import EvidenceRecord, FindingEvidenceLink, FindingRecord
from backend.app.main import create_app


def _sample_record(record_id: str = "distressed_asset_1") -> dict:
    return {
        "source_system": "distress-suite",
        "source_record_id": record_id,
        "financial": {
            "debt": {
                "total_outstanding": 1_000_000,
                "interest_rate_pct": 5.0,
                "collateral_value": 750_000,
            },
            "assets": {"total": 2_000_000},
        },
        "distressed_assets": [
            {"name": "Asset A", "value": 200_000, "recovery_rate_pct": 35},
            {"name": "Asset B", "value": 150_000, "recovery_rate_pct": 50},
        ],
    }


@pytest.mark.anyio
async def test_engine_returns_debt_exposure_and_stress_outcomes(sqlite_db: None) -> None:
    os.environ["TODISCOPE_ENABLED_ENGINES"] = "engine_distressed_asset_debt_stress"
    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ingest_res = await ac.post(
            "/api/v3/ingest-records",
            json={"records": [_sample_record()], "normalize": True},
        )
        assert ingest_res.status_code == 200
        dv_id = ingest_res.json()["dataset_version_id"]

        run_res = await ac.post(
            "/api/v3/engines/distressed-asset-debt-stress/run",
            json={
                "dataset_version_id": dv_id,
                "started_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        assert run_res.status_code == 200
        payload = run_res.json()

    report = payload["report"]
    exposure_section = report["debt_exposure"]
    assert exposure_section["interest_payment"] == pytest.approx(50_000)
    assert exposure_section["collateral_coverage_ratio"] == pytest.approx(0.75)
    assert exposure_section["net_exposure_after_recovery"] == pytest.approx(105_000)

    stress_tests = report["stress_tests"]
    assert len(stress_tests) == 3
    interest_scenario = next(
        scenario for scenario in stress_tests if scenario["scenario_id"] == "interest_rate_spike"
    )
    assert interest_scenario["interest_rate_pct"] == pytest.approx(7.5)
    assert interest_scenario["loss_estimate"] > 0

    assert "material_findings" in payload
    assert len(payload["material_findings"]) == 4

    async with get_sessionmaker()() as db:
        evidence = await db.scalar(
            select(EvidenceRecord).where(EvidenceRecord.evidence_id == payload["debt_exposure_evidence_id"])
        )
        assert evidence is not None
        assert evidence.dataset_version_id == dv_id
        assert evidence.kind == "debt_exposure"

        for scenario_id, stress_evidence_id in payload["stress_test_evidence_ids"].items():
            ev = await db.scalar(select(EvidenceRecord).where(EvidenceRecord.evidence_id == stress_evidence_id))
            assert ev is not None
            assert ev.kind == "stress_test"

        finding_ids = [f["id"] for f in payload["material_findings"]]
        findings = (
            await db.scalars(select(FindingRecord).where(FindingRecord.finding_id.in_(finding_ids)))
        ).all()
        assert len(findings) == len(finding_ids)

        links = await db.scalars(select(FindingEvidenceLink).where(FindingEvidenceLink.finding_id.in_(finding_ids)))
        assert links.all()

        raw_record = await db.scalar(select(RawRecord).where(RawRecord.dataset_version_id == dv_id))
        assert raw_record is not None


@pytest.mark.anyio
async def test_engine_requires_normalized_record(sqlite_db: None) -> None:
    os.environ["TODISCOPE_ENABLED_ENGINES"] = "engine_distressed_asset_debt_stress"
    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ingest_res = await ac.post("/api/v3/ingest-records", json={"records": [_sample_record("raw_only")]})
        assert ingest_res.status_code == 200
        dv_id = ingest_res.json()["dataset_version_id"]

        run_res = await ac.post(
            "/api/v3/engines/distressed-asset-debt-stress/run",
            json={
                "dataset_version_id": dv_id,
                "started_at": datetime.now(timezone.utc).isoformat(),
            },
        )
    assert run_res.status_code == 409
    assert "NORMALIZED_RECORD_REQUIRED" in run_res.json().get("detail", "")
