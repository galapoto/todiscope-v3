"""Errors raised by the Data Migration Readiness engine."""


class DataMigrationReadinessError(RuntimeError):
    """Base error for all data migration readiness failures."""


class DatasetVersionMissingError(DataMigrationReadinessError):
    pass


class DatasetVersionInvalidError(DataMigrationReadinessError):
    pass


class DatasetVersionNotFoundError(DataMigrationReadinessError):
    pass


class StartedAtMissingError(DataMigrationReadinessError):
    pass


class StartedAtInvalidError(DataMigrationReadinessError):
    pass


class RawRecordsMissingError(DataMigrationReadinessError):
    pass


class ConfigurationLoadError(DataMigrationReadinessError):
    pass
