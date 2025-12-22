"""Tests for the Data Migration Readiness Engine."""
from __future__ import annotations

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from backend.app.engines.data_migration_readiness.engine import router
from backend.app.engines.data_migration_readiness.errors import (
    DatasetVersionMissingError,
    DatasetVersionInvalidError,
    DatasetVersionNotFoundError,
    StartedAtMissingError,
    StartedAtInvalidError,
    RawRecordsMissingError,
    ConfigurationLoadError,
)
from backend.app.engines.data_migration_readiness.models import (
    DataMigrationReadinessFinding,
    DataMigrationReadinessRun,
)


class _SimpleScalars:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _SimpleSession:
    def __init__(self, dataset, records):
        self._dataset = dataset
        self._records = records
        self.add = MagicMock()
        self.flush = AsyncMock()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def scalar(self, query):
        return self._dataset

    async def scalars(self, query):
        return _SimpleScalars(self._records)

    async def commit(self):
        return None


@pytest.fixture
def mock_run_readiness_check():
    """Mock the run_readiness_check function."""
    with patch("backend.app.engines.data_migration_readiness.engine.run_readiness_check") as mock:
        yield mock


@pytest.fixture(autouse=True)
def enable_engine(monkeypatch):
    """Enable the data migration readiness engine for all endpoint tests."""
    monkeypatch.setenv("TODISCOPE_ENABLED_ENGINES", "engine_data_migration_readiness")


@pytest.fixture
def valid_payload():
    """Return a valid payload for the engine endpoint."""
    return {
        "dataset_version_id": "test-dv-1",
        "started_at": "2023-01-01T00:00:00Z",
        "parameters": {
            "config_overrides": {
                "quality_thresholds": {"completeness": 0.95}
            }
        }
    }


@pytest.mark.asyncio
async def test_engine_endpoint_success(mock_run_readiness_check, valid_payload):
    """Test the engine endpoint with valid input."""
    # Setup mock
    expected_result = {
        "dataset_version_id": "test-dv-1",
        "started_at": "2023-01-01T00:00:00Z",
        "structure": {"compliant": True},
        "quality": {"passes": True},
        "mapping": {"compliant": True},
        "integrity": {"compliant": True},
        "risks": [],
    }
    mock_run_readiness_check.return_value = expected_result
    
    # Call the endpoint
    response = await router.routes[0].endpoint(valid_payload)
    
    # Verify the response
    assert response == expected_result
    mock_run_readiness_check.assert_awaited_once_with(
        dataset_version_id=valid_payload["dataset_version_id"],
        started_at=valid_payload["started_at"],
        parameters=valid_payload["parameters"],
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("error_cls, status_code, error_detail", [
    (DatasetVersionMissingError, 400, "DATASET_VERSION_ID_REQUIRED"),
    (DatasetVersionInvalidError, 400, "DATASET_VERSION_ID_INVALID"),
    (DatasetVersionNotFoundError, 404, "DATASET_VERSION_NOT_FOUND"),
    (StartedAtMissingError, 400, "STARTED_AT_REQUIRED"),
    (StartedAtInvalidError, 400, "STARTED_AT_INVALID"),
    (RawRecordsMissingError, 400, "RAW_RECORDS_REQUIRED"),
    (ConfigurationLoadError, 500, "CONFIG_LOADING_FAILED"),
])
async def test_engine_endpoint_error_handling(
    mock_run_readiness_check, 
    valid_payload, 
    error_cls, 
    status_code, 
    error_detail
):
    """Test error handling in the engine endpoint."""
    # Setup mock to raise an exception
    mock_run_readiness_check.side_effect = error_cls(error_detail)
    
    # Call the endpoint and expect an exception
    with pytest.raises(HTTPException) as exc_info:
        await router.routes[0].endpoint(valid_payload)
    
    # Verify the exception details
    assert exc_info.value.status_code == status_code
    assert error_detail in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_engine_endpoint_unexpected_error(mock_run_readiness_check, valid_payload):
    """Test handling of unexpected errors in the engine endpoint."""
    # Setup mock to raise an unexpected exception
    mock_run_readiness_check.side_effect = ValueError("Unexpected error")
    
    # Call the endpoint and expect an exception
    with pytest.raises(HTTPException) as exc_info:
        await router.routes[0].endpoint(valid_payload)
    
    # Verify the exception details
    assert exc_info.value.status_code == 500
    assert "ENGINE_RUN_FAILED" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_run_readiness_check_immutability():
    """Test that the run_readiness_check function enforces immutability."""
    from backend.app.engines.data_migration_readiness.run import run_readiness_check
    from backend.app.core.dataset.immutability import ImmutabilityError
    
    # Mock the database and other dependencies
    with patch("backend.app.engines.data_migration_readiness.run.get_sessionmaker") as mock_get_sessionmaker, \
         patch("backend.app.engines.data_migration_readiness.run.load_default_config") as mock_load_config, \
         patch("backend.app.core.dataset.immutability.install_immutability_guards") as mock_install_guards:
        with patch("backend.app.engines.data_migration_readiness.run._strict_create_evidence", new_callable=AsyncMock), \
             patch("backend.app.engines.data_migration_readiness.run._strict_create_finding", new_callable=AsyncMock), \
             patch("backend.app.engines.data_migration_readiness.run._strict_link", new_callable=AsyncMock):
            # Setup mock session
            session = _SimpleSession(MagicMock(), [MagicMock()])
            mock_get_sessionmaker.return_value = lambda: session

            # Setup mock config
            mock_load_config.return_value = {
                "structural_requirements": {"collections": {}, "metadata_keys": []},
                "quality_thresholds": {},
                "mapping_expectations": {},
            }

            # Test that immutability guards are installed
            await run_readiness_check(
                dataset_version_id="test-dv-1",
                started_at="2023-01-01T00:00:00Z",
                parameters={},
            )

            # Verify immutability guards were installed
            mock_install_guards.assert_called_once()


@pytest.mark.asyncio
async def test_run_readiness_check_validation():
    """Test input validation in run_readiness_check."""
    from backend.app.engines.data_migration_readiness.run import run_readiness_check
    
    # Test missing dataset_version_id
    with pytest.raises(DatasetVersionMissingError):
        await run_readiness_check(dataset_version_id=None, started_at="2023-01-01T00:00:00Z")
    
    # Test invalid dataset_version_id
    with pytest.raises(DatasetVersionInvalidError):
        await run_readiness_check(dataset_version_id="", started_at="2023-01-01T00:00:00Z")
    
    # Test missing started_at
    with pytest.raises(StartedAtMissingError):
        await run_readiness_check(dataset_version_id="test-dv-1", started_at=None)
    
    # Test invalid started_at format
    with pytest.raises(StartedAtInvalidError):
        await run_readiness_check(dataset_version_id="test-dv-1", started_at="invalid-date")


@pytest.mark.asyncio
async def test_run_readiness_check_database_interaction():
    """Test database interaction in run_readiness_check."""
    from backend.app.engines.data_migration_readiness.run import run_readiness_check
    from backend.app.core.dataset.models import DatasetVersion
    from backend.app.core.dataset.raw_models import RawRecord
    
    # Create test data
    test_dv = DatasetVersion(id="test-dv-1")
    test_records = [
        RawRecord(
            raw_record_id="1",
            dataset_version_id="test-dv-1",
            source_system="test",
            source_record_id="rec1",
            payload={"id": "1", "amount": "100.00"},
        )
    ]
    
    # Mock the database session
    with patch("backend.app.engines.data_migration_readiness.run.get_sessionmaker") as mock_get_sessionmaker, \
         patch("backend.app.engines.data_migration_readiness.run.load_default_config") as mock_load_config:
        with patch("backend.app.engines.data_migration_readiness.run._strict_create_evidence", new_callable=AsyncMock), \
             patch("backend.app.engines.data_migration_readiness.run._strict_create_finding", new_callable=AsyncMock), \
             patch("backend.app.engines.data_migration_readiness.run._strict_link", new_callable=AsyncMock):
            # Setup mock session
            session = _SimpleSession(test_dv, test_records)
            mock_get_sessionmaker.return_value = lambda: session

            # Setup mock config
            mock_load_config.return_value = {
                "structural_requirements": {"collections": {}, "metadata_keys": []},
                "quality_thresholds": {},
                "mapping_expectations": {},
            }

            # Call the function
            result = await run_readiness_check(
                dataset_version_id="test-dv-1",
                started_at="2023-01-01T00:00:00Z",
                parameters={"config_overrides": {}},
            )

            # Verify the result structure
            assert "dataset_version_id" in result
            assert "started_at" in result
            assert "structure" in result
            assert "quality" in result
            assert "mapping" in result
            assert "integrity" in result
            assert "risks" in result

            # Verify the session factory and persistence were invoked
            mock_get_sessionmaker.assert_called_once()
            added_types = {type(call.args[0]) for call in session.add.call_args_list}
            assert DataMigrationReadinessRun in added_types
            assert DataMigrationReadinessFinding in added_types
