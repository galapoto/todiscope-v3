from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from backend.app.engines.enterprise_distressed_asset_debt_stress.models import (
    Scenario,
    ScenarioExecution,
    ScenarioResult,
)


def generate_granular_report(
    *,
    scenario_result: ScenarioResult,
) -> dict[str, Any]:
    """
    Generate a granular report with period-by-period details.
    
    Returns:
        Dictionary containing detailed period-by-period results
    """
    report = {
        "report_type": "granular",
        "scenario": {
            "scenario_id": scenario_result.scenario.scenario_id,
            "scenario_name": scenario_result.scenario.scenario_name,
            "description": scenario_result.scenario.description,
            "time_horizon_months": scenario_result.scenario.time_horizon_months,
            "dataset_version_id": scenario_result.scenario.dataset_version_id,
            "created_at": scenario_result.scenario.created_at,
        },
        "execution": {
            "execution_id": scenario_result.execution.execution_id,
            "executed_at": scenario_result.execution.executed_at,
            "executed_by": scenario_result.execution.executed_by,
        },
        "periods": [],
    }
    
    # Add detailed period-by-period data
    for period_result in scenario_result.granular_results:
        period_data = {
            "period_month": period_result.period_month,
            "period_date": period_result.period_date.isoformat(),
            "exposure_changes": [
                {
                    "asset_category": ec.asset_category,
                    "exposure_before": float(ec.exposure_before),
                    "exposure_after": float(ec.exposure_after),
                    "exposure_change": float(ec.exposure_change),
                    "exposure_change_percent": float(ec.exposure_change_percent),
                }
                for ec in period_result.exposure_changes
            ],
            "cash_shortfalls": [
                {
                    "shortfall_category": cs.shortfall_category,
                    "cash_available": float(cs.cash_available),
                    "cash_required": float(cs.cash_required),
                    "shortfall": float(cs.shortfall),
                    "shortfall_percent": float(cs.shortfall_percent),
                }
                for cs in period_result.cash_shortfalls
            ],
            "debt_service_coverage": {
                "dscr": float(dsc.dscr) if dsc.dscr is not None else None,
                "interest_coverage": float(dsc.interest_coverage) if dsc.interest_coverage is not None else None,
                "principal_coverage": float(dsc.principal_coverage) if dsc.principal_coverage is not None else None,
                "total_debt_service": float(dsc.total_debt_service),
                "cash_available_for_debt_service": float(dsc.cash_available_for_debt_service),
                "coverage_status": dsc.coverage_status,
            },
            "cumulative_metrics": {
                "cumulative_exposure_change": float(period_result.cumulative_exposure_change),
                "cumulative_cash_shortfall": float(period_result.cumulative_cash_shortfall),
            },
        }
        report["periods"].append(period_data)
    
    return report


def generate_aggregated_report(
    *,
    scenario_result: ScenarioResult,
) -> dict[str, Any]:
    """
    Generate an aggregated report with summary metrics.
    
    Returns:
        Dictionary containing aggregated summary metrics
    """
    execution = scenario_result.execution
    summary = execution.summary
    
    # Calculate additional aggregated metrics
    periods = scenario_result.granular_results
    if not periods:
        return {
            "report_type": "aggregated",
            "scenario": {
                "scenario_id": scenario_result.scenario.scenario_id,
                "scenario_name": scenario_result.scenario.scenario_name,
            },
            "summary": summary,
            "aggregated_metrics": {},
        }
    
    # Aggregate exposure changes
    total_exposure_change = periods[-1].cumulative_exposure_change
    max_exposure_change = max(
        (ec.exposure_change for pr in periods for ec in pr.exposure_changes),
        default=Decimal("0"),
    )
    
    # Aggregate cash shortfalls
    total_cash_shortfall = periods[-1].cumulative_cash_shortfall
    max_cash_shortfall = max(
        (cs.shortfall for pr in periods for cs in pr.cash_shortfalls),
        default=Decimal("0"),
    )
    
    # Aggregate DSCR metrics
    dscr_values = [
        pr.debt_service_coverage.dscr
        for pr in periods
        if pr.debt_service_coverage.dscr is not None
    ]
    avg_dscr = (
        sum(dscr_values) / Decimal(str(len(dscr_values)))
        if dscr_values
        else None
    )
    min_dscr = min(dscr_values) if dscr_values else None
    max_dscr = max(dscr_values) if dscr_values else None
    
    # Count critical periods
    critical_periods = sum(
        1 for pr in periods
        if pr.debt_service_coverage.coverage_status == "insufficient"
        or any(cs.shortfall > Decimal("100000") for cs in pr.cash_shortfalls)
    )
    
    # Aggregate by category
    shortfalls_by_category: dict[str, Decimal] = {}
    for pr in periods:
        for cs in pr.cash_shortfalls:
            category = cs.shortfall_category
            if category not in shortfalls_by_category:
                shortfalls_by_category[category] = Decimal("0")
            shortfalls_by_category[category] += cs.shortfall
    
    aggregated_metrics = {
        "exposure": {
            "total_exposure_change": float(total_exposure_change),
            "max_period_exposure_change": float(max_exposure_change),
            "exposure_change_percent": (
                float((total_exposure_change / periods[0].exposure_changes[0].exposure_before * Decimal("100")))
                if periods and periods[0].exposure_changes and periods[0].exposure_changes[0].exposure_before > 0
                else None
            ),
        },
        "cash_shortfalls": {
            "total_cash_shortfall": float(total_cash_shortfall),
            "max_period_cash_shortfall": float(max_cash_shortfall),
            "periods_with_shortfalls": summary.get("periods_with_shortfalls", 0),
            "shortfalls_by_category": {
                category: float(amount)
                for category, amount in shortfalls_by_category.items()
            },
        },
        "debt_service_coverage": {
            "average_dscr": float(avg_dscr) if avg_dscr is not None else None,
            "min_dscr": float(min_dscr) if min_dscr is not None else None,
            "max_dscr": float(max_dscr) if max_dscr is not None else None,
            "periods_insufficient_coverage": summary.get("periods_insufficient_coverage", 0),
            "critical_periods": critical_periods,
        },
        "risk_assessment": {
            "overall_risk_level": _assess_overall_risk(
                total_exposure_change=total_exposure_change,
                total_cash_shortfall=total_cash_shortfall,
                min_dscr=min_dscr,
                critical_periods=critical_periods,
            ),
            "key_risks": _identify_key_risks(
                periods=periods,
                summary=summary,
            ),
        },
    }
    
    return {
        "report_type": "aggregated",
        "scenario": {
            "scenario_id": scenario_result.scenario.scenario_id,
            "scenario_name": scenario_result.scenario.scenario_name,
            "description": scenario_result.scenario.description,
            "time_horizon_months": scenario_result.scenario.time_horizon_months,
            "dataset_version_id": scenario_result.scenario.dataset_version_id,
        },
        "execution": {
            "execution_id": execution.execution_id,
            "executed_at": execution.executed_at,
        },
        "summary": summary,
        "aggregated_metrics": aggregated_metrics,
    }


def _assess_overall_risk(
    *,
    total_exposure_change: Decimal,
    total_cash_shortfall: Decimal,
    min_dscr: Decimal | None,
    critical_periods: int,
) -> str:
    """Assess overall risk level based on aggregated metrics."""
    risk_score = 0
    
    # Exposure change risk
    if total_exposure_change < Decimal("-1000000"):
        risk_score += 3
    elif total_exposure_change < Decimal("-500000"):
        risk_score += 2
    elif total_exposure_change < Decimal("-100000"):
        risk_score += 1
    
    # Cash shortfall risk
    if total_cash_shortfall > Decimal("1000000"):
        risk_score += 3
    elif total_cash_shortfall > Decimal("500000"):
        risk_score += 2
    elif total_cash_shortfall > Decimal("100000"):
        risk_score += 1
    
    # DSCR risk
    if min_dscr is not None:
        if min_dscr < Decimal("0.5"):
            risk_score += 3
        elif min_dscr < Decimal("1.0"):
            risk_score += 2
        elif min_dscr < Decimal("1.25"):
            risk_score += 1
    
    # Critical periods risk
    if critical_periods > 6:
        risk_score += 3
    elif critical_periods > 3:
        risk_score += 2
    elif critical_periods > 0:
        risk_score += 1
    
    if risk_score >= 8:
        return "critical"
    elif risk_score >= 5:
        return "high"
    elif risk_score >= 3:
        return "moderate"
    else:
        return "low"


def _identify_key_risks(
    *,
    periods: list[Any],
    summary: dict[str, Any],
) -> list[str]:
    """Identify key risks from the scenario results."""
    risks: list[str] = []
    
    if summary.get("periods_insufficient_coverage", 0) > 0:
        risks.append("Insufficient debt service coverage in multiple periods")
    
    if summary.get("periods_with_shortfalls", 0) > 0:
        risks.append("Cash shortfalls detected in multiple periods")
    
    if summary.get("min_dscr") is not None and summary["min_dscr"] < 1.0:
        risks.append("Debt service coverage ratio below 1.0 in at least one period")
    
    total_shortfall = summary.get("total_cash_shortfall", 0)
    if total_shortfall > 1000000:
        risks.append("Significant cumulative cash shortfall")
    
    total_exposure_change = summary.get("total_exposure_change", 0)
    if total_exposure_change < -1000000:
        risks.append("Significant exposure reduction")
    
    return risks


def generate_executive_summary(
    *,
    scenario_result: ScenarioResult,
) -> dict[str, Any]:
    """
    Generate an executive summary report.
    
    Returns:
        Dictionary containing executive-level summary
    """
    aggregated = generate_aggregated_report(scenario_result=scenario_result)
    
    return {
        "report_type": "executive_summary",
        "scenario_name": scenario_result.scenario.scenario_name,
        "time_horizon_months": scenario_result.scenario.time_horizon_months,
        "executed_at": scenario_result.execution.executed_at,
        "overall_risk_level": aggregated["aggregated_metrics"]["risk_assessment"]["overall_risk_level"],
        "key_findings": {
            "total_exposure_change": aggregated["aggregated_metrics"]["exposure"]["total_exposure_change"],
            "total_cash_shortfall": aggregated["aggregated_metrics"]["cash_shortfalls"]["total_cash_shortfall"],
            "min_dscr": aggregated["aggregated_metrics"]["debt_service_coverage"]["min_dscr"],
            "critical_periods": aggregated["aggregated_metrics"]["debt_service_coverage"]["critical_periods"],
        },
        "key_risks": aggregated["aggregated_metrics"]["risk_assessment"]["key_risks"],
        "recommendations": _generate_recommendations(aggregated),
    }


def _generate_recommendations(
    aggregated: dict[str, Any],
) -> list[str]:
    """Generate recommendations based on aggregated metrics."""
    recommendations: list[str] = []
    
    risk_level = aggregated["aggregated_metrics"]["risk_assessment"]["overall_risk_level"]
    
    if risk_level == "critical":
        recommendations.append("Immediate action required to address critical financial stress")
        recommendations.append("Consider emergency financing or restructuring options")
    
    if aggregated["aggregated_metrics"]["cash_shortfalls"]["total_cash_shortfall"] > 500000:
        recommendations.append("Develop cash management strategy to address shortfalls")
    
    min_dscr = aggregated["aggregated_metrics"]["debt_service_coverage"]["min_dscr"]
    if min_dscr is not None and min_dscr < 1.0:
        recommendations.append("Review debt service obligations and consider restructuring")
    
    if aggregated["aggregated_metrics"]["debt_service_coverage"]["critical_periods"] > 3:
        recommendations.append("Monitor debt service coverage closely in critical periods")
    
    if not recommendations:
        recommendations.append("Continue monitoring financial metrics under stress conditions")
    
    return recommendations


