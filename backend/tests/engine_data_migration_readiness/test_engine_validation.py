"""Tests for engine validation and registration."""
import pytest

from backend.app.core.registry.utils import (
    validate_engine_name,
    EngineValidationError
)


@pytest.mark.parametrize("engine_name, is_valid, expected_error", [
    # Valid names
    ("valid_engine", True, None),
    ("another_valid_engine_123", True, None),
    ("a" * 40, True, None),  # Max length
    ("abc", True, None),     # Min length
    
    # Invalid names
    ("InvalidEngine", False, "must be lowercase"),
    ("engine-with-dash", False, "only contain letters and underscores"),
    ("1engine", False, "must start with a letter"),
    ("a" * 41, False, "must be between 3 and 40 characters"),
    ("ab", False, "must be between 3 and 40 characters"),
    ("", False, "must be between 3 and 40 characters"),
    ("engine!name", False, "only contain letters and underscores"),
    ("engine name", False, "only contain letters and underscores"),
])
def test_validate_engine_name(engine_name, is_valid, expected_error):
    """Test engine name validation rules."""
    if is_valid:
        # Should not raise for valid names
        validate_engine_name(engine_name)
    else:
        # Should raise EngineValidationError with specific message for invalid names
        with pytest.raises(ValueError) as exc_info:
            validate_engine_name(engine_name)
        assert expected_error in str(exc_info.value).lower()


def test_engine_name_validation_in_registry():
    """Test that engine names are validated during registration."""
    from backend.app.core.registry.registry import register_engine
    from backend.app.core.registry.spec import EngineSpec
    
    # Mock engine spec
    valid_spec = EngineSpec(
        name="test_engine",
        version="1.0",
        description="Test engine",
        run_endpoint="/test",
        parameters_schema={},
    )
    
    # Test valid registration
    register_engine(valid_spec)
    
    # Test invalid registration
    invalid_spec = valid_spec._replace(name="Invalid-Engine-Name")
    with pytest.raises(ValueError):
        register_engine(invalid_spec)


@pytest.mark.parametrize("engine_name, expected_normalized", [
    ("test_engine", "test_engine"),
    ("TestEngine", "testengine"),
    ("test-engine", "test_engine"),
    ("test.engine", "test_engine"),
])
def test_engine_name_normalization(engine_name, expected_normalized):
    """Test that engine names are normalized consistently."""
    from backend.app.core.registry.utils import normalize_engine_name
    assert normalize_engine_name(engine_name) == expected_normalized


def test_duplicate_engine_registration():
    """Test that duplicate engine names are not allowed."""
    from backend.app.core.registry.registry import register_engine, get_engine
    from backend.app.core.registry.spec import EngineSpec
    
    # First registration should succeed
    spec1 = EngineSpec(
        name="test_duplicate_engine",
        version="1.0",
        description="Test engine",
        run_endpoint="/test",
        parameters_schema={},
    )
    register_engine(spec1)
    
    # Second registration with same name should fail
    spec2 = spec1._replace(version="2.0")
    with pytest.raises(ValueError) as exc_info:
        register_engine(spec2)
    assert "already registered" in str(exc_info.value).lower()
    
    # Original registration should still be accessible
    assert get_engine("test_duplicate_engine") == spec1


def test_engine_metadata_validation():
    """Test validation of engine metadata."""
    from backend.app.core.registry.spec import EngineSpec
    
    # Test missing required fields
    with pytest.raises(ValueError):
        EngineSpec(
            name="test_engine",
            version="",  # Empty version
            description="Test engine",
            run_endpoint="/test",
            parameters_schema={},
        )
    
    # Test invalid endpoint format
    with pytest.raises(ValueError):
        EngineSpec(
            name="test_engine",
            version="1.0",
            description="Test engine",
            run_endpoint="invalid_endpoint",  # Missing leading slash
            parameters_schema={},
        )


def test_engine_parameter_validation():
    """Test validation of engine parameters."""
    from backend.app.core.registry.spec import EngineSpec, ParameterType
    
    # Test valid parameter schema
    valid_spec = EngineSpec(
        name="test_engine_params",
        version="1.0",
        description="Test engine with parameters",
        run_endpoint="/test",
        parameters_schema={
            "required_param": {
                "type": ParameterType.STRING,
                "required": True,
                "description": "A required parameter",
            },
            "optional_param": {
                "type": ParameterType.INTEGER,
                "required": False,
                "description": "An optional parameter",
            },
        },
    )
    
    # Test missing required parameter
    with pytest.raises(ValueError) as exc_info:
        valid_spec.validate_parameters({})  # Missing required_param
    assert "missing required parameter" in str(exc_info.value).lower()
    
    # Test invalid parameter type
    with pytest.raises(ValueError) as exc_info:
        valid_spec.validate_parameters({
            "required_param": 123,  # Should be string
            "optional_param": "not_an_integer",
        })
    assert "invalid type" in str(exc_info.value).lower()
    
    # Test valid parameters
    params = {
        "required_param": "test_value",
        "optional_param": 42,
    }
    assert valid_spec.validate_parameters(params) == params
