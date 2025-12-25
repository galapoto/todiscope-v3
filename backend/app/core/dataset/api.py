from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.artifacts.checksums import sha256_hex, verify_sha256
from backend.app.core.auth.dependencies import require_principal
from backend.app.core.dataset.backfill import backfill_raw_record_checksums, flag_legacy_no_checksum_records
from backend.app.core.db import get_db_session
from backend.app.core.ingestion.parsers import ParseError, parse_records
from backend.app.core.ingestion.service import ImportContext, ingest_records as ingest_records_service
from backend.app.core.rbac.roles import Role


router = APIRouter(prefix="/api/v3", tags=["ingest"])


@router.post("/ingest")
async def ingest_dataset(
    db: AsyncSession = Depends(get_db_session),
    principal: object = Depends(require_principal(Role.INGEST)),
) -> dict:
    dataset_version_id, import_id, _, quality = await ingest_records_service(
        db,
        records=[],
        normalize=False,
        import_context=ImportContext(raw_payload={"records": []}),
    )
    from backend.app.core.audit.service import log_import_action
    await log_import_action(
        db,
        actor_id=getattr(principal, "subject", "system"),
        dataset_version_id=dataset_version_id,
        import_id=import_id,
        record_count=0,
    )
    return {
        "dataset_version_id": dataset_version_id,
        "import_id": import_id,
        "data_quality": quality,
    }


@router.post("/ingest-records")
async def ingest_records(
    payload: dict,
    db: AsyncSession = Depends(get_db_session),
    principal: object = Depends(require_principal(Role.INGEST)),
) -> dict:
    """
    Generic ingestion endpoint that creates a DatasetVersion and stores raw records as JSON.
    Domain mapping happens in engines, not core.
    """
    records = payload.get("records")
    if not isinstance(records, list) or not records:
        raise HTTPException(status_code=400, detail="RECORDS_REQUIRED")
    normalize = bool(payload.get("normalize", False))
    if normalize:
        raise HTTPException(status_code=400, detail="NORMALIZATION_NOT_ALLOWED_USE_NORMALIZE_ENDPOINTS")
    try:
        dataset_version_id, import_id, written, quality = await ingest_records_service(
            db,
            records=records,
            normalize=False,
            import_context=ImportContext(raw_payload=payload),
        )
        from backend.app.core.audit.service import log_import_action
        await log_import_action(
            db,
            actor_id=getattr(principal, "subject", "system"),
            dataset_version_id=dataset_version_id,
            import_id=import_id,
            record_count=written,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {
        "dataset_version_id": dataset_version_id,
        "import_id": import_id,
        "raw_records_written": written,
        "data_quality": quality,
    }


@router.post("/ingest-file")
async def ingest_file(
    file: UploadFile = File(...),
    normalize: bool = False,
    expected_checksum: str | None = Query(None, description="Optional SHA256 checksum to verify against uploaded file"),
    source_system: str | None = Query(None, description="Optional default source_system to apply when missing in records"),
    db: AsyncSession = Depends(get_db_session),
    principal: object = Depends(require_principal(Role.INGEST)),
) -> dict:
    """
    Ingest a file and store raw records with file integrity checks.
    
    Args:
        file: The file to ingest (JSON, CSV, or NDJSON)
        normalize: Whether to normalize records during ingestion
        expected_checksum: Optional SHA256 checksum to verify against uploaded file
        db: Database session
        _: Authenticated principal with INGEST role
    
    Returns:
        Dictionary containing dataset_version_id, import_id, raw_records_written, and data_quality
    
    Raises:
        HTTPException: If file parsing fails, validation fails, or checksum mismatch
    """
    content = await file.read()
    
    # Compute checksum of uploaded file content
    computed_checksum = sha256_hex(content)
    
    # Verify checksum if expected_checksum is provided
    if expected_checksum is not None:
        try:
            verify_sha256(content, expected_checksum)
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=f"FILE_CHECKSUM_MISMATCH: {str(e)}. Expected: {expected_checksum}, Computed: {computed_checksum}",
            ) from e
    
    if normalize:
        raise HTTPException(status_code=400, detail="NORMALIZATION_NOT_ALLOWED_USE_NORMALIZE_ENDPOINTS")
    try:
        records = parse_records(filename=file.filename, content_type=file.content_type, content=content)
        if source_system and isinstance(source_system, str) and source_system.strip():
            safe_source = source_system.strip()
            for index, record in enumerate(records, start=1):
                if not isinstance(record, dict):
                    continue
                if not record.get("source_system"):
                    record["source_system"] = safe_source
                if not record.get("source_record_id"):
                    record["source_record_id"] = f"{safe_source}-{index}"
        actor_id = getattr(principal, "subject", "system")
        dataset_version_id, import_id, written, quality = await ingest_records_service(
            db,
            records=records,
            normalize=False,
            import_context=ImportContext(
                filename=file.filename,
                content_type=file.content_type,
                raw_content=content,
            ),
            actor_id=actor_id,
        )
        from backend.app.core.audit.service import log_import_action
        await log_import_action(
            db,
            actor_id=getattr(principal, "subject", "system"),
            dataset_version_id=dataset_version_id,
            import_id=import_id,
            record_count=written,
        )
    except ParseError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    
    return {
        "dataset_version_id": dataset_version_id,
        "import_id": import_id,
        "raw_records_written": written,
        "data_quality": quality,
        "file_checksum": computed_checksum,
    }


@router.post("/raw-records/flag-legacy-missing-checksums")
async def flag_legacy_missing_checksums(
    db: AsyncSession = Depends(get_db_session),
    principal: object = Depends(require_principal(Role.INGEST)),
) -> dict:
    flagged = await flag_legacy_no_checksum_records(db)
    from backend.app.core.audit.service import log_action
    actor_id = getattr(principal, "subject", "system")
    user_context = {
        "actor_id": actor_id,
        "roles": list(getattr(principal, "roles", []) or []),
    }
    for record in flagged:
        await log_action(
            db,
            actor_id=actor_id,
            actor_type="user",
            action_type="integrity",
            action_label="Flag legacy missing checksums",
            dataset_version_id=record.dataset_version_id,
            reason="Flagged RawRecord entry with missing checksum as legacy",
            context={
                "raw_record_id": record.raw_record_id,
                "checksum_status": "legacy_missing",
                "user_context": user_context,
            },
            status="warning",
        )
    return {"legacy_no_checksum_flagged": len(flagged)}


@router.post("/raw-records/backfill-checksums")
async def backfill_checksums(
    payload: dict,
    db: AsyncSession = Depends(get_db_session),
    principal: object = Depends(require_principal(Role.INGEST)),
) -> dict:
    batch_size = payload.get("batch_size", 500)
    if not isinstance(batch_size, int) or batch_size <= 0:
        raise HTTPException(status_code=400, detail="BATCH_SIZE_INVALID")
    report = await backfill_raw_record_checksums(db, batch_size=batch_size)
    from backend.app.core.audit.service import log_action
    actor_id = getattr(principal, "subject", "system")
    user_context = {
        "actor_id": actor_id,
        "roles": list(getattr(principal, "roles", []) or []),
    }
    for outcome in report.outcomes:
        status = "success" if outcome.checksum_status == "backfilled" else "warning"
        await log_action(
            db,
            actor_id=actor_id,
            actor_type="user",
            action_type="maintenance",
            action_label="Backfill raw-record checksums",
            dataset_version_id=outcome.dataset_version_id,
            reason=outcome.reason or "Backfilled RawRecord checksum",
            context={
                "raw_record_id": outcome.raw_record_id,
                "checksum_status": outcome.checksum_status,
                "user_context": user_context,
            },
            status=status,
            error_message=outcome.reason,
        )
    return {
        "total_missing": report.total_missing,
        "flagged_legacy": report.flagged_legacy,
        "backfilled": report.backfilled,
        "failed": [
            {
                "raw_record_id": failure.raw_record_id,
                "dataset_version_id": failure.dataset_version_id,
                "reason": failure.reason,
            }
            for failure in report.failed
        ],
    }
