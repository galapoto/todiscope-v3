import os

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.main import create_app


@pytest.mark.anyio
async def test_ingest_requires_key_when_configured(sqlite_db: None) -> None:
    os.environ["TODISCOPE_API_KEYS"] = "k1:ingest"
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/v3/ingest")
        assert res.status_code == 401

        res2 = await ac.post("/api/v3/ingest", headers={"X-API-Key": "k1"})
        assert res2.status_code == 200


@pytest.mark.anyio
async def test_ingest_forbidden_without_ingest_role(sqlite_db: None) -> None:
    os.environ["TODISCOPE_API_KEYS"] = "k2:read"
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/v3/ingest", headers={"X-API-Key": "k2"})
        assert res.status_code == 403

