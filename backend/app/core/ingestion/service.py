from __future__ import annotations

from datetime import datetime, timezone
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.dataset.raw_models import RawRecord
from backend.app.core.dataset.service import create_dataset_version_via_ingestion
from backend.app.core.normalization.models import NormalizedRecord
from backend.app.core.normalization.pipeline import normalize_payload


async def ingest_records(
    db: AsyncSession,
    *,
    records: list[dict],
    normalize: bool,
) -> tuple[str, int]:
    dv = await create_dataset_version_via_ingestion(db)
    now = datetime.now(timezone.utc)
    written = 0

    for item in records:
        if not isinstance(item, dict):
            raise ValueError("RECORD_INVALID_TYPE")
        source_system = item.get("source_system")
        source_record_id = item.get("source_record_id")
        if not isinstance(source_system, str) or not source_system.strip():
            raise ValueError("SOURCE_SYSTEM_REQUIRED")
        if not isinstance(source_record_id, str) or not source_record_id.strip():
            raise ValueError("SOURCE_RECORD_ID_REQUIRED")

        raw_id = str(uuid.uuid4())
        db.add(
            RawRecord(
                raw_record_id=raw_id,
                dataset_version_id=dv.id,
                source_system=source_system.strip(),
                source_record_id=source_record_id.strip(),
                payload=item,
                ingested_at=now,
            )
        )
        if normalize:
            db.add(
                NormalizedRecord(
                    normalized_record_id=str(uuid.uuid4()),
                    dataset_version_id=dv.id,
                    raw_record_id=raw_id,
                    payload=normalize_payload(item),  # type: ignore[arg-type]
                    normalized_at=now,
                )
            )
        written += 1

    await db.commit()
    return dv.id, written

