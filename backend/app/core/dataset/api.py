from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.auth.dependencies import require_principal
from backend.app.core.db import get_db_session
from backend.app.core.ingestion.parsers import ParseError, parse_records
from backend.app.core.ingestion.service import ingest_records as ingest_records_service
from backend.app.core.rbac.roles import Role


router = APIRouter(prefix="/api/v3", tags=["ingest"])


@router.post("/ingest")
async def ingest_dataset(
    db: AsyncSession = Depends(get_db_session),
    _: object = Depends(require_principal(Role.INGEST)),
) -> dict:
    dataset_version_id, _ = await ingest_records_service(db, records=[], normalize=False)
    return {"dataset_version_id": dataset_version_id}


@router.post("/ingest-records")
async def ingest_records(
    payload: dict,
    db: AsyncSession = Depends(get_db_session),
    _: object = Depends(require_principal(Role.INGEST)),
) -> dict:
    """
    Generic ingestion endpoint that creates a DatasetVersion and stores raw records as JSON.
    Domain mapping happens in engines, not core.
    """
    records = payload.get("records")
    if not isinstance(records, list) or not records:
        raise HTTPException(status_code=400, detail="RECORDS_REQUIRED")
    normalize = bool(payload.get("normalize", False))
    try:
        dataset_version_id, written = await ingest_records_service(db, records=records, normalize=normalize)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"dataset_version_id": dataset_version_id, "raw_records_written": written}


@router.post("/ingest-file")
async def ingest_file(
    file: UploadFile = File(...),
    normalize: bool = False,
    db: AsyncSession = Depends(get_db_session),
    _: object = Depends(require_principal(Role.INGEST)),
) -> dict:
    content = await file.read()
    try:
        records = parse_records(filename=file.filename, content_type=file.content_type, content=content)
        dataset_version_id, written = await ingest_records_service(db, records=records, normalize=normalize)
    except ParseError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"dataset_version_id": dataset_version_id, "raw_records_written": written}
