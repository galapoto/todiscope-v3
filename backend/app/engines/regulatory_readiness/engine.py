from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.app.core.db import get_sessionmaker
from backend.app.core.dataset.errors import ChecksumMismatchError, ChecksumMissingError
from backend.app.core.engine_registry.kill_switch import is_engine_enabled, log_disabled_engine_attempt
from backend.app.core.engine_registry.registry import REGISTRY
from backend.app.core.engine_registry.spec import EngineSpec
from backend.app.core.lifecycle.enforcement import (
    LifecycleViolationError,
    verify_import_complete,
    verify_normalize_complete,
    record_calculation_completion,
)
from backend.app.engines.regulatory_readiness.constants import ENGINE_ID, ENGINE_VERSION
from backend.app.engines.regulatory_readiness.errors import (
    ControlPayloadInvalidError,
    DatasetVersionInvalidError,
    DatasetVersionMissingError,
    DatasetVersionNotFoundError,
    ImmutableConflictError,
    RawRecordsMissingError,
    StartedAtInvalidError,
    StartedAtMissingError,
)
from backend.app.engines.regulatory_readiness.run import _validate_dataset_version_id, run_engine

router = APIRouter(prefix="/api/v3/engines/regulatory-readiness", tags=[ENGINE_ID])


@router.post("/run")
async def run_endpoint(payload: dict) -> dict:
    if not is_engine_enabled(ENGINE_ID):
        dataset_version_id = payload.get("dataset_version_id")
        await log_disabled_engine_attempt(
            engine_id=ENGINE_ID,
            actor_id="system",
            attempted_action="run",
            dataset_version_id=dataset_version_id if isinstance(dataset_version_id, str) else None,
        )
        
        raise HTTPException(
            status_code=503,
            detail=(
                f"ENGINE_DISABLED: Engine {ENGINE_ID} is disabled. "
                "Enable via TODISCOPE_ENABLED_ENGINES environment variable."
            ),
        )

    try:
        validated_dv_id = _validate_dataset_version_id(payload.get("dataset_version_id"))
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as guard_db:
            await verify_import_complete(
                guard_db,
                dataset_version_id=validated_dv_id,
                engine_id=ENGINE_ID,
                actor_id=f"engine:{ENGINE_ID}",
                attempted_action="run",
            )
            await verify_normalize_complete(
                guard_db,
                dataset_version_id=validated_dv_id,
                engine_id=ENGINE_ID,
                actor_id=f"engine:{ENGINE_ID}",
                attempted_action="run",
            )

        result = await run_engine(
            dataset_version_id=validated_dv_id,
            started_at=payload.get("started_at"),
            parameters=payload.get("parameters"),
        )
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as db:
            run_id = await record_calculation_completion(
                db,
                dataset_version_id=validated_dv_id,
                engine_id=ENGINE_ID,
                engine_version=ENGINE_VERSION,
                parameter_payload=payload,
                started_at=payload.get("started_at"),
                actor_id=f"engine:{ENGINE_ID}",
            )
        if isinstance(result, dict):
            result.setdefault("dataset_version_id", validated_dv_id)
            result.setdefault("run_id", run_id)
            return result
        return {"dataset_version_id": validated_dv_id, "run_id": run_id, "result": result}
    except DatasetVersionMissingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except DatasetVersionInvalidError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except DatasetVersionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RawRecordsMissingError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ChecksumMissingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ChecksumMismatchError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ControlPayloadInvalidError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ImmutableConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except StartedAtMissingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except StartedAtInvalidError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LifecycleViolationError as exc:
        raise HTTPException(status_code=409, detail=exc.detail) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"ENGINE_RUN_FAILED: {type(exc).__name__}: {exc}") from exc


def register_engine() -> None:
    if REGISTRY.get(ENGINE_ID) is not None:
        return
    REGISTRY.register(
        EngineSpec(
            engine_id=ENGINE_ID,
            engine_version=ENGINE_VERSION,
            enabled_by_default=False,
            owned_tables=("regulatory_controls", "regulatory_gaps", "regulatory_remediation_tasks"),
            report_sections=(),
            routers=(router,),
            run_entrypoint=run_engine,
        )
    )
