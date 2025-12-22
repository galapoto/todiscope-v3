import os

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.main import create_app


@pytest.mark.anyio
async def test_fx_artifact_immutable_idempotent(sqlite_db: None) -> None:
    os.environ["TODISCOPE_ARTIFACT_STORE_KIND"] = "memory"
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        dv_id = (await ac.post("/api/v3/ingest")).json()["dataset_version_id"]
        payload = {
            "dataset_version_id": dv_id,
            "base_currency": "EUR",
            "effective_date": "2026-01-31",
            "rates": {"USD": "0.91", "EUR": "1"},
            "created_at": "2026-01-01T00:00:00+00:00",
        }
        r1 = await ac.post("/api/v3/fx-artifacts", json=payload)
        assert r1.status_code == 200
        r2 = await ac.post("/api/v3/fx-artifacts", json=payload)
        assert r2.status_code == 200
        assert r1.json()["fx_artifact_id"] == r2.json()["fx_artifact_id"]


@pytest.mark.anyio
async def test_run_fails_without_fx_artifact_id(sqlite_db: None) -> None:
    os.environ["TODISCOPE_ENABLED_ENGINES"] = "engine_financial_forensics"
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        dv_id = (await ac.post("/api/v3/ingest")).json()["dataset_version_id"]
        res = await ac.post(
            "/api/v3/engines/financial-forensics/run",
            json={
                "dataset_version_id": dv_id,
                "started_at": "2026-01-01T00:00:00+00:00",
                "parameters": {"rounding_mode": "ROUND_HALF_UP", "rounding_quantum": "0.01"},
            },
        )
    assert res.status_code == 400
    assert "FX_ARTIFACT_ID_REQUIRED" in res.json()["detail"]


@pytest.mark.anyio
async def test_normalization_works_without_fx(sqlite_db: None) -> None:
    os.environ["TODISCOPE_ENABLED_ENGINES"] = "engine_financial_forensics"
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ingest = await ac.post(
            "/api/v3/ingest-records",
            json={
                "records": [
                    {
                        "source_system": "erp",
                        "source_record_id": "inv-1",
                        "record_type": "invoice",
                        "posted_at": "2026-01-01T00:00:00+00:00",
                        "counterparty_id": "c1",
                        "amount_original": "100.00",
                        "currency_original": "USD",
                        "direction": "debit",
                        "reference_ids": ["r1"],
                    }
                ]
            },
        )
        dv_id = ingest.json()["dataset_version_id"]
        norm = await ac.post("/api/v3/engines/financial-forensics/normalize", json={"dataset_version_id": dv_id})
    assert norm.status_code == 200
    assert norm.json()["canonical_created"] == 1


@pytest.mark.anyio
async def test_replay_same_dataset_and_fx_identical_conversions(sqlite_db: None) -> None:
    os.environ["TODISCOPE_ARTIFACT_STORE_KIND"] = "memory"
    os.environ["TODISCOPE_ENABLED_ENGINES"] = "engine_financial_forensics"
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ingest = await ac.post(
            "/api/v3/ingest-records",
            json={
                "records": [
                    {
                        "source_system": "erp",
                        "source_record_id": "inv-1",
                        "record_type": "invoice",
                        "posted_at": "2026-01-01T00:00:00+00:00",
                        "counterparty_id": "c1",
                        "amount_original": "100.00",
                        "currency_original": "USD",
                        "direction": "debit",
                        "reference_ids": ["r1"],
                    }
                ]
            },
        )
        dv_id = ingest.json()["dataset_version_id"]
        _ = await ac.post("/api/v3/engines/financial-forensics/normalize", json={"dataset_version_id": dv_id})
        fx = await ac.post(
            "/api/v3/fx-artifacts",
            json={
                "dataset_version_id": dv_id,
                "base_currency": "EUR",
                "effective_date": "2026-01-31",
                "rates": {"USD": "0.91", "EUR": "1"},
                "created_at": "2026-01-01T00:00:00+00:00",
            },
        )
        fx_id = fx.json()["fx_artifact_id"]

        params = {"rounding_mode": "ROUND_HALF_UP", "rounding_quantum": "0.01"}
        r1 = await ac.post(
            "/api/v3/engines/financial-forensics/run",
            json={"dataset_version_id": dv_id, "fx_artifact_id": fx_id, "started_at": "2026-01-01T00:00:00+00:00", "parameters": params},
        )
        r2 = await ac.post(
            "/api/v3/engines/financial-forensics/run",
            json={"dataset_version_id": dv_id, "fx_artifact_id": fx_id, "started_at": "2026-01-01T00:00:00+00:00", "parameters": params},
        )
    assert r1.status_code == 200 and r2.status_code == 200
    d1 = {(c["record_id"], c["amount_converted"], c["fx_rate_used"]) for c in r1.json()["conversions"]}
    d2 = {(c["record_id"], c["amount_converted"], c["fx_rate_used"]) for c in r2.json()["conversions"]}
    assert d1 == d2
