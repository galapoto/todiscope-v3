from __future__ import annotations


class ConstructionCostIntelligenceError(RuntimeError):
    pass


class DatasetVersionMissingError(ConstructionCostIntelligenceError):
    pass


class DatasetVersionInvalidError(ConstructionCostIntelligenceError):
    pass


class DatasetVersionMismatchError(ConstructionCostIntelligenceError):
    pass


class IdentityInvalidError(ConstructionCostIntelligenceError):
    pass


class CostLineInvalidError(ConstructionCostIntelligenceError):
    pass


# Core run/traceability errors
class RawRecordMissingError(ConstructionCostIntelligenceError):
    pass


class RawRecordInvalidError(ConstructionCostIntelligenceError):
    pass


class StartedAtMissingError(ConstructionCostIntelligenceError):
    pass


class StartedAtInvalidError(ConstructionCostIntelligenceError):
    pass


# Backwards-compat aliases (if referenced elsewhere)
MissingArtifactError = ConstructionCostIntelligenceError
InconsistentReferenceError = DatasetVersionMismatchError
InvalidParameterError = ConstructionCostIntelligenceError


__all__ = [
    "ConstructionCostIntelligenceError",
    "DatasetVersionMissingError",
    "DatasetVersionInvalidError",
    "DatasetVersionMismatchError",
    "IdentityInvalidError",
    "CostLineInvalidError",
    "RawRecordMissingError",
    "RawRecordInvalidError",
    "StartedAtMissingError",
    "StartedAtInvalidError",
    "MissingArtifactError",
    "InconsistentReferenceError",
    "InvalidParameterError",
]
