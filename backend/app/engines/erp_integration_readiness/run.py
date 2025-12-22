from __future__ import annotations

import logging
from datetime import datetime
import uuid

from sqlalchemy import select

from backend.app.core.dataset.models import DatasetVersion
from backend.app.core.dataset.uuidv7 import uuid7
from backend.app.core.db import get_sessionmaker
from backend.app.core.engine_registry.kill_switch import is_engine_enabled
from backend.app.engines.erp_integration_readiness.engine import ENGINE_ID, ENGINE_VERSION
from backend.app.engines.erp_integration_readiness.errors import (
    DatasetVersionInvalidError,
    DatasetVersionMissingError,
    DatasetVersionNotFoundError,
    EngineDisabledError,
    ErpSystemConfigInvalidError,
    ErpSystemConfigMissingError,
    ParametersInvalidError,
    ParametersMissingError,
    StartedAtInvalidError,
    StartedAtMissingError,
)
from backend.app.engines.erp_integration_readiness.findings_service import (
    evaluate_optional_inputs_and_persist_findings,
    persist_compatibility_findings,
    persist_readiness_findings,
    persist_risk_assessment_findings,
)
from backend.app.engines.erp_integration_readiness.ids import (
    deterministic_erp_readiness_finding_id,
    deterministic_result_set_id,
)
from backend.app.engines.erp_integration_readiness.models.runs import (
    ErpIntegrationReadinessRun,
)
from backend.app.engines.erp_integration_readiness.models.findings import (
    ErpIntegrationReadinessFinding,
)
from backend.app.engines.erp_integration_readiness.compatibility import (
    check_infrastructure_compatibility,
    check_security_compatibility,
    check_version_compatibility,
)
from backend.app.engines.erp_integration_readiness.readiness import (
    check_data_integrity_requirements,
    check_erp_system_availability,
    check_operational_readiness,
)
from backend.app.engines.erp_integration_readiness.risk_assessment import (
    assess_compatibility_risk,
    assess_data_integrity_risk,
    assess_downtime_risk,
)

logger = logging.getLogger(__name__)


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


def _validate_erp_system_config(erp_system_config: object) -> dict:
    if erp_system_config is None:
        raise ErpSystemConfigMissingError("ERP_SYSTEM_CONFIG_REQUIRED")
    if not isinstance(erp_system_config, dict):
        raise ErpSystemConfigInvalidError("ERP_SYSTEM_CONFIG_INVALID_TYPE")
    
    # Validate required fields
    if "system_id" not in erp_system_config:
        raise ErpSystemConfigInvalidError("ERP_SYSTEM_CONFIG_SYSTEM_ID_REQUIRED")
    if not isinstance(erp_system_config["system_id"], str) or not erp_system_config["system_id"].strip():
        raise ErpSystemConfigInvalidError("ERP_SYSTEM_CONFIG_SYSTEM_ID_INVALID")
    
    if "connection_type" not in erp_system_config:
        raise ErpSystemConfigInvalidError("ERP_SYSTEM_CONFIG_CONNECTION_TYPE_REQUIRED")
    
    return erp_system_config


def _validate_parameters(parameters: object) -> dict:
    if parameters is None:
        raise ParametersMissingError("PARAMETERS_REQUIRED")
    if not isinstance(parameters, dict):
        raise ParametersInvalidError("PARAMETERS_INVALID_TYPE")
    if "assumptions" not in parameters:
        raise ParametersInvalidError("ASSUMPTIONS_REQUIRED")
    assumptions = parameters.get("assumptions")
    if not isinstance(assumptions, dict):
        raise ParametersInvalidError("ASSUMPTIONS_INVALID_TYPE")
    
    # Infrastructure config is optional but if provided must be a dict
    infrastructure_config = parameters.get("infrastructure_config")
    if infrastructure_config is not None and not isinstance(infrastructure_config, dict):
        raise ParametersInvalidError("INFRASTRUCTURE_CONFIG_INVALID_TYPE")
    
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
    erp_system_config: object,
    parameters: object,
    optional_inputs: object = None,
) -> dict:
    if not is_engine_enabled(ENGINE_ID):
        raise EngineDisabledError(f"ENGINE_DISABLED: Engine {ENGINE_ID} is disabled")

    validated_dv_id = _validate_dataset_version_id(dataset_version_id)
    validated_started_at = _parse_started_at(started_at)
    validated_erp_config = _validate_erp_system_config(erp_system_config)
    validated_parameters = _validate_parameters(parameters)
    validated_optional_inputs = _validate_optional_inputs(optional_inputs)

    result_set_id = deterministic_result_set_id(
        dataset_version_id=validated_dv_id,
        engine_version=ENGINE_VERSION,
        erp_system_config=validated_erp_config,
        parameters=validated_parameters,
        optional_inputs=validated_optional_inputs,
    )

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        dv = await db.scalar(select(DatasetVersion).where(DatasetVersion.id == validated_dv_id))
        if dv is None:
            raise DatasetVersionNotFoundError("DATASET_VERSION_NOT_FOUND")

        run_id = str(uuid7())
        run = ErpIntegrationReadinessRun(
            run_id=run_id,
            result_set_id=result_set_id,
            dataset_version_id=validated_dv_id,
            started_at=validated_started_at,
            status="completed",
            erp_system_config=validated_erp_config,
            parameters=validated_parameters,
            optional_inputs=validated_optional_inputs,
            engine_version=ENGINE_VERSION,
        )
        db.add(run)

        # Get infrastructure config from parameters (optional)
        infrastructure_config = validated_parameters.get("infrastructure_config", {})
        erp_system_id = validated_erp_config.get("system_id", "unknown")

        # Perform readiness checks
        readiness_results = {
            "erp_system_availability": check_erp_system_availability(
                erp_system_config=validated_erp_config,
                dataset_version_id=validated_dv_id,
            ),
            "data_integrity_requirements": check_data_integrity_requirements(
                erp_system_config=validated_erp_config,
                dataset_version_id=validated_dv_id,
            ),
            "operational_readiness": check_operational_readiness(
                erp_system_config=validated_erp_config,
                dataset_version_id=validated_dv_id,
            ),
        }

        # Perform compatibility checks (if infrastructure config provided)
        compatibility_results = {}
        if infrastructure_config:
            compatibility_results = {
                "infrastructure_compatibility": check_infrastructure_compatibility(
                    erp_system_config=validated_erp_config,
                    infrastructure_config=infrastructure_config,
                    dataset_version_id=validated_dv_id,
                ),
                "version_compatibility": check_version_compatibility(
                    erp_system_config=validated_erp_config,
                    infrastructure_config=infrastructure_config,
                    dataset_version_id=validated_dv_id,
                ),
                "security_compatibility": check_security_compatibility(
                    erp_system_config=validated_erp_config,
                    infrastructure_config=infrastructure_config,
                    dataset_version_id=validated_dv_id,
                ),
            }

        # Perform risk assessments
        risk_assessments = {
            "downtime_risk": assess_downtime_risk(
                erp_system_config=validated_erp_config,
                readiness_results=readiness_results,
                compatibility_results=compatibility_results,
                dataset_version_id=validated_dv_id,
            ),
            "data_integrity_risk": assess_data_integrity_risk(
                erp_system_config=validated_erp_config,
                readiness_results=readiness_results,
                dataset_version_id=validated_dv_id,
            ),
            "compatibility_risk": assess_compatibility_risk(
                compatibility_results=compatibility_results,
                dataset_version_id=validated_dv_id,
            ),
        }

        # Persist findings
        await persist_readiness_findings(
            db,
            dataset_version_id=validated_dv_id,
            result_set_id=result_set_id,
            erp_system_id=erp_system_id,
            readiness_results=readiness_results,
            deterministic_finding_id_fn=deterministic_erp_readiness_finding_id,
        )

        if compatibility_results:
            await persist_compatibility_findings(
                db,
                dataset_version_id=validated_dv_id,
                result_set_id=result_set_id,
                erp_system_id=erp_system_id,
                compatibility_results=compatibility_results,
                deterministic_finding_id_fn=deterministic_erp_readiness_finding_id,
            )

        await persist_risk_assessment_findings(
            db,
            dataset_version_id=validated_dv_id,
            result_set_id=result_set_id,
            erp_system_id=erp_system_id,
            risk_assessments=risk_assessments,
            deterministic_finding_id_fn=deterministic_erp_readiness_finding_id,
        )

        # Evaluate optional inputs
        await evaluate_optional_inputs_and_persist_findings(
            db,
            dataset_version_id=validated_dv_id,
            result_set_id=result_set_id,
            optional_inputs=validated_optional_inputs,
            deterministic_finding_id_fn=deterministic_erp_readiness_finding_id,
        )

        # Flush to ensure all findings are persisted before querying
        await db.flush()

        # Log high-severity findings for monitoring and alerting
        result = await db.execute(
            select(ErpIntegrationReadinessFinding).where(
                ErpIntegrationReadinessFinding.result_set_id == result_set_id,
                ErpIntegrationReadinessFinding.severity.in_(["critical", "high"]),
            )
        )
        high_severity_findings = result.scalars().all()

        if high_severity_findings:
            risk_descriptions = [
                f"{f.severity.upper()}: {f.title}" for f in high_severity_findings
            ]
            logger.warning(
                "ERP_INTEGRATION_READINESS_RISKS dataset_version_id=%s erp_system_id=%s result_set_id=%s risks=%s",
                validated_dv_id,
                erp_system_id,
                result_set_id,
                risk_descriptions,
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

