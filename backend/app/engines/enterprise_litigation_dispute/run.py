"""Entry point for the Enterprise Litigation & Dispute Analysis engine."""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any

from sqlalchemy import select

from backend.app.core.db import get_sessionmaker
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
from backend.app.engines.enterprise_litigation_dispute.analysis import (
    assess_liability,
    compare_scenarios,
    damage_payload,
    evaluate_legal_consistency,
    legal_consistency_payload,
    liability_payload,
    quantify_damages,
    scenario_payload,
)
from backend.app.engines.enterprise_litigation_dispute.models import (
    EnterpriseLitigationDisputeFinding,
    EnterpriseLitigationDisputeRun,
)
from backend.app.engines.enterprise_litigation_dispute.constants import ENGINE_ID
from backend.app.engines.enterprise_litigation_dispute.errors import (
    DatasetVersionInvalidError,
    DatasetVersionMissingError,
    DatasetVersionNotFoundError,
    ImmutableConflictError,
    LegalPayloadMissingError,
    NormalizedRecordMissingError,
    ParametersInvalidError,
    StartedAtInvalidError,
    StartedAtMissingError,
)
from backend.app.engines.enterprise_litigation_dispute.ids import deterministic_id

logger = logging.getLogger(__name__)


def _parse_started_at(value: object) -> datetime:
    if value is None:
        raise StartedAtMissingError("STARTED_AT_REQUIRED")
    if not isinstance(value, str) or not value.strip():
        raise StartedAtMissingError("STARTED_AT_REQUIRED")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise StartedAtInvalidError("STARTED_AT_INVALID") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _validate_dataset_version_id(value: object) -> str:
    if value is None:
        raise DatasetVersionMissingError("DATASET_VERSION_ID_REQUIRED")
    if not isinstance(value, str):
        raise DatasetVersionInvalidError("DATASET_VERSION_ID_INVALID")
    trimmed = value.strip()
    if not trimmed:
        raise DatasetVersionInvalidError("DATASET_VERSION_ID_INVALID")
    return trimmed


def _validate_parameters(value: object | None) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ParametersInvalidError("PARAMETERS_INVALID_TYPE")
    return value


def _extract_legal_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise LegalPayloadMissingError("LEGAL_PAYLOAD_REQUIRED")
    if isinstance(payload.get("data"), dict) and isinstance(payload["data"].get("legal_dispute"), dict):
        payload = payload["data"]
    legal_payload = payload.get("legal_dispute")
    if not isinstance(legal_payload, dict):
        raise LegalPayloadMissingError("LEGAL_PAYLOAD_REQUIRED")
    return legal_payload


async def _strict_create_evidence(
    db,
    *,
    evidence_id: str,
    dataset_version_id: str,
    engine_id: str,
    kind: str,
    payload: dict[str, Any],
    created_at: datetime,
) -> EvidenceRecord:
    existing = await db.scalar(select(EvidenceRecord).where(EvidenceRecord.evidence_id == evidence_id))
    if existing is not None:
        if existing.dataset_version_id != dataset_version_id or existing.engine_id != engine_id or existing.kind != kind:
            logger.warning(
                "LITIGATION_IMMUTABLE_CONFLICT evidence_id_collision evidence_id=%s dataset_version_id=%s",
                evidence_id,
                dataset_version_id,
            )
            raise ImmutableConflictError("EVIDENCE_ID_COLLISION")
        existing_created_at = existing.created_at
        if existing_created_at.tzinfo is None:
            existing_created_at = existing_created_at.replace(tzinfo=timezone.utc)
        normalized_created_at = created_at if created_at.tzinfo is not None else created_at.replace(tzinfo=timezone.utc)
        if existing_created_at != normalized_created_at:
            logger.warning(
                "LITIGATION_IMMUTABLE_CONFLICT evidence_created_at_mismatch evidence_id=%s dataset_version_id=%s",
                evidence_id,
                dataset_version_id,
            )
            raise ImmutableConflictError("IMMUTABLE_EVIDENCE_CREATED_AT_MISMATCH")
        if existing.payload != payload:
            logger.warning(
                "LITIGATION_IMMUTABLE_CONFLICT evidence_payload_mismatch evidence_id=%s dataset_version_id=%s",
                evidence_id,
                dataset_version_id,
            )
            raise ImmutableConflictError("IMMUTABLE_EVIDENCE_MISMATCH")
        return existing
    return await create_evidence(
        db,
        evidence_id=evidence_id,
        dataset_version_id=dataset_version_id,
        engine_id=engine_id,
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
    payload: dict[str, Any],
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
                "LITIGATION_IMMUTABLE_CONFLICT finding_id_collision finding_id=%s dataset_version_id=%s",
                finding_id,
                dataset_version_id,
            )
            raise ImmutableConflictError("FINDING_ID_COLLISION")
        if existing.payload != payload:
            logger.warning(
                "LITIGATION_IMMUTABLE_CONFLICT finding_payload_mismatch finding_id=%s dataset_version_id=%s",
                finding_id,
                dataset_version_id,
            )
            raise ImmutableConflictError("IMMUTABLE_FINDING_MISMATCH")
        return existing
    return await create_finding(
        db,
        finding_id=finding_id,
        dataset_version_id=dataset_version_id,
        raw_record_id=raw_record_id,
        kind=kind,
        payload=payload,
        created_at=created_at,
    )


async def _strict_link(
    db,
    *,
    link_id: str,
    finding_id: str,
    evidence_id: str,
) -> FindingEvidenceLink:
    existing = await db.scalar(select(FindingEvidenceLink).where(FindingEvidenceLink.link_id == link_id))
    if existing is not None:
        if existing.finding_id != finding_id or existing.evidence_id != evidence_id:
            logger.warning(
                "LITIGATION_IMMUTABLE_CONFLICT link_mismatch link_id=%s",
                link_id,
            )
            raise ImmutableConflictError("IMMUTABLE_LINK_MISMATCH")
        return existing
    return await link_finding_to_evidence(db, link_id=link_id, finding_id=finding_id, evidence_id=evidence_id)


async def run_engine(*, dataset_version_id: object, started_at: object, parameters: object | None = None) -> dict[str, Any]:
    install_immutability_guards()
    dv_id = _validate_dataset_version_id(dataset_version_id)
    started = _parse_started_at(started_at)
    validated_parameters = _validate_parameters(parameters)
    assumptions_map = validated_parameters.get("assumptions") if isinstance(validated_parameters.get("assumptions"), dict) else {}

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
        legal_payload = _extract_legal_payload(normalized_record.payload)
        source_raw_id = normalized_record.raw_record_id

        damage_result = quantify_damages(
            dataset_version_id=dv_id,
            dispute_payload=legal_payload,
            assumptions=assumptions_map,
        )
        liability_result = assess_liability(
            dataset_version_id=dv_id,
            dispute_payload=legal_payload,
            assumptions=assumptions_map,
        )
        scenario_result = compare_scenarios(
            dataset_version_id=dv_id,
            dispute_payload=legal_payload,
            assumptions=assumptions_map,
        )
        consistency_result = evaluate_legal_consistency(
            dataset_version_id=dv_id,
            dispute_payload=legal_payload,
            assumptions=assumptions_map,
        )

        damage_info = damage_payload(damage_result)
        liability_info = liability_payload(liability_result)
        scenario_info = scenario_payload(scenario_result)
        consistency_info = legal_consistency_payload(consistency_result)

        aggregated_assumptions: list[dict[str, str]] = []
        for section in (damage_info.get("assumptions"), liability_info.get("assumptions"), scenario_info.get("assumptions"), consistency_info.get("assumptions")):
            if isinstance(section, list):
                aggregated_assumptions.extend(section)

        evidence_ids: dict[str, str] = {}
        result_payloads = {
            "damage": damage_info,
            "liability": liability_info,
            "scenario": scenario_info,
            "legal_consistency": consistency_info,
        }
        for key, payload in result_payloads.items():
            evidence_id = deterministic_evidence_id(
                dataset_version_id=dv_id,
                engine_id=ENGINE_ID,
                kind=key,
                stable_key="v1",
            )
            evidence_ids[key] = evidence_id
            await _strict_create_evidence(
                db,
                evidence_id=evidence_id,
                dataset_version_id=dv_id,
                engine_id=ENGINE_ID,
                kind=key,
                payload={
                    key: payload,
                    "source_raw_record_id": source_raw_id,
                    "assumptions": payload.get("assumptions"),
                },
                created_at=started,
            )

        summary = {
            "dataset_version_id": dv_id,
            "started_at": started.isoformat(),
            "raw_record_id": source_raw_id,
            "damage_assessment": damage_info,
            "liability_assessment": liability_info,
            "scenario_comparison": scenario_info,
            "legal_consistency": consistency_info,
            "assumptions": aggregated_assumptions,
        }

        summary_evidence_id = deterministic_evidence_id(
            dataset_version_id=dv_id,
            engine_id=ENGINE_ID,
            kind="summary",
            stable_key="v1",
        )
        evidence_ids["summary"] = summary_evidence_id
        await _strict_create_evidence(
            db,
            evidence_id=summary_evidence_id,
            dataset_version_id=dv_id,
            engine_id=ENGINE_ID,
            kind="summary",
            payload={
                "summary": summary,
                "source_raw_record_id": source_raw_id,
            },
            created_at=started,
        )

        completion_time = datetime.now(timezone.utc)
        # Calculate deterministic run_id from stable inputs (not timestamp)
        # Same inputs → same run_id, enabling deterministic replay
        import hashlib
        import json
        
        stable_inputs = {
            "parameters": json.dumps(validated_parameters, sort_keys=True) if validated_parameters else "",
            "assumptions": json.dumps(assumptions_map, sort_keys=True) if assumptions_map else "",
        }
        param_hash = hashlib.sha256(json.dumps(stable_inputs, sort_keys=True).encode()).hexdigest()[:16]
        run_id = deterministic_id(dv_id, "run", param_hash)
        run_record = EnterpriseLitigationDisputeRun(
            run_id=run_id,
            dataset_version_id=dv_id,
            run_start_time=started,
            run_end_time=completion_time,
            status="completed",
            damage_payload=damage_info,
            liability_payload=liability_info,
            scenario_payload=scenario_info,
            legal_consistency_payload=consistency_info,
            assumptions=aggregated_assumptions,
            summary=summary,
            evidence_map=evidence_ids,
        )
        db.add(run_record)

        findings: list[dict[str, Any]] = []
        finding_specs = [
            (
                "damage",
                "legal_damage",
                "net_damage",
                "Damage Quantification",
                "Net legal damages after mitigation.",
                damage_info["net_damage"],
                damage_info["severity"],
                damage_info["confidence"],
                {
                    "gross_damages": damage_info["gross_damages"],
                    "mitigation": damage_info["mitigation"],
                    "severity_score": damage_info["severity_score"],
                },
            ),
            (
                "liability",
                "liability",
                "responsibility_pct",
                "Liability Assessment",
                "Estimated party liability exposure.",
                liability_info["responsibility_pct"],
                liability_info["liability_strength"],
                liability_info["confidence"],
                {
                    "responsible_party": liability_info["responsible_party"],
                    "evidence_strength": liability_info["evidence_strength"],
                    "indicators": liability_info["indicators"],
                },
            ),
            (
                "scenario",
                "scenario_analysis",
                "best_case_loss",
                "Scenario Comparison",
                "Preferred and worst-case exposures.",
                scenario_info.get("best_case", {}).get("expected_loss") if scenario_info.get("best_case") else 0.0,
                scenario_info.get("best_case", {}).get("name") if scenario_info.get("best_case") else "n/a",
                "medium",
                {
                    "total_probability": scenario_info.get("total_probability"),
                    "best_case": scenario_info.get("best_case"),
                    "worst_case": scenario_info.get("worst_case"),
                },
            ),
            (
                "legal_consistency",
                "legal_consistency",
                "consistent",
                "Legal Consistency Check",
                "Checks for conflicting statutes and missing support.",
                float(1 if consistency_info.get("consistent") else 0),
                "pass" if consistency_info.get("consistent") else "attention",
                consistency_info.get("confidence"),
                {
                    "issues": consistency_info.get("issues"),
                },
            ),
        ]

        for key, category, metric, title, description, value, status, confidence, details in finding_specs:
            finding_id = deterministic_id(dv_id, "finding", key)
            finding_payload = {
                "id": finding_id,
                "dataset_version_id": dv_id,
                "title": title,
                "category": category,
                "metric": metric,
                "description": description,
                "value": value,
                "threshold": 0.0,
                "status": status,
                "confidence": confidence,
                "details": details,
            }
            findings.append(finding_payload)
            await _strict_create_finding(
                db,
                finding_id=finding_id,
                dataset_version_id=dv_id,
                raw_record_id=source_raw_id,
                kind=category,
                payload=finding_payload,
                created_at=started,
            )
            finding_evidence_id = deterministic_evidence_id(
                dataset_version_id=dv_id,
                engine_id=ENGINE_ID,
                kind="finding",
                stable_key=finding_id,
            )
            await _strict_create_evidence(
                db,
                evidence_id=finding_evidence_id,
                dataset_version_id=dv_id,
                engine_id=ENGINE_ID,
                kind="finding",
                payload={
                    "source_raw_record_id": source_raw_id,
                    "finding": finding_payload,
                    "result_evidence_ids": evidence_ids,
                },
                created_at=started,
            )
            link_id = deterministic_id(dv_id, "link", finding_id, finding_evidence_id)
            await _strict_link(db, link_id=link_id, finding_id=finding_id, evidence_id=finding_evidence_id)
            db.add(
                EnterpriseLitigationDisputeFinding(
                    finding_id=finding_id,
                    dataset_version_id=dv_id,
                    run_id=run_id,
                    category=category,
                    metric=metric,
                    status=status,
                    confidence=confidence,
                    evidence_ids=evidence_ids,
                    payload=finding_payload,
                    created_at=started,
                )
            )

        await db.commit()

    return {
        "dataset_version_id": dv_id,
        "started_at": started.isoformat(),
        "raw_record_id": source_raw_id,
        "damage_assessment": damage_info,
        "liability_assessment": liability_info,
        "scenario_comparison": scenario_info,
        "legal_consistency": consistency_info,
        "assumptions": aggregated_assumptions,
        "findings": findings,
        "evidence": evidence_ids,
        "summary": summary,
    }
