from collections.abc import Sequence

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.dataset.checksums import verify_raw_record_checksum
from backend.app.core.dataset.models import DatasetVersion
from backend.app.core.dataset.raw_models import RawRecord
from backend.app.core.dataset.uuidv7 import uuid7


async def create_dataset_version_via_ingestion(db: AsyncSession) -> DatasetVersion:
    dv = DatasetVersion(id=str(uuid7()))
    db.add(dv)
    await db.commit()
    await db.refresh(dv)
    return dv


async def create_dataset_version_for_normalization(db: AsyncSession) -> DatasetVersion:
    dv = DatasetVersion(id=str(uuid7()))
    db.add(dv)
    await db.commit()
    await db.refresh(dv)
    return dv


async def load_raw_records(
    db: AsyncSession,
    *,
    dataset_version_id: str,
    verify_checksums: bool = False,
    flag_legacy_missing: bool = False,
    order_by: Sequence[object] | None = None,
    strict_mode: bool = True,
) -> list[RawRecord]:
    """
    Load raw records for a dataset version with optional checksum verification.
    
    Args:
        db: Database session
        dataset_version_id: Dataset version ID
        verify_checksums: If True, verify checksums (default: False)
        flag_legacy_missing: If True, records with missing checksums are automatically
            flagged as legacy (legacy_no_checksum=True) and verification is skipped.
            Disallowed when strict_mode=True. Default: False.
        order_by: Optional ordering for records
        strict_mode: If True, raise exceptions on missing or mismatched checksums
            (default: True). If False, log warnings but continue.
            When True, flag_legacy_missing is disallowed.
    
    Returns:
        List of RawRecord instances
    
    Raises:
        ValueError: If strict_mode=True and flag_legacy_missing=True (incompatible)
        ChecksumMissingError: If strict_mode=True and record has missing checksum (unless legacy)
        ChecksumMismatchError: If strict_mode=True and checksum mismatch detected
    
    Strict Mode vs. Migration-Friendly Mode:
        This function supports two distinct modes for handling checksum verification:
        
        **Strict Mode (strict_mode=True, default):**
        - Enforces checksum verification on all non-legacy records
        - Missing checksums raise ChecksumMissingError (prevents data processing)
        - Checksum mismatches raise ChecksumMismatchError (prevents data processing)
        - flag_legacy_missing=True is disallowed (raises ValueError)
        - Already-flagged legacy records (legacy_no_checksum=True) are skipped
        - Use for production environments requiring strict integrity checks
        
        **Migration-Friendly Mode (strict_mode=False, flag_legacy_missing=True):**
        - Allows graceful handling of historical records without checksums
        - Missing checksums are automatically flagged as legacy (legacy_no_checksum=True)
        - Legacy flag is persisted to database for future reads
        - Verification is skipped for newly flagged legacy records
        - Use for migration scenarios where old records need to be processed
        
        **Legacy Records:**
        - Only records with legacy_no_checksum=True are skipped from verification
        - The legacy_no_checksum flag is the ONLY mechanism for bypassing checksum verification
        - This applies regardless of strict_mode value
        - Legacy records were flagged before strict mode enforcement or during migration
        - Non-legacy records with missing checksums always raise ChecksumMissingError in strict mode
    
    Legacy Record Handling:
        - Only records with legacy_no_checksum=True are skipped from verification
        - The legacy_no_checksum flag is the ONLY mechanism for bypassing checksum verification
        - Legacy auto-flagging is disallowed in strict mode to enforce integrity checks
        - Legacy flag is persisted to database
        - Non-legacy records with missing checksums raise ChecksumMissingError in strict mode
        - Legacy records allow graceful handling of pre-checksum data
    
    Strict Mode (strict_mode=True, default):
        - Missing checksums raise ChecksumMissingError for non-legacy records
        - Only records with legacy_no_checksum=True are skipped from verification
        - Checksum mismatches raise ChecksumMismatchError
        - flag_legacy_missing=True is disallowed (raises ValueError)
        - Use for environments requiring strict integrity checks on all new records
    
    Soft Mode (strict_mode=False):
        - Missing checksums log warnings and return True (unless flagged as legacy)
        - Checksum mismatches log warnings and return False
        - flag_legacy_missing=True is allowed for migration-friendly behavior
        - Use for audit/debugging scenarios or migration workflows
    """
    # Disallow flag_legacy_missing=True when strict_mode=True
    if strict_mode and flag_legacy_missing:
        raise ValueError(
            "flag_legacy_missing=True is disallowed when strict_mode=True. "
            "Strict mode requires all records to have valid checksums. "
            "Set flag_legacy_missing=False or strict_mode=False."
        )
    
    stmt: Select = select(RawRecord).where(RawRecord.dataset_version_id == dataset_version_id)
    if order_by:
        stmt = stmt.order_by(*order_by)
    records = (await db.scalars(stmt)).all()
    updated = 0
    if verify_checksums:
        for record in records:
            if record.file_checksum is None:
                # Already flagged as legacy: skip verification
                if record.legacy_no_checksum:
                    continue
                # Legacy flagging: only allowed in soft mode (strict_mode=False)
                if flag_legacy_missing and not record.legacy_no_checksum:
                    record.legacy_no_checksum = True
                    updated += 1
                    continue  # Skip verification for newly flagged legacy records
                # No legacy flagging: verify (will raise ChecksumMissingError in strict mode)
                verify_raw_record_checksum(
                    record,
                    raise_on_missing=strict_mode,
                    raise_on_mismatch=strict_mode,
                )
            else:
                # Record has checksum: verify it (will raise ChecksumMismatchError in strict mode)
                verify_raw_record_checksum(
                    record,
                    raise_on_missing=strict_mode,
                    raise_on_mismatch=strict_mode,
                )
    if updated:
        await db.commit()
    return records


async def load_raw_record_by_id(
    db: AsyncSession,
    *,
    raw_record_id: str,
    verify_checksums: bool = False,
    flag_legacy_missing: bool = False,
    strict_mode: bool = True,
) -> RawRecord | None:
    """
    Load a single raw record by ID with optional checksum verification.
    
    Args:
        db: Database session
        raw_record_id: Raw record ID
        verify_checksums: If True, verify checksum (default: False)
        flag_legacy_missing: If True, records with missing checksums are automatically
            flagged as legacy (legacy_no_checksum=True) and verification is skipped.
            Disallowed when strict_mode=True. Default: False.
        strict_mode: If True, raise exceptions on missing or mismatched checksums
            (default: True). If False, log warnings but continue.
            When True, flag_legacy_missing is disallowed.
    
    Returns:
        RawRecord instance or None if not found
    
    Raises:
        ValueError: If strict_mode=True and flag_legacy_missing=True (incompatible)
        ChecksumMissingError: If strict_mode=True and record has missing checksum (unless legacy)
        ChecksumMismatchError: If strict_mode=True and checksum mismatch detected
    
    Strict Mode vs. Migration-Friendly Mode:
        This function supports two distinct modes for handling checksum verification:
        
        **Strict Mode (strict_mode=True, default):**
        - Enforces checksum verification on all non-legacy records
        - Missing checksums raise ChecksumMissingError (prevents data processing)
        - Checksum mismatches raise ChecksumMismatchError (prevents data processing)
        - flag_legacy_missing=True is disallowed (raises ValueError)
        - Already-flagged legacy records (legacy_no_checksum=True) are skipped
        - Use for production environments requiring strict integrity checks
        
        **Migration-Friendly Mode (strict_mode=False, flag_legacy_missing=True):**
        - Allows graceful handling of historical records without checksums
        - Missing checksums are automatically flagged as legacy (legacy_no_checksum=True)
        - Legacy flag is persisted to database for future reads
        - Verification is skipped for newly flagged legacy records
        - Use for migration scenarios where old records need to be processed
        
        **Legacy Records:**
        - Only records with legacy_no_checksum=True are skipped from verification
        - The legacy_no_checksum flag is the ONLY mechanism for bypassing checksum verification
        - This applies regardless of strict_mode value
        - Legacy records were flagged before strict mode enforcement or during migration
        - Non-legacy records with missing checksums always raise ChecksumMissingError in strict mode
    
    Legacy Record Handling:
        - Only records with legacy_no_checksum=True are skipped from verification
        - The legacy_no_checksum flag is the ONLY mechanism for bypassing checksum verification
        - Legacy auto-flagging is disallowed in strict mode to enforce integrity checks
        - Legacy flag is persisted to database
        - Non-legacy records with missing checksums raise ChecksumMissingError in strict mode
        - Legacy records allow graceful handling of pre-checksum data
    
    Strict Mode (strict_mode=True, default):
        - Missing checksums raise ChecksumMissingError for non-legacy records
        - Only records with legacy_no_checksum=True are skipped from verification
        - Checksum mismatches raise ChecksumMismatchError
        - flag_legacy_missing=True is disallowed (raises ValueError)
        - Use for environments requiring strict integrity checks on all new records
    
    Soft Mode (strict_mode=False):
        - Missing checksums log warnings and return True (unless flagged as legacy)
        - Checksum mismatches log warnings and return False
        - flag_legacy_missing=True is allowed for migration-friendly behavior
        - Use for audit/debugging scenarios or migration workflows
    """
    # Disallow flag_legacy_missing=True when strict_mode=True
    if strict_mode and flag_legacy_missing:
        raise ValueError(
            "flag_legacy_missing=True is disallowed when strict_mode=True. "
            "Strict mode requires all records to have valid checksums. "
            "Set flag_legacy_missing=False or strict_mode=False."
        )
    
    record = await db.scalar(select(RawRecord).where(RawRecord.raw_record_id == raw_record_id))
    if record is None:
        return None
    if verify_checksums:
        if record.file_checksum is None:
            # Already flagged as legacy: skip verification
            if record.legacy_no_checksum:
                return record
            # Legacy flagging: only allowed in soft mode (strict_mode=False)
            if flag_legacy_missing and not record.legacy_no_checksum:
                record.legacy_no_checksum = True
                await db.commit()
                return record  # Skip verification for newly flagged legacy records
            # No legacy flagging: verify (will raise ChecksumMissingError in strict mode)
            verify_raw_record_checksum(
                record,
                raise_on_missing=strict_mode,
                raise_on_mismatch=strict_mode,
            )
            return record
        # Record has checksum: verify it (will raise ChecksumMismatchError in strict mode)
        verify_raw_record_checksum(
            record,
            raise_on_missing=strict_mode,
            raise_on_mismatch=strict_mode,
        )
    return record
