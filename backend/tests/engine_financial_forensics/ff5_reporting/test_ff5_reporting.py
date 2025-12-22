import os

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from backend.app.core.db import get_engine
from backend.app.main import create_app


@pytest.mark.anyio
async def test_report_assembly_deterministic(sqlite_db: None) -> None:
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
                        "source_record_id": "inv-r1",
                        "record_type": "invoice",
                        "posted_at": "2026-01-01T00:00:00+00:00",
                        "counterparty_id": "c1",
                        "amount_original": "100.00",
                        "currency_original": "USD",
                        "direction": "debit",
                        "reference_ids": ["doc-1"],
                    },
                    {
                        "source_system": "erp",
                        "source_record_id": "pay-r1",
                        "record_type": "payment",
                        "posted_at": "2026-01-02T00:00:00+00:00",
                        "counterparty_id": "c1",
                        "amount_original": "99.50",
                        "currency_original": "USD",
                        "direction": "credit",
                        "reference_ids": ["doc-1"],
                    },
                ]
            },
        )
        dv_id = ingest.json()["dataset_version_id"]
        _ = await ac.post("/api/v3/engines/financial-forensics/normalize", json={"dataset_version_id": dv_id})
        fx = await ac.post(
            "/api/v3/fx-artifacts",
            json={
                "dataset_version_id": dv_id,
                "base_currency": "USD",
                "effective_date": "2026-01-31",
                "created_at": "2026-01-01T00:00:00+00:00",
                "rates": {"USD": "1"},
            },
        )
        fx_id = fx.json()["fx_artifact_id"]
        run = await ac.post(
            "/api/v3/engines/financial-forensics/run",
            json={
                "dataset_version_id": dv_id,
                "fx_artifact_id": fx_id,
                "started_at": "2026-02-01T00:00:00+00:00",
                "parameters": {"rounding_mode": "ROUND_HALF_UP", "rounding_quantum": "0.01", "tolerance_amount": "1.00"},
            },
        )
        assert run.status_code == 200
        run_id = run.json()["run_id"]

        r1 = await ac.post("/api/v3/engines/financial-forensics/report", json={"dataset_version_id": dv_id, "run_id": run_id})
        r2 = await ac.post("/api/v3/engines/financial-forensics/report", json={"dataset_version_id": dv_id, "run_id": run_id})
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json() == r2.json()


@pytest.mark.anyio
async def test_report_missing_leakage_items_fails(sqlite_db: None) -> None:
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
                        "source_record_id": "inv-r2",
                        "record_type": "invoice",
                        "posted_at": "2026-01-01T00:00:00+00:00",
                        "counterparty_id": "c2",
                        "amount_original": "100.00",
                        "currency_original": "USD",
                        "direction": "debit",
                        "reference_ids": ["doc-2"],
                    },
                    {
                        "source_system": "erp",
                        "source_record_id": "pay-r2",
                        "record_type": "payment",
                        "posted_at": "2026-01-02T00:00:00+00:00",
                        "counterparty_id": "c2",
                        "amount_original": "100.00",
                        "currency_original": "USD",
                        "direction": "credit",
                        "reference_ids": ["doc-2"],
                    },
                ]
            },
        )
        dv_id = ingest.json()["dataset_version_id"]
        _ = await ac.post("/api/v3/engines/financial-forensics/normalize", json={"dataset_version_id": dv_id})
        fx = await ac.post(
            "/api/v3/fx-artifacts",
            json={
                "dataset_version_id": dv_id,
                "base_currency": "USD",
                "effective_date": "2026-01-31",
                "created_at": "2026-01-01T00:00:00+00:00",
                "rates": {"USD": "1"},
            },
        )
        fx_id = fx.json()["fx_artifact_id"]
        run = await ac.post(
            "/api/v3/engines/financial-forensics/run",
            json={
                "dataset_version_id": dv_id,
                "fx_artifact_id": fx_id,
                "started_at": "2026-02-01T00:00:00+00:00",
                "parameters": {"rounding_mode": "ROUND_HALF_UP", "rounding_quantum": "0.01"},
            },
        )
        assert run.status_code == 200, run.json()
        run_id = run.json()["run_id"]

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.execute(text("delete from engine_financial_forensics_leakage_items where run_id = :run_id"), {"run_id": run_id})

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac2:
        res = await ac2.post("/api/v3/engines/financial-forensics/report", json={"dataset_version_id": dv_id, "run_id": run_id})
    assert res.status_code == 404
    assert "MISSING_LEAKAGE_ITEMS_FOR_RUN" in res.json()["detail"]


@pytest.mark.anyio
async def test_run_limit_exceeded_fails_hard(sqlite_db: None) -> None:
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
                        "source_record_id": "inv-l1",
                        "record_type": "invoice",
                        "posted_at": "2026-01-01T00:00:00+00:00",
                        "counterparty_id": "c3",
                        "amount_original": "100.00",
                        "currency_original": "USD",
                        "direction": "debit",
                        "reference_ids": ["doc-3"],
                    },
                    {
                        "source_system": "erp",
                        "source_record_id": "pay-l1",
                        "record_type": "payment",
                        "posted_at": "2026-01-02T00:00:00+00:00",
                        "counterparty_id": "c3",
                        "amount_original": "100.00",
                        "currency_original": "USD",
                        "direction": "credit",
                        "reference_ids": ["doc-3"],
                    },
                ]
            },
        )
        dv_id = ingest.json()["dataset_version_id"]
        _ = await ac.post("/api/v3/engines/financial-forensics/normalize", json={"dataset_version_id": dv_id})
        fx = await ac.post(
            "/api/v3/fx-artifacts",
            json={
                "dataset_version_id": dv_id,
                "base_currency": "USD",
                "effective_date": "2026-01-31",
                "created_at": "2026-01-01T00:00:00+00:00",
                "rates": {"USD": "1"},
            },
        )
        fx_id = fx.json()["fx_artifact_id"]
        run = await ac.post(
            "/api/v3/engines/financial-forensics/run",
            json={
                "dataset_version_id": dv_id,
                "fx_artifact_id": fx_id,
                "started_at": "2026-02-01T00:00:00+00:00",
                "parameters": {"rounding_mode": "ROUND_HALF_UP", "rounding_quantum": "0.01", "max_canonical_records": 1},
            },
        )
    assert run.status_code == 413
    assert "RUNTIME_LIMIT_EXCEEDED" in run.json()["detail"]
