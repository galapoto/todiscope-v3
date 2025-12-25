from __future__ import annotations


class DatasetVersionMissingError(ValueError):
    pass


class DatasetVersionInvalidError(ValueError):
    pass


class DatasetVersionNotFoundError(LookupError):
    pass


class StartedAtMissingError(ValueError):
    pass


class StartedAtInvalidError(ValueError):
    pass


class NormalizedRecordMissingError(ValueError):
    pass


class ImmutableConflictError(RuntimeError):
    pass


# Scenario management errors used by enterprise scenario tooling


class ScenarioInvalidError(ValueError):
    """Raised when a stress scenario definition or its assumptions are invalid."""


class ScenarioNotFoundError(LookupError):
    """Raised when a requested scenario or scenario execution cannot be found."""





