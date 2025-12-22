"""FastAPI router and registry integration for the Enterprise Insurance Claim Forensics engine."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.app.core.engine_registry.registry import REGISTRY
from backend.app.core.engine_registry.spec import EngineSpec
from backend.app.engines.enterprise_insurance_claim_forensics.constants import ENGINE_ID, ENGINE_VERSION
from backend.app.engines.enterprise_insurance_claim_forensics.errors import (
    ClaimPayloadMissingError,
    DatasetVersionInvalidError,
    DatasetVersionMissingError,
    DatasetVersionNotFoundError,
    ImmutableConflictError,
    NormalizedRecordMissingError,
    ParametersInvalidError,
    StartedAtInvalidError,
    StartedAtMissingError,
)

router = APIRouter(
    prefix="/api/v3/engines/enterprise-insurance-claim-forensics",
    tags=["engine_enterprise_insurance_claim_forensics"],
)


@router.post("/run")
async def run_engine_endpoint(payload: dict) -> dict:
    dataset_version_id = payload.get("dataset_version_id")
    started_at = payload.get("started_at")
    parameters = payload.get("parameters")
    from backend.app.engines.enterprise_insurance_claim_forensics.run import run_engine

    try:
        return await run_engine(
            dataset_version_id=dataset_version_id,
            started_at=started_at,
            parameters=parameters,
        )
    except DatasetVersionMissingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except DatasetVersionInvalidError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except DatasetVersionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except StartedAtMissingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except StartedAtInvalidError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ParametersInvalidError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except NormalizedRecordMissingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ClaimPayloadMissingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ImmutableConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
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
            owned_tables=(
                "engine_enterprise_insurance_claim_forensics_runs",
                "engine_enterprise_insurance_claim_forensics_findings",
            ),
            report_sections=("insurance_claim_forensics_loss_exposure",),
            routers=(router,),
            run_entrypoint=None,
        )
    )

