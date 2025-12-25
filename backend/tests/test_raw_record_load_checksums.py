from datetime import datetime, timezone

import pytest

from backend.app.core.db import get_sessionmaker
from backend.app.core.dataset.checksums import raw_record_payload_checksum
from backend.app.core.dataset.errors import ChecksumMismatchError, ChecksumMissingError
from backend.app.core.dataset.raw_models import RawRecord
from backend.app.core.dataset.service import (
    create_dataset_version_via_ingestion,
    load_raw_records,
    load_raw_record_by_id,
)


@pytest.mark.anyio
async def test_load_raw_records_optional_checksum_verification(sqlite_db: None) -> None:
    """load_raw_records should optionally verify checksums when requested.

    When verify_checksums=False, all records are returned even if a checksum
    mismatch exists. When verify_checksums=True, a mismatch should surface
    as RAW_RECORD_CHECKSUM_MISMATCH.
    """

    sessionmaker = get_sessionmaker()

    # Seed a DatasetVersion and two RawRecords (one valid, one with bad checksum).
    async with sessionmaker() as db:
        dv = await create_dataset_version_via_ingestion(db)
        dv_id = dv.id

        payload = {"source_system": "source", "source_record_id": "rec-1", "value": 42}
        good_checksum = raw_record_payload_checksum(payload)

        now = datetime.now(timezone.utc)

        db.add(
            RawRecord(
                raw_record_id="raw-ok",
                dataset_version_id=dv_id,
                source_system="source",
                source_record_id="rec-1",
                payload=payload,
                file_checksum=good_checksum,
                ingested_at=now,
            )
        )

        # This record intentionally has a bad checksum to trigger verification failure.
        db.add(
            RawRecord(
                raw_record_id="raw-bad",
                dataset_version_id=dv_id,
                source_system="source",
                source_record_id="rec-2",
                payload=payload,
                file_checksum="bad-checksum",
                ingested_at=now,
            )
        )

        await db.commit()

    # With verify_checksums=False, both records should be returned without error.
    async with sessionmaker() as db:
        records = await load_raw_records(db, dataset_version_id=dv_id, verify_checksums=False)
        assert {r.raw_record_id for r in records} == {"raw-ok", "raw-bad"}

    # With verify_checksums=True and strict_mode=True, checksum mismatch should raise an error.
    async with sessionmaker() as db:
        with pytest.raises(ChecksumMismatchError, match="RAW_RECORD_CHECKSUM_MISMATCH"):
            await load_raw_records(
                db,
                dataset_version_id=dv_id,
                verify_checksums=True,
                strict_mode=True,
            )
    
    # With verify_checksums=True and strict_mode=False, checksum mismatch should log warning but continue.
    async with sessionmaker() as db:
        records = await load_raw_records(db, dataset_version_id=dv_id, verify_checksums=True, strict_mode=False)
        assert {r.raw_record_id for r in records} == {"raw-ok", "raw-bad"}


@pytest.mark.anyio
async def test_load_raw_records_ignores_missing_checksum(sqlite_db: None) -> None:
    """Records without file_checksum are flagged as legacy in migration-friendly mode.

    This test verifies migration-friendly behavior where records with missing checksums
    are automatically flagged as legacy (legacy_no_checksum=True) and verification is
    skipped. This allows graceful handling of old records without checksums.
    
    Migration-Friendly Mode (strict_mode=False, flag_legacy_missing=True):
    - Missing checksums are automatically flagged as legacy
    - Legacy flag (legacy_no_checksum=True) is persisted to database
    - Verification is skipped for newly flagged legacy records
    
    Note: flag_legacy_missing=True is disallowed when strict_mode=True to enforce
    strict integrity checks.
    """

    sessionmaker = get_sessionmaker()

    async with sessionmaker() as db:
        dv = await create_dataset_version_via_ingestion(db)
        dv_id = dv.id

        payload = {"source_system": "source", "source_record_id": "rec-1", "value": 42}
        now = datetime.now(timezone.utc)

        # file_checksum=None should be treated as legacy when flag_legacy_missing=True
        db.add(
            RawRecord(
                raw_record_id="raw-no-checksum",
                dataset_version_id=dv_id,
                source_system="source",
                source_record_id="rec-1",
                payload=payload,
                file_checksum=None,
                legacy_no_checksum=False,  # Initially not flagged
                ingested_at=now,
            )
        )

        await db.commit()

    # With verify_checksums=True, flag_legacy_missing=True, and strict_mode=False,
    # the record should be flagged as legacy and verification skipped.
    async with sessionmaker() as db:
        records = await load_raw_records(
            db, 
            dataset_version_id=dv_id, 
            verify_checksums=True,
            flag_legacy_missing=True,
            strict_mode=False,  # Soft mode allows legacy flagging
        )
        assert [r.raw_record_id for r in records] == ["raw-no-checksum"]
        
        # Explicitly assert that legacy_no_checksum flag is set in migration-friendly mode
        # This confirms that the legacy flag is the mechanism for skipping verification
        record = records[0]
        assert record.legacy_no_checksum is True, (
            "Record should be flagged as legacy (legacy_no_checksum=True) "
            "when flag_legacy_missing=True in migration-friendly mode. "
            "The legacy_no_checksum flag is the ONLY mechanism for bypassing verification."
        )
    
    # Verify the legacy flag persists in a new session (both strict and soft mode)
    # This confirms that legacy records are skipped regardless of strict_mode value
    async with sessionmaker() as db:
        # In strict mode, legacy records should still be skipped (legacy flag is the ONLY bypass)
        records = await load_raw_records(
            db,
            dataset_version_id=dv_id,
            verify_checksums=True,
            strict_mode=True,
            flag_legacy_missing=False,
        )
        assert records[0].legacy_no_checksum is True, (
            "Legacy flag should persist after commit in strict mode. "
            "Only records with legacy_no_checksum=True are skipped from verification."
        )
    
    async with sessionmaker() as db:
        # In soft mode, legacy records should also be skipped
        records = await load_raw_records(
            db,
            dataset_version_id=dv_id,
            verify_checksums=True,
            strict_mode=False,
            flag_legacy_missing=False,
        )
        assert records[0].legacy_no_checksum is True, (
            "Legacy flag should persist after commit in soft mode. "
            "The legacy_no_checksum flag is the ONLY mechanism for bypassing verification."
        )

    # With strict_mode=True, flag_legacy_missing=True should be disallowed
    async with sessionmaker() as db:
        with pytest.raises(ValueError, match="flag_legacy_missing=True is disallowed when strict_mode=True"):
            await load_raw_records(
                db,
                dataset_version_id=dv_id,
                verify_checksums=True,
                flag_legacy_missing=True,
                strict_mode=True,
            )


@pytest.mark.anyio
async def test_load_raw_records_strict_mode_missing_checksum(sqlite_db: None) -> None:
    """Non-legacy records without file_checksum raise error in strict mode.

    This test verifies that in strict mode, non-legacy records (legacy_no_checksum=False)
    with missing checksums raise ChecksumMissingError. Only records with
    legacy_no_checksum=True are allowed to bypass verification.
    
    Strict Mode Behavior:
    - Non-legacy records with missing checksums raise ChecksumMissingError
    - The legacy_no_checksum flag is the ONLY mechanism for bypassing verification
    - flag_legacy_missing=True is disallowed in strict mode
    """

    sessionmaker = get_sessionmaker()

    async with sessionmaker() as db:
        dv = await create_dataset_version_via_ingestion(db)
        dv_id = dv.id

        payload = {"source_system": "source", "source_record_id": "rec-1", "value": 42}
        now = datetime.now(timezone.utc)

        db.add(
            RawRecord(
                raw_record_id="raw-no-checksum",
                dataset_version_id=dv_id,
                source_system="source",
                source_record_id="rec-1",
                payload=payload,
                file_checksum=None,
                legacy_no_checksum=False,
                ingested_at=now,
            )
        )

        await db.commit()

    # With strict_mode=True and flag_legacy_missing=False, missing checksum should raise error
    # for non-legacy records. Only records with legacy_no_checksum=True are skipped.
    async with sessionmaker() as db:
        with pytest.raises(ChecksumMissingError, match="RAW_RECORD_CHECKSUM_MISSING"):
            await load_raw_records(
                db,
                dataset_version_id=dv_id,
                verify_checksums=True,
                flag_legacy_missing=False,  # No legacy flagging
                strict_mode=True,  # Strict mode: raise on missing for non-legacy records
            )
    
    # With strict_mode=False and flag_legacy_missing=False, missing checksum should log warning but continue
    # Record should NOT be flagged as legacy when flag_legacy_missing=False
    async with sessionmaker() as db:
        records = await load_raw_records(
            db,
            dataset_version_id=dv_id,
            verify_checksums=True,
            flag_legacy_missing=False,  # No legacy flagging
            strict_mode=False,  # Soft mode: log warning
        )
        assert [r.raw_record_id for r in records] == ["raw-no-checksum"]
        # Explicitly assert that record is NOT flagged as legacy when flag_legacy_missing=False
        # This confirms that legacy_no_checksum flag is the ONLY mechanism for skipping verification
        assert records[0].legacy_no_checksum is False, (
            "Record should NOT be flagged as legacy when flag_legacy_missing=False. "
            "The legacy_no_checksum flag is the ONLY mechanism for bypassing verification."
        )


@pytest.mark.anyio
async def test_load_raw_record_by_id_strict_verification(sqlite_db: None) -> None:
    """load_raw_record_by_id should enforce strict checksum verification when verify_checksums=True."""

    sessionmaker = get_sessionmaker()

    async with sessionmaker() as db:
        dv = await create_dataset_version_via_ingestion(db)
        dv_id = dv.id

        payload = {"source_system": "source", "source_record_id": "rec-1", "value": 42}
        good_checksum = raw_record_payload_checksum(payload)
        now = datetime.now(timezone.utc)

        # Valid record with correct checksum
        db.add(
            RawRecord(
                raw_record_id="raw-ok",
                dataset_version_id=dv_id,
                source_system="source",
                source_record_id="rec-1",
                payload=payload,
                file_checksum=good_checksum,
                ingested_at=now,
            )
        )

        # Record with bad checksum
        db.add(
            RawRecord(
                raw_record_id="raw-bad",
                dataset_version_id=dv_id,
                source_system="source",
                source_record_id="rec-2",
                payload=payload,
                file_checksum="bad-checksum",
                ingested_at=now,
            )
        )

        # Record without checksum
        db.add(
            RawRecord(
                raw_record_id="raw-no-checksum",
                dataset_version_id=dv_id,
                source_system="source",
                source_record_id="rec-3",
                payload=payload,
                file_checksum=None,
                legacy_no_checksum=False,
                ingested_at=now,
            )
        )

        # Legacy record without checksum
        db.add(
            RawRecord(
                raw_record_id="raw-legacy",
                dataset_version_id=dv_id,
                source_system="source",
                source_record_id="rec-4",
                payload=payload,
                file_checksum=None,
                legacy_no_checksum=True,
                ingested_at=now,
            )
        )

        await db.commit()

    # Valid record should pass verification
    async with sessionmaker() as db:
        record = await load_raw_record_by_id(
            db,
            raw_record_id="raw-ok",
            verify_checksums=True,
            strict_mode=True,
        )
        assert record is not None
        assert record.raw_record_id == "raw-ok"

    # Bad checksum should raise error in strict mode
    async with sessionmaker() as db:
        with pytest.raises(ChecksumMismatchError, match="RAW_RECORD_CHECKSUM_MISMATCH"):
            await load_raw_record_by_id(
                db,
                raw_record_id="raw-bad",
                verify_checksums=True,
                strict_mode=True,
            )

    # Missing checksum should raise error in strict mode (when not flagged as legacy)
    async with sessionmaker() as db:
        with pytest.raises(ChecksumMissingError, match="RAW_RECORD_CHECKSUM_MISSING"):
            await load_raw_record_by_id(
                db,
                raw_record_id="raw-no-checksum",
                verify_checksums=True,
                flag_legacy_missing=False,
                strict_mode=True,
            )

    # Legacy record should be skipped (no verification, no error) in strict mode
    async with sessionmaker() as db:
        record = await load_raw_record_by_id(
            db,
            raw_record_id="raw-legacy",
            verify_checksums=True,
            strict_mode=True,
        )
        assert record is not None
        assert record.raw_record_id == "raw-legacy"
        # Explicitly assert that legacy_no_checksum flag is True
        assert record.legacy_no_checksum is True, "Legacy record should have legacy_no_checksum=True"
    
    # Legacy record should also be skipped in soft mode
    async with sessionmaker() as db:
        record = await load_raw_record_by_id(
            db,
            raw_record_id="raw-legacy",
            verify_checksums=True,
            strict_mode=False,
        )
        assert record is not None
        assert record.legacy_no_checksum is True, "Legacy flag should persist in soft mode"

    # With verify_checksums=False, all records should be returned without verification
    async with sessionmaker() as db:
        record = await load_raw_record_by_id(
            db,
            raw_record_id="raw-bad",
            verify_checksums=False,
        )
        assert record is not None
        assert record.raw_record_id == "raw-bad"


@pytest.mark.anyio
async def test_load_raw_records_legacy_records_always_skipped(sqlite_db: None) -> None:
    """Legacy records (legacy_no_checksum=True) are always skipped from verification.

    This test verifies that records with legacy_no_checksum=True are correctly
    skipped from checksum verification in both strict mode and soft mode. Legacy
    records are handled gracefully regardless of the verification mode.
    """

    sessionmaker = get_sessionmaker()

    async with sessionmaker() as db:
        dv = await create_dataset_version_via_ingestion(db)
        dv_id = dv.id

        payload = {"source_system": "source", "source_record_id": "rec-1", "value": 42}
        now = datetime.now(timezone.utc)

        # Legacy record without checksum
        db.add(
            RawRecord(
                raw_record_id="raw-legacy-no-checksum",
                dataset_version_id=dv_id,
                source_system="source",
                source_record_id="rec-1",
                payload=payload,
                file_checksum=None,
                legacy_no_checksum=True,  # Explicitly flagged as legacy
                ingested_at=now,
            )
        )

        # Legacy record with bad checksum (should still be skipped)
        db.add(
            RawRecord(
                raw_record_id="raw-legacy-bad-checksum",
                dataset_version_id=dv_id,
                source_system="source",
                source_record_id="rec-2",
                payload=payload,
                file_checksum="bad-checksum",
                legacy_no_checksum=True,  # Explicitly flagged as legacy
                ingested_at=now,
            )
        )

        await db.commit()

    # Legacy records should be skipped even in strict mode
    async with sessionmaker() as db:
        records = await load_raw_records(
            db,
            dataset_version_id=dv_id,
            verify_checksums=True,
            strict_mode=True,
            flag_legacy_missing=False,
        )
        assert len(records) == 2
        assert {r.raw_record_id for r in records} == {"raw-legacy-no-checksum", "raw-legacy-bad-checksum"}
        # Explicitly assert that all records have legacy_no_checksum=True
        # This confirms that only legacy records are skipped from verification
        for record in records:
            assert record.legacy_no_checksum is True, (
                f"Record {record.raw_record_id} should have legacy_no_checksum=True. "
                "Only records with legacy_no_checksum=True are skipped from verification."
            )
    
    # Legacy records should also be skipped in soft mode
    async with sessionmaker() as db:
        records = await load_raw_records(
            db,
            dataset_version_id=dv_id,
            verify_checksums=True,
            strict_mode=False,
            flag_legacy_missing=False,
        )
        assert len(records) == 2
        # Explicitly assert that legacy flag persists
        assert all(r.legacy_no_checksum is True for r in records), "Legacy flag should persist in soft mode"


@pytest.mark.anyio
async def test_load_raw_records_no_data_processed_without_integrity_validation(sqlite_db: None) -> None:
    """No data should be processed without integrity validation unless explicitly bypassed (legacy).

    This test verifies that in strict mode, non-legacy records with missing or mismatched
    checksums raise exceptions, preventing data processing. Only records with
    legacy_no_checksum=True are allowed to bypass verification.
    """

    sessionmaker = get_sessionmaker()

    async with sessionmaker() as db:
        dv = await create_dataset_version_via_ingestion(db)
        dv_id = dv.id

        payload = {"source_system": "source", "source_record_id": "rec-1", "value": 42}
        now = datetime.now(timezone.utc)

        # Record with bad checksum (not legacy)
        db.add(
            RawRecord(
                raw_record_id="raw-bad",
                dataset_version_id=dv_id,
                source_system="source",
                source_record_id="rec-1",
                payload=payload,
                file_checksum="bad-checksum",
                legacy_no_checksum=False,  # Not legacy - should raise error
                ingested_at=now,
            )
        )

        # Record without checksum (not legacy)
        db.add(
            RawRecord(
                raw_record_id="raw-no-checksum",
                dataset_version_id=dv_id,
                source_system="source",
                source_record_id="rec-2",
                payload=payload,
                file_checksum=None,
                legacy_no_checksum=False,  # Not legacy - should raise error
                ingested_at=now,
            )
        )

        await db.commit()

    # With verify_checksums=True and strict_mode=True, bad checksum should prevent processing
    # for non-legacy records
    async with sessionmaker() as db:
        with pytest.raises(ChecksumMismatchError):
            await load_raw_records(
                db,
                dataset_version_id=dv_id,
                verify_checksums=True,
                strict_mode=True,
                flag_legacy_missing=False,
            )

    # With verify_checksums=True and strict_mode=True, missing checksum should prevent processing
    # for non-legacy records. Only records with legacy_no_checksum=True are skipped.
    async with sessionmaker() as db:
        with pytest.raises(ChecksumMissingError):
            await load_raw_records(
                db,
                dataset_version_id=dv_id,
                verify_checksums=True,
                strict_mode=True,
                flag_legacy_missing=False,
            )


@pytest.mark.anyio
async def test_load_raw_records_strict_mode_disallows_legacy_flagging(sqlite_db: None) -> None:
    """Strict mode disallows flag_legacy_missing=True to enforce integrity checks."""

    sessionmaker = get_sessionmaker()

    async with sessionmaker() as db:
        dv = await create_dataset_version_via_ingestion(db)
        dv_id = dv.id

        payload = {"source_system": "source", "source_record_id": "rec-1", "value": 42}
        now = datetime.now(timezone.utc)

        db.add(
            RawRecord(
                raw_record_id="raw-no-checksum",
                dataset_version_id=dv_id,
                source_system="source",
                source_record_id="rec-1",
                payload=payload,
                file_checksum=None,
                legacy_no_checksum=False,
                ingested_at=now,
            )
        )

        await db.commit()

    # With strict_mode=True and flag_legacy_missing=True, should raise ValueError
    async with sessionmaker() as db:
        with pytest.raises(ValueError, match="flag_legacy_missing=True is disallowed when strict_mode=True"):
            await load_raw_records(
                db,
                dataset_version_id=dv_id,
                verify_checksums=True,
                flag_legacy_missing=True,
                strict_mode=True,
            )


@pytest.mark.anyio
async def test_load_raw_record_by_id_strict_mode_disallows_legacy_flagging(sqlite_db: None) -> None:
    """load_raw_record_by_id disallows flag_legacy_missing=True when strict_mode=True."""

    sessionmaker = get_sessionmaker()

    async with sessionmaker() as db:
        dv = await create_dataset_version_via_ingestion(db)
        dv_id = dv.id

        payload = {"source_system": "source", "source_record_id": "rec-1", "value": 42}
        now = datetime.now(timezone.utc)

        db.add(
            RawRecord(
                raw_record_id="raw-no-checksum",
                dataset_version_id=dv_id,
                source_system="source",
                source_record_id="rec-1",
                payload=payload,
                file_checksum=None,
                legacy_no_checksum=False,
                ingested_at=now,
            )
        )

        await db.commit()

    # With strict_mode=True and flag_legacy_missing=True, should raise ValueError
    async with sessionmaker() as db:
        with pytest.raises(ValueError, match="flag_legacy_missing=True is disallowed when strict_mode=True"):
            await load_raw_record_by_id(
                db,
                raw_record_id="raw-no-checksum",
                verify_checksums=True,
                flag_legacy_missing=True,
                strict_mode=True,
            )
