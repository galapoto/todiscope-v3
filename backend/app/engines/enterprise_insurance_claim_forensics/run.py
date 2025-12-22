"""Entry point for the Enterprise Insurance Claim Forensics engine."""

from __future__ import annotations

import logging

from collections import defaultdict
from datetime import datetime, timezone
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
from backend.app.engines.enterprise_insurance_claim_forensics.analysis import (
    PAYMENT_INDICATORS,
    SEVERITY_FACTORS,
    analyze_claim_portfolio,
    extract_claims_and_transactions,
)
from backend.app.engines.enterprise_insurance_claim_forensics.readiness_scores import (
    calculate_portfolio_readiness_score,
    calculate_claim_readiness_score,
)
from backend.app.engines.enterprise_insurance_claim_forensics.remediation import (
    build_remediation_tasks,
)
from backend.app.core.review.service import ensure_review_item
from backend.app.engines.enterprise_insurance_claim_forensics.audit_trail import AuditTrail
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
from backend.app.engines.enterprise_insurance_claim_forensics.constants import ENGINE_ID
from backend.app.engines.enterprise_insurance_claim_forensics.ids import deterministic_id
from backend.app.engines.enterprise_insurance_claim_forensics.models import (
    EnterpriseInsuranceClaimForensicsFinding,
    EnterpriseInsuranceClaimForensicsRun,
)

logger = logging.getLogger(__name__)

MODEL_ASSUMPTIONS = [
    {"name": "payment_indicators", "value": list(sorted(PAYMENT_INDICATORS))},
    {"name": "severity_factors", "value": SEVERITY_FACTORS},
    {
        "name": "range_buffer_strategy",
        "value": "max(2% of claim amount, 50% of evidence delta)",
    },
]


def _parse_started_at(value: object) -> datetime:
    if value is None:
        raise StartedAtMissingError("STARTED_AT_REQUIRED")
    if not isinstance(value, str) or not value.strip():
        raise StartedAtInvalidError("STARTED_AT_INVALID")
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
        raise ParametersInvalidError("PARAMETERS_INVALID")
    return value


def _collect_assumptions(parameters: dict[str, Any]) -> list[dict[str, Any]]:
    raw = parameters.get("assumptions")
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    return []


def _build_evidence_maps(
    entries: list[dict[str, Any]]
) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    evidence_map: dict[str, list[str]] = {}
    claim_map: dict[str, list[str]] = defaultdict(list)
    for entry in entries:
        evidence_id = entry.get("evidence_id")
        if not evidence_id:
            continue
        claim_id = entry.get("claim_id")
        key = claim_id or entry.get("action_type", "audit")
        evidence_map.setdefault(key, []).append(evidence_id)
        if claim_id:
            claim_map[claim_id].append(evidence_id)
    return evidence_map, claim_map


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
                "INSURANCE_CLAIM_IMMUTABLE_CONFLICT evidence_id_collision evidence_id=%s dataset_version_id=%s",
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
                "INSURANCE_CLAIM_IMMUTABLE_CONFLICT evidence_created_at_mismatch evidence_id=%s dataset_version_id=%s",
                evidence_id,
                dataset_version_id,
            )
            raise ImmutableConflictError("IMMUTABLE_EVIDENCE_CREATED_AT_MISMATCH")
        if existing.payload != payload:
            logger.warning(
                "INSURANCE_CLAIM_IMMUTABLE_CONFLICT evidence_payload_mismatch evidence_id=%s dataset_version_id=%s",
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
                "INSURANCE_CLAIM_IMMUTABLE_CONFLICT finding_id_collision finding_id=%s dataset_version_id=%s",
                finding_id,
                dataset_version_id,
            )
            raise ImmutableConflictError("FINDING_ID_COLLISION")
        if existing.payload != payload:
            logger.warning(
                "INSURANCE_CLAIM_IMMUTABLE_CONFLICT finding_payload_mismatch finding_id=%s dataset_version_id=%s",
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
                "INSURANCE_CLAIM_IMMUTABLE_CONFLICT link_mismatch link_id=%s",
                link_id,
            )
            raise ImmutableConflictError("IMMUTABLE_LINK_MISMATCH")
        return existing
    return await link_finding_to_evidence(db, link_id=link_id, finding_id=finding_id, evidence_id=evidence_id)


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
    """Create evidence with immutability conflict detection."""
    existing = await db.scalar(select(EvidenceRecord).where(EvidenceRecord.evidence_id == evidence_id))
    if existing is not None:
        if existing.dataset_version_id != dataset_version_id or existing.engine_id != engine_id or existing.kind != kind:
            logger.warning(
                "INSURANCE_CLAIM_IMMUTABLE_CONFLICT evidence_id_collision evidence_id=%s dataset_version_id=%s",
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
                "INSURANCE_CLAIM_IMMUTABLE_CONFLICT evidence_created_at_mismatch evidence_id=%s dataset_version_id=%s",
                evidence_id,
                dataset_version_id,
            )
            raise ImmutableConflictError("IMMUTABLE_EVIDENCE_CREATED_AT_MISMATCH")
        if existing.payload != payload:
            logger.warning(
                "INSURANCE_CLAIM_IMMUTABLE_CONFLICT evidence_payload_mismatch evidence_id=%s dataset_version_id=%s",
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
    """Create finding with immutability conflict detection."""
    existing = await db.scalar(select(FindingRecord).where(FindingRecord.finding_id == finding_id))
    if existing is not None:
        if (
            existing.dataset_version_id != dataset_version_id
            or existing.raw_record_id != raw_record_id
            or existing.kind != kind
        ):
            logger.warning(
                "INSURANCE_CLAIM_IMMUTABLE_CONFLICT finding_id_collision finding_id=%s dataset_version_id=%s",
                finding_id,
                dataset_version_id,
            )
            raise ImmutableConflictError("FINDING_ID_COLLISION")
        if existing.payload != payload:
            logger.warning(
                "INSURANCE_CLAIM_IMMUTABLE_CONFLICT finding_payload_mismatch finding_id=%s dataset_version_id=%s",
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


async def _persist_findings(
    db,
    *,
    run_id: str,
    dataset_version_id: str,
    exposures: list[dict[str, Any]],
    validations: dict[str, dict[str, Any]],
    evidence_lookup: dict[str, list[str]],
    claim_to_raw_record: dict[str, str],
    created_at: datetime,
) -> list[dict[str, Any]]:
    """Persist findings using core services with raw_record_id linkage and evidence linking."""
    extra_entries: list[dict[str, Any]] = []
    for exposure in exposures:
        claim_id = exposure.get("claim_id")
        if not claim_id:
            continue

        raw_record_id = claim_to_raw_record.get(claim_id)
        if not raw_record_id:
            raise ClaimPayloadMissingError("CLAIM_RAW_RECORD_ID_REQUIRED")

        validation = validations.get(claim_id, {})
        outstanding = exposure.get("outstanding_exposure", 0.0)
        is_valid = validation.get("is_valid", False)
        status = "validated" if outstanding == 0 and is_valid else "review"
        confidence = "high" if status == "validated" else "medium"

        finding_id = deterministic_id(dataset_version_id, run_id, claim_id, "loss_exposure")
        finding_payload = {
            "id": finding_id,
            "dataset_version_id": dataset_version_id,
            "claim_id": claim_id,
            "category": "claim_forensics",
            "metric": "loss_exposure",
            "status": status,
            "confidence": confidence,
            "exposure": exposure,
            "validation": validation,
        }

        await _strict_create_finding(
            db,
            finding_id=finding_id,
            dataset_version_id=dataset_version_id,
            raw_record_id=raw_record_id,
            kind="claim_forensics",
            payload=finding_payload,
            created_at=created_at,
        )

        finding_evidence_id = deterministic_evidence_id(
            dataset_version_id=dataset_version_id,
            engine_id=ENGINE_ID,
            kind="loss_exposure",
            stable_key=f"{run_id}|{claim_id}|{finding_id}",
        )
        await _strict_create_evidence(
            db,
            evidence_id=finding_evidence_id,
            dataset_version_id=dataset_version_id,
            engine_id=ENGINE_ID,
            kind="loss_exposure",
            payload={
                "source_raw_record_id": raw_record_id,
                "finding": finding_payload,
                "exposure": exposure,
                "validation": validation,
                "audit_trail_evidence_ids": list(evidence_lookup.get(claim_id, [])),
            },
            created_at=created_at,
        )

        link_id = deterministic_id(dataset_version_id, run_id, claim_id, "loss_exposure_link")
        await _strict_link(
            db,
            link_id=link_id,
            finding_id=finding_id,
            evidence_id=finding_evidence_id,
        )

        engine_finding = EnterpriseInsuranceClaimForensicsFinding(
            finding_id=finding_id,
            dataset_version_id=dataset_version_id,
            run_id=run_id,
            category="claim_forensics",
            metric="loss_exposure",
            status=status,
            confidence=confidence,
            evidence_ids={
                "audit_trail": list(evidence_lookup.get(claim_id, [])),
                "loss_exposure": [finding_evidence_id],
            },
            payload=finding_payload,
            created_at=created_at,
        )
        db.add(engine_finding)
        
        # Create review item for findings requiring review
        if status == "review":
            try:
                await ensure_review_item(
                    db,
                    dataset_version_id=dataset_version_id,
                    engine_id=ENGINE_ID,
                    subject_type="finding",
                    subject_id=finding_id,
                    created_at=created_at,
                )
            except Exception as e:
                logger.warning(
                    "Failed to create review item for finding %s: %s",
                    finding_id,
                    e,
                )

        extra_entries.append(
            {
                "evidence_id": finding_evidence_id,
                "action_type": "loss_exposure_evidence",
                "claim_id": claim_id,
                "finding_id": finding_id,
                "timestamp": created_at.isoformat(),
            }
        )
    return extra_entries


async def run_engine(*, dataset_version_id: object, started_at: object, parameters: object | None = None) -> dict[str, Any]:
    install_immutability_guards()
    dv_id = _validate_dataset_version_id(dataset_version_id)
    started = _parse_started_at(started_at)
    validated_parameters = _validate_parameters(parameters)
    assumptions = MODEL_ASSUMPTIONS + _collect_assumptions(validated_parameters)

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        dataset_version = await db.scalar(select(DatasetVersion).where(DatasetVersion.id == dv_id))
        if dataset_version is None:
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
        records_with_raw = [(record.raw_record_id, record.payload) for record in normalized_records]
        claims, transactions, claim_raw_map = extract_claims_and_transactions(records_with_raw, dv_id)
        if not claims:
            raise ClaimPayloadMissingError("CLAIMS_REQUIRED")

        exposures, portfolio_summary, validation_results, validation_summary = analyze_claim_portfolio(
            claims, transactions
        )

        # Calculate readiness scores
        readiness_scores_result = calculate_portfolio_readiness_score(
            exposures=exposures,
            validation_results=validation_results,
        )

        # Calculate run_id for remediation tasks
        run_id = deterministic_id(dv_id, started.isoformat())
        
        # Build remediation tasks
        remediation_tasks = build_remediation_tasks(
            dataset_version_id=dv_id,
            run_id=run_id,
            exposures=exposures,
            validation_results=validation_results,
            readiness_scores=readiness_scores_result.get("claim_scores"),
        )

        audit = AuditTrail(db, dataset_version_id=dv_id)
        for claim in claims:
            await audit.log_claim_creation(claim, created_at=started)
        for transaction in transactions:
            await audit.log_transaction(transaction, created_at=transaction.transaction_date)

        exposure_lookup = {detail["claim_id"]: detail for detail in exposures if detail.get("claim_id")}
        for claim in claims:
            claim_id = claim.claim_id
            validation_payload = validation_results.get(claim_id, {})
            await audit.log_validation_result(claim_id, validation_payload, validated_at=started)
            exposure_payload = exposure_lookup.get(claim_id)
            if exposure_payload is not None:
                await audit.log_forensic_analysis(
                    claim_id,
                    analysis_type="loss_exposure",
                    analysis_result=exposure_payload,
                    analyzed_at=started,
                )

        completed = datetime.now(timezone.utc)
        base_entries = audit.get_entries()
        _, claim_evidence = _build_evidence_maps(base_entries)
        extra_entries = await _persist_findings(
            db,
            run_id=run_id,
            dataset_version_id=dv_id,
            exposures=exposures,
            validations=validation_results,
            evidence_lookup=claim_evidence,
            claim_to_raw_record=claim_raw_map,
            created_at=completed,
        )
        all_entries = base_entries + extra_entries
        evidence_map, _ = _build_evidence_maps(all_entries)

        run_record = EnterpriseInsuranceClaimForensicsRun(
            run_id=run_id,
            dataset_version_id=dv_id,
            run_start_time=started,
            run_end_time=completed,
            status="completed",
            claim_summary=portfolio_summary,
            validation_results=validation_results,
            audit_trail_summary=audit.get_summary(),
            assumptions=assumptions,
            evidence_map=evidence_map,
        )
        db.add(run_record)
        await db.commit()

    return {
        "run_id": run_id,
        "dataset_version_id": dv_id,
        "status": run_record.status,
        "loss_exposures": exposures,
        "claim_summary": portfolio_summary,
        "validation_summary": validation_summary,
        "validation_results": validation_results,
        "readiness_scores": readiness_scores_result,
        "remediation_tasks": remediation_tasks,
        "assumptions": assumptions,
        "audit_trail_summary": audit.get_summary(),
    }
