"""
Engine #5 — Enterprise Deal & Transaction Readiness

Build Task 1 scope:
- Transaction scope is a runtime parameter persisted in engine-owned run table.
- Run parameters are runtime parameters persisted in engine-owned run table (not DatasetVersion).
- DatasetVersion is immutable data-only anchor (UUIDv7).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.app.core.engine_registry.kill_switch import is_engine_enabled
from backend.app.core.engine_registry.registry import REGISTRY
from backend.app.core.engine_registry.spec import EngineSpec


ENGINE_ID = "engine_enterprise_deal_transaction_readiness"
ENGINE_VERSION = "v1"


router = APIRouter(
    prefix="/api/v3/engines/enterprise-deal-transaction-readiness",
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

    from backend.app.engines.enterprise_deal_transaction_readiness.errors import (
        DatasetVersionInvalidError,
        DatasetVersionMissingError,
        DatasetVersionNotFoundError,
        EngineDisabledError,
        ParametersInvalidError,
        ParametersMissingError,
        StartedAtInvalidError,
        StartedAtMissingError,
        TransactionScopeInvalidError,
        TransactionScopeMissingError,
    )
    from backend.app.engines.enterprise_deal_transaction_readiness.run import run_engine

    try:
        return await run_engine(
            dataset_version_id=payload.get("dataset_version_id"),
            started_at=payload.get("started_at"),
            transaction_scope=payload.get("transaction_scope"),
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
    except TransactionScopeMissingError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except TransactionScopeInvalidError as exc:
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


@router.post("/report")
async def report_endpoint(payload: dict) -> dict:
    """
    Generate transaction readiness report.
    
    Kill-Switch Revalidation:
    - Engine must be enabled before report generation
    - Disabled engine cannot create reports
    - Kill-switch check occurs before any side effects
    
    Platform Law #2: Engines are detachable
    """
    # Kill-switch revalidation (hardening)
    if not is_engine_enabled(ENGINE_ID):
        raise HTTPException(
            status_code=503,
            detail=(
                f"ENGINE_DISABLED: Engine {ENGINE_ID} is disabled. "
                "Enable via TODISCOPE_ENABLED_ENGINES environment variable."
            ),
        )
    
    from backend.app.engines.enterprise_deal_transaction_readiness.report.assembler import (
        DatasetVersionMismatchError,
        RunNotFoundError,
        assemble_report,
    )
    from backend.app.engines.enterprise_deal_transaction_readiness.run import _validate_dataset_version_id
    from backend.app.core.db import get_sessionmaker
    
    dataset_version_id = payload.get("dataset_version_id")
    run_id = payload.get("run_id")
    view_type = payload.get("view_type", "internal")  # "internal" or "external"
    anonymization_salt = payload.get("anonymization_salt", "")
    
    # Validate inputs
    try:
        validated_dv_id = _validate_dataset_version_id(dataset_version_id)
    except Exception:
        raise HTTPException(status_code=400, detail="DATASET_VERSION_ID_INVALID")
    if not isinstance(run_id, str) or not run_id.strip():
        raise HTTPException(status_code=400, detail="RUN_ID_REQUIRED")
    if view_type not in ("internal", "external"):
        raise HTTPException(status_code=400, detail="VIEW_TYPE_INVALID")
    
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        try:
            report = await assemble_report(
                db,
                dataset_version_id=validated_dv_id,
                run_id=run_id,
            )
            if view_type == "external":
                from backend.app.engines.enterprise_deal_transaction_readiness.externalization.views import (
                    create_external_view,
                    validate_external_view,
                )

                external_view = create_external_view(report, anonymization_salt=anonymization_salt)
                validate_external_view(external_view)
                return external_view
            return report
        except RunNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        except DatasetVersionMismatchError as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"REPORT_ASSEMBLY_FAILED: {type(exc).__name__}: {exc}",
            )


@router.post("/export")
async def export_endpoint(payload: dict) -> dict:
    """
    Export transaction readiness report in external view (JSON).
    
    Kill-Switch Revalidation:
    - Engine must be enabled before export
    - Disabled engine cannot create exports
    - Kill-switch check occurs before any side effects
    
    Platform Law #2: Engines are detachable
    Platform Law #4: Artifacts are content-addressed
    """
    # Kill-switch revalidation (hardening)
    if not is_engine_enabled(ENGINE_ID):
        raise HTTPException(
            status_code=503,
            detail=(
                f"ENGINE_DISABLED: Engine {ENGINE_ID} is disabled. "
                "Enable via TODISCOPE_ENABLED_ENGINES environment variable."
            ),
        )
    
    from backend.app.engines.enterprise_deal_transaction_readiness.report.assembler import (
        DatasetVersionMismatchError,
        RunNotFoundError,
        assemble_report,
    )
    from backend.app.core.db import get_sessionmaker
    from backend.app.engines.enterprise_deal_transaction_readiness.externalization.exporter import (
        export_report_json,
        export_report_pdf,
    )
    from backend.app.engines.enterprise_deal_transaction_readiness.externalization.views import (
        create_external_view,
        create_internal_view,
        validate_external_view,
    )
    from backend.app.engines.enterprise_deal_transaction_readiness.run import _validate_dataset_version_id
    
    dataset_version_id = payload.get("dataset_version_id")
    run_id = payload.get("run_id")
    view_type = payload.get("view_type", "external")  # "internal" or "external"
    formats = payload.get("formats", ["json", "pdf"])
    anonymization_salt = payload.get("anonymization_salt", "")
    include_report = payload.get("include_report", False)
    
    # Validate inputs
    try:
        validated_dv_id = _validate_dataset_version_id(dataset_version_id)
    except Exception:
        raise HTTPException(status_code=400, detail="DATASET_VERSION_ID_INVALID")
    if not isinstance(run_id, str) or not run_id.strip():
        raise HTTPException(status_code=400, detail="RUN_ID_REQUIRED")
    if view_type not in ("internal", "external"):
        raise HTTPException(status_code=400, detail="VIEW_TYPE_INVALID: must be 'internal' or 'external'")
    if not isinstance(formats, list) or not formats:
        raise HTTPException(status_code=400, detail="FORMATS_REQUIRED")
    if any(f not in ("json", "pdf") for f in formats):
        raise HTTPException(status_code=400, detail="FORMAT_UNSUPPORTED")
    if not isinstance(include_report, bool):
        raise HTTPException(status_code=400, detail="INCLUDE_REPORT_INVALID")
    
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        try:
            # Assemble full report
            full_report = await assemble_report(
                db,
                dataset_version_id=validated_dv_id,
                run_id=run_id,
            )
            
            # Create view based on type (externalization)
            if view_type == "external":
                report_view = create_external_view(full_report, anonymization_salt=anonymization_salt)
                validate_external_view(report_view)
            else:
                report_view = create_internal_view(full_report)

            result_set_id = full_report.get("result_set_id")
            if not isinstance(result_set_id, str) or not result_set_id.strip():
                raise HTTPException(status_code=500, detail="RESULT_SET_ID_MISSING")

            exports: list[dict] = []
            if "json" in formats:
                exports.append(
                    await export_report_json(
                        dataset_version_id=validated_dv_id,
                        result_set_id=result_set_id,
                        view_type=view_type,
                        report_view=report_view,
                    )
                )
            if "pdf" in formats:
                exports.append(
                    await export_report_pdf(
                        dataset_version_id=validated_dv_id,
                        result_set_id=result_set_id,
                        view_type=view_type,
                        report_view=report_view,
                    )
                )

            out: dict = {
                "view_type": view_type,
                "dataset_version_id": validated_dv_id,
                "run_id": run_id,
                "result_set_id": result_set_id,
                "exports": exports,
            }
            if include_report:
                out["report"] = report_view
            return out
        except RunNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        except DatasetVersionMismatchError as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        except ValueError as exc:
            # External view validation failure
            raise HTTPException(status_code=500, detail=f"EXTERNAL_VIEW_VALIDATION_FAILED: {exc}")
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"EXPORT_FAILED: {type(exc).__name__}: {exc}",
            )


def register_engine() -> None:
    if REGISTRY.get(ENGINE_ID) is not None:
        return
    REGISTRY.register(
        EngineSpec(
            engine_id=ENGINE_ID,
            engine_version=ENGINE_VERSION,
            enabled_by_default=False,
            owned_tables=(
                "engine_enterprise_deal_transaction_readiness_runs",
                "engine_enterprise_deal_transaction_readiness_findings",
            ),
            report_sections=(),
            routers=(router,),
            run_entrypoint=None,
        )
    )
