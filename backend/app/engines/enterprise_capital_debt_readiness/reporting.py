from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, Iterable


DEFAULT_SCENARIOS: dict[str, dict[str, Any]] = {
    "base": {
        "description": "Current dataset values represent the base case view.",
        "score_delta": Decimal("0"),
        "exposure_multiplier": Decimal("1"),
        "dscr_multiplier": Decimal("1"),
    },
    "best_case": {
        "description": "Optimistic market/trading environment reduces leakage and improves serviceability.",
        "score_delta": Decimal("4"),
        "exposure_multiplier": Decimal("0.8"),
        "dscr_multiplier": Decimal("1.1"),
    },
    "worst_case": {
        "description": "Stress scenario inflates leakage exposure and squeezes debt coverage.",
        "score_delta": Decimal("-6"),
        "exposure_multiplier": Decimal("1.25"),
        "dscr_multiplier": Decimal("0.85"),
    },
}


def _decimal_to_float(value: Decimal | None) -> float | None:
    if value is None:
        return None
    return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _quantize(value: Decimal | None) -> Decimal | None:
    if value is None:
        return None
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _build_scenario(
    *,
    name: str,
    description: str,
    readiness_score: Decimal,
    exposure: Decimal,
    dscr: Decimal | None,
    interest_coverage: Decimal | None,
    modifiers: dict[str, Decimal],
) -> dict[str, Any]:
    score_delta = modifiers.get("score_delta", Decimal("0"))
    exposure_multiplier = modifiers.get("exposure_multiplier", Decimal("1"))
    dscr_multiplier = modifiers.get("dscr_multiplier", Decimal("1"))

    scenario_score = (readiness_score + score_delta).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    scenario_score = max(min(scenario_score, Decimal("100")), Decimal("0"))
    scenario_exposure = (exposure * exposure_multiplier).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    scenario_dscr = (dscr * dscr_multiplier).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if dscr is not None else None
    scenario_interest = (
        (interest_coverage * dscr_multiplier).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if interest_coverage is not None
        else None
    )

    insight = (
        f"{description} Readiness score would move to {scenario_score} "
        f"with exposure ~{scenario_exposure} and DSCR {scenario_dscr or 'N/A'}."
    )

    return {
        "name": name,
        "description": description,
        "readiness_score": float(scenario_score),
        "total_exposure": float(scenario_exposure) if scenario_exposure is not None else None,
        "dscr": float(scenario_dscr) if scenario_dscr is not None else None,
        "interest_coverage": float(scenario_interest) if scenario_interest is not None else None,
        "insight": insight,
    }


def generate_executive_report(
    *,
    dataset_version_id: str,
    generated_at: str,
    readiness_result: dict[str, Any],
    capital_adequacy: dict[str, Any],
    debt_service: dict[str, Any],
    assumptions: dict[str, Any],
    cross_engine_data: dict[str, Any],
    findings: Iterable[dict[str, Any]],
    evidence_ids: Iterable[str],
) -> dict[str, Any]:
    readiness_score = Decimal(str(readiness_result.get("readiness_score", 0)))
    readiness_level = readiness_result.get("readiness_level", "adequate")

    ff_data = cross_engine_data.get("financial_forensics", {}) or {}
    deal_data = cross_engine_data.get("deal_readiness", {}) or {}
    total_exposure = Decimal(str(ff_data.get("total_leakage_exposure") or 0))
    dscr = Decimal(str(debt_service.get("dscr") or 0))
    interest_coverage = Decimal(str(debt_service.get("interest_coverage") or 0))

    scenario_defs = assumptions.get("readiness_scenarios", DEFAULT_SCENARIOS)
    scenario_insights = [
        _build_scenario(
            name=name,
            description=str(cfg.get("description", DEFAULT_SCENARIOS.get(name, {}).get("description", ""))),
            readiness_score=readiness_score,
            exposure=total_exposure,
            dscr=dscr if dscr > 0 else None,
            interest_coverage=interest_coverage if interest_coverage > 0 else None,
            modifiers={
                "score_delta": Decimal(str(cfg.get("score_delta", 0))),
                "exposure_multiplier": Decimal(str(cfg.get("exposure_multiplier", 1))),
                "dscr_multiplier": Decimal(str(cfg.get("dscr_multiplier", 1))),
            },
        )
        for name, cfg in scenario_defs.items()
    ]

    component_scores = readiness_result.get("component_scores", {})
    risk_assessment = {
        "readiness_score": readiness_score,
        "readiness_level": readiness_level,
        "component_scores": component_scores,
        "capital_adequacy_flags": capital_adequacy.get("flags", []),
        "debt_service_flags": debt_service.get("flags", []),
        "cross_engine_exposure": {
            "financial_forensics": {
                "total_leakage_exposure": _decimal_to_float(total_exposure),
                "findings_count": ff_data.get("findings_count", 0),
            },
            "deal_readiness": {
                "readiness_score": float(deal_data.get("readiness_score") or 0),
                "high_findings": deal_data.get("high_findings", 0),
                "status": deal_data.get("readiness_status", "unknown"),
            },
        },
        "metrics": {
            "coverage_ratio": capital_adequacy.get("coverage_ratio"),
            "dscr": debt_service.get("dscr"),
            "interest_coverage": debt_service.get("interest_coverage"),
        },
    }

    executive_summary = {
        "dataset_version_id": dataset_version_id,
        "generated_at": generated_at,
        "title": "Enterprise Capital & Debt Readiness Report",
        "highlights": [
            f"Composite readiness score: {float(readiness_score)} ({readiness_level})",
            f"Debt service DSCR: {debt_service.get('dscr', 'N/A')}",
            f"Capital coverage ratio: {capital_adequacy.get('coverage_ratio', 'N/A')}",
        ],
        "actions": [
            "Monitor Financial Forensics leakage exposures to keep stress scenarios contained.",
            "Prioritize improving DSCR/interest coverage when interest volatility surfaces.",
        ],
    }

    return {
        "metadata": {
            "dataset_version_id": dataset_version_id,
            "generated_at": generated_at,
            "report_type": "executive_readiness",
            "scenario_count": len(scenario_insights),
        },
        "executive_summary": executive_summary,
        "risk_assessment": risk_assessment,
        "scenario_insights": scenario_insights,
        "findings_summary": {
            "count": len(list(findings)),
            "linked_evidence": list(evidence_ids),
        },
    }
