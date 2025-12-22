from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from backend.app.core.auth.dependencies import require_principal
from backend.app.core.auth.models import Principal
from backend.app.core.engine_registry.kill_switch import is_engine_enabled
from backend.app.core.engine_registry.registry import REGISTRY
from backend.app.core.engine_registry.spec import EngineSpec
from backend.app.core.rbac.roles import Role
from backend.app.engines.enterprise_distressed_asset_debt_stress.constants import ENGINE_ID, ENGINE_VERSION

router = APIRouter(prefix="/api/v3/engines/distressed-asset-debt-stress", tags=[ENGINE_ID])
logger = logging.getLogger(__name__)


@router.post("/run")
async def run_endpoint(
    payload: dict,
    request: Request,
    principal: Principal = Depends(require_principal(Role.EXECUTE)),
) -> dict:
    """
    Execute the Enterprise Distressed Asset & Debt Stress Engine.
    
    **RBAC Requirements:**
    - Requires `EXECUTE` role for engine execution
    - Requires `READ` role for accessing DatasetVersion and normalized records (enforced at platform level)
    - `ADMIN` role has full access to all operations
    
    **Security:**
    - All operations are logged for audit purposes
    - DatasetVersion access is validated before processing
    - Evidence and findings are bound to DatasetVersion for access control
    """
    if not is_engine_enabled(ENGINE_ID):
        raise HTTPException(
            status_code=503,
            detail=(
                f"ENGINE_DISABLED: Engine {ENGINE_ID} is disabled. "
                "Enable via TODISCOPE_ENABLED_ENGINES environment variable."
            ),
        )

    from backend.app.engines.enterprise_distressed_asset_debt_stress.run import run_engine
    from backend.app.engines.enterprise_distressed_asset_debt_stress.errors import (
        DatasetVersionInvalidError,
        DatasetVersionMissingError,
        DatasetVersionNotFoundError,
        ImmutableConflictError,
        NormalizedRecordMissingError,
        StartedAtInvalidError,
        StartedAtMissingError,
    )

    try:
        request_id = request.headers.get("x-request-id")
        return await run_engine(
            dataset_version_id=payload.get("dataset_version_id"),
            started_at=payload.get("started_at"),
            parameters=payload.get("parameters"),
            actor_id=principal.subject,
            request_id=request_id,
        )
    except DatasetVersionMissingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except DatasetVersionInvalidError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except DatasetVersionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except NormalizedRecordMissingError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ImmutableConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except StartedAtMissingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except StartedAtInvalidError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("DISTRESSED_DEBT_ENGINE_ERROR error=%s", type(exc).__name__)
        raise HTTPException(status_code=500, detail=f"ENGINE_RUN_FAILED: {type(exc).__name__}: {exc}") from exc


@router.get("/health")
async def engine_health() -> dict:
    if not is_engine_enabled(ENGINE_ID):
        return {"status": "disabled", "engine_id": ENGINE_ID}
    return {"status": "ok", "engine_id": ENGINE_ID}


def register_engine() -> None:
    if REGISTRY.get(ENGINE_ID) is not None:
        return
    REGISTRY.register(
        EngineSpec(
            engine_id=ENGINE_ID,
            engine_version=ENGINE_VERSION,
            enabled_by_default=False,
            owned_tables=(),
            report_sections=("metadata", "debt_exposure", "stress_tests", "assumptions"),
            routers=(router,),
            run_entrypoint=None,
        )
    )
