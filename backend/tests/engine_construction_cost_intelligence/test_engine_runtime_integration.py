from __future__ import annotations

import os

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.main import create_app


@pytest.mark.anyio
async def test_cost_intelligence_router_not_mounted_when_disabled() -> None:
    os.environ["TODISCOPE_ENABLED_ENGINES"] = ""
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v3/engines/cost-intelligence/ping")
    assert res.status_code == 404


@pytest.mark.anyio
async def test_cost_intelligence_router_mounted_when_enabled_and_killswitch_blocks() -> None:
    os.environ["TODISCOPE_ENABLED_ENGINES"] = "engine_construction_cost_intelligence"
    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ok = await ac.get("/api/v3/engines/cost-intelligence/ping")
        assert ok.status_code == 200
        status = await ac.get("/api/v3/engines/cost-intelligence/status")
        assert status.status_code == 200
        assert status.json().get("status") == "enabled"

        # Flip kill-switch after mount: routes remain, but endpoints must block safely.
        os.environ["TODISCOPE_ENABLED_ENGINES"] = ""
        blocked = await ac.get("/api/v3/engines/cost-intelligence/ping")
        assert blocked.status_code == 503
        assert "ENGINE_DISABLED" in blocked.text

        blocked_status = await ac.get("/api/v3/engines/cost-intelligence/status")
        assert blocked_status.status_code == 503
