from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.db import get_db_session
from backend.app.core.artifacts.fx_service import FxArtifactError, create_fx_artifact, load_fx_artifact


router = APIRouter(prefix="/api/v3/fx-artifacts", tags=["fx-artifacts"])


@router.post("")
async def create(payload: dict, db: AsyncSession = Depends(get_db_session)) -> dict:
    from datetime import datetime
    
    dataset_version_id = payload.get("dataset_version_id")
    base_currency = payload.get("base_currency")
    effective_date = payload.get("effective_date")
    rates = payload.get("rates")
    created_at_str = payload.get("created_at")
    
    if not isinstance(dataset_version_id, str) or not dataset_version_id.strip():
        raise HTTPException(status_code=400, detail="DATASET_VERSION_ID_REQUIRED")
    
    # created_at is required for determinism
    if not created_at_str:
        raise HTTPException(status_code=400, detail="CREATED_AT_REQUIRED: created_at is required for deterministic FX artifact creation")
    
    try:
        created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="CREATED_AT_INVALID_FORMAT: created_at must be ISO 8601 format with timezone")
    
    try:
        row = await create_fx_artifact(
            db,
            dataset_version_id=dataset_version_id,
            base_currency=base_currency,
            effective_date=effective_date,
            rates=rates,
            created_at=created_at,
        )
    except FxArtifactError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {
        "fx_artifact_id": row.fx_artifact_id,
        "dataset_version_id": row.dataset_version_id,
        "base_currency": row.base_currency,
        "effective_date": row.effective_date,
        "checksum": row.checksum,
        "artifact_uri": row.artifact_uri,
    }


@router.get("/{fx_artifact_id}")
async def get(fx_artifact_id: str, db: AsyncSession = Depends(get_db_session)) -> dict:
    try:
        row, payload = await load_fx_artifact(db, fx_artifact_id=fx_artifact_id)
    except FxArtifactError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {
        "fx_artifact_id": row.fx_artifact_id,
        "dataset_version_id": row.dataset_version_id,
        "checksum": row.checksum,
        "payload": payload,
    }

