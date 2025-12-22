
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.app.engines.data_migration_readiness.errors import (
    ConfigurationLoadError,
    DatasetVersionInvalidError,
    DatasetVersionMissingError,
    DatasetVersionNotFoundError,
    RawRecordsMissingError,
    StartedAtInvalidError,
    StartedAtMissingError,
)
from backend.app.engines.data_migration_readiness.run import run_readiness_check
from backend.app.core.engine_registry.kill_switch import is_engine_enabled
from backend.app.core.engine_registry.registry import REGISTRY
from backend.app.core.engine_registry.spec import EngineSpec


ENGINE_ID = "engine_data_migration_readiness"
ENGINE_VERSION = "v1"


router = APIRouter(
    prefix="/api/v3/engines/data-migration-readiness",
    tags=[ENGINE_ID],
)


@router.post("/run")
async def run_endpoint(payload: dict) -> dict:
    if not is_engine_enabled(ENGINE_ID):
        raise HTTPException(
            status_code=503,
            detail=(
                f"ENGINE_DISABLED: Engine {ENGINE_ID} is disabled. "
                "Enable via TODISCOPE_ENABLED_ENGINES environment variable."
            ),
        )

    try:
        return await run_readiness_check(
            dataset_version_id=payload.get("dataset_version_id"),
            started_at=payload.get("started_at"),
            parameters=payload.get("parameters"),
        )
    except DatasetVersionMissingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except DatasetVersionInvalidError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except DatasetVersionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RawRecordsMissingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except StartedAtMissingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except StartedAtInvalidError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ConfigurationLoadError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"ENGINE_RUN_FAILED: {type(exc).__name__}: {exc}",
        ) from exc


def register_engine() -> None:
    if REGISTRY.get(ENGINE_ID) is not None:
        return
    REGISTRY.register(
        EngineSpec(
            engine_id=ENGINE_ID,
            engine_version=ENGINE_VERSION,
            enabled_by_default=False,
            owned_tables=(
                "engine_data_migration_readiness_runs",
                "engine_data_migration_readiness_findings",
            ),
            report_sections=(),
            routers=(router,),
            run_entrypoint=None,
        )
    )
