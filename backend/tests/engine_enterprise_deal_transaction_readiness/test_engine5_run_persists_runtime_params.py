import os
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from backend.app.core.db import get_sessionmaker
from backend.app.main import create_app
from backend.app.engines.enterprise_deal_transaction_readiness.engine import ENGINE_ID
from backend.app.engines.enterprise_deal_transaction_readiness.models.runs import (
    EnterpriseDealTransactionReadinessRun,
)


@pytest.mark.anyio
async def test_engine5_run_persists_transaction_scope_and_parameters(sqlite_db: None) -> None:
    os.environ["TODISCOPE_ENABLED_ENGINES"] = ENGINE_ID
    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ingest = await ac.post("/api/v3/ingest")
        assert ingest.status_code == 200
        dv_id = ingest.json()["dataset_version_id"]

        payload = {
            "dataset_version_id": dv_id,
            "started_at": "2025-01-01T00:00:00+00:00",
            "transaction_scope": {"scope_kind": "full_dataset"},
            "parameters": {"fx": {"rates": {}}, "assumptions": {"note": "explicit"}},
        }
        res = await ac.post("/api/v3/engines/enterprise-deal-transaction-readiness/run", json=payload)

    assert res.status_code == 200
    body = res.json()
    assert body["engine_id"] == ENGINE_ID
    assert body["dataset_version_id"] == dv_id
    assert isinstance(body["run_id"], str)
    assert uuid.UUID(body["run_id"]).version == 7

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        row = await db.scalar(
            select(EnterpriseDealTransactionReadinessRun).where(
                EnterpriseDealTransactionReadinessRun.run_id == body["run_id"]
            )
        )
        assert row is not None
        assert row.dataset_version_id == dv_id
        assert row.transaction_scope == payload["transaction_scope"]
        assert row.parameters == payload["parameters"]


@pytest.mark.anyio
async def test_engine5_rejects_non_uuidv7_dataset_version_id(sqlite_db: None) -> None:
    os.environ["TODISCOPE_ENABLED_ENGINES"] = ENGINE_ID
    app = create_app()

    fake_uuidv4 = str(uuid.uuid4())
    payload = {
        "dataset_version_id": fake_uuidv4,
        "started_at": "2025-01-01T00:00:00+00:00",
        "transaction_scope": {"scope_kind": "full_dataset"},
        "parameters": {"fx": {}, "assumptions": {}},
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/v3/engines/enterprise-deal-transaction-readiness/run", json=payload)

    assert res.status_code == 400
    assert "UUIDV7_REQUIRED" in res.text

