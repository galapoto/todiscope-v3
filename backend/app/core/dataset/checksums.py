from __future__ import annotations

import json
import logging

from backend.app.core.artifacts.checksums import sha256_hex
from backend.app.core.dataset.errors import ChecksumMismatchError, ChecksumMissingError
from backend.app.core.dataset.raw_models import RawRecord

logger = logging.getLogger(__name__)


def raw_record_payload_checksum(payload: dict) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256_hex(encoded)


def verify_raw_record_checksum(
    raw_record: RawRecord,
    *,
    raise_on_missing: bool = True,
    raise_on_mismatch: bool = True,
) -> bool:
    """
    Verify RawRecord payload integrity by comparing computed checksum with stored checksum.
    
    Args:
        raw_record: The RawRecord to verify
        raise_on_missing: If True, raise ChecksumMissingError when checksum is missing
            (default: True). Set False for soft verification.
        raise_on_mismatch: If True, raise ChecksumMismatchError on mismatch
            (default: True). Set False for soft verification.
    
    Returns:
        True if checksum is valid or missing (when raise_on_missing=False),
        False if checksum mismatch (when raise_on_mismatch=False).
        Raises exception if raise_on_missing=True or raise_on_mismatch=True.
    
    Strict Mode vs. Legacy Records:
        This function implements strict verification by default (raise_on_missing=True,
        raise_on_mismatch=True), requiring all records to have valid checksums. The only
        supported bypass is the legacy_no_checksum flag: records with
        legacy_no_checksum=True are always skipped from verification, regardless of the
        raise_on_missing/raise_on_mismatch parameters. This provides a migration-friendly
        path for pre-checksum records while keeping strict integrity checks for new records.

        - Strict Mode (default): Missing or mismatched checksums raise exceptions
        - Legacy Records: Only records with legacy_no_checksum=True are skipped
        - Migration-Friendly: Legacy records bypass strict verification by flag
    
    Legacy Record Handling:
        Records with legacy_no_checksum=True are silently skipped (no verification,
        no error, no warning). This allows graceful handling of pre-checksum records
        that were ingested before checksum validation was implemented. The legacy flag
        is set by the service layer (load_raw_records, load_raw_record_by_id) when
        flag_legacy_missing=True in soft mode, or can be set manually for migration
        scenarios. No other bypass exists for missing checksums.
    
    Strict Verification (default):
        - Missing checksums raise ChecksumMissingError (unless legacy_no_checksum=True)
        - Checksum mismatches raise ChecksumMismatchError
        - Use for environments requiring strict integrity checks on all new records

    Soft Verification:
        - Set raise_on_missing=False to log warnings and return True for missing checksums
        - Set raise_on_mismatch=False to log warnings and return False for mismatches
        - Use for audit/debugging scenarios where you want to flag issues but continue
    
    Note: This function does not set legacy_no_checksum. Use load_raw_records() with
    flag_legacy_missing=True (in soft mode) for migration-friendly legacy flagging.
    """
    if not raw_record.file_checksum:
        if raw_record.legacy_no_checksum:
            # Legacy record without checksum - silently skip
            return True
        if raise_on_missing:
            raise ChecksumMissingError("RAW_RECORD_CHECKSUM_MISSING")
        logger.warning(
            "RAW_RECORD_CHECKSUM_MISSING raw_record_id=%s dataset_version_id=%s",
            raw_record.raw_record_id,
            raw_record.dataset_version_id,
        )
        return True
    
    # Compute and compare checksum
    actual = raw_record_payload_checksum(raw_record.payload)
    if actual != raw_record.file_checksum:
        if raise_on_mismatch:
            raise ChecksumMismatchError("RAW_RECORD_CHECKSUM_MISMATCH")
        logger.warning(
            "RAW_RECORD_CHECKSUM_MISMATCH raw_record_id=%s dataset_version_id=%s "
            "expected=%s actual=%s",
            raw_record.raw_record_id,
            raw_record.dataset_version_id,
            raw_record.file_checksum,
            actual,
        )
        return False
    
    # Checksum matches
    return True
