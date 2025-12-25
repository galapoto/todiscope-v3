"""
API endpoints for workflow state management.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.auth.dependencies import require_principal
from backend.app.core.auth.models import Principal
from backend.app.core.db import get_db_session
from backend.app.core.rbac.roles import Role
from backend.app.core.workflows.service import get_workflow_setting, set_workflow_strict_mode
from backend.app.core.workflows.state_machine import (
    create_workflow_state,
    get_workflow_state,
    transition_workflow_state,
    InvalidStateTransitionError,
    MissingPrerequisitesError,
)

router = APIRouter(prefix="/api/v3/workflow", tags=["workflow"])


@router.get("/settings")
async def get_workflow_settings_endpoint(
    workflow_id: str,
    db: AsyncSession = Depends(get_db_session),
    _: object = Depends(require_principal(Role.READ)),
) -> dict:
    """
    Get workflow settings for a workflow ID.
    
    Query parameters:
        - workflow_id: str (required)
    """
    if not workflow_id or not isinstance(workflow_id, str):
        raise HTTPException(status_code=400, detail="WORKFLOW_ID_REQUIRED")
    setting = await get_workflow_setting(db, workflow_id=workflow_id.strip())
    if setting is None:
        return {"workflow_id": workflow_id.strip(), "strict_mode": False, "updated_at": None}
    return {
        "workflow_id": setting.workflow_id,
        "strict_mode": setting.strict_mode,
        "updated_at": setting.updated_at.isoformat(),
    }


@router.post("/settings")
async def set_workflow_settings_endpoint(
    payload: dict,
    db: AsyncSession = Depends(get_db_session),
    _: object = Depends(require_principal(Role.ADMIN)),
) -> dict:
    """
    Update workflow settings for a workflow ID.
    
    Request body:
        - workflow_id: str (required)
        - strict_mode: bool (required)
    """
    workflow_id = payload.get("workflow_id")
    strict_mode = payload.get("strict_mode")
    if not workflow_id or not isinstance(workflow_id, str):
        raise HTTPException(status_code=400, detail="WORKFLOW_ID_REQUIRED")
    if strict_mode is None or not isinstance(strict_mode, bool):
        raise HTTPException(status_code=400, detail="STRICT_MODE_REQUIRED")
    setting = await set_workflow_strict_mode(
        db,
        workflow_id=workflow_id.strip(),
        strict_mode=bool(strict_mode),
    )
    return {
        "workflow_id": setting.workflow_id,
        "strict_mode": setting.strict_mode,
        "updated_at": setting.updated_at.isoformat(),
    }


@router.post("/state")
async def create_state_endpoint(
    payload: dict,
    db: AsyncSession = Depends(get_db_session),
    principal: object = Depends(require_principal(Role.INGEST)),
) -> dict:
    """
    Create initial workflow state for a subject.
    
    Request body:
        - dataset_version_id: str (required)
        - subject_type: str (required) - "finding", "report", "calculation"
        - subject_id: str (required)
        - initial_state: str (optional, default: "draft")
    
    Note: actor_id is extracted from the authenticated principal, not from the payload.
    """
    dataset_version_id = payload.get("dataset_version_id")
    subject_type = payload.get("subject_type")
    subject_id = payload.get("subject_id")
    initial_state = payload.get("initial_state", "draft")

    if not dataset_version_id or not isinstance(dataset_version_id, str):
        raise HTTPException(status_code=400, detail="DATASET_VERSION_ID_REQUIRED")
    if not subject_type or not isinstance(subject_type, str):
        raise HTTPException(status_code=400, detail="SUBJECT_TYPE_REQUIRED")
    if not subject_id or not isinstance(subject_id, str):
        raise HTTPException(status_code=400, detail="SUBJECT_ID_REQUIRED")

    # Extract actor_id from principal (not from payload)
    actor_id = getattr(principal, "subject", "system")

    try:
        state = await create_workflow_state(
            db,
            dataset_version_id=dataset_version_id.strip(),
            subject_type=subject_type.strip(),
            subject_id=subject_id.strip(),
            initial_state=initial_state.strip() if isinstance(initial_state, str) else "draft",
            actor_id=actor_id,
        )
        return {
            "workflow_state_id": state.workflow_state_id,
            "dataset_version_id": state.dataset_version_id,
            "subject_type": state.subject_type,
            "subject_id": state.subject_id,
            "current_state": state.current_state,
            "created_at": state.created_at.isoformat(),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"WORKFLOW_STATE_CREATION_FAILED: {str(e)}") from e


@router.get("/state")
async def get_state_endpoint(
    dataset_version_id: str,
    subject_type: str,
    subject_id: str,
    db: AsyncSession = Depends(get_db_session),
    _: object = Depends(require_principal(Role.INGEST)),
) -> dict:
    """
    Get current workflow state for a subject.
    
    Query parameters:
        - dataset_version_id: str (required)
        - subject_type: str (required)
        - subject_id: str (required)
    """
    if not dataset_version_id or not isinstance(dataset_version_id, str):
        raise HTTPException(status_code=400, detail="DATASET_VERSION_ID_REQUIRED")
    if not subject_type or not isinstance(subject_type, str):
        raise HTTPException(status_code=400, detail="SUBJECT_TYPE_REQUIRED")
    if not subject_id or not isinstance(subject_id, str):
        raise HTTPException(status_code=400, detail="SUBJECT_ID_REQUIRED")

    state = await get_workflow_state(
        db,
        dataset_version_id=dataset_version_id.strip(),
        subject_type=subject_type.strip(),
        subject_id=subject_id.strip(),
    )

    if state is None:
        raise HTTPException(status_code=404, detail="WORKFLOW_STATE_NOT_FOUND")

    return {
        "workflow_state_id": state.workflow_state_id,
        "dataset_version_id": state.dataset_version_id,
        "subject_type": state.subject_type,
        "subject_id": state.subject_id,
        "current_state": state.current_state,
        "created_at": state.created_at.isoformat(),
        "updated_at": state.updated_at.isoformat(),
    }


@router.post("/state/transition")
async def transition_state_endpoint(
    payload: dict,
    db: AsyncSession = Depends(get_db_session),
    principal: Principal = Depends(require_principal(Role.INGEST)),
) -> dict:
    """
    Transition workflow state with validation.
    
    Request body:
        - dataset_version_id: str (required)
        - subject_type: str (required)
        - subject_id: str (required)
        - to_state: str (required) - "draft", "review", "approved", "locked"
        - reason: str (optional)
    
    Notes:
        - actor identity is derived from the authenticated principal
        - transition prerequisites (evidence/approval) are derived and enforced by core
    """
    dataset_version_id = payload.get("dataset_version_id")
    subject_type = payload.get("subject_type")
    subject_id = payload.get("subject_id")
    to_state = payload.get("to_state")
    reason = payload.get("reason")

    if not dataset_version_id or not isinstance(dataset_version_id, str):
        raise HTTPException(status_code=400, detail="DATASET_VERSION_ID_REQUIRED")
    if not subject_type or not isinstance(subject_type, str):
        raise HTTPException(status_code=400, detail="SUBJECT_TYPE_REQUIRED")
    if not subject_id or not isinstance(subject_id, str):
        raise HTTPException(status_code=400, detail="SUBJECT_ID_REQUIRED")
    if not to_state or not isinstance(to_state, str):
        raise HTTPException(status_code=400, detail="TO_STATE_REQUIRED")

    normalized_to_state = to_state.strip()
    actor_roles = principal.roles or ()
    if normalized_to_state in ("approved", "locked") and Role.ADMIN.value not in actor_roles:
        raise HTTPException(status_code=403, detail="WORKFLOW_TRANSITION_FORBIDDEN")

    # Extract actor_id with consistent fallback pattern
    actor_id = getattr(principal, "subject", "system")

    try:
        state = await transition_workflow_state(
            db,
            dataset_version_id=dataset_version_id.strip(),
            subject_type=subject_type.strip(),
            subject_id=subject_id.strip(),
            to_state=normalized_to_state,
            actor_id=actor_id,
            actor_roles=actor_roles,
            reason=reason.strip() if reason else None,
        )
        return {
            "workflow_state_id": state.workflow_state_id,
            "dataset_version_id": state.dataset_version_id,
            "subject_type": state.subject_type,
            "subject_id": state.subject_id,
            "current_state": state.current_state,
            "updated_at": state.updated_at.isoformat(),
        }
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except MissingPrerequisitesError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"WORKFLOW_STATE_TRANSITION_FAILED: {str(e)}") from e
