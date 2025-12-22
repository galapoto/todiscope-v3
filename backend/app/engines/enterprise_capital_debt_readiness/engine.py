from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.app.core.engine_registry.kill_switch import is_engine_enabled
from backend.app.core.engine_registry.registry import REGISTRY
from backend.app.core.engine_registry.spec import EngineSpec


ENGINE_ID = "engine_enterprise_capital_debt_readiness"
ENGINE_VERSION = "v1"


router = APIRouter(
    prefix="/api/v3/engines/enterprise-capital-debt-readiness",
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

    from backend.app.engines.enterprise_capital_debt_readiness.errors import (
        DatasetVersionInvalidError,
        DatasetVersionMissingError,
        DatasetVersionNotFoundError,
        ImmutableConflictError,
        RawRecordsMissingError,
        StartedAtInvalidError,
        StartedAtMissingError,
    )
    from backend.app.engines.enterprise_capital_debt_readiness.run import run_engine

    try:
        return await run_engine(
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
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ImmutableConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except StartedAtMissingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except StartedAtInvalidError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"ENGINE_RUN_FAILED: {type(exc).__name__}: {exc}") from exc


@router.post("/report")
async def report_endpoint(payload: dict) -> dict:
    """
    Generate comprehensive report from engine evidence records.
    
    Kill-Switch Revalidation:
    - Engine must be enabled before report generation
    - Disabled engine cannot create reports
    - Kill-switch check occurs before any side effects
    """
    if not is_engine_enabled(ENGINE_ID):
        raise HTTPException(
            status_code=503,
            detail=(
                f"ENGINE_DISABLED: Engine {ENGINE_ID} is disabled. "
                "Enable via TODISCOPE_ENABLED_ENGINES environment variable."
            ),
        )
    
    from backend.app.engines.enterprise_capital_debt_readiness.errors import (
        DatasetVersionInvalidError,
        DatasetVersionMissingError,
    )
    from backend.app.engines.enterprise_capital_debt_readiness.report.assembler import (
        DatasetVersionMismatchError,
        EvidenceNotFoundError,
        assemble_report,
    )
    from backend.app.engines.enterprise_capital_debt_readiness.run import (
        _validate_dataset_version_id,
    )
    from backend.app.core.db import get_sessionmaker
    
    dataset_version_id = payload.get("dataset_version_id")
    
    try:
        validated_dv_id = _validate_dataset_version_id(dataset_version_id)
    except DatasetVersionMissingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except DatasetVersionInvalidError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        try:
            return await assemble_report(
                db,
                dataset_version_id=validated_dv_id,
            )
        except EvidenceNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except DatasetVersionMismatchError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"REPORT_GENERATION_FAILED: {type(exc).__name__}: {exc}",
            ) from exc


def register_engine() -> None:
    if REGISTRY.get(ENGINE_ID) is not None:
        return
    REGISTRY.register(
        EngineSpec(
            engine_id=ENGINE_ID,
            engine_version=ENGINE_VERSION,
            enabled_by_default=False,
            owned_tables=(),
            report_sections=("capital_adequacy", "debt_service"),
            routers=(router,),
            run_entrypoint=None,
        )
    )

