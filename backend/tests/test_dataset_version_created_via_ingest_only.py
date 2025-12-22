import os
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.main import create_app


@pytest.mark.anyio
async def test_ingest_creates_dataset_version_id(sqlite_db: None) -> None:
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/v3/ingest")
    assert res.status_code == 200
    body = res.json()
    assert "dataset_version_id" in body
    assert isinstance(body["dataset_version_id"], str)
    assert uuid.UUID(body["dataset_version_id"]).version == 7
