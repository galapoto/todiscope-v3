from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.artifacts.checksums import sha256_hex
from backend.app.core.dataset.raw_models import RawRecord
from backend.app.core.dataset.service import create_dataset_version_via_ingestion
from backend.app.core.dataset.uuidv7 import uuid7
from backend.app.core.ingestion.models import Import
from backend.app.core.normalization.models import NormalizedRecord
from backend.app.core.normalization.pipeline import normalize_payload


@dataclass(frozen=True)
class ImportContext:
    filename: str | None = None
    content_type: str | None = None
    raw_content: bytes | None = None
    raw_payload: dict | None = None


def _hash_bytes(content: bytes) -> str:
    """Compute SHA256 hash of bytes using the standard checksum utility."""
    return sha256_hex(content)


def _hash_payload(payload: object) -> str:
    """Compute SHA256 hash of a JSON-serializable payload."""
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return _hash_bytes(encoded)


def _hash_record_payload(record: dict) -> str:
    """Compute SHA256 hash of an individual record payload."""
    encoded = json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256_hex(encoded)


def _quality_report(records: list[dict]) -> dict:
    seen: set[tuple[str, str]] = set()
    duplicate_keys = 0
    for item in records:
        if not isinstance(item, dict):
            continue
        source_system = item.get("source_system")
        source_record_id = item.get("source_record_id")
        if not isinstance(source_system, str) or not isinstance(source_record_id, str):
            continue
        key = (source_system.strip(), source_record_id.strip())
        if key in seen:
            duplicate_keys += 1
        else:
            seen.add(key)
    warnings = []
    if duplicate_keys:
        warnings.append("DUPLICATE_SOURCE_KEYS")
    return {
        "records_total": len(records),
        "duplicate_source_keys": duplicate_keys,
        "warnings": warnings,
    }


def _build_import_record(
    *,
    dataset_version_id: str,
    import_id: str,
    records: list[dict],
    context: ImportContext | None,
    created_at: datetime,
) -> Import:
    if context and context.raw_content is not None:
        checksum = _hash_bytes(context.raw_content)
        raw_content = context.raw_content
        raw_payload = None
        byte_size = len(context.raw_content)
    else:
        raw_payload = context.raw_payload if context else {"records": records}
        checksum = _hash_payload(raw_payload)
        raw_content = None
        byte_size = len(json.dumps(raw_payload, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    return Import(
        import_id=import_id,
        dataset_version_id=dataset_version_id,
        filename=context.filename if context else None,
        content_type=context.content_type if context else None,
        byte_size=byte_size,
        checksum_algorithm="sha256",
        checksum_sha256=checksum,
        record_count=len(records),
        raw_content=raw_content,
        raw_payload=raw_payload,
        quality_report=_quality_report(records),
        created_at=created_at,
    )


async def ingest_records(
    db: AsyncSession,
    *,
    records: list[dict],
    normalize: bool = False,  # Default to False - normalization should be explicit
    import_context: ImportContext | None = None,
    actor_id: str | None = None,  # Actor ID for audit and workflow state
) -> tuple[str, str, int, dict]:
    """
    Ingest raw records into the system.
    
    Note: The `normalize` parameter only performs basic key normalization (non-domain-specific).
    For engine-specific normalization, use the explicit normalization workflow API endpoints:
    - POST /api/v3/normalization/preview
    - POST /api/v3/normalization/validate
    - POST /api/v3/normalization/commit
    """
    dv = await create_dataset_version_via_ingestion(db)
    now = datetime.now(timezone.utc)
    written = 0
    import_id = str(uuid7())
    import_record = _build_import_record(
        dataset_version_id=dv.id,
        import_id=import_id,
        records=records,
        context=import_context,
        created_at=now,
    )
    db.add(import_record)

    for item in records:
        if not isinstance(item, dict):
            raise ValueError("RECORD_INVALID_TYPE")
        source_system = item.get("source_system")
        source_record_id = item.get("source_record_id")
        if not isinstance(source_system, str) or not source_system.strip():
            raise ValueError("SOURCE_SYSTEM_REQUIRED")
        if not isinstance(source_record_id, str) or not source_record_id.strip():
            raise ValueError("SOURCE_RECORD_ID_REQUIRED")

        # Store a deterministic checksum of the raw payload for integrity checks.
        record_checksum = _hash_record_payload(item)

        raw_id = str(uuid.uuid4())
        db.add(
            RawRecord(
                raw_record_id=raw_id,
                dataset_version_id=dv.id,
                source_system=source_system.strip(),
                source_record_id=source_record_id.strip(),
                payload=item,
                file_checksum=record_checksum,
                legacy_no_checksum=False,
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
    
    # Record import completion in workflow state machine (authoritative source)
    from backend.app.core.lifecycle.enforcement import record_import_completion
    await record_import_completion(
        db,
        dataset_version_id=dv.id,
        actor_id=actor_id,  # Use provided actor_id or None for system-initiated
    )
    
    return dv.id, import_id, written, import_record.quality_report
