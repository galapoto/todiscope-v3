"""
FF-1 Engine Skeleton — Financial Forensics

FF-1 engines must not persist artifacts. Artifact usage begins in FF-2.
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi import HTTPException

from backend.app.core.engine_registry.registry import REGISTRY
from backend.app.core.engine_registry.spec import EngineSpec


ENGINE_ID = "engine_financial_forensics"
ENGINE_VERSION = "v1"


router = APIRouter(prefix="/api/v3/engines/financial-forensics", tags=["engine_financial_forensics"])


@router.post("/run")
async def run_engine_endpoint(payload: dict) -> dict:
    dataset_version_id = payload.get("dataset_version_id")
    fx_artifact_id = payload.get("fx_artifact_id")
    started_at = payload.get("started_at")
    parameters = payload.get("parameters", {})
    from backend.app.engines.financial_forensics.run import run_engine
    from backend.app.engines.financial_forensics.run import (
        DatasetVersionInvalidError,
        DatasetVersionMissingError,
        DatasetVersionNotFoundError,
        FxArtifactInvalidError,
        FxArtifactMissingError,
    )
    from backend.app.engines.financial_forensics.failures import RuntimeLimitError

    try:
        return await run_engine(
            dataset_version_id=dataset_version_id,
            fx_artifact_id=fx_artifact_id,
            started_at=started_at,
            parameters=parameters,
        )
    except DatasetVersionInvalidError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except DatasetVersionMissingError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except DatasetVersionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except FxArtifactMissingError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except FxArtifactInvalidError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeLimitError as exc:
        raise HTTPException(status_code=413, detail=str(exc))

    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"ENGINE_RUN_FAILED: {type(exc).__name__}: {exc}")


@router.post("/normalize")
async def normalize_endpoint(payload: dict) -> dict:
    dataset_version_id = payload.get("dataset_version_id")
    from backend.app.engines.financial_forensics.run import _validate_dataset_version_id
    from backend.app.core.db import get_sessionmaker
    from backend.app.engines.financial_forensics.normalization import normalize_dataset

    validated = _validate_dataset_version_id(dataset_version_id)
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        created = await normalize_dataset(db, dataset_version_id=validated)
    return {"dataset_version_id": validated, "canonical_created": created}


@router.post("/report")
async def report_endpoint(payload: dict) -> dict:
    dataset_version_id = payload.get("dataset_version_id")
    run_id = payload.get("run_id")
    parameters = payload.get("parameters", {})
    from backend.app.engines.financial_forensics.run import _validate_dataset_version_id
    from backend.app.core.db import get_sessionmaker
    from backend.app.engines.financial_forensics.report.assembler import assemble_report
    from backend.app.engines.financial_forensics.failures import (
        InconsistentReferenceError,
        MissingArtifactError,
        RuntimeLimitError,
    )

    validated = _validate_dataset_version_id(dataset_version_id)
    if not isinstance(run_id, str) or not run_id.strip():
        raise HTTPException(status_code=400, detail="RUN_ID_REQUIRED")

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        try:
            return await assemble_report(
                db,
                dataset_version_id=validated,
                run_id=run_id,
                parameters=parameters or {},
            )
        except MissingArtifactError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        except InconsistentReferenceError as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        except RuntimeLimitError as exc:
            raise HTTPException(status_code=413, detail=str(exc))


def register_engine() -> None:
    if REGISTRY.get(ENGINE_ID) is not None:
        return
    REGISTRY.register(
        EngineSpec(
            engine_id=ENGINE_ID,
            engine_version=ENGINE_VERSION,
            enabled_by_default=False,
            owned_tables=(
                "engine_financial_forensics_runs",
                "engine_financial_forensics_canonical_records",
                "engine_financial_forensics_findings",
                "engine_financial_forensics_leakage_items",
            ),
            report_sections=("financial_forensics_stub",),
            routers=(router,),
            run_entrypoint=None,
        )
    )
