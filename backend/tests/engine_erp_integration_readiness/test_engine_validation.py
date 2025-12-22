"""Tests for engine validation and registration."""
import pytest

from backend.app.core.engine_registry.registry import REGISTRY
from backend.app.core.engine_registry.spec import EngineSpec
from backend.app.engines.erp_integration_readiness.engine import (
    ENGINE_ID,
    ENGINE_VERSION,
)
from backend.app.engines import register_all_engines


def test_engine_registration():
    """Test that the engine registers correctly through proper registration path."""
    # Reset registry for clean test
    REGISTRY.reset_for_tests()
    
    # Register all engines (proper path)
    register_all_engines()
    
    # Verify engine is registered
    spec = REGISTRY.get(ENGINE_ID)
    assert spec is not None
    assert spec.engine_id == ENGINE_ID
    assert spec.engine_version == ENGINE_VERSION
    assert spec.enabled_by_default is False
    assert "engine_erp_integration_readiness_runs" in spec.owned_tables
    assert "engine_erp_integration_readiness_findings" in spec.owned_tables


def test_engine_idempotent_registration():
    """Test that engine registration is idempotent."""
    # Reset registry for clean test
    REGISTRY.reset_for_tests()
    
    # Register all engines twice
    register_all_engines()
    register_all_engines()  # Should not raise an error
    
    # Verify engine is still registered correctly
    spec = REGISTRY.get(ENGINE_ID)
    assert spec is not None
    assert spec.engine_id == ENGINE_ID


def test_engine_metadata():
    """Test that engine metadata is correct."""
    REGISTRY.reset_for_tests()
    register_all_engines()
    
    spec = REGISTRY.get(ENGINE_ID)
    assert spec is not None
    
    # Verify required metadata
    assert isinstance(spec.engine_id, str)
    assert isinstance(spec.engine_version, str)
    assert len(spec.engine_id) > 0
    assert len(spec.engine_version) > 0
    
    # Verify owned tables
    assert isinstance(spec.owned_tables, tuple)
    assert len(spec.owned_tables) > 0
    
    # Verify routers
    assert isinstance(spec.routers, tuple)
    assert len(spec.routers) > 0


def test_engine_spec_structure():
    """Test that engine spec has the correct structure."""
    REGISTRY.reset_for_tests()
    register_all_engines()
    
    spec = REGISTRY.get(ENGINE_ID)
    assert spec is not None
    
    # Verify all required fields are present
    assert hasattr(spec, "engine_id")
    assert hasattr(spec, "engine_version")
    assert hasattr(spec, "enabled_by_default")
    assert hasattr(spec, "owned_tables")
    assert hasattr(spec, "report_sections")
    assert hasattr(spec, "routers")
    assert hasattr(spec, "run_entrypoint")


def test_engine_router_configuration():
    """Test that the engine router is configured correctly."""
    REGISTRY.reset_for_tests()
    register_all_engines()
    
    spec = REGISTRY.get(ENGINE_ID)
    assert spec is not None
    assert len(spec.routers) == 1
    
    router = spec.routers[0]
    assert router.prefix == "/api/v3/engines/erp-integration-readiness"
    assert ENGINE_ID in router.tags


def test_engine_owned_tables():
    """Test that engine owns the correct tables."""
    REGISTRY.reset_for_tests()
    register_all_engines()
    
    spec = REGISTRY.get(ENGINE_ID)
    assert spec is not None
    
    expected_tables = {
        "engine_erp_integration_readiness_runs",
        "engine_erp_integration_readiness_findings",
    }
    
    assert set(spec.owned_tables) == expected_tables

