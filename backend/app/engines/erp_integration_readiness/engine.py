"""
ERP System Integration Readiness Engine

Build Task scope:
- ERP system readiness assessment is a runtime parameter persisted in engine-owned run table.
- Run parameters are runtime parameters persisted in engine-owned run table (not DatasetVersion).
- DatasetVersion is immutable data-only anchor (UUIDv7).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.app.core.engine_registry.kill_switch import is_engine_enabled
from backend.app.core.engine_registry.registry import REGISTRY
from backend.app.core.engine_registry.spec import EngineSpec


ENGINE_ID = "engine_erp_integration_readiness"
ENGINE_VERSION = "v1"


router = APIRouter(
    prefix="/api/v3/engines/erp-integration-readiness",
    tags=[ENGINE_ID],
)


@router.post("/run")
async def run_engine_endpoint(payload: dict) -> dict:
    if not is_engine_enabled(ENGINE_ID):
        raise HTTPException(
            status_code=503,
            detail=(
                f"ENGINE_DISABLED: Engine {ENGINE_ID} is disabled. "
                "Enable via TODISCOPE_ENABLED_ENGINES environment variable."
            ),
        )

    from backend.app.engines.erp_integration_readiness.errors import (
        DatasetVersionInvalidError,
        DatasetVersionMissingError,
        DatasetVersionNotFoundError,
        EngineDisabledError,
        ParametersInvalidError,
        ParametersMissingError,
        StartedAtInvalidError,
        StartedAtMissingError,
        ErpSystemConfigInvalidError,
        ErpSystemConfigMissingError,
    )
    from backend.app.engines.erp_integration_readiness.run import run_engine

    try:
        return await run_engine(
            dataset_version_id=payload.get("dataset_version_id"),
            started_at=payload.get("started_at"),
            erp_system_config=payload.get("erp_system_config"),
            parameters=payload.get("parameters"),
            optional_inputs=payload.get("optional_inputs"),
        )
    except EngineDisabledError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except DatasetVersionMissingError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except DatasetVersionInvalidError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except DatasetVersionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ErpSystemConfigMissingError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ErpSystemConfigInvalidError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ParametersMissingError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ParametersInvalidError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except StartedAtMissingError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except StartedAtInvalidError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"ENGINE_RUN_FAILED: {type(exc).__name__}: {exc}")


def register_engine() -> None:
    if REGISTRY.get(ENGINE_ID) is not None:
        return
    REGISTRY.register(
        EngineSpec(
            engine_id=ENGINE_ID,
            engine_version=ENGINE_VERSION,
            enabled_by_default=False,
            owned_tables=(
                "engine_erp_integration_readiness_runs",
                "engine_erp_integration_readiness_findings",
            ),
            report_sections=(),
            routers=(router,),
            run_entrypoint=None,
        )
    )


