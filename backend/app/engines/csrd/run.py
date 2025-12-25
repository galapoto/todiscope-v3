from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import logging

from sqlalchemy import select

from backend.app.core.db import get_sessionmaker
from backend.app.core.dataset.immutability import install_immutability_guards
from backend.app.core.dataset.models import DatasetVersion
from backend.app.core.dataset.service import load_raw_records
from backend.app.core.workflows.service import resolve_strict_mode
from backend.app.core.evidence.service import create_evidence, create_finding, deterministic_evidence_id, link_finding_to_evidence
from backend.app.core.evidence.models import EvidenceRecord, FindingEvidenceLink, FindingRecord
from backend.app.engines.csrd.emissions import calculate_emissions
from backend.app.core.governance import log_model_call, log_rag_event, log_tool_call
from backend.app.engines.csrd.engine import ENGINE_ID, ENGINE_VERSION
from backend.app.engines.csrd.errors import (
    DatasetVersionInvalidError,
    DatasetVersionMissingError,
    DatasetVersionNotFoundError,
    ImmutableConflictError,
    RawRecordsMissingError,
    StartedAtInvalidError,
    StartedAtMissingError,
)
from backend.app.engines.csrd.ids import deterministic_id
from backend.app.engines.csrd.materiality import assess_double_materiality
from backend.app.engines.csrd.reporting import generate_esrs_report

logger = logging.getLogger(__name__)


def _parse_started_at(value: object) -> datetime:
    if value is None:
        raise StartedAtMissingError("STARTED_AT_REQUIRED")
    if not isinstance(value, str) or not value.strip():
        raise StartedAtInvalidError("STARTED_AT_INVALID")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as e:
        raise StartedAtInvalidError("STARTED_AT_INVALID") from e
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _validate_dataset_version_id(value: object) -> str:
    if value is None:
        raise DatasetVersionMissingError("DATASET_VERSION_ID_REQUIRED")
    if not isinstance(value, str) or not value.strip():
        raise DatasetVersionInvalidError("DATASET_VERSION_ID_INVALID")
    return value.strip()


def _extract_inputs(raw_payload: dict) -> tuple[dict, dict]:
    if isinstance(raw_payload.get("data"), dict):
        raw_payload = raw_payload["data"]
    esg = raw_payload.get("esg") if isinstance(raw_payload.get("esg"), dict) else {}
    financial = raw_payload.get("financial") if isinstance(raw_payload.get("financial"), dict) else {}
    return esg, financial


async def _strict_create_evidence(
    db,
    *,
    evidence_id: str,
    dataset_version_id: str,
    engine_id: str,
    kind: str,
    payload: dict,
    created_at: datetime,
) -> EvidenceRecord:
    existing = await db.scalar(select(EvidenceRecord).where(EvidenceRecord.evidence_id == evidence_id))
    if existing is not None:
        if existing.dataset_version_id != dataset_version_id or existing.engine_id != engine_id or existing.kind != kind:
            logger.warning(
                "CSRD_IMMUTABLE_CONFLICT evidence_id_collision evidence_id=%s dataset_version_id=%s",
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
                "CSRD_IMMUTABLE_CONFLICT evidence_created_at_mismatch evidence_id=%s dataset_version_id=%s",
                evidence_id,
                dataset_version_id,
            )
            raise ImmutableConflictError("IMMUTABLE_EVIDENCE_CREATED_AT_MISMATCH")
        if existing.payload != payload:
            logger.warning(
                "CSRD_IMMUTABLE_CONFLICT evidence_payload_mismatch evidence_id=%s dataset_version_id=%s",
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
    payload: dict,
    created_at: datetime,
) -> FindingRecord:
    existing = await db.scalar(select(FindingRecord).where(FindingRecord.finding_id == finding_id))
    if existing is not None:
        if existing.dataset_version_id != dataset_version_id or existing.raw_record_id != raw_record_id or existing.kind != kind:
            logger.warning(
                "CSRD_IMMUTABLE_CONFLICT finding_id_collision finding_id=%s dataset_version_id=%s",
                finding_id,
                dataset_version_id,
            )
            raise ImmutableConflictError("FINDING_ID_COLLISION")
        if existing.payload != payload:
            logger.warning(
                "CSRD_IMMUTABLE_CONFLICT finding_payload_mismatch finding_id=%s dataset_version_id=%s",
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
                "CSRD_IMMUTABLE_CONFLICT link_mismatch link_id=%s dataset_version_id=%s",
                link_id,
                "unknown",
            )
            raise ImmutableConflictError("IMMUTABLE_LINK_MISMATCH")
        return existing
    return await link_finding_to_evidence(db, link_id=link_id, finding_id=finding_id, evidence_id=evidence_id)


async def run_engine(*, dataset_version_id: object, started_at: object, parameters: dict | None = None) -> dict:
    install_immutability_guards()
    dv_id = _validate_dataset_version_id(dataset_version_id)
    started = _parse_started_at(started_at)
    params = parameters or {}

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        dv = await db.scalar(select(DatasetVersion).where(DatasetVersion.id == dv_id))
        if dv is None:
            raise DatasetVersionNotFoundError("DATASET_VERSION_NOT_FOUND")

        strict_mode_override = params.get("strict_mode") if isinstance(params.get("strict_mode"), bool) else None
        strict_mode = await resolve_strict_mode(db, workflow_id=ENGINE_ID, override=strict_mode_override)
        raw_records = await load_raw_records(
            db,
            dataset_version_id=dv_id,
            verify_checksums=True,
            strict_mode=strict_mode,
        )
        if not raw_records:
            raise RawRecordsMissingError("RAW_RECORDS_REQUIRED")
        esg, financial = _extract_inputs(raw_records[0].payload)
        source_raw_id = raw_records[0].raw_record_id
        rag_sources = [
            {
                "source_type": "RawRecord",
                "raw_record_id": r.raw_record_id,
                "dataset_version_id": r.dataset_version_id,
            }
            for r in raw_records
        ]
        await log_rag_event(
            db,
            engine_id=ENGINE_ID,
            dataset_version_id=dv_id,
            rag_sources=rag_sources,
            context_id=source_raw_id,
            governance_metadata={
                "confidence_score": None,
                "decision_boundary": "raw_record_retrieval",
                "retrieved_records": len(raw_records),
            },
            timestamp=started,
        )

        warnings: list[str] = []
        emissions_dict = esg.get("emissions") if isinstance(esg.get("emissions"), dict) else None
        if not emissions_dict:
            warnings.append("MISSING_ESG_EMISSIONS")
        if not isinstance(financial, dict) or not financial:
            warnings.append("MISSING_FINANCIAL_DATA")
        if warnings:
            logger.warning("CSRD_DATA_INTEGRITY_WARNINGS dataset_version_id=%s warnings=%s", dv_id, warnings)

        emissions_res = calculate_emissions(dataset_version_id=dv_id, esg=esg, parameters=params)
        total_emissions = sum(emissions_res.totals_tco2e.values())
        emissions_event_outputs = {
            "dataset_version_id": dv_id,
            "totals_tco2e": emissions_res.totals_tco2e,
            "factors": {scope: asdict(factor) for scope, factor in emissions_res.factors.items()},
            "assumptions": emissions_res.assumptions,
        }
        await log_model_call(
            db,
            engine_id=ENGINE_ID,
            dataset_version_id=dv_id,
            model_identifier="csrd.calculate_emissions",
            model_version=ENGINE_VERSION,
            inputs={"esg": esg, "parameters": params},
            outputs=emissions_event_outputs,
            context_id=source_raw_id,
            governance_metadata={
                "confidence_score": None,
                "decision_boundary": "deterministic_emissions_calc",
                "warnings": warnings,
            },
            timestamp=started,
            event_label="emissions_calculation",
        )

        findings_dc, assumptions_dc = assess_double_materiality(
            dataset_version_id=dv_id,
            esg=esg,
            financial=financial,
            total_emissions_tco2e=total_emissions,
            parameters=params,
        )

        assumptions: list[dict] = [
            {
                "id": a.assumption_id,
                "description": a.description,
                "source": a.source,
                "impact": a.impact,
                "sensitivity": a.sensitivity,
            }
            for a in assumptions_dc
        ] + list(emissions_res.assumptions)

        material_findings: list[dict] = []
        if warnings:
            material_findings.append(
                {
                    "id": deterministic_id(dv_id, "finding", "data_gap:missing_inputs"),
                    "dataset_version_id": dv_id,
                    "title": "data_gap: missing inputs",
                    "category": "data_quality",
                    "metric": "data_gap",
                    "description": "Data gap: missing required inputs for full CSRD assessment.",
                    "value": 0.0,
                    "threshold": 1.0,
                    "is_material": True,
                    "materiality": "material",
                    "financial_impact_eur": 0.0,
                    "impact_score": 0.0,
                    "confidence": "low",
                    "warnings": warnings,
                }
            )
        for f in findings_dc:
            materiality = "material" if f.is_material else "not_material"
            material_findings.append(
                {
                    "id": deterministic_id(dv_id, "finding", f.stable_key),
                    "dataset_version_id": dv_id,
                    "title": f"{f.category}: {f.metric}",
                    "category": f.category,
                    "metric": f.metric,
                    "description": f.description,
                    "value": f.value,
                    "threshold": f.threshold,
                    "is_material": bool(f.is_material),
                    "materiality": materiality,
                    "financial_impact_eur": f.financial_impact_eur,
                    "impact_score": f.impact_score,
                    "confidence": f.confidence,
                }
            )

        emissions_payload = {
            "dataset_version_id": dv_id,
            "scopes": {
                k: {
                    "value": v.value,
                    "unit": v.unit,
                    "source": v.source,
                    "methodology": v.methodology,
                }
                for k, v in emissions_res.factors.items()
            },
            "total_emissions_tco2e": total_emissions,
        }

        emissions_evidence_id = deterministic_evidence_id(
            dataset_version_id=dv_id, engine_id="engine_csrd", kind="emissions", stable_key="scopes_v1"
        )
        await _strict_create_evidence(
            db,
            evidence_id=emissions_evidence_id,
            dataset_version_id=dv_id,
            engine_id="engine_csrd",
            kind="emissions",
            payload={"emissions": emissions_payload, "assumptions": emissions_res.assumptions, "source_raw_record_id": source_raw_id},
            created_at=started,
        )

        report_id = deterministic_id(dv_id, "report", "v1")
        report = generate_esrs_report(
            report_id=report_id,
            dataset_version_id=dv_id,
            material_findings=material_findings,
            emissions=emissions_payload,
            assumptions=assumptions,
            parameters=params,
            generated_at=started.isoformat(),
            warnings=warnings,
        )
        await log_tool_call(
            db,
            engine_id=ENGINE_ID,
            dataset_version_id=dv_id,
            tool_name="generate_esrs_report",
            inputs={
                "report_id": report_id,
                "material_findings": material_findings,
                "emissions": emissions_payload,
                "assumptions": assumptions,
                "parameters": params,
                "warnings": warnings,
            },
            outputs=report,
            model_identifier="csrd.reporting",
            context_id=report_id,
            governance_metadata={
                "confidence_score": None,
                "decision_boundary": "esrs_structure",
                "warnings": warnings,
            },
            event_label="esrs_report_generation",
            timestamp=started,
        )

        # Persist traceability in core evidence + finding tables (append-only).
        report_evidence_id = deterministic_evidence_id(
            dataset_version_id=dv_id, engine_id="engine_csrd", kind="report", stable_key="report"
        )
        await _strict_create_evidence(
            db,
            evidence_id=report_evidence_id,
            dataset_version_id=dv_id,
            engine_id="engine_csrd",
            kind="report",
            payload={"report": report},
            created_at=started,
        )

        for f in material_findings:
            finding_id = f["id"]
            await _strict_create_finding(
                db,
                finding_id=finding_id,
                dataset_version_id=dv_id,
                raw_record_id=source_raw_id,
                kind=f["category"],
                payload=f,
                created_at=started,
            )
            ev_id = deterministic_evidence_id(
                dataset_version_id=dv_id,
                engine_id="engine_csrd",
                kind="finding",
                stable_key=finding_id,
            )
            await _strict_create_evidence(
                db,
                evidence_id=ev_id,
                dataset_version_id=dv_id,
                engine_id="engine_csrd",
                kind="finding",
                payload={
                    "source_raw_record_id": source_raw_id,
                    "finding": f,
                    "assumptions": assumptions,
                    "emissions_evidence_id": emissions_evidence_id,
                },
                created_at=started,
            )
            link_id = deterministic_id(dv_id, "link", finding_id, ev_id)
            await _strict_link(db, link_id=link_id, finding_id=finding_id, evidence_id=ev_id)

        await db.commit()

    return {
        "dataset_version_id": dv_id,
        "started_at": started.isoformat(),
        "total_emissions_tco2e": total_emissions,
        "material_findings": material_findings,
        "assumptions": assumptions,
        "report": report,
        "emissions_evidence_id": emissions_evidence_id,
        "report_evidence_id": report_evidence_id,
    }
