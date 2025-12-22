"""Tests for the ERP Integration Readiness Engine."""
from __future__ import annotations

import os
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import ASGITransport, AsyncClient

from backend.app.main import create_app
from backend.app.engines.erp_integration_readiness.errors import (
    DatasetVersionMissingError,
    DatasetVersionInvalidError,
    DatasetVersionNotFoundError,
    StartedAtMissingError,
    StartedAtInvalidError,
    ErpSystemConfigMissingError,
    ErpSystemConfigInvalidError,
    ParametersMissingError,
    ParametersInvalidError,
)


@pytest.fixture
def valid_payload():
    """Return a valid payload for the engine endpoint."""
    return {
        "dataset_version_id": "01234567-89ab-7def-8123-456789abcdef",  # UUIDv7 format
        "started_at": "2024-01-01T00:00:00Z",
        "erp_system_config": {
            "system_id": "erp_system_001",
            "connection_type": "api",
            "api_endpoint": "https://erp.example.com/api",
            "version": "2.1.0",
            "api_version": "v2",
        },
        "parameters": {
            "assumptions": {},
            "infrastructure_config": {
                "supported_protocols": ["REST", "SOAP"],
                "supported_data_formats": ["JSON", "XML"],
            },
        },
        "optional_inputs": {},
    }


@pytest.mark.anyio
async def test_run_engine_validation(sqlite_db: None):
    """Test input validation in run_engine."""
    from backend.app.engines.erp_integration_readiness.run import run_engine
    
    # Mock engine enabled
    with patch("backend.app.engines.erp_integration_readiness.run.is_engine_enabled", return_value=True):
        # Test missing dataset_version_id
        with pytest.raises(DatasetVersionMissingError):
            await run_engine(
                dataset_version_id=None,
                started_at="2024-01-01T00:00:00Z",
                erp_system_config={"system_id": "test", "connection_type": "api"},
                parameters={"assumptions": {}},
            )
        
        # Test invalid dataset_version_id
        with pytest.raises(DatasetVersionInvalidError):
            await run_engine(
                dataset_version_id="",
                started_at="2024-01-01T00:00:00Z",
                erp_system_config={"system_id": "test", "connection_type": "api"},
                parameters={"assumptions": {}},
            )
        
        # Test missing erp_system_config
        with pytest.raises(ErpSystemConfigMissingError):
            await run_engine(
                dataset_version_id="01234567-89ab-7def-8123-456789abcdef",
                started_at="2024-01-01T00:00:00Z",
                erp_system_config=None,
                parameters={"assumptions": {}},
            )
        
        # Test missing parameters
        with pytest.raises(ParametersMissingError):
            await run_engine(
                dataset_version_id="01234567-89ab-7def-8123-456789abcdef",
                started_at="2024-01-01T00:00:00Z",
                erp_system_config={"system_id": "test", "connection_type": "api"},
                parameters=None,
            )
        
        # Test missing started_at
        with pytest.raises(StartedAtMissingError):
            await run_engine(
                dataset_version_id="01234567-89ab-7def-8123-456789abcdef",
                started_at=None,
                erp_system_config={"system_id": "test", "connection_type": "api"},
                parameters={"assumptions": {}},
            )


@pytest.mark.anyio
async def test_run_engine_database_interaction(sqlite_db: None):
    """Test database interaction in run_engine."""
    from backend.app.engines.erp_integration_readiness.run import run_engine
    from backend.app.core.dataset.models import DatasetVersion
    from backend.app.core.dataset.uuidv7 import uuid7
    
    # Create test data with valid UUIDv7
    test_dv_id = str(uuid7())
    test_dv = DatasetVersion(id=test_dv_id)
    
    # Mock the database session
    with patch("backend.app.engines.erp_integration_readiness.run.get_sessionmaker") as mock_get_sessionmaker, \
         patch("backend.app.engines.erp_integration_readiness.run.is_engine_enabled", return_value=True):
        
        # Setup mock session
        mock_session = AsyncMock()
        mock_session.scalar = AsyncMock(return_value=test_dv)
        mock_session.scalars = AsyncMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        mock_execute_result = MagicMock()
        mock_execute_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        mock_session.execute = AsyncMock(return_value=mock_execute_result)
        mock_session.commit = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        
        # Setup mock sessionmaker - it's a callable that returns an async context manager
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_session)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        
        mock_sessionmaker = MagicMock(return_value=mock_context_manager)
        mock_get_sessionmaker.return_value = mock_sessionmaker
        
        # Call the function
        result = await run_engine(
            dataset_version_id=test_dv_id,
            started_at="2024-01-01T00:00:00Z",
            erp_system_config={
                "system_id": "test_erp",
                "connection_type": "api",
                "api_endpoint": "https://example.com/api",
            },
            parameters={"assumptions": {}},
        )
        
        # Verify the result structure
        assert "engine_id" in result
        assert "engine_version" in result
        assert "run_id" in result
        assert "result_set_id" in result
        assert "dataset_version_id" in result
        assert "status" in result
        
        # Verify database queries were made
        assert mock_session.scalar.await_count > 0, "scalar should have been called"
        assert mock_session.commit.await_count > 0, "commit should have been called"

