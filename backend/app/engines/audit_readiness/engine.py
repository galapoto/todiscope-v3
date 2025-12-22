"""
Engine HTTP endpoint for Audit Readiness Engine
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.app.core.engine_registry.kill_switch import is_engine_enabled
from backend.app.core.engine_registry.registry import REGISTRY
from backend.app.core.engine_registry.spec import EngineSpec
from backend.app.engines.audit_readiness.errors import (
    ControlCatalogError,
    DatasetVersionInvalidError,
    DatasetVersionMissingError,
    DatasetVersionNotFoundError,
    EvidenceStorageError,
    RawRecordsMissingError,
    RegulatoryFrameworkNotFoundError,
    StartedAtInvalidError,
    StartedAtMissingError,
)

ENGINE_ID = "engine_audit_readiness"
ENGINE_VERSION = "v1"

router = APIRouter(prefix="/api/v3/engines/audit-readiness", tags=[ENGINE_ID])


@router.post("/run")
async def run_endpoint(payload: dict) -> dict:
    """Run audit readiness evaluation."""
    if not is_engine_enabled(ENGINE_ID):
        raise HTTPException(
            status_code=503,
            detail=(
                f"ENGINE_DISABLED: Engine {ENGINE_ID} is disabled. "
                "Enable via TODISCOPE_ENABLED_ENGINES environment variable."
            ),
        )
    
    from backend.app.engines.audit_readiness.run import run_engine
    
    try:
        return await run_engine(
            dataset_version_id=payload.get("dataset_version_id"),
            started_at=payload.get("started_at"),
            regulatory_frameworks=payload.get("regulatory_frameworks"),
            control_catalog=payload.get("control_catalog"),
            evaluation_scope=payload.get("evaluation_scope"),
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
    except StartedAtMissingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except StartedAtInvalidError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RegulatoryFrameworkNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ControlCatalogError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except EvidenceStorageError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"ENGINE_RUN_FAILED: {type(exc).__name__}: {exc}") from exc


def register_engine() -> None:
    """Register the audit readiness engine."""
    if REGISTRY.get(ENGINE_ID) is not None:
        return
    REGISTRY.register(
        EngineSpec(
            engine_id=ENGINE_ID,
            engine_version=ENGINE_VERSION,
            enabled_by_default=False,
            owned_tables=(
                "audit_readiness_runs",
            ),
            report_sections=(
                "regulatory_readiness",
                "control_gaps",
                "risk_assessment",
                "evidence_coverage",
            ),
            routers=(router,),
            run_entrypoint=None,
        )
    )

