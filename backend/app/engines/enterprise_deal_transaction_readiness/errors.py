"""
Engine #5 Error Classes

Error handling follows the DR-1 Boundary Document requirements:
- Mandatory core inputs missing/invalid: hard-fail deterministically with typed errors
- Optional upstream artifacts missing: emit deterministic "missing prerequisite" findings

Platform Law #6: No implicit defaults — missing required inputs fail hard with deterministic errors
"""
from __future__ import annotations


class EnterpriseDealTransactionReadinessError(RuntimeError):
    """Base error class for Engine #5"""
    pass


class EngineDisabledError(EnterpriseDealTransactionReadinessError):
    """
    Raised when engine is disabled but execution is attempted.
    
    Platform Law #2: Engines are detachable
    - Disabled engine must not perform writes
    - This error should be caught at mount-time (routes not mounted) and runtime (entrypoint check)
    """
    pass


class DatasetVersionMissingError(EnterpriseDealTransactionReadinessError):
    """
    Raised when dataset_version_id is missing.
    
    Platform Law #3: DatasetVersion is mandatory
    - Every entrypoint requires explicit dataset_version_id
    - No implicit dataset selection ("latest", "current", "default")
    """
    pass


class DatasetVersionInvalidError(EnterpriseDealTransactionReadinessError):
    """
    Raised when dataset_version_id is invalid (wrong type, empty, malformed).
    
    Platform Law #3: DatasetVersion is mandatory
    - dataset_version_id must be UUIDv7 string
    - Must be validated at function entry before any database operations
    """
    pass


class DatasetVersionNotFoundError(EnterpriseDealTransactionReadinessError):
    """
    Raised when dataset_version_id does not exist in the registry.
    
    Platform Law #3: DatasetVersion is mandatory
    - DatasetVersion must exist and be accessible before evaluation begins
    - No fallback to alternative DatasetVersions
    """
    pass


class TransactionScopeMissingError(EnterpriseDealTransactionReadinessError):
    """
    Raised when transaction_scope is missing.
    
    Platform Law #6: No implicit defaults
    - Transaction scope is a required run parameter
    - Must be explicit, validated, and persisted
    - No defaults, no inference
    """
    pass


class TransactionScopeInvalidError(EnterpriseDealTransactionReadinessError):
    """
    Raised when transaction_scope is invalid (unknown type, not in allowed list).
    
    Platform Law #6: No implicit defaults
    - Transaction scope must be validated against engine-owned transaction scope definitions
    - Hard-fail if invalid or unknown
    """
    pass


class MissingPrerequisiteArtifactError(EnterpriseDealTransactionReadinessError):
    """
    Raised when optional upstream artifact is missing.
    
    This should be handled by emitting a "missing prerequisite" finding rather than hard-failing,
    but this error can be used internally for control flow.
    
    Platform Law #6: No implicit defaults
    - Missing optional upstream artifacts produce deterministic findings, not best-effort guesses
    """
    pass


class ParametersMissingError(EnterpriseDealTransactionReadinessError):
    """Raised when parameters dict is missing."""
    pass


class ParametersInvalidError(EnterpriseDealTransactionReadinessError):
    """Raised when parameters dict is invalid or missing required fields."""
    pass


class StartedAtMissingError(EnterpriseDealTransactionReadinessError):
    """Raised when started_at is missing."""
    pass


class StartedAtInvalidError(EnterpriseDealTransactionReadinessError):
    """Raised when started_at is invalid or missing timezone."""
    pass


__all__ = [
    "EnterpriseDealTransactionReadinessError",
    "EngineDisabledError",
    "DatasetVersionMissingError",
    "DatasetVersionInvalidError",
    "DatasetVersionNotFoundError",
    "TransactionScopeMissingError",
    "TransactionScopeInvalidError",
    "MissingPrerequisiteArtifactError",
    "ParametersMissingError",
    "ParametersInvalidError",
    "StartedAtMissingError",
    "StartedAtInvalidError",
]

