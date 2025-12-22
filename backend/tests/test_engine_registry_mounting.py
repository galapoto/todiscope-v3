import os

import pytest
from fastapi import APIRouter
from httpx import ASGITransport, AsyncClient

from backend.app.core.engine_registry.registry import REGISTRY
from backend.app.core.engine_registry.spec import EngineSpec
from backend.app.main import create_app


def _dummy_engine_router() -> APIRouter:
    r = APIRouter(prefix="/api/v3/dummy-engine", tags=["dummy"])

    @r.get("/ping")
    async def ping() -> dict:
        return {"ok": True}

    return r


@pytest.mark.anyio
async def test_engine_router_not_mounted_when_disabled() -> None:
    REGISTRY.register(
        EngineSpec(
            engine_id="engine.dummy",
            engine_version="0.0.0",
            enabled_by_default=False,
            owned_tables=(),
            report_sections=(),
            routers=( _dummy_engine_router(), ),
        )
    )
    os.environ["TODISCOPE_ENABLED_ENGINES"] = ""
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v3/dummy-engine/ping")
    assert res.status_code == 404


@pytest.mark.anyio
async def test_engine_router_mounted_when_enabled() -> None:
    REGISTRY.register(
        EngineSpec(
            engine_id="engine.dummy",
            engine_version="0.0.0",
            enabled_by_default=False,
            owned_tables=(),
            report_sections=(),
            routers=( _dummy_engine_router(), ),
        )
    )
    os.environ["TODISCOPE_ENABLED_ENGINES"] = "engine.dummy"
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v3/dummy-engine/ping")
    assert res.status_code == 200
    assert res.json() == {"ok": True}
