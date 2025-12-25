from __future__ import annotations

from datetime import datetime
import uuid

from sqlalchemy import select

from backend.app.core.dataset.models import DatasetVersion
from backend.app.core.dataset.uuidv7 import uuid7
from backend.app.core.db import get_sessionmaker
from backend.app.core.engine_registry.kill_switch import is_engine_enabled
from backend.app.engines.enterprise_deal_transaction_readiness.engine import ENGINE_ID, ENGINE_VERSION
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
from backend.app.engines.enterprise_deal_transaction_readiness.findings_service import (
    evaluate_optional_inputs_and_persist_findings,
)
from backend.app.engines.enterprise_deal_transaction_readiness.ids import (
    deterministic_readiness_finding_id,
    deterministic_result_set_id,
)
from backend.app.engines.enterprise_deal_transaction_readiness.models.runs import (
    EnterpriseDealTransactionReadinessRun,
)


def _validate_dataset_version_id(dataset_version_id: str | None) -> str:
    if dataset_version_id is None:
        raise DatasetVersionMissingError("DATASET_VERSION_ID_REQUIRED")
    if not isinstance(dataset_version_id, str):
        raise DatasetVersionInvalidError("DATASET_VERSION_ID_INVALID_TYPE")
    dv = dataset_version_id.strip()
    if not dv:
        raise DatasetVersionInvalidError("DATASET_VERSION_ID_EMPTY")
    try:
        parsed = uuid.UUID(dv)
    except ValueError as exc:
        raise DatasetVersionInvalidError("DATASET_VERSION_ID_INVALID_UUID") from exc
    if parsed.version != 7:
        raise DatasetVersionInvalidError("DATASET_VERSION_ID_UUIDV7_REQUIRED")
    return dv


def _validate_sha256(s: object) -> str:
    if not isinstance(s, str) or not s.strip():
        raise ParametersInvalidError("SHA256_REQUIRED")
    val = s.strip().lower()
    if len(val) != 64:
        raise ParametersInvalidError("SHA256_INVALID_LENGTH")
    try:
        int(val, 16)
    except ValueError as exc:
        raise ParametersInvalidError("SHA256_INVALID_HEX") from exc
    return val


def _validate_optional_inputs(optional_inputs: object) -> dict:
    if optional_inputs is None:
        return {}
    if not isinstance(optional_inputs, dict):
        raise ParametersInvalidError("OPTIONAL_INPUTS_INVALID_TYPE")

    normalized: dict[str, dict] = {}
    for name, spec in optional_inputs.items():
        if not isinstance(name, str) or not name.strip():
            raise ParametersInvalidError("OPTIONAL_INPUT_NAME_INVALID")
        if not isinstance(spec, dict):
            raise ParametersInvalidError("OPTIONAL_INPUT_SPEC_INVALID_TYPE")
        key = spec.get("artifact_key")
        sha = spec.get("sha256")
        content_type = spec.get("content_type")
        if not isinstance(key, str) or not key.strip():
            raise ParametersInvalidError("OPTIONAL_INPUT_ARTIFACT_KEY_REQUIRED")
        if content_type is not None and (not isinstance(content_type, str) or not content_type.strip()):
            raise ParametersInvalidError("OPTIONAL_INPUT_CONTENT_TYPE_INVALID")
        normalized[name] = {
            "artifact_key": key.strip(),
            "sha256": _validate_sha256(sha),
            "content_type": content_type.strip() if isinstance(content_type, str) else None,
        }
    return normalized


def _validate_transaction_scope(transaction_scope: object) -> dict:
    if transaction_scope is None:
        raise TransactionScopeMissingError("TRANSACTION_SCOPE_REQUIRED")
    if not isinstance(transaction_scope, dict):
        raise TransactionScopeInvalidError("TRANSACTION_SCOPE_INVALID_TYPE")
    return transaction_scope


def _validate_parameters(parameters: object) -> dict:
    if parameters is None:
        raise ParametersMissingError("PARAMETERS_REQUIRED")
    if not isinstance(parameters, dict):
        raise ParametersInvalidError("PARAMETERS_INVALID_TYPE")
    if "assumptions" not in parameters:
        raise ParametersInvalidError("ASSUMPTIONS_REQUIRED")
    if "fx" not in parameters:
        raise ParametersInvalidError("FX_REQUIRED")
    assumptions = parameters.get("assumptions")
    fx = parameters.get("fx")
    if not isinstance(assumptions, dict):
        raise ParametersInvalidError("ASSUMPTIONS_INVALID_TYPE")
    if not isinstance(fx, dict):
        raise ParametersInvalidError("FX_INVALID_TYPE")
    return parameters


def _parse_started_at(started_at: object) -> datetime:
    if started_at is None:
        raise StartedAtMissingError("STARTED_AT_REQUIRED")
    if not isinstance(started_at, str) or not started_at.strip():
        raise StartedAtMissingError("STARTED_AT_REQUIRED")
    try:
        parsed = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise StartedAtInvalidError("STARTED_AT_INVALID_FORMAT") from exc
    if parsed.tzinfo is None:
        raise StartedAtInvalidError("STARTED_AT_TZ_REQUIRED")
    return parsed


async def run_engine(
    *,
    dataset_version_id: str | None,
    started_at: object,
    transaction_scope: object,
    parameters: object,
    optional_inputs: object = None,
) -> dict:
    if not is_engine_enabled(ENGINE_ID):
        raise EngineDisabledError(f"ENGINE_DISABLED: Engine {ENGINE_ID} is disabled")

    validated_dv_id = _validate_dataset_version_id(dataset_version_id)
    validated_started_at = _parse_started_at(started_at)
    validated_scope = _validate_transaction_scope(transaction_scope)
    validated_parameters = _validate_parameters(parameters)
    validated_optional_inputs = _validate_optional_inputs(optional_inputs)

    result_set_id = deterministic_result_set_id(
        dataset_version_id=validated_dv_id,
        engine_version=ENGINE_VERSION,
        transaction_scope=validated_scope,
        parameters=validated_parameters,
        optional_inputs=validated_optional_inputs,
    )

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        dv = await db.scalar(select(DatasetVersion).where(DatasetVersion.id == validated_dv_id))
        if dv is None:
            raise DatasetVersionNotFoundError("DATASET_VERSION_NOT_FOUND")

        run_id = str(uuid7())
        run = EnterpriseDealTransactionReadinessRun(
            run_id=run_id,
            result_set_id=result_set_id,
            dataset_version_id=validated_dv_id,
            started_at=validated_started_at,
            status="completed",
            transaction_scope=validated_scope,
            parameters=validated_parameters,
            optional_inputs=validated_optional_inputs,
            engine_version=ENGINE_VERSION,
        )
        db.add(run)

        await evaluate_optional_inputs_and_persist_findings(
            db,
            dataset_version_id=validated_dv_id,
            result_set_id=result_set_id,
            optional_inputs=validated_optional_inputs,
            deterministic_finding_id_fn=deterministic_readiness_finding_id,
        )

        await db.commit()

    return {
        "engine_id": ENGINE_ID,
        "engine_version": ENGINE_VERSION,
        "run_id": run_id,
        "result_set_id": result_set_id,
        "dataset_version_id": validated_dv_id,
        "status": "completed",
    }





