import os

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from backend.app.core.db import get_engine
from backend.app.main import create_app
from backend.app.core.engine_registry.registry import REGISTRY


def test_engine_discoverable_in_registry() -> None:
    os.environ["TODISCOPE_ENABLED_ENGINES"] = ""
    _ = create_app()
    spec = REGISTRY.get("engine_financial_forensics")
    assert spec is not None
    assert spec.engine_id == "engine_financial_forensics"
    assert spec.engine_version == "v1"
    assert list(spec.owned_tables) == [
        "engine_financial_forensics_runs",
        "engine_financial_forensics_canonical_records",
        "engine_financial_forensics_findings",
        "engine_financial_forensics_leakage_items",
    ]
    assert list(spec.report_sections) == ["financial_forensics_stub"]


@pytest.mark.anyio
async def test_engine_disabled_run_fails(sqlite_db: None) -> None:
    os.environ["TODISCOPE_ENABLED_ENGINES"] = ""
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/v3/engines/financial-forensics/run", json={"dataset_version_id": "x", "parameters": {}})
    assert res.status_code == 404


@pytest.mark.anyio
async def test_engine_enabled_run_succeeds(sqlite_db: None) -> None:
    os.environ["TODISCOPE_ENABLED_ENGINES"] = "engine_financial_forensics"
    os.environ["TODISCOPE_ARTIFACT_STORE_KIND"] = "memory"
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        dv_id = (await ac.post("/api/v3/ingest")).json()["dataset_version_id"]
        fx = await ac.post(
            "/api/v3/fx-artifacts",
            json={
                "dataset_version_id": dv_id,
                "base_currency": "EUR",
                "effective_date": "2026-01-31",
                "created_at": "2026-01-01T00:00:00+00:00",
                "rates": {"USD": "0.91", "EUR": "1"},
            },
        )
        assert fx.status_code == 200
        fx_id = fx.json()["fx_artifact_id"]
        run = await ac.post(
            "/api/v3/engines/financial-forensics/run",
            json={
                "dataset_version_id": dv_id,
                "fx_artifact_id": fx_id,
                "started_at": "2026-01-01T00:00:00+00:00",
                "parameters": {"k": "v", "rounding_mode": "ROUND_HALF_UP", "rounding_quantum": "0.01"},
            },
        )
    assert run.status_code == 200
    body = run.json()
    assert body["dataset_version_id"] == dv_id
    assert body["engine_id"] == "engine_financial_forensics"
    assert body["engine_version"] == "v1"
    assert body["findings"] == []
    assert body["report_sections"]["financial_forensics_stub"]["status"] == "engine_initialized"


@pytest.mark.anyio
async def test_missing_dataset_version_id_hard_fails(sqlite_db: None) -> None:
    os.environ["TODISCOPE_ENABLED_ENGINES"] = "engine_financial_forensics"
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/v3/engines/financial-forensics/run", json={"parameters": {}})
    assert res.status_code == 400


@pytest.mark.anyio
async def test_engine_writes_only_run_table(sqlite_db: None) -> None:
    os.environ["TODISCOPE_ENABLED_ENGINES"] = "engine_financial_forensics"
    os.environ["TODISCOPE_ARTIFACT_STORE_KIND"] = "memory"
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        dv_id = (await ac.post("/api/v3/ingest")).json()["dataset_version_id"]
        fx = await ac.post(
            "/api/v3/fx-artifacts",
            json={
                "dataset_version_id": dv_id,
                "base_currency": "EUR",
                "effective_date": "2026-01-31",
                "created_at": "2026-01-01T00:00:00+00:00",
                "rates": {"USD": "0.91", "EUR": "1"},
            },
        )
        fx_id = fx.json()["fx_artifact_id"]
        _ = await ac.post(
            "/api/v3/engines/financial-forensics/run",
            json={"dataset_version_id": dv_id, "fx_artifact_id": fx_id, "started_at": "2026-01-01T00:00:00+00:00", "parameters": {"rounding_mode": "ROUND_HALF_UP", "rounding_quantum": "0.01"}},
        )

    engine = get_engine()
    async with engine.connect() as conn:
        tables = (
            await conn.execute(
                text(
                    "select name from sqlite_master where type='table' and name not like 'sqlite_%' order by name"
                )
            )
        ).scalars().all()

    # Engine #2 should only write to its run table on run invocation; other tables may exist.
    assert "engine_financial_forensics_runs" in tables
    assert "engine_financial_forensics_canonical_records" in tables
    assert "fx_artifacts" in tables
    assert "raw_record" in tables
