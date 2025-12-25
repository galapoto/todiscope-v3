from __future__ import annotations

"""
Construction Cost Intelligence Engine — Platform Runtime Integration

This module provides:
- FastAPI router endpoints
- EngineSpec registration hook (called only via backend/app/engines/__init__.py)
- Kill-switch enforcement (Platform Law #2: engines are detachable)
"""

from fastapi import APIRouter, HTTPException

from backend.app.core.dataset.errors import ChecksumMismatchError, ChecksumMissingError
from backend.app.core.engine_registry.kill_switch import is_engine_enabled, log_disabled_engine_attempt
from backend.app.core.engine_registry.registry import REGISTRY
from backend.app.core.engine_registry.spec import EngineSpec
from backend.app.core.db import get_sessionmaker
from backend.app.core.lifecycle.enforcement import (
    LifecycleViolationError,
    verify_calculate_complete,
    verify_import_complete,
    verify_normalize_complete,
    record_calculation_completion,
)


ENGINE_ID = "engine_construction_cost_intelligence"
ENGINE_VERSION = "v1"


router = APIRouter(prefix="/api/v3/engines/cost-intelligence", tags=[ENGINE_ID])


async def _require_enabled(payload: dict | None = None) -> None:
    if not is_engine_enabled(ENGINE_ID):
        dataset_version_id = payload.get("dataset_version_id") if payload else None
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


@router.get("/ping")
async def ping() -> dict:
    await _require_enabled()
    return {"ok": True, "engine_id": ENGINE_ID, "engine_version": ENGINE_VERSION}


@router.get("/status")
async def status() -> dict:
    await _require_enabled()
    return {"status": "enabled", "engine_id": ENGINE_ID, "engine_version": ENGINE_VERSION}


@router.post("")
async def run_default_endpoint(payload: dict) -> dict:
    """
    Default engine entrypoint.

    For platform compatibility, this is an alias of POST /run.
    """
    return await run_endpoint(payload)


@router.post("/run")
async def run_endpoint(payload: dict) -> dict:
    """
    Run core comparison + traceability materialization.

    Required payload keys:
      - dataset_version_id (UUIDv7 string)
      - started_at (ISO datetime)
      - boq_raw_record_id
      - actual_raw_record_id
      - normalization_mapping (dict)
      - comparison_config (dict)
    """
    await _require_enabled(payload)

    from backend.app.engines.construction_cost_intelligence.errors import (
        DatasetVersionInvalidError,
        DatasetVersionMismatchError,
        DatasetVersionMissingError,
        RawRecordInvalidError,
        RawRecordMissingError,
        StartedAtInvalidError,
        StartedAtMissingError,
    )
    from backend.app.engines.construction_cost_intelligence.run import run_engine

    try:
        dataset_version_id = payload.get("dataset_version_id")
        validated_dv_id = dataset_version_id.strip() if isinstance(dataset_version_id, str) else dataset_version_id

        sessionmaker = get_sessionmaker()
        async with sessionmaker() as guard_db:
            await verify_import_complete(
                guard_db,
                dataset_version_id=str(validated_dv_id),
                engine_id=ENGINE_ID,
                actor_id=f"engine:{ENGINE_ID}",
                attempted_action="run",
            )
            await verify_normalize_complete(
                guard_db,
                dataset_version_id=str(validated_dv_id),
                engine_id=ENGINE_ID,
                actor_id=f"engine:{ENGINE_ID}",
                attempted_action="run",
            )

        result = await run_engine(
            dataset_version_id=validated_dv_id,
            started_at=payload.get("started_at"),
            boq_raw_record_id=payload.get("boq_raw_record_id"),
            actual_raw_record_id=payload.get("actual_raw_record_id"),
            normalization_mapping=payload.get("normalization_mapping"),
            comparison_config=payload.get("comparison_config"),
        )
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as db:
            run_id = await record_calculation_completion(
                db,
                dataset_version_id=str(validated_dv_id),
                engine_id=ENGINE_ID,
                engine_version=ENGINE_VERSION,
                parameter_payload=payload,
                started_at=payload.get("started_at"),
                actor_id=f"engine:{ENGINE_ID}",
            )
        if isinstance(result, dict):
            result.setdefault("dataset_version_id", str(validated_dv_id))
            result.setdefault("run_id", run_id)
            return result
        return {"dataset_version_id": str(validated_dv_id), "run_id": run_id, "result": result}
    except DatasetVersionMissingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except DatasetVersionInvalidError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except DatasetVersionMismatchError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except RawRecordMissingError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ChecksumMissingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ChecksumMismatchError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RawRecordInvalidError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except StartedAtMissingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except StartedAtInvalidError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LifecycleViolationError as exc:
        raise HTTPException(status_code=409, detail=exc.detail) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"ENGINE_RUN_FAILED: {type(exc).__name__}: {exc}") from exc


@router.post("/report")
async def report_endpoint(payload: dict) -> dict:
    """
    Assemble a report (cost_variance or time_phased) with optional core traceability linkage.

    Required payload keys:
      - dataset_version_id
      - run_id
      - report_type: "cost_variance" | "time_phased"
      - parameters: dict (see report/README.md)

    Notes:
      - To include core traceability in report output, provide parameters.core_traceability
        using the `traceability` object returned by POST /run.
      - This endpoint does not persist engine-owned run state; it is a pure assembly call.
    """
    _require_enabled()

    dataset_version_id = payload.get("dataset_version_id")
    run_id = payload.get("run_id")
    report_type = payload.get("report_type")
    parameters = payload.get("parameters") if isinstance(payload.get("parameters"), dict) else {}

    if not isinstance(dataset_version_id, str) or not dataset_version_id.strip():
        raise HTTPException(status_code=400, detail="DATASET_VERSION_ID_REQUIRED")
    if not isinstance(run_id, str) or not run_id.strip():
        raise HTTPException(status_code=400, detail="RUN_ID_REQUIRED")
    if report_type not in ("cost_variance", "time_phased"):
        raise HTTPException(status_code=400, detail="REPORT_TYPE_INVALID")

    from backend.app.engines.construction_cost_intelligence.report.assembler import assemble_report

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        try:
            await verify_calculate_complete(
                db,
                dataset_version_id=dataset_version_id.strip(),
                run_id=run_id.strip(),
                engine_id=ENGINE_ID,
                actor_id=f"engine:{ENGINE_ID}",
            )
            return await assemble_report(
                db,
                dataset_version_id=dataset_version_id.strip(),
                run_id=run_id.strip(),
                report_type=report_type,
                parameters=parameters,
                emit_evidence=bool(payload.get("emit_evidence", True)),
            )
        except HTTPException:
            raise
        except LifecycleViolationError as exc:
            raise HTTPException(status_code=409, detail=exc.detail) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"REPORT_ASSEMBLY_FAILED: {type(exc).__name__}: {exc}") from exc


def register_engine() -> None:
    if REGISTRY.get(ENGINE_ID) is not None:
        return
    REGISTRY.register(
        EngineSpec(
            engine_id=ENGINE_ID,
            engine_version=ENGINE_VERSION,
            enabled_by_default=False,
            owned_tables=(),
            report_sections=(
                "executive_summary",
                "variance_summary_by_severity",
                "variance_summary_by_category",
                "cost_variances",
                "time_phased_report",
                "limitations_assumptions",
                "core_traceability",
                "evidence_index",
            ),
            routers=(router,),
            run_entrypoint=None,
        )
    )
