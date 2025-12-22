import os

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.main import create_app


@pytest.mark.anyio
async def test_artifact_store_put_get_roundtrip() -> None:
    os.environ["TODISCOPE_ARTIFACT_STORE_KIND"] = "memory"
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        put = await ac.post("/api/v3/artifacts/put-test")
        assert put.status_code == 200
        get = await ac.get("/api/v3/artifacts/get-test")
        assert get.status_code == 200
        assert get.json()["data"] == "hello"
