from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.app.core.dataset.errors import ChecksumMismatchError, ChecksumMissingError
from backend.app.core.db import get_sessionmaker
from backend.app.core.engine_registry.kill_switch import is_engine_enabled, log_disabled_engine_attempt
from backend.app.core.engine_registry.registry import REGISTRY
from backend.app.core.engine_registry.spec import EngineSpec
from backend.app.core.lifecycle.enforcement import (
    LifecycleViolationError,
    verify_calculate_complete,
    verify_import_complete,
    verify_normalize_complete,
    record_calculation_completion,
)


ENGINE_ID = "engine_csrd"
ENGINE_VERSION = "v1"


router = APIRouter(prefix="/api/v3/engines/csrd", tags=[ENGINE_ID])


@router.post("/run")
async def run_endpoint(payload: dict) -> dict:
    if not is_engine_enabled(ENGINE_ID):
        dataset_version_id = payload.get("dataset_version_id")
        await log_disabled_engine_attempt(
            engine_id=ENGINE_ID,
            actor_id="system",  # System-level enforcement, not user-initiated
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

    from backend.app.engines.csrd.run import _validate_dataset_version_id, run_engine
    from backend.app.engines.csrd.errors import (
        DatasetVersionInvalidError,
        DatasetVersionMissingError,
        DatasetVersionNotFoundError,
        ImmutableConflictError,
        RawRecordsMissingError,
        StartedAtInvalidError,
        StartedAtMissingError,
    )

    dataset_version_id = payload.get("dataset_version_id")
    try:
        validated_dv_id = _validate_dataset_version_id(dataset_version_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as guard_db:
        try:
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
        except LifecycleViolationError as exc:
            raise HTTPException(status_code=409, detail=exc.detail) from exc

    try:
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


@router.post("/report")
async def report_endpoint(payload: dict) -> dict:
    """
    Generate CSRD/ESRS compliance report from engine run results.
    
    Kill-Switch Revalidation:
    - Engine must be enabled before report generation
    - Disabled engine cannot create reports
    """
    if not is_engine_enabled(ENGINE_ID):
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

    from backend.app.engines.csrd.run import _validate_dataset_version_id
    from backend.app.engines.csrd.reporting import generate_esrs_report
    from backend.app.core.evidence.models import FindingRecord, EvidenceRecord
    from sqlalchemy import select
    from datetime import datetime, timezone

    dataset_version_id = payload.get("dataset_version_id")
    run_id = payload.get("run_id")
    parameters = payload.get("parameters") or {}

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
            await verify_calculate_complete(
                db,
                dataset_version_id=validated_dv_id,
                run_id=run_id,
                engine_id=ENGINE_ID,
                actor_id=f"engine:{ENGINE_ID}",
            )
            # Fetch findings for this dataset version
            findings_query = select(FindingRecord).where(
                FindingRecord.dataset_version_id == validated_dv_id
            )
            findings_result = await db.execute(findings_query)
            findings = findings_result.scalars().all()

            # Fetch evidence
            evidence_query = select(EvidenceRecord).where(
                EvidenceRecord.dataset_version_id == validated_dv_id,
                EvidenceRecord.engine_id == ENGINE_ID,
            )
            evidence_result = await db.execute(evidence_query)
            evidence = evidence_result.scalars().all()

            # Extract material findings and emissions from findings
            material_findings = []
            emissions_data = {}
            assumptions = []
            warnings = []

            for finding in findings:
                if finding.payload and isinstance(finding.payload, dict):
                    payload = finding.payload
                    if payload.get("metric"):
                        material_findings.append({
                            "metric": payload.get("metric"),
                            "is_material": payload.get("is_material", False),
                            "severity": payload.get("severity"),
                            "description": payload.get("description"),
                        })
                    if "emissions" in payload:
                        emissions_data.update(payload.get("emissions", {}))
                    if "assumptions" in payload:
                        assumptions.extend(payload.get("assumptions", []))
                    if "warnings" in payload:
                        warnings.extend(payload.get("warnings", []))

            # Generate report
            report_id = f"csrd_report_{validated_dv_id}_{run_id}"
            report = generate_esrs_report(
                report_id=report_id,
                dataset_version_id=validated_dv_id,
                material_findings=material_findings,
                emissions=emissions_data,
                assumptions=assumptions,
                parameters=parameters,
                generated_at=datetime.now(timezone.utc).isoformat(),
                warnings=warnings,
            )

            return {
                "report_id": report_id,
                "dataset_version_id": validated_dv_id,
                "run_id": run_id,
                "report": report,
                "findings_count": len(material_findings),
                "evidence_count": len(evidence),
            }
    except LifecycleViolationError as exc:
        raise HTTPException(status_code=409, detail=exc.detail) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"ENGINE_REPORT_FAILED: {type(exc).__name__}: {exc}") from exc


def register_engine() -> None:
    if REGISTRY.get(ENGINE_ID) is not None:
        return
    REGISTRY.register(
        EngineSpec(
            engine_id=ENGINE_ID,
            engine_version=ENGINE_VERSION,
            enabled_by_default=False,
            owned_tables=(),
            report_sections=("executive_summary", "materiality_assessment", "data_integrity", "compliance_summary"),
            routers=(router,),
            run_entrypoint=None,
        )
    )
