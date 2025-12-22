from __future__ import annotations

from datetime import datetime, timezone
import logging

from sqlalchemy import select

from backend.app.core.db import get_sessionmaker
from backend.app.core.dataset.immutability import install_immutability_guards
from backend.app.core.dataset.models import DatasetVersion
from backend.app.core.dataset.raw_models import RawRecord
from backend.app.core.evidence.models import EvidenceRecord, FindingEvidenceLink, FindingRecord
from backend.app.core.evidence.service import create_evidence, create_finding, deterministic_evidence_id, link_finding_to_evidence
from backend.app.engines.enterprise_capital_debt_readiness.assumptions import resolved_assumptions
from backend.app.engines.enterprise_capital_debt_readiness.capital_adequacy import assess_capital_adequacy, capital_adequacy_payload
from backend.app.engines.enterprise_capital_debt_readiness.debt_service import assess_debt_service_ability, debt_service_payload
from backend.app.engines.enterprise_capital_debt_readiness.reporting import generate_executive_report
from backend.app.engines.enterprise_capital_debt_readiness.readiness_scores import (
    calculate_composite_readiness_score,
    load_deal_readiness_data,
    load_financial_forensics_data,
)
from backend.app.engines.enterprise_capital_debt_readiness.scenario_modeling import (
    run_scenario_analysis,
)
from backend.app.engines.enterprise_capital_debt_readiness.errors import (
    DatasetVersionInvalidError,
    DatasetVersionMissingError,
    DatasetVersionNotFoundError,
    ImmutableConflictError,
    RawRecordsMissingError,
    StartedAtInvalidError,
    StartedAtMissingError,
)
from backend.app.engines.enterprise_capital_debt_readiness.ids import deterministic_id

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


def _extract_financial(raw_payload: dict) -> dict:
    if isinstance(raw_payload.get("data"), dict):
        raw_payload = raw_payload["data"]
    financial = raw_payload.get("financial") if isinstance(raw_payload.get("financial"), dict) else raw_payload
    return financial if isinstance(financial, dict) else {}


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
            raise ImmutableConflictError("EVIDENCE_ID_COLLISION")
        existing_created_at = existing.created_at
        if existing_created_at.tzinfo is None:
            existing_created_at = existing_created_at.replace(tzinfo=timezone.utc)
        created_at_norm = created_at if created_at.tzinfo is not None else created_at.replace(tzinfo=timezone.utc)
        if existing_created_at != created_at_norm:
            raise ImmutableConflictError("IMMUTABLE_EVIDENCE_CREATED_AT_MISMATCH")
        if existing.payload != payload:
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
            raise ImmutableConflictError("FINDING_ID_COLLISION")
        if existing.payload != payload:
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

        raw_records = (await db.scalars(select(RawRecord).where(RawRecord.dataset_version_id == dv_id))).all()
        if not raw_records:
            raise RawRecordsMissingError("RAW_RECORDS_REQUIRED")
        financial = _extract_financial(raw_records[0].payload)
        source_raw_id = raw_records[0].raw_record_id

        analysis_date_str = financial.get("analysis_date") or financial.get("as_of_date")
        analysis_date = started.date()
        if isinstance(analysis_date_str, str) and analysis_date_str.strip():
            try:
                analysis_date = datetime.fromisoformat(analysis_date_str.replace("Z", "+00:00")).date()
            except ValueError:
                logger.warning("CAPDEBT_ANALYSIS_DATE_INVALID dataset_version_id=%s value=%s", dv_id, analysis_date_str)

        assumptions = resolved_assumptions(params)
        cap = assess_capital_adequacy(
            dataset_version_id=dv_id,
            analysis_date=analysis_date,
            financial=financial,
            assumptions=assumptions,
        )
        debt = assess_debt_service_ability(
            dataset_version_id=dv_id,
            analysis_date=analysis_date,
            financial=financial,
            assumptions=assumptions,
        )

        capital_payload = capital_adequacy_payload(cap)
        debt_payload = debt_service_payload(debt)

        # Load cross-engine data (optional)
        ff_data = await load_financial_forensics_data(db, dataset_version_id=dv_id)
        deal_data = await load_deal_readiness_data(db, dataset_version_id=dv_id)
        
        # Calculate composite readiness score
        readiness_result = calculate_composite_readiness_score(
            capital_adequacy=cap,
            debt_service=debt,
            financial=financial,
            assumptions=assumptions,
            ff_leakage_exposure=ff_data.get("total_leakage_exposure"),
            deal_readiness_score=deal_data.get("readiness_score"),
        )
        
        # Run scenario analysis
        from decimal import Decimal
        scenario_analysis = run_scenario_analysis(
            base_capital_adequacy=cap,
            base_debt_service=debt,
            base_readiness_score=Decimal(str(readiness_result["readiness_score"])),
            base_readiness_level=readiness_result["readiness_level"],
            base_component_scores={
                k: Decimal(str(v)) if v is not None else Decimal("0")
                for k, v in readiness_result["component_scores"].items()
            },
            financial=financial,
            assumptions=assumptions,
        )

        findings: list[dict] = []
        cap_finding_id = deterministic_id(dv_id, "finding", "capital_adequacy:v1")
        findings.append(
            {
                "id": cap_finding_id,
                "dataset_version_id": dv_id,
                "title": "capital_adequacy",
                "category": "capital_adequacy",
                "metric": "capital_coverage_ratio",
                "description": "Available capital vs required near-term operating buffer and capex.",
                "value": capital_payload.get("coverage_ratio") or 0.0,
                "threshold": 1.0,
                "is_material": cap.adequacy_level in ("weak", "insufficient_data"),
                "status": cap.adequacy_level,
                "flags": cap.flags,
            }
        )
        debt_finding_id = deterministic_id(dv_id, "finding", "debt_service:v1")
        findings.append(
            {
                "id": debt_finding_id,
                "dataset_version_id": dv_id,
                "title": "debt_service_ability",
                "category": "debt_service",
                "metric": "dscr",
                "description": "Debt service ability using scheduled debt service and estimated cash available.",
                "value": debt_payload.get("dscr") or 0.0,
                "threshold": assumptions.get("debt_service", {}).get("min_dscr", 1.25),
                "is_material": debt.ability_level in ("weak", "insufficient_data"),
                "status": debt.ability_level,
                "flags": debt.flags,
            }
        )

        capital_evidence_id = deterministic_evidence_id(
            dataset_version_id=dv_id,
            engine_id="engine_enterprise_capital_debt_readiness",
            kind="capital_adequacy",
            stable_key="v1",
        )
        await _strict_create_evidence(
            db,
            evidence_id=capital_evidence_id,
            dataset_version_id=dv_id,
            engine_id="engine_enterprise_capital_debt_readiness",
            kind="capital_adequacy",
            payload={
                "capital_adequacy": capital_payload,
                "assumptions": cap.assumptions,
                "resolved_assumptions": assumptions,
                "source_raw_record_id": source_raw_id,
            },
            created_at=started,
        )

        debt_evidence_id = deterministic_evidence_id(
            dataset_version_id=dv_id,
            engine_id="engine_enterprise_capital_debt_readiness",
            kind="debt_service",
            stable_key="v1",
        )
        await _strict_create_evidence(
            db,
            evidence_id=debt_evidence_id,
            dataset_version_id=dv_id,
            engine_id="engine_enterprise_capital_debt_readiness",
            kind="debt_service",
            payload={
                "debt_service": debt_payload,
                "assumptions": debt.assumptions,
                "resolved_assumptions": assumptions,
                "source_raw_record_id": source_raw_id,
            },
            created_at=started,
        )

        # Create readiness score finding
        readiness_finding_id = deterministic_id(dv_id, "finding", "readiness_score:v1")
        findings.append(
            {
                "id": readiness_finding_id,
                "dataset_version_id": dv_id,
                "title": "composite_readiness_score",
                "category": "readiness_score",
                "metric": "readiness_score",
                "description": "Composite readiness score integrating capital adequacy, debt service, credit risk, and cross-engine data.",
                "value": readiness_result["readiness_score"],
                "threshold": 70.0,  # Good threshold
                "is_material": readiness_result["readiness_level"] in ("weak", "adequate"),
                "status": readiness_result["readiness_level"],
                "flags": [],
            }
        )

        # Create scenario analysis evidence
        scenario_evidence_id = deterministic_evidence_id(
            dataset_version_id=dv_id,
            engine_id="engine_enterprise_capital_debt_readiness",
            kind="scenario_analysis",
            stable_key="v1",
        )
        await _strict_create_evidence(
            db,
            evidence_id=scenario_evidence_id,
            dataset_version_id=dv_id,
            engine_id="engine_enterprise_capital_debt_readiness",
            kind="scenario_analysis",
            payload={
                "scenario_analysis": scenario_analysis,
                "source_raw_record_id": source_raw_id,
            },
            created_at=started,
        )

        # Create readiness score evidence
        readiness_evidence_id = deterministic_evidence_id(
            dataset_version_id=dv_id,
            engine_id="engine_enterprise_capital_debt_readiness",
            kind="readiness_score",
            stable_key="v1",
        )
        await _strict_create_evidence(
            db,
            evidence_id=readiness_evidence_id,
            dataset_version_id=dv_id,
            engine_id="engine_enterprise_capital_debt_readiness",
            kind="readiness_score",
            payload={
                "readiness_score": readiness_result,
                "cross_engine_data": {
                    "financial_forensics": ff_data,
                    "deal_readiness": deal_data,
                },
                "source_raw_record_id": source_raw_id,
            },
            created_at=started,
        )

        summary = {
            "dataset_version_id": dv_id,
            "analysis_date": analysis_date.isoformat(),
            "readiness_score": readiness_result["readiness_score"],
            "readiness_level": readiness_result["readiness_level"],
            "capital_adequacy": capital_payload,
            "debt_service": debt_payload,
            "findings": findings,
            "evidence": {
                "capital_adequacy": capital_evidence_id,
                "debt_service": debt_evidence_id,
                "readiness_score": readiness_evidence_id,
                "scenario_analysis": scenario_evidence_id,
            },
            "readiness_breakdown": {
                "component_scores": readiness_result["component_scores"],
                "credit_risk_details": readiness_result["credit_risk_details"],
                "breakdown": readiness_result["breakdown"],
                "cross_engine_data": {
                    "financial_forensics": {
                        "has_data": ff_data.get("has_data", False),
                        "total_exposure": float(ff_data.get("total_leakage_exposure")) if ff_data.get("total_leakage_exposure") else None,
                        "findings_count": ff_data.get("findings_count", 0),
                    },
                    "deal_readiness": {
                        "has_data": deal_data.get("has_data", False),
                        "readiness_score": float(deal_data.get("readiness_score")) if deal_data.get("readiness_score") else None,
                        "findings_count": deal_data.get("findings_count", 0),
                    },
                },
            },
            "scenario_analysis": scenario_analysis,
        }

        summary_evidence_id = deterministic_evidence_id(
            dataset_version_id=dv_id,
            engine_id="engine_enterprise_capital_debt_readiness",
            kind="summary",
            stable_key="v1",
        )
        await _strict_create_evidence(
            db,
            evidence_id=summary_evidence_id,
            dataset_version_id=dv_id,
            engine_id="engine_enterprise_capital_debt_readiness",
            kind="summary",
            payload={"summary": summary},
            created_at=started,
        )

        report_evidence_ids = [
            capital_evidence_id,
            debt_evidence_id,
            readiness_evidence_id,
            scenario_evidence_id,
            summary_evidence_id,
        ]
        executive_report = generate_executive_report(
            dataset_version_id=dv_id,
            generated_at=started.isoformat(),
            readiness_result=readiness_result,
            capital_adequacy=capital_payload,
            debt_service=debt_payload,
            assumptions=assumptions,
            cross_engine_data={
                "financial_forensics": ff_data,
                "deal_readiness": deal_data,
            },
            findings=findings,
            evidence_ids=report_evidence_ids,
        )
        executive_report_evidence_id = deterministic_evidence_id(
            dataset_version_id=dv_id,
            engine_id="engine_enterprise_capital_debt_readiness",
            kind="executive_report",
            stable_key="v1",
        )
        await _strict_create_evidence(
            db,
            evidence_id=executive_report_evidence_id,
            dataset_version_id=dv_id,
            engine_id="engine_enterprise_capital_debt_readiness",
            kind="executive_report",
            payload={
                "executive_report": executive_report,
                "source_raw_record_id": source_raw_id,
            },
            created_at=started,
        )
        summary["executive_report"] = executive_report
        summary["evidence"]["executive_report"] = executive_report_evidence_id

        for f in findings:
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
                engine_id="engine_enterprise_capital_debt_readiness",
                kind="finding",
                stable_key=finding_id,
            )
            # Link to appropriate evidence based on finding category
            related_evidence_ids = {
                "capital_adequacy": capital_evidence_id,
                "debt_service": debt_evidence_id,
                "readiness_score": readiness_evidence_id,
            }
            related_evidence_id = related_evidence_ids.get(f["category"], summary_evidence_id)
            
            await _strict_create_evidence(
                db,
                evidence_id=ev_id,
                dataset_version_id=dv_id,
                engine_id="engine_enterprise_capital_debt_readiness",
                kind="finding",
                payload={
                    "source_raw_record_id": source_raw_id,
                    "finding": f,
                    "capital_evidence_id": capital_evidence_id,
                    "debt_evidence_id": debt_evidence_id,
                    "readiness_evidence_id": readiness_evidence_id,
                    "scenario_evidence_id": scenario_evidence_id,
                    "summary_evidence_id": summary_evidence_id,
                },
                created_at=started,
            )
            link_id = deterministic_id(dv_id, "link", finding_id, ev_id)
            await _strict_link(db, link_id=link_id, finding_id=finding_id, evidence_id=ev_id)

        await db.commit()

    return summary
