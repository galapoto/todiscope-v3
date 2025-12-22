"""Custom errors for the Enterprise Litigation & Dispute Analysis engine."""

from __future__ import annotations


class EnterpriseLitigationDisputeError(Exception):
    """Base class for all data-quality and validation errors."""
    pass


class DatasetVersionMissingError(EnterpriseLitigationDisputeError):
    pass


class DatasetVersionInvalidError(EnterpriseLitigationDisputeError):
    pass


class DatasetVersionNotFoundError(EnterpriseLitigationDisputeError):
    pass


class StartedAtMissingError(EnterpriseLitigationDisputeError):
    pass


class StartedAtInvalidError(EnterpriseLitigationDisputeError):
    pass


class ParametersInvalidError(EnterpriseLitigationDisputeError):
    pass


class NormalizedRecordMissingError(EnterpriseLitigationDisputeError):
    pass


class LegalPayloadMissingError(EnterpriseLitigationDisputeError):
    pass


class ImmutableConflictError(RuntimeError):
    pass
