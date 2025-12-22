from __future__ import annotations


class EngineDisabledError(RuntimeError):
    pass


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


class RawRecordsMissingError(ValueError):
    pass


class ControlPayloadInvalidError(ValueError):
    pass


class ImmutableConflictError(RuntimeError):
    pass
