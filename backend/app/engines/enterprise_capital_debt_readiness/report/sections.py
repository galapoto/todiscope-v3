"""
Report Section Generators

Deterministic report section generators for the Enterprise Capital & Debt Readiness Engine.
"""

from __future__ import annotations

from typing import Any


def section_executive_summary(
    *,
    summary_payload: dict[str, Any],
) -> dict[str, Any]:
    """Generate executive summary section."""
    readiness_score = summary_payload.get("readiness_score")
    readiness_level = summary_payload.get("readiness_level")
    findings = summary_payload.get("findings", [])
    
    material_findings = [f for f in findings if f.get("is_material", False)]
    
    return {
        "readiness_score": readiness_score,
        "readiness_level": readiness_level,
        "findings_count": len(findings),
        "material_findings_count": len(material_findings),
        "key_metrics": {
            "capital_adequacy_level": summary_payload.get("capital_adequacy", {}).get("adequacy_level"),
            "debt_service_level": summary_payload.get("debt_service", {}).get("ability_level"),
        },
    }


def section_capital_adequacy(
    *,
    capital_payload: dict[str, Any],
) -> dict[str, Any]:
    """Generate capital adequacy section."""
    capital_data = capital_payload.get("capital_adequacy", {})
    
    return {
        "available_capital": capital_data.get("available_capital"),
        "required_capital": capital_data.get("required_capital"),
        "coverage_ratio": capital_data.get("coverage_ratio"),
        "runway_months": capital_data.get("runway_months"),
        "debt_to_equity_ratio": capital_data.get("debt_to_equity_ratio"),
        "current_ratio": capital_data.get("current_ratio"),
        "adequacy_level": capital_data.get("adequacy_level"),
        "flags": capital_data.get("flags", []),
    }


def section_debt_service(
    *,
    debt_payload: dict[str, Any],
) -> dict[str, Any]:
    """Generate debt service section."""
    debt_data = debt_payload.get("debt_service", {})
    
    return {
        "dscr": debt_data.get("dscr"),
        "interest_coverage": debt_data.get("interest_coverage"),
        "debt_service_total": debt_data.get("debt_service_total"),
        "interest_total": debt_data.get("interest_total"),
        "principal_total": debt_data.get("principal_total"),
        "maturity_concentration": debt_data.get("maturity_concentration"),
        "ability_level": debt_data.get("ability_level"),
        "flags": debt_data.get("flags", []),
    }


def section_readiness_score(
    *,
    readiness_payload: dict[str, Any],
) -> dict[str, Any]:
    """Generate readiness score section."""
    readiness_data = readiness_payload.get("readiness_score", {})
    
    return {
        "readiness_score": readiness_data.get("readiness_score"),
        "readiness_level": readiness_data.get("readiness_level"),
        "component_scores": readiness_data.get("component_scores", {}),
        "credit_risk_details": readiness_data.get("credit_risk_details", {}),
        "breakdown": readiness_data.get("breakdown", {}),
    }


def section_scenario_analysis(
    *,
    scenario_payload: dict[str, Any],
) -> dict[str, Any]:
    """Generate scenario analysis section with risk insights."""
    scenario_data = scenario_payload.get("scenario_analysis", {})
    
    scenarios = scenario_data.get("scenarios", [])
    aggregate_metrics = scenario_data.get("aggregate_risk_metrics", {})
    
    # Find worst case scenario
    worst_case = None
    for scenario in scenarios:
        if scenario.get("scenario_name") == "worst_case":
            worst_case = scenario
            break
    
    # Find best case scenario
    best_case = None
    for scenario in scenarios:
        if scenario.get("scenario_name") == "best_case":
            best_case = scenario
            break
    
    # Find stress test scenarios
    stress_tests = [
        s for s in scenarios
        if s.get("scenario_name", "").startswith("stress_test_")
    ]
    
    # Risk insights
    risk_insights = []
    if aggregate_metrics.get("max_liquidity_risk", 0) > 70:
        risk_insights.append({
            "type": "liquidity_risk",
            "severity": "high" if aggregate_metrics.get("max_liquidity_risk", 0) > 80 else "moderate",
            "message": f"High liquidity risk detected (score: {aggregate_metrics.get('max_liquidity_risk', 0):.1f}). "
                      f"Company may face liquidity challenges under adverse conditions.",
        })
    
    if aggregate_metrics.get("max_solvency_risk", 0) > 70:
        risk_insights.append({
            "type": "solvency_risk",
            "severity": "high" if aggregate_metrics.get("max_solvency_risk", 0) > 80 else "moderate",
            "message": f"High solvency risk detected (score: {aggregate_metrics.get('max_solvency_risk', 0):.1f}). "
                      f"Company's ability to meet long-term obligations may be compromised under stress.",
        })
    
    if aggregate_metrics.get("max_market_sensitivity", 0) > 70:
        risk_insights.append({
            "type": "market_sensitivity",
            "severity": "high" if aggregate_metrics.get("max_market_sensitivity", 0) > 80 else "moderate",
            "message": f"High market sensitivity detected (score: {aggregate_metrics.get('max_market_sensitivity', 0):.1f}). "
                      f"Readiness score is highly sensitive to market condition changes.",
        })
    
    # Scenario comparison
    scenario_comparison = {
        "base_case_score": next(
            (s.get("readiness_score") for s in scenarios if s.get("scenario_name") == "base_case"),
            None,
        ),
        "best_case_score": best_case.get("readiness_score") if best_case else None,
        "worst_case_score": worst_case.get("readiness_score") if worst_case else None,
        "score_range": aggregate_metrics.get("score_range"),
    }
    
    return {
        "scenarios": {
            "base_case": next(
                (s for s in scenarios if s.get("scenario_name") == "base_case"),
                None,
            ),
            "best_case": best_case,
            "worst_case": worst_case,
            "stress_tests": stress_tests,
        },
        "aggregate_risk_metrics": aggregate_metrics,
        "risk_insights": risk_insights,
        "scenario_comparison": scenario_comparison,
        "key_findings": [
            {
                "finding": f"Readiness score ranges from {scenario_comparison.get('best_case_score', 0):.1f} "
                          f"(best case) to {scenario_comparison.get('worst_case_score', 0):.1f} (worst case)",
                "impact": "high" if scenario_comparison.get("score_range", 0) > 20 else "moderate",
            },
            *[
                {
                    "finding": insight["message"],
                    "impact": insight["severity"],
                }
                for insight in risk_insights
            ],
        ],
    }


