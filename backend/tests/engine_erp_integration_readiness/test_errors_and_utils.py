"""Tests for error classes and utility functions."""
from __future__ import annotations

import pytest

from backend.app.engines.erp_integration_readiness.errors import (
    ErpIntegrationReadinessError,
    DatasetVersionMissingError,
    DatasetVersionInvalidError,
    DatasetVersionNotFoundError,
    ErpSystemConfigMissingError,
    ErpSystemConfigInvalidError,
    ParametersMissingError,
    ParametersInvalidError,
    StartedAtMissingError,
    StartedAtInvalidError,
    EngineDisabledError,
)


def test_error_hierarchy():
    """Test that all custom exceptions inherit from the base error class."""
    error_classes = [
        DatasetVersionMissingError,
        DatasetVersionInvalidError,
        DatasetVersionNotFoundError,
        ErpSystemConfigMissingError,
        ErpSystemConfigInvalidError,
        ParametersMissingError,
        ParametersInvalidError,
        StartedAtMissingError,
        StartedAtInvalidError,
        EngineDisabledError,
    ]
    
    for error_cls in error_classes:
        # Create an instance of the error class
        error = error_cls("test message")
        # Verify it's an instance of the base class
        assert isinstance(error, ErpIntegrationReadinessError)
        # Verify the message is set correctly
        assert str(error) == "test message"


def test_error_messages():
    """Test error messages for different error types."""
    # Test DatasetVersionMissingError
    with pytest.raises(DatasetVersionMissingError) as exc_info:
        raise DatasetVersionMissingError("DATASET_VERSION_ID_REQUIRED")
    assert "DATASET_VERSION_ID_REQUIRED" in str(exc_info.value)
    
    # Test DatasetVersionInvalidError
    with pytest.raises(DatasetVersionInvalidError) as exc_info:
        raise DatasetVersionInvalidError("DATASET_VERSION_ID_INVALID")
    assert "DATASET_VERSION_ID_INVALID" in str(exc_info.value)
    
    # Test DatasetVersionNotFoundError
    with pytest.raises(DatasetVersionNotFoundError) as exc_info:
        raise DatasetVersionNotFoundError("DATASET_VERSION_NOT_FOUND")
    assert "DATASET_VERSION_NOT_FOUND" in str(exc_info.value)
    
    # Test ErpSystemConfigMissingError
    with pytest.raises(ErpSystemConfigMissingError) as exc_info:
        raise ErpSystemConfigMissingError("ERP_SYSTEM_CONFIG_REQUIRED")
    assert "ERP_SYSTEM_CONFIG_REQUIRED" in str(exc_info.value)
    
    # Test ErpSystemConfigInvalidError
    with pytest.raises(ErpSystemConfigInvalidError) as exc_info:
        raise ErpSystemConfigInvalidError("ERP_SYSTEM_CONFIG_INVALID")
    assert "ERP_SYSTEM_CONFIG_INVALID" in str(exc_info.value)
    
    # Test ParametersMissingError
    with pytest.raises(ParametersMissingError) as exc_info:
        raise ParametersMissingError("PARAMETERS_REQUIRED")
    assert "PARAMETERS_REQUIRED" in str(exc_info.value)
    
    # Test ParametersInvalidError
    with pytest.raises(ParametersInvalidError) as exc_info:
        raise ParametersInvalidError("PARAMETERS_INVALID")
    assert "PARAMETERS_INVALID" in str(exc_info.value)
    
    # Test StartedAtMissingError
    with pytest.raises(StartedAtMissingError) as exc_info:
        raise StartedAtMissingError("STARTED_AT_REQUIRED")
    assert "STARTED_AT_REQUIRED" in str(exc_info.value)
    
    # Test StartedAtInvalidError
    with pytest.raises(StartedAtInvalidError) as exc_info:
        raise StartedAtInvalidError("STARTED_AT_INVALID")
    assert "STARTED_AT_INVALID" in str(exc_info.value)
    
    # Test EngineDisabledError
    with pytest.raises(EngineDisabledError) as exc_info:
        raise EngineDisabledError("ENGINE_DISABLED")
    assert "ENGINE_DISABLED" in str(exc_info.value)


def test_error_chaining():
    """Test that errors can be chained with their causes."""
    try:
        # Simulate an underlying error
        try:
            raise ValueError("Underlying error")
        except ValueError as e:
            # Wrap it in a custom error
            raise ErpSystemConfigInvalidError("Failed to validate config") from e
    except ErpSystemConfigInvalidError as e:
        assert "Failed to validate config" in str(e)
        assert "Underlying error" in str(e.__cause__)


def test_error_inheritance():
    """Test that custom errors can be caught by their base class."""
    def raise_custom_error():
        raise DatasetVersionMissingError("MISSING")
    
    # Should be caught by the specific exception class
    with pytest.raises(DatasetVersionMissingError):
        raise_custom_error()
    
    # Should also be caught by the base class
    with pytest.raises(ErpIntegrationReadinessError):
        raise_custom_error()


def test_deterministic_id_generation():
    """Test deterministic ID generation functions."""
    from backend.app.engines.erp_integration_readiness.ids import (
        deterministic_erp_readiness_finding_id,
        deterministic_result_set_id,
        hash_run_parameters,
    )
    
    # Test finding ID generation is deterministic
    finding_id_1 = deterministic_erp_readiness_finding_id(
        dataset_version_id="test-dv-1",
        engine_version="v1",
        rule_id="test_rule",
        rule_version="v1",
        stable_key="test_key",
        erp_system_id="test_erp",
    )
    finding_id_2 = deterministic_erp_readiness_finding_id(
        dataset_version_id="test-dv-1",
        engine_version="v1",
        rule_id="test_rule",
        rule_version="v1",
        stable_key="test_key",
        erp_system_id="test_erp",
    )
    assert finding_id_1 == finding_id_2
    
    # Test result set ID generation is deterministic
    params = {
        "erp_system_config": {"system_id": "test"},
        "parameters": {"assumptions": {}},
        "optional_inputs": {},
    }
    result_set_id_1 = deterministic_result_set_id(
        dataset_version_id="test-dv-1",
        engine_version="v1",
        erp_system_config=params["erp_system_config"],
        parameters=params["parameters"],
        optional_inputs=params["optional_inputs"],
    )
    result_set_id_2 = deterministic_result_set_id(
        dataset_version_id="test-dv-1",
        engine_version="v1",
        erp_system_config=params["erp_system_config"],
        parameters=params["parameters"],
        optional_inputs=params["optional_inputs"],
    )
    assert result_set_id_1 == result_set_id_2
    
    # Test parameter hashing is deterministic
    hash_1 = hash_run_parameters(params)
    hash_2 = hash_run_parameters(params)
    assert hash_1 == hash_2
    
    # Test parameter hashing is order-independent
    params_reordered = {
        "optional_inputs": {},
        "parameters": {"assumptions": {}},
        "erp_system_config": {"system_id": "test"},
    }
    hash_3 = hash_run_parameters(params_reordered)
    assert hash_1 == hash_3






