"""Tests for error classes and utility functions."""
from __future__ import annotations

import pytest

from backend.app.engines.data_migration_readiness.errors import (
    DataMigrationReadinessError,
    DatasetVersionMissingError,
    DatasetVersionInvalidError,
    DatasetVersionNotFoundError,
    StartedAtMissingError,
    StartedAtInvalidError,
    RawRecordsMissingError,
    ConfigurationLoadError,
)


def test_error_hierarchy():
    """Test that all custom exceptions inherit from the base error class."""
    error_classes = [
        DatasetVersionMissingError,
        DatasetVersionInvalidError,
        DatasetVersionNotFoundError,
        StartedAtMissingError,
        StartedAtInvalidError,
        RawRecordsMissingError,
        ConfigurationLoadError,
    ]
    
    for error_cls in error_classes:
        # Create an instance of the error class
        error = error_cls("test message")
        # Verify it's an instance of the base class
        assert isinstance(error, DataMigrationReadinessError)
        # Verify the message is set correctly
        assert str(error) == "test message"


def test_error_messages():
    """Test error messages for different error types."""
    # Test DatasetVersionMissingError
    with pytest.raises(DatasetVersionMissingError) as exc_info:
        raise DatasetVersionMissingError("MISSING_DATASET_VERSION")
    assert "MISSING_DATASET_VERSION" in str(exc_info.value)
    
    # Test DatasetVersionInvalidError
    with pytest.raises(DatasetVersionInvalidError) as exc_info:
        raise DatasetVersionInvalidError("INVALID_DATASET_VERSION")
    assert "INVALID_DATASET_VERSION" in str(exc_info.value)
    
    # Test DatasetVersionNotFoundError
    with pytest.raises(DatasetVersionNotFoundError) as exc_info:
        raise DatasetVersionNotFoundError("DATASET_VERSION_NOT_FOUND")
    assert "DATASET_VERSION_NOT_FOUND" in str(exc_info.value)
    
    # Test StartedAtMissingError
    with pytest.raises(StartedAtMissingError) as exc_info:
        raise StartedAtMissingError("MISSING_STARTED_AT")
    assert "MISSING_STARTED_AT" in str(exc_info.value)
    
    # Test StartedAtInvalidError
    with pytest.raises(StartedAtInvalidError) as exc_info:
        raise StartedAtInvalidError("INVALID_STARTED_AT")
    assert "INVALID_STARTED_AT" in str(exc_info.value)
    
    # Test RawRecordsMissingError
    with pytest.raises(RawRecordsMissingError) as exc_info:
        raise RawRecordsMissingError("NO_RAW_RECORDS")
    assert "NO_RAW_RECORDS" in str(exc_info.value)
    
    # Test ConfigurationLoadError
    with pytest.raises(ConfigurationLoadError) as exc_info:
        raise ConfigurationLoadError("CONFIG_LOAD_FAILED")
    assert "CONFIG_LOAD_FAILED" in str(exc_info.value)


def test_error_chaining():
    """Test that errors can be chained with their causes."""
    try:
        # Simulate an underlying error
        try:
            raise ValueError("Underlying error")
        except ValueError as e:
            # Wrap it in a custom error
            raise ConfigurationLoadError("Failed to load config") from e
    except ConfigurationLoadError as e:
        assert "Failed to load config" in str(e)
        assert "Underlying error" in str(e.__cause__)


def test_error_equality():
    """Test that error instances with the same message are equal."""
    error1 = DatasetVersionMissingError("MISSING")
    error2 = DatasetVersionMissingError("MISSING")
    error3 = DatasetVersionMissingError("DIFFERENT")
    
    assert error1 == error2
    assert error1 != error3
    assert error1 != "not an error"


def test_error_repr():
    """Test the string representation of error objects."""
    error = DatasetVersionMissingError("MISSING")
    assert "DatasetVersionMissingError" in repr(error)
    assert "MISSING" in repr(error)


def test_error_inheritance():
    """Test that custom errors can be caught by their base class."""
    def raise_custom_error():
        raise DatasetVersionMissingError("MISSING")
    
    # Should be caught by the specific exception class
    with pytest.raises(DatasetVersionMissingError):
        raise_custom_error()
    
    # Should also be caught by the base class
    with pytest.raises(DataMigrationReadinessError):
        raise_custom_error()
    
    # Should not be caught by unrelated exceptions
    with pytest.raises(ValueError):
        try:
            raise_custom_error()
        except ValueError:
            raise
        except DataMigrationReadinessError:
            pass  # Ignore the expected error


def test_configuration_load_error_specifics():
    """Test specific behavior of ConfigurationLoadError."""
    # Test with just a message
    error1 = ConfigurationLoadError("CONFIG_LOAD_FAILED")
    assert error1.error_code == "CONFIG_LOAD_FAILED"
    
    # Test with a message and a cause
    try:
        try:
            raise ValueError("File not found")
        except ValueError as e:
            raise ConfigurationLoadError("CONFIG_LOAD_FAILED") from e
    except ConfigurationLoadError as e:
        assert e.error_code == "CONFIG_LOAD_FAILED"
        assert isinstance(e.__cause__, ValueError)


def test_error_serialization():
    """Test that error objects can be serialized to dict/JSON."""
    error = DatasetVersionMissingError("MISSING_DATASET_VERSION")
    error_dict = {"error": str(error), "type": error.__class__.__name__}
    
    assert error_dict["error"] == "MISSING_DATASET_VERSION"
    assert error_dict["type"] == "DatasetVersionMissingError"


def test_error_additional_context():
    """Test that errors can carry additional context."""
    class CustomError(DataMigrationReadinessError):
        def __init__(self, message: str, context: dict):
            super().__init__(message)
            self.context = context
    
    error = CustomError("ERROR_WITH_CONTEXT", {"field": "value", "count": 42})
    assert error.context == {"field": "value", "count": 42}
    assert str(error) == "ERROR_WITH_CONTEXT"
