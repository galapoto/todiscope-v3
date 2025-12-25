"""
ERP Integration Readiness Engine Error Classes

Error handling follows the Platform Laws:
- Mandatory core inputs missing/invalid: hard-fail deterministically with typed errors
- Optional upstream artifacts missing: emit deterministic "missing prerequisite" findings

Platform Law #6: No implicit defaults — missing required inputs fail hard with deterministic errors
"""
from __future__ import annotations


class ErpIntegrationReadinessError(RuntimeError):
    """Base error class for ERP Integration Readiness Engine"""
    pass


class EngineDisabledError(ErpIntegrationReadinessError):
    """
    Raised when engine is disabled but execution is attempted.
    
    Platform Law #2: Engines are detachable
    - Disabled engine must not perform writes
    - This error should be caught at mount-time (routes not mounted) and runtime (entrypoint check)
    """
    pass


class DatasetVersionMissingError(ErpIntegrationReadinessError):
    """
    Raised when dataset_version_id is missing.
    
    Platform Law #3: DatasetVersion is mandatory
    - Every entrypoint requires explicit dataset_version_id
    - No implicit dataset selection ("latest", "current", "default")
    """
    pass


class DatasetVersionInvalidError(ErpIntegrationReadinessError):
    """
    Raised when dataset_version_id is invalid (wrong type, empty, malformed).
    
    Platform Law #3: DatasetVersion is mandatory
    - dataset_version_id must be UUIDv7 string
    - Must be validated at function entry before any database operations
    """
    pass


class DatasetVersionNotFoundError(ErpIntegrationReadinessError):
    """
    Raised when dataset_version_id does not exist in the registry.
    
    Platform Law #3: DatasetVersion is mandatory
    - DatasetVersion must exist and be accessible before evaluation begins
    - No fallback to alternative DatasetVersions
    """
    pass


class ErpSystemConfigMissingError(ErpIntegrationReadinessError):
    """
    Raised when erp_system_config is missing.
    
    Platform Law #6: No implicit defaults
    - ERP system configuration is a required run parameter
    - Must be explicit, validated, and persisted
    - No defaults, no inference
    """
    pass


class ErpSystemConfigInvalidError(ErpIntegrationReadinessError):
    """
    Raised when erp_system_config is invalid (wrong type, missing required fields).
    
    Platform Law #6: No implicit defaults
    - ERP system configuration must be validated against engine-owned schema
    - Hard-fail if invalid or missing required fields
    """
    pass


class ParametersMissingError(ErpIntegrationReadinessError):
    """Raised when parameters dict is missing."""
    pass


class ParametersInvalidError(ErpIntegrationReadinessError):
    """Raised when parameters dict is invalid or missing required fields."""
    pass


class StartedAtMissingError(ErpIntegrationReadinessError):
    """Raised when started_at is missing."""
    pass


class StartedAtInvalidError(ErpIntegrationReadinessError):
    """Raised when started_at is invalid or missing timezone."""
    pass


__all__ = [
    "ErpIntegrationReadinessError",
    "EngineDisabledError",
    "DatasetVersionMissingError",
    "DatasetVersionInvalidError",
    "DatasetVersionNotFoundError",
    "ErpSystemConfigMissingError",
    "ErpSystemConfigInvalidError",
    "ParametersMissingError",
    "ParametersInvalidError",
    "StartedAtMissingError",
    "StartedAtInvalidError",
]






