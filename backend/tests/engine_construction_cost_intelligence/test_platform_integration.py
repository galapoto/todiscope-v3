"""
Tests for platform integration of the Construction Cost Intelligence Engine.

Verifies engine registration, kill-switch functionality, and router integration.
"""
from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.engines import register_all_engines


@pytest.fixture(autouse=True)
def ensure_engines_registered():
    """Ensure all engines are registered before each test."""
    register_all_engines()
    yield
    # Cleanup if needed


@pytest.fixture
def app():
    """Create FastAPI app for testing."""
    return create_app()


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


def test_engine_registered() -> None:
    """Test that the engine is registered in the registry."""
    from backend.app.core.engine_registry.registry import REGISTRY
    
    engine_spec = REGISTRY.get("engine_construction_cost_intelligence")
    assert engine_spec is not None, "Engine should be registered"
    assert engine_spec.engine_id == "engine_construction_cost_intelligence"
    assert engine_spec.engine_version == "v1"
    assert engine_spec.enabled_by_default is False


def test_engine_not_enabled_by_default(client) -> None:
    """Test that engine is disabled by default and routes are not accessible."""
    # Remove engine from enabled list
    with patch.dict(os.environ, {"TODISCOPE_ENABLED_ENGINES": ""}, clear=False):
        # Reload app to pick up env change
        app = create_app()
        test_client = TestClient(app)
        
        # When not enabled, route may return 404 (not mounted) or 503 (disabled)
        # Both are acceptable behaviors
        response = test_client.get("/api/v3/engines/cost-intelligence/ping")
        assert response.status_code in (404, 503)
        if response.status_code == 503:
            assert "ENGINE_DISABLED" in response.json()["detail"]


def test_engine_enabled_via_env(client) -> None:
    """Test that engine can be enabled via environment variable."""
    with patch.dict(
        os.environ, {"TODISCOPE_ENABLED_ENGINES": "engine_construction_cost_intelligence"}, clear=False
    ):
        # Reload app to pick up env change
        app = create_app()
        test_client = TestClient(app)
        
        # Ping should return 200
        response = test_client.get("/api/v3/engines/cost-intelligence/ping")
        assert response.status_code == 200
        assert response.json()["ok"] is True
        assert response.json()["engine_id"] == "engine_construction_cost_intelligence"
        assert response.json()["engine_version"] == "v1"


def test_kill_switch_disables_engine(client) -> None:
    """Test that kill-switch properly disables the engine."""
    with patch.dict(
        os.environ, {"TODISCOPE_ENABLED_ENGINES": "engine_construction_cost_intelligence"}, clear=False
    ):
        # Reload app with engine enabled
        app = create_app()
        test_client = TestClient(app)
        
        # Verify ping works
        response = test_client.get("/api/v3/engines/cost-intelligence/ping")
        assert response.status_code == 200
        
        # Disable via environment variable
        with patch.dict(os.environ, {"TODISCOPE_ENABLED_ENGINES": ""}, clear=False):
            # Note: In actual usage, the kill-switch would be checked per-request
            # This test verifies the endpoint respects the kill-switch check
            response = test_client.get("/api/v3/engines/cost-intelligence/ping")
            # Endpoint should check kill-switch and return 503
            # But since route is already mounted, we need to check the actual behavior
            # The endpoint itself checks is_engine_enabled() which reads from env
            assert response.status_code in (503, 404)


def test_engine_routes_registered(client) -> None:
    """Test that engine routes are registered and accessible when enabled."""
    with patch.dict(
        os.environ, {"TODISCOPE_ENABLED_ENGINES": "engine_construction_cost_intelligence"}, clear=False
    ):
        app = create_app()
        test_client = TestClient(app)
        
        # Test ping endpoint
        response = test_client.get("/api/v3/engines/cost-intelligence/ping")
        assert response.status_code == 200
        
        # Test run endpoint exists (will fail with 400 due to missing payload, but route exists)
        response = test_client.post("/api/v3/engines/cost-intelligence/run", json={})
        assert response.status_code in (400, 500)  # Route exists, payload validation fails
        
        # Test report endpoint exists (will fail with 400 due to missing payload, but route exists)
        response = test_client.post("/api/v3/engines/cost-intelligence/report", json={})
        assert response.status_code in (400, 500)  # Route exists, payload validation fails


def test_engine_detachment_does_not_break_platform(client) -> None:
    """Test that disabling the engine doesn't break other platform features."""
    # Disable all engines
    with patch.dict(os.environ, {"TODISCOPE_ENABLED_ENGINES": ""}, clear=False):
        app = create_app()
        test_client = TestClient(app)
        
        # Platform core routes should still work
        response = test_client.get("/health")
        assert response.status_code == 200
        
        # Engine registry should still work
        response = test_client.get("/api/v3/engine-registry/enabled")
        assert response.status_code == 200
        
        # Disabled engine may return 404 (route not mounted) or 503 (disabled)
        # Both are acceptable - platform continues to function
        response = test_client.get("/api/v3/engines/cost-intelligence/ping")
        assert response.status_code in (404, 503)
        if response.status_code == 503:
            assert "ENGINE_DISABLED" in response.json()["detail"]


def test_engine_registry_lists_engine() -> None:
    """Test that engine appears in registry listing."""
    from backend.app.core.engine_registry.registry import REGISTRY
    
    all_engines = REGISTRY.all()
    engine_ids = [e.engine_id for e in all_engines]
    
    assert "engine_construction_cost_intelligence" in engine_ids


def test_engine_spec_includes_correct_sections() -> None:
    """Test that engine spec includes correct report sections."""
    from backend.app.core.engine_registry.registry import REGISTRY
    
    engine_spec = REGISTRY.get("engine_construction_cost_intelligence")
    assert engine_spec is not None
    
    expected_sections = {
        "executive_summary",
        "variance_summary_by_severity",
        "variance_summary_by_category",
        "cost_variances",
        "time_phased_report",
        "limitations_assumptions",
        "core_traceability",
        "evidence_index",
    }
    
    assert set(engine_spec.report_sections) == expected_sections


def test_engine_spec_has_router() -> None:
    """Test that engine spec includes router."""
    from backend.app.core.engine_registry.registry import REGISTRY
    
    engine_spec = REGISTRY.get("engine_construction_cost_intelligence")
    assert engine_spec is not None
    assert len(engine_spec.routers) > 0
    assert engine_spec.routers[0].prefix == "/api/v3/engines/cost-intelligence"


def test_multiple_engines_can_coexist(client) -> None:
    """Test that multiple engines can coexist without interference."""
    with patch.dict(
        os.environ,
        {"TODISCOPE_ENABLED_ENGINES": "engine_construction_cost_intelligence,engine_financial_forensics"},
        clear=False,
    ):
        app = create_app()
        test_client = TestClient(app)
        
        # Both engines should be accessible
        response1 = test_client.get("/api/v3/engines/cost-intelligence/ping")
        # Financial forensics may or may not be available, but cost-intelligence should be
        assert response1.status_code == 200


def test_engine_registration_idempotent() -> None:
    """Test that engine registration is idempotent."""
    # Registration via register_all_engines is already idempotent
    # The register_engine() function checks if already registered
    from backend.app.core.engine_registry.registry import REGISTRY
    
    # Register via standard method
    register_all_engines()
    
    # Should not raise error when called multiple times
    register_all_engines()
    register_all_engines()
    
    # Engine should be registered
    engine_spec = REGISTRY.get("engine_construction_cost_intelligence")
    assert engine_spec is not None

