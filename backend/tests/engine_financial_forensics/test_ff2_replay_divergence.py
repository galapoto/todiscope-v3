import os

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.main import create_app


@pytest.mark.anyio
async def test_different_fx_artifact_produces_different_converted_amounts(sqlite_db: None) -> None:
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

        fx1 = await ac.post(
            "/api/v3/fx-artifacts",
            json={
                "dataset_version_id": dv_id,
                "base_currency": "EUR",
                "effective_date": "2026-01-31",
                "rates": {"USD": "0.91", "EUR": "1"},
                "created_at": "2026-01-01T00:00:00+00:00",
            },
        )
        fx2 = await ac.post(
            "/api/v3/fx-artifacts",
            json={
                "dataset_version_id": dv_id,
                "base_currency": "EUR",
                "effective_date": "2026-01-31",
                "rates": {"USD": "0.92", "EUR": "1"},
                "created_at": "2026-01-01T00:00:00+00:00",
            },
        )
        assert fx1.status_code == 200 and fx2.status_code == 200
        fx1_id = fx1.json()["fx_artifact_id"]
        fx2_id = fx2.json()["fx_artifact_id"]
        assert fx1_id != fx2_id

        params = {"rounding_mode": "ROUND_HALF_UP", "rounding_quantum": "0.01"}
        r1 = await ac.post(
            "/api/v3/engines/financial-forensics/run",
            json={"dataset_version_id": dv_id, "fx_artifact_id": fx1_id, "started_at": "2026-01-01T00:00:00+00:00", "parameters": params},
        )
        r2 = await ac.post(
            "/api/v3/engines/financial-forensics/run",
            json={"dataset_version_id": dv_id, "fx_artifact_id": fx2_id, "started_at": "2026-01-01T00:00:00+00:00", "parameters": params},
        )
    assert r1.status_code == 200 and r2.status_code == 200

    c1 = r1.json()["conversions"][0]
    c2 = r2.json()["conversions"][0]
    assert c1["record_id"] == c2["record_id"]
    assert c1["fx_rate_used"] != c2["fx_rate_used"]
    assert c1["amount_converted"] != c2["amount_converted"]
