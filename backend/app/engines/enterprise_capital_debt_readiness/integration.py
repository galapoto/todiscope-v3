from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import Table, Column, String, Numeric, DateTime, JSON, MetaData, select, desc
from sqlalchemy.ext.asyncio import AsyncSession

_metadata = MetaData()

_ff_leakage_table = Table(
    "engine_financial_forensics_leakage_items",
    _metadata,
    Column("leakage_item_id", String),
    Column("run_id", String),
    Column("finding_id", String),
    Column("dataset_version_id", String),
    Column("typology", String),
    Column("exposure_abs", Numeric(38, 12)),
    Column("exposure_signed", Numeric(38, 12)),
    Column("created_at", DateTime(timezone=True)),
)

_ff_findings_table = Table(
    "engine_financial_forensics_findings",
    _metadata,
    Column("finding_id", String),
    Column("primary_evidence_item_id", String),
    Column("rule_id", String),
    Column("rule_version", String),
    Column("framework_version", String),
    Column("finding_type", String),
    Column("confidence", String),
)

_deal_runs_table = Table(
    "engine_enterprise_deal_transaction_readiness_runs",
    _metadata,
    Column("run_id", String),
    Column("result_set_id", String),
    Column("dataset_version_id", String),
    Column("started_at", DateTime(timezone=True)),
    Column("status", String),
    Column("transaction_scope", JSON),
    Column("parameters", JSON),
    Column("optional_inputs", JSON),
)

_deal_findings_table = Table(
    "engine_enterprise_deal_transaction_readiness_findings",
    _metadata,
    Column("finding_id", String),
    Column("result_set_id", String),
    Column("kind", String),
    Column("severity", String),
    Column("title", String),
    Column("detail", JSON),
    Column("evidence_id", String),
)


def _decimal_to_float(value: Decimal | None) -> float | None:
    if value is None:
        return None
    return float(value)


async def load_financial_forensics_insights(
    db: AsyncSession, *, dataset_version_id: str
) -> dict[str, Any] | None:
    rows = (
        await db.execute(
            select(_ff_leakage_table).where(
                _ff_leakage_table.c.dataset_version_id == dataset_version_id
            )
        )
    ).mappings().all()
    if not rows:
        return None

    total_abs = Decimal("0")
    total_signed = Decimal("0")
    typology_summary: dict[str, dict[str, Any]] = {}
    for row in rows:
        abs_value = Decimal(row["exposure_abs"]) if row["exposure_abs"] is not None else Decimal("0")
        signed_value = Decimal(row["exposure_signed"]) if row["exposure_signed"] is not None else Decimal("0")
        total_abs += abs_value
        total_signed += signed_value
        typology = str(row["typology"] or "unknown")
        bucket = typology_summary.setdefault(typology, {"count": 0, "exposure_abs": Decimal("0")})
        bucket["count"] += 1
        bucket["exposure_abs"] += abs_value

    finding_ids = sorted({str(row["finding_id"]) for row in rows if row["finding_id"]})
    findings = []
    source_evidence_ids: list[str] = []
    if finding_ids:
        finding_rows = (
            await db.execute(
                select(_ff_findings_table).where(_ff_findings_table.c.finding_id.in_(finding_ids))
            )
        ).mappings().all()
        for finding in finding_rows:
            findings.append(
                {
                    "finding_id": finding["finding_id"],
                    "rule_id": finding["rule_id"],
                    "rule_version": finding["rule_version"],
                    "framework_version": finding["framework_version"],
                    "finding_type": finding["finding_type"],
                    "confidence": finding["confidence"],
                    "primary_evidence_id": finding["primary_evidence_item_id"],
                }
            )
            primary_evidence_id = finding["primary_evidence_item_id"]
            if primary_evidence_id:
                source_evidence_ids.append(primary_evidence_id)

    items = [
        {
            "leakage_item_id": row["leakage_item_id"],
            "typology": row["typology"],
            "exposure_abs": _decimal_to_float(Decimal(row["exposure_abs"])) if row["exposure_abs"] is not None else None,
            "exposure_signed": _decimal_to_float(Decimal(row["exposure_signed"])) if row["exposure_signed"] is not None else None,
            "finding_id": row["finding_id"],
        }
        for row in rows
    ]

    typology_summary_out = {
        typ: {
            "count": data["count"],
            "exposure_abs": _decimal_to_float(data["exposure_abs"]),
        }
        for typ, data in typology_summary.items()
    }

    return {
        "total_exposure_abs": _decimal_to_float(total_abs),
        "total_exposure_signed": _decimal_to_float(total_signed),
        "items": items,
        "typology_summary": typology_summary_out,
        "source_findings": findings,
        "source_evidence_ids": sorted(set(source_evidence_ids)),
    }


async def load_deal_readiness_insights(
    db: AsyncSession, *, dataset_version_id: str
) -> dict[str, Any] | None:
    run_row = (
        await db.execute(
            select(_deal_runs_table)
            .where(_deal_runs_table.c.dataset_version_id == dataset_version_id)
            .order_by(desc(_deal_runs_table.c.started_at))
            .limit(1)
        )
    ).mappings().first()
    if not run_row:
        return None

    findings_rows = (
        await db.execute(
            select(_deal_findings_table)
            .where(_deal_findings_table.c.result_set_id == run_row["result_set_id"])
            .order_by(_deal_findings_table.c.finding_id)
        )
    ).mappings().all()

    high_findings = sum(1 for row in findings_rows if row["severity"] == "high")
    total_findings = len(findings_rows)
    readiness_status = "ready" if high_findings == 0 else "gaps_present"

    return {
        "run_id": run_row["run_id"],
        "result_set_id": run_row["result_set_id"],
        "status": run_row["status"],
        "transaction_scope": run_row["transaction_scope"],
        "parameters": run_row["parameters"],
        "optional_inputs": run_row["optional_inputs"],
        "total_findings": total_findings,
        "high_findings": high_findings,
        "readiness_status": readiness_status,
        "findings": [
            {
                "finding_id": row["finding_id"],
                "kind": row["kind"],
                "severity": row["severity"],
                "title": row["title"],
                "detail": row["detail"],
                "evidence_id": row["evidence_id"],
            }
            for row in findings_rows
        ],
    }
