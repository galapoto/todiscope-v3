import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.main import create_app


@pytest.mark.anyio
async def test_engine_router_mounted_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TODISCOPE_ENABLED_ENGINES", "engine_enterprise_capital_debt_readiness")
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/v3/engines/enterprise-capital-debt-readiness/run", json={})
    assert res.status_code == 400


@pytest.mark.anyio
async def test_engine_router_not_mounted_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TODISCOPE_ENABLED_ENGINES", "")
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/v3/engines/enterprise-capital-debt-readiness/run", json={})
    assert res.status_code == 404
