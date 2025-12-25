"""
API endpoints for normalization workflow.

Provides endpoints for preview, validation, and commit of normalization operations.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.auth.dependencies import require_principal
from backend.app.core.audit.service import log_normalization_action
from backend.app.core.auth.models import Principal
from backend.app.core.db import get_db_session
from backend.app.core.rbac.roles import Role
from backend.app.core.normalization.workflow import (
    commit_normalization,
    preview_normalization,
    validate_normalization,
)

router = APIRouter(prefix="/api/v3/normalize", tags=["normalization"])


@router.post("/preview")
async def preview_normalization_endpoint(
    payload: dict,
    db: AsyncSession = Depends(get_db_session),
    principal: Principal = Depends(require_principal(Role.INGEST)),
) -> dict:
    """
    Preview normalization results without committing.
    
    Request body:
        - dataset_version_id: str (required)
        - preview_limit: int (optional, default: 10)
        - verify_checksums: bool (optional, default: true)
        - strict_mode: bool (optional, default: true)
    
    Returns:
        NormalizationPreview with preview records and warnings
    """
    dataset_version_id = payload.get("dataset_version_id")
    if not isinstance(dataset_version_id, str) or not dataset_version_id.strip():
        raise HTTPException(status_code=400, detail="DATASET_VERSION_ID_REQUIRED")

    preview_limit = payload.get("preview_limit", 10)
    if not isinstance(preview_limit, int) or preview_limit < 1:
        raise HTTPException(status_code=400, detail="PREVIEW_LIMIT_INVALID")

    verify_checksums = payload.get("verify_checksums", True)
    strict_mode = payload.get("strict_mode", True)

    try:
        preview = await preview_normalization(
            db,
            dataset_version_id=dataset_version_id.strip(),
            preview_limit=preview_limit,
            verify_checksums=bool(verify_checksums),
            strict_mode=bool(strict_mode),
        )
        await log_normalization_action(
            db,
            actor_id=getattr(principal, "subject", "system"),
            dataset_version_id=dataset_version_id.strip(),
            records_normalized=0,
            records_skipped=0,
            action_label="Normalize dataset preview",
            reason="Preview normalization output",
            context={
                "preview_limit": preview_limit,
                "warning_count": len(preview.warnings),
            },
            metadata={
                "warnings": [w.to_dict() for w in preview.warnings],
            },
        )
        return preview.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"NORMALIZATION_PREVIEW_FAILED: {str(e)}") from e


@router.post("/validate")
async def validate_normalization_endpoint(
    payload: dict,
    db: AsyncSession = Depends(get_db_session),
    principal: Principal = Depends(require_principal(Role.INGEST)),
) -> dict:
    """
    Validate normalization rules without committing.
    
    Request body:
        - dataset_version_id: str (required)
        - verify_checksums: bool (optional, default: true)
        - strict_mode: bool (optional, default: true)
    
    Returns:
        Validation result with is_valid flag and warnings
    """
    dataset_version_id = payload.get("dataset_version_id")
    if not isinstance(dataset_version_id, str) or not dataset_version_id.strip():
        raise HTTPException(status_code=400, detail="DATASET_VERSION_ID_REQUIRED")

    verify_checksums = payload.get("verify_checksums", True)
    strict_mode = payload.get("strict_mode", True)

    try:
        is_valid, warnings = await validate_normalization(
            db,
            dataset_version_id=dataset_version_id.strip(),
            verify_checksums=bool(verify_checksums),
            strict_mode=bool(strict_mode),
        )
        await log_normalization_action(
            db,
            actor_id=getattr(principal, "subject", "system"),
            dataset_version_id=dataset_version_id.strip(),
            records_normalized=0,
            records_skipped=0,
            action_label="Normalize dataset validation",
            reason="Validated normalization output",
            context={
                "is_valid": is_valid,
                "warning_count": len(warnings),
            },
            metadata={
                "warnings": [w.to_dict() for w in warnings],
            },
        )
        return {
            "dataset_version_id": dataset_version_id.strip(),
            "is_valid": is_valid,
            "warnings": [w.to_dict() for w in warnings],
            "warning_count": len(warnings),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"NORMALIZATION_VALIDATION_FAILED: {str(e)}") from e


@router.post("/commit")
async def commit_normalization_endpoint(
    payload: dict,
    db: AsyncSession = Depends(get_db_session),
    principal: Principal = Depends(require_principal(Role.INGEST)),
) -> dict:
    """
    Commit normalization to database.
    
    Request body:
        - dataset_version_id: str (required)
        - verify_checksums: bool (optional, default: true)
        - strict_mode: bool (optional, default: true)
        - skip_on_error: bool (optional, default: false)
    
    Returns:
        NormalizationResult with normalization statistics
    """
    dataset_version_id = payload.get("dataset_version_id")
    if not isinstance(dataset_version_id, str) or not dataset_version_id.strip():
        raise HTTPException(status_code=400, detail="DATASET_VERSION_ID_REQUIRED")

    verify_checksums = payload.get("verify_checksums", True)
    strict_mode = payload.get("strict_mode", True)
    skip_on_error = payload.get("skip_on_error", False)

    try:
        result = await commit_normalization(
            db,
            dataset_version_id=dataset_version_id.strip(),
            verify_checksums=bool(verify_checksums),
            strict_mode=bool(strict_mode),
            skip_on_error=bool(skip_on_error),
        )
        await log_normalization_action(
            db,
            actor_id=getattr(principal, "subject", "system"),
            dataset_version_id=result.normalized_dataset_version_id,
            records_normalized=result.records_normalized,
            records_skipped=result.records_skipped,
            metadata={
                "source_dataset_version_id": result.source_dataset_version_id,
                "normalized_dataset_version_id": result.normalized_dataset_version_id,
            },
        )
        return result.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"NORMALIZATION_COMMIT_FAILED: {str(e)}") from e
