from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.dataset.checksums import raw_record_payload_checksum, verify_raw_record_checksum
from backend.app.core.dataset.errors import ChecksumMismatchError
from backend.app.core.dataset.raw_models import RawRecord


@dataclass(frozen=True)
class FlaggedLegacyRecord:
    raw_record_id: str
    dataset_version_id: str


@dataclass(frozen=True)
class BackfillFailure:
    raw_record_id: str
    dataset_version_id: str
    reason: str


@dataclass(frozen=True)
class BackfillOutcome:
    raw_record_id: str
    dataset_version_id: str
    checksum_status: str
    reason: str | None = None


@dataclass(frozen=True)
class BackfillReport:
    total_missing: int
    flagged_legacy: int
    backfilled: int
    failed: tuple[BackfillFailure, ...]
    outcomes: tuple[BackfillOutcome, ...]


async def flag_legacy_no_checksum_records(db: AsyncSession) -> tuple[FlaggedLegacyRecord, ...]:
    records = (
        await db.scalars(
            select(RawRecord).where(RawRecord.file_checksum.is_(None), RawRecord.legacy_no_checksum.is_(False))
        )
    ).all()
    flagged: list[FlaggedLegacyRecord] = []
    for record in records:
        record.legacy_no_checksum = True
        flagged.append(
            FlaggedLegacyRecord(
                raw_record_id=record.raw_record_id,
                dataset_version_id=record.dataset_version_id,
            )
        )
    if records:
        await db.commit()
    return tuple(flagged)


async def backfill_raw_record_checksums(db: AsyncSession, *, batch_size: int = 500) -> BackfillReport:
    failures: list[BackfillFailure] = []
    outcomes: list[BackfillOutcome] = []
    backfilled = 0
    flagged_legacy = 0
    total_missing = 0

    last_id = ""
    while True:
        batch = (
            await db.scalars(
                select(RawRecord)
                .where(RawRecord.file_checksum.is_(None), RawRecord.raw_record_id > last_id)
                .order_by(RawRecord.raw_record_id.asc())
                .limit(batch_size)
            )
        ).all()
        if not batch:
            break
        last_id = batch[-1].raw_record_id
        total_missing += len(batch)
        for record in batch:
            try:
                checksum = raw_record_payload_checksum(record.payload)
            except Exception as exc:  # noqa: BLE001
                record.legacy_no_checksum = True
                failures.append(
                    BackfillFailure(
                        raw_record_id=record.raw_record_id,
                        dataset_version_id=record.dataset_version_id,
                        reason=f"CHECKSUM_COMPUTE_FAILED: {type(exc).__name__}",
                    )
                )
                outcomes.append(
                    BackfillOutcome(
                        raw_record_id=record.raw_record_id,
                        dataset_version_id=record.dataset_version_id,
                        checksum_status="legacy_flagged_compute_failed",
                        reason=f"CHECKSUM_COMPUTE_FAILED: {type(exc).__name__}",
                    )
                )
                flagged_legacy += 1
                continue
            record.file_checksum = checksum
            record.legacy_no_checksum = False
            try:
                verify_raw_record_checksum(record, raise_on_missing=True, raise_on_mismatch=True)
            except ChecksumMismatchError as exc:
                record.file_checksum = None
                record.legacy_no_checksum = True
                failures.append(
                    BackfillFailure(
                        raw_record_id=record.raw_record_id,
                        dataset_version_id=record.dataset_version_id,
                        reason=str(exc),
                    )
                )
                outcomes.append(
                    BackfillOutcome(
                        raw_record_id=record.raw_record_id,
                        dataset_version_id=record.dataset_version_id,
                        checksum_status="legacy_flagged_mismatch",
                        reason=str(exc),
                    )
                )
                flagged_legacy += 1
                continue
            backfilled += 1
            outcomes.append(
                BackfillOutcome(
                    raw_record_id=record.raw_record_id,
                    dataset_version_id=record.dataset_version_id,
                    checksum_status="backfilled",
                )
            )
        await db.commit()

    return BackfillReport(
        total_missing=total_missing,
        flagged_legacy=flagged_legacy,
        backfilled=backfilled,
        failed=tuple(failures),
        outcomes=tuple(outcomes),
    )
