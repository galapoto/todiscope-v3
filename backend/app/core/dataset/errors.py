class DatasetIntegrityError(RuntimeError):
    pass


class ChecksumMissingError(DatasetIntegrityError):
    pass


class ChecksumMismatchError(DatasetIntegrityError):
    pass
