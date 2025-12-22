from __future__ import annotations

from collections import OrderedDict
from datetime import datetime, timezone
import logging
import time

from sqlalchemy import select

from backend.app.core.db import get_sessionmaker
from backend.app.core.metrics import (
    engine_errors_total,
    engine_model_duration_seconds,
    engine_persistence_duration_seconds,
    engine_run_duration_seconds,
    engine_runs_total,
)
from backend.app.core.dataset.immutability import install_immutability_guards
from backend.app.core.dataset.models import DatasetVersion
from backend.app.core.evidence.models import EvidenceRecord, FindingEvidenceLink, FindingRecord
from backend.app.core.evidence.service import (
    create_evidence,
    create_finding,
    deterministic_evidence_id,
    link_finding_to_evidence,
)
from backend.app.core.normalization.models import NormalizedRecord
from backend.app.engines.enterprise_distressed_asset_debt_stress.constants import ENGINE_ID
from backend.app.engines.enterprise_distressed_asset_debt_stress.errors import (
    DatasetVersionInvalidError,
    DatasetVersionMissingError,
    DatasetVersionNotFoundError,
    ImmutableConflictError,
    NormalizedRecordMissingError,
    StartedAtInvalidError,
    StartedAtMissingError,
)
from backend.app.engines.enterprise_distressed_asset_debt_stress.ids import deterministic_id
from backend.app.engines.enterprise_distressed_asset_debt_stress.models import (
    DEFAULT_STRESS_SCENARIOS,
    StressTestResult,
    StressTestScenario,
    apply_stress_scenario,
    calculate_debt_exposure,
)

logger = logging.getLogger(__name__)


def _parse_started_at(value: object) -> datetime:
    if value is None:
        raise StartedAtMissingError("STARTED_AT_REQUIRED")
    if not isinstance(value, str) or not value.strip():
        raise StartedAtInvalidError("STARTED_AT_INVALID")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise StartedAtInvalidError("STARTED_AT_INVALID") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _validate_dataset_version_id(value: object) -> str:
    if value is None:
        raise DatasetVersionMissingError("DATASET_VERSION_ID_REQUIRED")
    if not isinstance(value, str) or not value.strip():
        raise DatasetVersionInvalidError("DATASET_VERSION_ID_INVALID")
    return value.strip()


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        if isinstance(value, (int, float)):
            return float(value)
        return float(str(value))
    except (TypeError, ValueError):
        return default


def _resolve_scenarios(parameters: dict) -> list[StressTestScenario]:
    overrides = parameters.get("stress_scenarios")
    overrides_list = overrides if isinstance(overrides, list) else []
    ordered = OrderedDict((scenario.scenario_id, scenario) for scenario in DEFAULT_STRESS_SCENARIOS)
    for entry in overrides_list:
        if not isinstance(entry, dict):
            continue
        scenario_id = str(entry.get("scenario_id") or entry.get("id") or "").strip()
        if not scenario_id:
            continue
        base = ordered.get(scenario_id)
        description = str(
            entry.get("description")
            or entry.get("name")
            or (base.description if base else f"Custom stress scenario {scenario_id}")
        )
        ordered[scenario_id] = StressTestScenario(
            scenario_id=scenario_id,
            description=description,
            interest_rate_delta_pct=_to_float(
                entry.get("interest_rate_delta_pct"),
                base.interest_rate_delta_pct if base else 0.0,
            ),
            collateral_market_impact_pct=_to_float(
                entry.get("collateral_market_impact_pct"),
                base.collateral_market_impact_pct if base else 0.0,
            ),
            recovery_degradation_pct=_to_float(
                entry.get("recovery_degradation_pct"),
                base.recovery_degradation_pct if base else 0.0,
            ),
            default_risk_increment_pct=_to_float(
                entry.get("default_risk_increment_pct"),
                base.default_risk_increment_pct if base else 0.0,
            ),
        )
    return list(ordered.values())


async def _strict_create_evidence(
    db,
    *,
    evidence_id: str,
    dataset_version_id: str,
    kind: str,
    payload: dict,
    created_at: datetime,
) -> EvidenceRecord:
    existing = await db.scalar(select(EvidenceRecord).where(EvidenceRecord.evidence_id == evidence_id))
    if existing is not None:
        if existing.dataset_version_id != dataset_version_id or existing.engine_id != ENGINE_ID or existing.kind != kind:
            logger.warning(
                "DISTRESSED_DEBT_IMMUTABLE_CONFLICT evidence_id_collision evidence_id=%s dataset_version_id=%s",
                evidence_id,
                dataset_version_id,
            )
            raise ImmutableConflictError("EVIDENCE_ID_COLLISION")
        existing_created_at = existing.created_at
        if existing_created_at.tzinfo is None:
            existing_created_at = existing_created_at.replace(tzinfo=timezone.utc)
        created_at_norm = created_at if created_at.tzinfo is not None else created_at.replace(tzinfo=timezone.utc)
        if existing_created_at != created_at_norm:
            logger.warning(
                "DISTRESSED_DEBT_IMMUTABLE_CONFLICT evidence_created_at_mismatch evidence_id=%s dataset_version_id=%s",
                evidence_id,
                dataset_version_id,
            )
            raise ImmutableConflictError("IMMUTABLE_EVIDENCE_CREATED_AT_MISMATCH")
        if existing.payload != payload:
            logger.warning(
                "DISTRESSED_DEBT_IMMUTABLE_CONFLICT evidence_payload_mismatch evidence_id=%s dataset_version_id=%s",
                evidence_id,
                dataset_version_id,
            )
            raise ImmutableConflictError("IMMUTABLE_EVIDENCE_MISMATCH")
        return existing
    return await create_evidence(
        db=db,
        evidence_id=evidence_id,
        dataset_version_id=dataset_version_id,
        engine_id=ENGINE_ID,
        kind=kind,
        payload=payload,
        created_at=created_at,
    )


async def _strict_create_finding(
    db,
    *,
    finding_id: str,
    dataset_version_id: str,
    raw_record_id: str,
    kind: str,
    payload: dict,
    created_at: datetime,
) -> FindingRecord:
    existing = await db.scalar(select(FindingRecord).where(FindingRecord.finding_id == finding_id))
    if existing is not None:
        if (
            existing.dataset_version_id != dataset_version_id
            or existing.raw_record_id != raw_record_id
            or existing.kind != kind
        ):
            logger.warning(
                "DISTRESSED_DEBT_IMMUTABLE_CONFLICT finding_id_collision finding_id=%s dataset_version_id=%s",
                finding_id,
                dataset_version_id,
            )
            raise ImmutableConflictError("FINDING_ID_COLLISION")
        if existing.payload != payload:
            logger.warning(
                "DISTRESSED_DEBT_IMMUTABLE_CONFLICT finding_payload_mismatch finding_id=%s dataset_version_id=%s",
                finding_id,
                dataset_version_id,
            )
            raise ImmutableConflictError("IMMUTABLE_FINDING_MISMATCH")
        return existing
    return await create_finding(
        db=db,
        finding_id=finding_id,
        dataset_version_id=dataset_version_id,
        raw_record_id=raw_record_id,
        kind=kind,
        payload=payload,
        created_at=created_at,
    )


async def _strict_link(db, *, link_id: str, finding_id: str, evidence_id: str) -> FindingEvidenceLink:
    existing = await db.scalar(select(FindingEvidenceLink).where(FindingEvidenceLink.link_id == link_id))
    if existing is not None:
        if existing.finding_id != finding_id or existing.evidence_id != evidence_id:
            logger.warning(
                "DISTRESSED_DEBT_IMMUTABLE_CONFLICT link_mismatch link_id=%s dataset_version_id=%s",
                link_id,
                "unknown",
            )
            raise ImmutableConflictError("IMMUTABLE_LINK_MISMATCH")
        return existing
    return await link_finding_to_evidence(db, link_id=link_id, finding_id=finding_id, evidence_id=evidence_id)


def _build_assumptions(*, parameters: dict, normalized_record_id: str) -> list[dict]:
    scenarios_metadata = parameters.get("stress_scenarios")
    override_ids: list[str] = []
    if isinstance(scenarios_metadata, list):
        for entry in scenarios_metadata:
            if isinstance(entry, dict):
                scenario_id = entry.get("scenario_id") or entry.get("id")
                if isinstance(scenario_id, str) and scenario_id.strip():
                    override_ids.append(scenario_id.strip())
    return [
        {
            "id": "assumption_interest_units",
            "description": "Interest rates are annual and expressed as percentage points before additional shocks.",
            "source": "Engine design",
            "impact": "Interest payment exposure scales linearly with the rate.",
            "sensitivity": "Medium",
        },
        {
            "id": "assumption_normalized_record_source",
            "description": f"Debt exposure relies on normalized record {normalized_record_id}.",
            "source": "Normalization pipeline",
            "impact": "Provides traceability back to canonical ingestion.",
            "sensitivity": "Low",
        },
        {
            "id": "assumption_stress_scenarios",
            "description": "Stress scenarios follow defaults or user overrides.",
            "source": "Engine defaults and provided parameters",
            "impact": "Shapes scenario adjustments to collateral, recovery, and interest.",
            "sensitivity": "High",
            "details": {
                "override_scenario_ids": override_ids,
                "provided_parameters": parameters.get("stress_scenarios"),
            },
        },
    ]


def _build_material_findings(
    *,
    dataset_version_id: str,
    exposure_payload: dict,
    stress_results: list[StressTestResult],
    threshold_pct: float,
    scenario_threshold_pct: float,
) -> list[dict]:
    findings: list[dict] = []
    exposure_value = exposure_payload["net_exposure_after_recovery"]
    total_outstanding = max(1.0, exposure_payload["total_outstanding"])
    material_threshold = total_outstanding * threshold_pct
    findings.append(
        {
            "id": deterministic_id(dataset_version_id, "finding", "debt_exposure:net"),
            "dataset_version_id": dataset_version_id,
            "title": "debt_exposure: net",
            "category": "debt_exposure",
            "metric": "net_exposure_after_recovery",
            "description": "Net debt exposure after collateral and distressed asset recoveries.",
            "value": exposure_value,
            "threshold": material_threshold,
            "is_material": exposure_value >= material_threshold,
            "materiality": "material" if exposure_value >= material_threshold else "not_material",
            "financial_impact_eur": exposure_value,
            "impact_score": min(1.0, exposure_value / total_outstanding),
            "confidence": "medium",
            "raw_record_hint": "financial",
        }
    )
    for result in stress_results:
        threshold = total_outstanding * scenario_threshold_pct
        is_material = result.loss_estimate >= threshold
        findings.append(
            {
                "id": deterministic_id(dataset_version_id, "finding", f"stress:{result.scenario.scenario_id}"),
                "dataset_version_id": dataset_version_id,
                "title": f"stress:{result.scenario.scenario_id}",
                "category": "stress_test",
                "metric": "loss_estimate",
                "description": result.scenario.description,
                "value": result.loss_estimate,
                "threshold": threshold,
                "is_material": is_material,
                "materiality": "material" if is_material else "not_material",
                "financial_impact_eur": result.loss_estimate,
                "impact_score": result.impact_score,
                "confidence": "medium",
                "raw_record_hint": "distressed_assets",
                "scenario_id": result.scenario.scenario_id,
            }
        )
    return findings


def _classify_error(exc: Exception) -> str:
    if isinstance(exc, DatasetVersionMissingError):
        return "dataset_version_missing"
    if isinstance(exc, DatasetVersionInvalidError):
        return "dataset_version_invalid"
    if isinstance(exc, DatasetVersionNotFoundError):
        return "dataset_version_not_found"
    if isinstance(exc, NormalizedRecordMissingError):
        return "normalized_record_missing"
    if isinstance(exc, StartedAtMissingError):
        return "started_at_missing"
    if isinstance(exc, StartedAtInvalidError):
        return "started_at_invalid"
    if isinstance(exc, ImmutableConflictError):
        return "immutable_conflict"
    return "unknown"


async def run_engine(
    *,
    dataset_version_id: object,
    started_at: object,
    parameters: dict | None = None,
    actor_id: str | None = None,
    request_id: str | None = None,
) -> dict:
    start = time.perf_counter()
    status = "success"
    install_immutability_guards()
    dv_id = _validate_dataset_version_id(dataset_version_id)
    started = _parse_started_at(started_at)
    params = dict(parameters) if isinstance(parameters, dict) else {}

    try:
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as db:
            dv = await db.scalar(select(DatasetVersion).where(DatasetVersion.id == dv_id))
            if dv is None:
                raise DatasetVersionNotFoundError("DATASET_VERSION_NOT_FOUND")

            normalized_records = (
                await db.scalars(
                    select(NormalizedRecord)
                    .where(NormalizedRecord.dataset_version_id == dv_id)
                    .order_by(NormalizedRecord.normalized_at.asc())
                )
            ).all()
            if not normalized_records:
                raise NormalizedRecordMissingError("NORMALIZED_RECORD_REQUIRED")
            normalized_record = normalized_records[0]
            raw_id = normalized_record.raw_record_id

            model_start = time.perf_counter()
            exposure = calculate_debt_exposure(normalized_payload=normalized_record.payload)
            warnings: list[str] = []
            if exposure.total_outstanding <= 0:
                warnings.append("NO_DEBT_OUTSTANDING")
            if exposure.distressed_asset_count == 0:
                warnings.append("NO_DISTRESSED_ASSETS")

            scenarios = _resolve_scenarios(params)
            stress_results = [
                apply_stress_scenario(
                    exposure=exposure,
                    base_net_exposure=exposure.net_exposure_after_recovery,
                    scenario=scenario,
                )
                for scenario in scenarios
            ]
            engine_model_duration_seconds.labels(engine_id=ENGINE_ID).observe(time.perf_counter() - model_start)

            assumptions = _build_assumptions(parameters=params, normalized_record_id=normalized_record.normalized_record_id)
            exposure_payload = exposure.to_payload()
            stress_payloads = [result.to_payload() for result in stress_results]
            report = {
                "metadata": {
                    "dataset_version_id": dv_id,
                    "generated_at": started.isoformat(),
                    "normalized_record_id": normalized_record.normalized_record_id,
                    "raw_record_id": raw_id,
                    "warnings": warnings,
                    "parameters": params,
                },
                "debt_exposure": exposure_payload,
                "stress_tests": stress_payloads,
                "assumptions": assumptions,
            }

            threshold_pct = _to_float(params.get("net_exposure_materiality_threshold_pct"), 0.2)
            scenario_threshold_pct = _to_float(params.get("stress_loss_materiality_threshold_pct"), 0.05)
            material_findings = _build_material_findings(
                dataset_version_id=dv_id,
                exposure_payload=exposure_payload,
                stress_results=stress_results,
                threshold_pct=threshold_pct,
                scenario_threshold_pct=scenario_threshold_pct,
            )

            persist_start = time.perf_counter()
            exposure_evidence_id = deterministic_evidence_id(
                dataset_version_id=dv_id, engine_id=ENGINE_ID, kind="debt_exposure", stable_key="base"
            )
            await _strict_create_evidence(
                db=db,
                evidence_id=exposure_evidence_id,
                dataset_version_id=dv_id,
                kind="debt_exposure",
                payload={
                    "debt_exposure": exposure_payload,
                    "assumptions": assumptions,
                    "normalized_record_id": normalized_record.normalized_record_id,
                    "raw_record_id": raw_id,
                },
                created_at=started,
            )

            stress_evidence_ids: dict[str, str] = {}
            for result in stress_results:
                evidence_id = deterministic_evidence_id(
                    dataset_version_id=dv_id,
                    engine_id=ENGINE_ID,
                    kind="stress_test",
                    stable_key=result.scenario.scenario_id,
                )
                stress_evidence_ids[result.scenario.scenario_id] = evidence_id
                await _strict_create_evidence(
                    db=db,
                    evidence_id=evidence_id,
                    dataset_version_id=dv_id,
                    kind="stress_test",
                    payload={
                        "stress_test": result.to_payload(),
                        "assumptions": assumptions,
                        "normalized_record_id": normalized_record.normalized_record_id,
                        "raw_record_id": raw_id,
                    },
                    created_at=started,
                )

            for finding in material_findings:
                finding_id = finding["id"]
                await _strict_create_finding(
                    db=db,
                    finding_id=finding_id,
                    dataset_version_id=dv_id,
                    raw_record_id=raw_id,
                    kind=finding["category"],
                    payload=finding,
                    created_at=started,
                )
                evidence_id = (
                    stress_evidence_ids.get(finding.get("scenario_id"))
                    if finding.get("category") == "stress_test"
                    else exposure_evidence_id
                )
                if evidence_id is None:
                    evidence_id = exposure_evidence_id
                link_id = deterministic_id(dv_id, "link", finding_id, evidence_id)
                await _strict_link(db=db, link_id=link_id, finding_id=finding_id, evidence_id=evidence_id)

            audit_evidence_id = deterministic_evidence_id(
                dataset_version_id=dv_id,
                engine_id=ENGINE_ID,
                kind="audit_trail",
                stable_key=f"run:{started.isoformat()}:{normalized_record.normalized_record_id}",
            )
            await _strict_create_evidence(
                db=db,
                evidence_id=audit_evidence_id,
                dataset_version_id=dv_id,
                kind="audit_trail",
                payload={
                    "action": "engine_run",
                    "actor_id": actor_id,
                    "request_id": request_id,
                    "dataset_version_id": dv_id,
                    "normalized_record_id": normalized_record.normalized_record_id,
                    "raw_record_id": raw_id,
                    "started_at": started.isoformat(),
                    "parameters": params,
                    "evidence_ids": {
                        "debt_exposure": exposure_evidence_id,
                        "stress_tests": stress_evidence_ids,
                    },
                    "finding_ids": [finding["id"] for finding in material_findings],
                },
                created_at=started,
            )

            engine_persistence_duration_seconds.labels(engine_id=ENGINE_ID, stage="write").observe(
                time.perf_counter() - persist_start
            )
            commit_start = time.perf_counter()
            await db.commit()
            engine_persistence_duration_seconds.labels(engine_id=ENGINE_ID, stage="commit").observe(
                time.perf_counter() - commit_start
            )

        logger.info(
            "DISTRESSED_DEBT_AUDIT engine_run dataset_version_id=%s normalized_record_id=%s raw_record_id=%s",
            dv_id,
            normalized_record.normalized_record_id,
            raw_id,
        )

        return {
            "dataset_version_id": dv_id,
            "started_at": started.isoformat(),
            "debt_exposure_evidence_id": exposure_evidence_id,
            "stress_test_evidence_ids": stress_evidence_ids,
            "material_findings": material_findings,
            "report": report,
            "assumptions": assumptions,
            "audit_trail_evidence_id": audit_evidence_id,
        }
    except Exception as exc:
        status = "error"
        engine_errors_total.labels(engine_id=ENGINE_ID, error_type=_classify_error(exc)).inc()
        raise
    finally:
        engine_runs_total.labels(engine_id=ENGINE_ID, status=status).inc()
        engine_run_duration_seconds.labels(engine_id=ENGINE_ID, status=status).observe(time.perf_counter() - start)
