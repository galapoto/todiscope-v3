from datetime import datetime, timezone

import pytest

from backend.app.core.dataset.checksums import raw_record_payload_checksum, verify_raw_record_checksum
from backend.app.core.dataset.errors import ChecksumMismatchError, ChecksumMissingError
from backend.app.core.dataset.raw_models import RawRecord


def _build_raw_record(*, payload: dict, checksum: str | None, legacy_no_checksum: bool = False) -> RawRecord:
    return RawRecord(
        raw_record_id="raw-1",
        dataset_version_id="dv-1",
        source_system="source",
        source_record_id="rec-1",
        payload=payload,
        file_checksum=checksum,
        legacy_no_checksum=legacy_no_checksum,
        ingested_at=datetime.now(timezone.utc),
    )


def test_verify_raw_record_checksum_ok() -> None:
    """Verify that correct checksum passes validation."""
    payload = {"source_system": "source", "source_record_id": "rec-1", "value": 42}
    checksum = raw_record_payload_checksum(payload)
    record = _build_raw_record(payload=payload, checksum=checksum)
    result = verify_raw_record_checksum(record)
    assert result is True


def test_verify_raw_record_checksum_mismatch_soft_failure(caplog: pytest.LogCaptureFixture) -> None:
    """Verify that checksum mismatch is strict by default and soft when requested."""
    payload = {"source_system": "source", "source_record_id": "rec-1", "value": 42}
    record = _build_raw_record(payload=payload, checksum="bad")
    
    # Default behavior is strict.
    with pytest.raises(ChecksumMismatchError, match="RAW_RECORD_CHECKSUM_MISMATCH"):
        verify_raw_record_checksum(record)

    # Soft failure: warn and return False.
    with caplog.at_level("WARNING"):
        result = verify_raw_record_checksum(record, raise_on_mismatch=False)
        assert result is False
        assert any("RAW_RECORD_CHECKSUM_MISMATCH" in record.message for record in caplog.records)


def test_verify_raw_record_checksum_mismatch_hard_failure() -> None:
    """Verify that checksum mismatch raises exception when raise_on_mismatch=True."""
    payload = {"source_system": "source", "source_record_id": "rec-1", "value": 42}
    record = _build_raw_record(payload=payload, checksum="bad")
    with pytest.raises(ChecksumMismatchError, match="RAW_RECORD_CHECKSUM_MISMATCH"):
        verify_raw_record_checksum(record, raise_on_mismatch=True)


def test_verify_raw_record_checksum_missing_soft_failure(caplog: pytest.LogCaptureFixture) -> None:
    """Verify that missing checksum is strict by default and soft when requested."""
    payload = {"source_system": "source", "source_record_id": "rec-1", "value": 42}
    record = _build_raw_record(payload=payload, checksum=None)
    
    # Default behavior is strict.
    with pytest.raises(ChecksumMissingError, match="RAW_RECORD_CHECKSUM_MISSING"):
        verify_raw_record_checksum(record)

    # Soft failure: skip verification, log warning, return True.
    with caplog.at_level("WARNING"):
        result = verify_raw_record_checksum(record, raise_on_missing=False)
        assert result is True
        assert any("RAW_RECORD_CHECKSUM_MISSING" in record.message for record in caplog.records)


def test_verify_raw_record_checksum_missing_hard_failure() -> None:
    """Verify that missing checksum raises exception when raise_on_missing=True."""
    payload = {"source_system": "source", "source_record_id": "rec-1", "value": 42}
    record = _build_raw_record(payload=payload, checksum=None)
    with pytest.raises(ChecksumMissingError, match="RAW_RECORD_CHECKSUM_MISSING"):
        verify_raw_record_checksum(record, raise_on_missing=True)


def test_verify_raw_record_checksum_missing_legacy_flagged() -> None:
    """Verify that legacy records without checksum are silently skipped."""
    payload = {"source_system": "source", "source_record_id": "rec-1", "value": 42}
    record = _build_raw_record(payload=payload, checksum=None, legacy_no_checksum=True)
    result = verify_raw_record_checksum(record)
    assert result is True
