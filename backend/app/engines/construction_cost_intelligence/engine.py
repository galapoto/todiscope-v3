from __future__ import annotations

"""
Construction Cost Intelligence Engine — Platform Runtime Integration

This module provides:
- FastAPI router endpoints
- EngineSpec registration hook (called only via backend/app/engines/__init__.py)
- Kill-switch enforcement (Platform Law #2: engines are detachable)
"""

from fastapi import APIRouter, HTTPException

from backend.app.core.engine_registry.kill_switch import is_engine_enabled
from backend.app.core.engine_registry.registry import REGISTRY
from backend.app.core.engine_registry.spec import EngineSpec
from backend.app.core.db import get_sessionmaker


ENGINE_ID = "engine_construction_cost_intelligence"
ENGINE_VERSION = "v1"


router = APIRouter(prefix="/api/v3/engines/cost-intelligence", tags=[ENGINE_ID])


def _require_enabled() -> None:
    if not is_engine_enabled(ENGINE_ID):
        raise HTTPException(
            status_code=503,
            detail=(
                f"ENGINE_DISABLED: Engine {ENGINE_ID} is disabled. "
                "Enable via TODISCOPE_ENABLED_ENGINES environment variable."
            ),
        )


@router.get("/ping")
async def ping() -> dict:
    _require_enabled()
    return {"ok": True, "engine_id": ENGINE_ID, "engine_version": ENGINE_VERSION}


@router.get("/status")
async def status() -> dict:
    _require_enabled()
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
    _require_enabled()

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
        return await run_engine(
            dataset_version_id=payload.get("dataset_version_id"),
            started_at=payload.get("started_at"),
            boq_raw_record_id=payload.get("boq_raw_record_id"),
            actual_raw_record_id=payload.get("actual_raw_record_id"),
            normalization_mapping=payload.get("normalization_mapping"),
            comparison_config=payload.get("comparison_config"),
        )
    except DatasetVersionMissingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except DatasetVersionInvalidError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except DatasetVersionMismatchError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except RawRecordMissingError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RawRecordInvalidError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except StartedAtMissingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except StartedAtInvalidError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
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
