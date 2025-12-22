import os

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.main import create_app


@pytest.mark.anyio
async def test_fx_artifact_create_and_load_checksum_verified(sqlite_db: None) -> None:
    os.environ["TODISCOPE_ARTIFACT_STORE_KIND"] = "memory"
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        dv_id = (await ac.post("/api/v3/ingest")).json()["dataset_version_id"]
        created = await ac.post(
            "/api/v3/fx-artifacts",
            json={
                "dataset_version_id": dv_id,
                "base_currency": "EUR",
                "effective_date": "2026-01-31",
                "rates": {"USD": "0.91", "EUR": "1"},
                "created_at": "2026-01-01T00:00:00+00:00",
            },
        )
        assert created.status_code == 200
        fx_id = created.json()["fx_artifact_id"]
        checksum = created.json()["checksum"]

        loaded = await ac.get(f"/api/v3/fx-artifacts/{fx_id}")
        assert loaded.status_code == 200
        assert loaded.json()["checksum"] == checksum
        assert loaded.json()["payload"]["base_currency"] == "EUR"


@pytest.mark.anyio
async def test_fx_artifact_idempotent_same_payload(sqlite_db: None) -> None:
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
        a = await ac.post("/api/v3/fx-artifacts", json=payload)
        b = await ac.post("/api/v3/fx-artifacts", json=payload)
        assert a.status_code == 200 and b.status_code == 200
        assert a.json()["fx_artifact_id"] == b.json()["fx_artifact_id"]
