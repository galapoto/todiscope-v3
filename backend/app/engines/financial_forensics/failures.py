from __future__ import annotations


class FinancialForensicsError(RuntimeError):
    pass


class MissingArtifactError(FinancialForensicsError):
    pass


class InconsistentReferenceError(FinancialForensicsError):
    pass


class PartialRunError(FinancialForensicsError):
    pass


class RuntimeLimitError(FinancialForensicsError):
    pass


__all__ = [
    "FinancialForensicsError",
    "MissingArtifactError",
    "InconsistentReferenceError",
    "PartialRunError",
    "RuntimeLimitError",
]

