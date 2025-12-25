from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from backend.app.core.auth.dependencies import require_principal
from backend.app.core.auth.models import Principal
from backend.app.core.db import get_sessionmaker
from backend.app.core.engine_registry.kill_switch import is_engine_enabled
from backend.app.core.engine_registry.registry import REGISTRY
from backend.app.core.engine_registry.spec import EngineSpec
from backend.app.core.lifecycle.enforcement import (
    LifecycleViolationError,
    verify_import_complete,
    verify_normalize_complete,
    record_calculation_completion,
)
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
        from backend.app.core.engine_registry.kill_switch import log_disabled_engine_attempt
        
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
    from backend.app.engines.enterprise_distressed_asset_debt_stress.run import _validate_dataset_version_id

    try:
        validated_dv_id = _validate_dataset_version_id(payload.get("dataset_version_id"))
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as guard_db:
            await verify_import_complete(
                guard_db,
                dataset_version_id=validated_dv_id,
                engine_id=ENGINE_ID,
                actor_id=principal.subject,
                attempted_action="run",
            )
            await verify_normalize_complete(
                guard_db,
                dataset_version_id=validated_dv_id,
                engine_id=ENGINE_ID,
                actor_id=principal.subject,
                attempted_action="run",
            )

        request_id = request.headers.get("x-request-id")
        result = await run_engine(
            dataset_version_id=validated_dv_id,
            started_at=payload.get("started_at"),
            parameters=payload.get("parameters"),
            actor_id=principal.subject,
            request_id=request_id,
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
                actor_id=principal.subject,
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
    except NormalizedRecordMissingError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ImmutableConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except StartedAtMissingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except StartedAtInvalidError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LifecycleViolationError as exc:
        raise HTTPException(status_code=409, detail=exc.detail) from exc
    except Exception as exc:
        logger.exception("DISTRESSED_DEBT_ENGINE_ERROR error=%s", type(exc).__name__)
        raise HTTPException(status_code=500, detail=f"ENGINE_RUN_FAILED: {type(exc).__name__}: {exc}") from exc


@router.post("/report")
async def report_endpoint(
    payload: dict,
    principal: Principal = Depends(require_principal(Role.EXECUTE)),
) -> dict:
    """
    Generate distressed asset & debt stress report from engine run results.
    
    **RBAC Requirements:**
    - Requires `EXECUTE` role for report generation
    - `ADMIN` role has full access to all operations
    
    **Report Sections:**
    - metadata: Run metadata and parameters
    - debt_exposure: Debt exposure analysis
    - stress_tests: Stress test scenario results
    - assumptions: Scenario assumptions and parameters
    """
    if not is_engine_enabled(ENGINE_ID):
        from backend.app.core.engine_registry.kill_switch import log_disabled_engine_attempt
        
        dataset_version_id = payload.get("dataset_version_id")
        await log_disabled_engine_attempt(
            engine_id=ENGINE_ID,
            actor_id="system",
            attempted_action="report",
            dataset_version_id=dataset_version_id if isinstance(dataset_version_id, str) else None,
        )
        
        raise HTTPException(
            status_code=503,
            detail=(
                f"ENGINE_DISABLED: Engine {ENGINE_ID} is disabled. "
                "Enable via TODISCOPE_ENABLED_ENGINES environment variable."
            ),
        )

    from backend.app.engines.enterprise_distressed_asset_debt_stress.run import _validate_dataset_version_id
    from backend.app.core.lifecycle.enforcement import verify_calculate_complete, LifecycleViolationError

    dataset_version_id = payload.get("dataset_version_id")
    run_id = payload.get("run_id")
    parameters = payload.get("parameters") or {}
    report_type = parameters.get("report_type", "standard")  # standard, granular, aggregated

    # Validate inputs
    try:
        validated_dv_id = _validate_dataset_version_id(dataset_version_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not isinstance(run_id, str) or not run_id.strip():
        raise HTTPException(status_code=400, detail="RUN_ID_REQUIRED")

    try:
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as db:
            # Verify calculation is complete
            await verify_calculate_complete(
                db,
                dataset_version_id=validated_dv_id,
                run_id=run_id.strip(),
                engine_id=ENGINE_ID,
                actor_id=principal.subject,
            )

            # Retrieve run result from evidence
            from backend.app.core.evidence.models import EvidenceRecord
            from sqlalchemy import select
            from backend.app.engines.enterprise_distressed_asset_debt_stress.ids import deterministic_evidence_id

            # Get the debt exposure evidence (stored with kind="debt_exposure", stable_key="base")
            exposure_evidence_id = deterministic_evidence_id(
                dataset_version_id=validated_dv_id,
                engine_id=ENGINE_ID,
                kind="debt_exposure",
                stable_key="base",
            )

            result = await db.execute(
                select(EvidenceRecord)
                .where(EvidenceRecord.evidence_id == exposure_evidence_id)
                .where(EvidenceRecord.dataset_version_id == validated_dv_id)
            )
            evidence = result.scalar_one_or_none()

            if not evidence:
                raise HTTPException(
                    status_code=404,
                    detail=f"Run result not found for run_id: {run_id}. Evidence may not have been persisted.",
                )

            # Parse the evidence payload
            import json
            evidence_payload = json.loads(evidence.payload_json) if isinstance(evidence.payload_json, str) else evidence.payload_json
            
            # Extract the report data from the evidence payload
            # The run.py stores debt_exposure and assumptions in the evidence
            debt_exposure = evidence_payload.get("debt_exposure", {}) if isinstance(evidence_payload, dict) else {}
            assumptions = evidence_payload.get("assumptions", {}) if isinstance(evidence_payload, dict) else {}
            
            # Get stress test evidence (stored separately)
            stress_evidence_list = []
            stress_evidence_query = await db.execute(
                select(EvidenceRecord)
                .where(EvidenceRecord.dataset_version_id == validated_dv_id)
                .where(EvidenceRecord.engine_id == ENGINE_ID)
                .where(EvidenceRecord.kind == "stress_test")
            )
            stress_evidence_records = stress_evidence_query.scalars().all()
            for stress_evidence in stress_evidence_records:
                stress_payload = json.loads(stress_evidence.payload_json) if isinstance(stress_evidence.payload_json, str) else stress_evidence.payload_json
                if isinstance(stress_payload, dict) and "stress_result" in stress_payload:
                    stress_evidence_list.append(stress_payload.get("stress_result", {}))

            # Generate report with all sections as defined in EngineSpec
            report = {
                "report_type": report_type,
                "dataset_version_id": validated_dv_id,
                "run_id": run_id.strip(),
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "sections": {
                    "metadata": {
                        "dataset_version_id": validated_dv_id,
                        "run_id": run_id.strip(),
                        "generated_at": datetime.now(timezone.utc).isoformat(),
                    },
                    "debt_exposure": debt_exposure,
                    "stress_tests": stress_evidence_list,
                    "assumptions": assumptions,
                },
            }

            return report

    except LifecycleViolationError as exc:
        raise HTTPException(status_code=409, detail=exc.detail) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("DISTRESSED_DEBT_REPORT_ERROR error=%s", type(exc).__name__)
        raise HTTPException(status_code=500, detail=f"REPORT_GENERATION_FAILED: {type(exc).__name__}: {exc}") from exc


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
