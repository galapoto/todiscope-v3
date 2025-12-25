"""Custom errors for the Enterprise Insurance Claim Forensics engine."""

from __future__ import annotations


class EnterpriseInsuranceClaimForensicsError(Exception):
    """Base class for all insurance claim forensics errors."""
    pass


class DatasetVersionMissingError(EnterpriseInsuranceClaimForensicsError):
    """Raised when dataset_version_id is missing."""
    pass


class DatasetVersionInvalidError(EnterpriseInsuranceClaimForensicsError):
    """Raised when dataset_version_id is invalid."""
    pass


class DatasetVersionNotFoundError(EnterpriseInsuranceClaimForensicsError):
    """Raised when dataset_version_id does not exist."""
    pass


class StartedAtMissingError(EnterpriseInsuranceClaimForensicsError):
    """Raised when started_at is missing."""
    pass


class StartedAtInvalidError(EnterpriseInsuranceClaimForensicsError):
    """Raised when started_at is invalid."""
    pass


class ParametersInvalidError(EnterpriseInsuranceClaimForensicsError):
    """Raised when parameters are invalid."""
    pass


class NormalizedRecordMissingError(EnterpriseInsuranceClaimForensicsError):
    """Raised when normalized records are missing."""
    pass


class ClaimPayloadMissingError(EnterpriseInsuranceClaimForensicsError):
    """Raised when claim payload is missing."""
    pass


class ClaimValidationError(EnterpriseInsuranceClaimForensicsError):
    """Raised when claim validation fails."""
    pass


class ImmutableConflictError(RuntimeError):
    """Raised when immutability constraints are violated."""
    pass






