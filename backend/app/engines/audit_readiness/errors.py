"""
Error classes for Audit Readiness Engine
"""
from __future__ import annotations


class AuditReadinessError(Exception):
    """Base exception for audit readiness engine errors."""


class DatasetVersionMissingError(AuditReadinessError):
    """Raised when dataset_version_id is missing."""


class DatasetVersionInvalidError(AuditReadinessError):
    """Raised when dataset_version_id is invalid."""


class DatasetVersionNotFoundError(AuditReadinessError):
    """Raised when dataset_version_id does not exist."""


class StartedAtMissingError(AuditReadinessError):
    """Raised when started_at is missing."""


class StartedAtInvalidError(AuditReadinessError):
    """Raised when started_at is invalid."""


class RawRecordsMissingError(AuditReadinessError):
    """Raised when raw records are missing for the dataset version."""


class ImmutableConflictError(AuditReadinessError):
    """Raised when an immutable conflict is detected."""


class RegulatoryFrameworkNotFoundError(AuditReadinessError):
    """Raised when a regulatory framework is not found."""


class ControlCatalogError(AuditReadinessError):
    """Raised when control catalog operations fail."""


class EvidenceStorageError(AuditReadinessError):
    """Raised when evidence storage operations fail."""


class ImmutableConflictError(AuditReadinessError):
    """Raised when an immutable conflict is detected."""

