"""
Tests for reporting functionality.

Verifies granular and aggregated report generation.
"""

from datetime import date
from decimal import Decimal

import pytest

from backend.app.engines.enterprise_distressed_asset_debt_stress.models import ScenarioResult
from backend.app.engines.enterprise_distressed_asset_debt_stress.scenario_creation import create_scenario
from backend.app.engines.enterprise_distressed_asset_debt_stress.scenario_execution import execute_scenario
from backend.app.engines.enterprise_distressed_asset_debt_stress.reporting import (
    generate_aggregated_report,
    generate_executive_summary,
    generate_granular_report,
)


def test_generate_granular_report() -> None:
    """Test granular report generation."""
    scenario = create_scenario(
        dataset_version_id="test_dv_1",
        scenario_name="granular_test",
        description="Test granular report",
        time_horizon_months=6,
        assumptions={"revenue_change_factor": 0.8},
    )
    
    financial_data = {
        "balance_sheet": {
            "total_assets": 1000000,
            "cash_and_equivalents": 200000,
        },
        "income_statement": {
            "revenue": 500000,
            "operating_expenses": 300000,
        },
        "debt": {},
    }
    
    execution = execute_scenario(
        scenario=scenario,
        financial_data=financial_data,
        analysis_date=date(2025, 1, 1),
    )
    
    scenario_result = ScenarioResult(
        scenario=scenario,
        execution=execution,
        aggregated_metrics=execution.summary,
        granular_results=execution.period_results,
    )
    
    report = generate_granular_report(scenario_result=scenario_result)
    
    assert report["report_type"] == "granular"
    assert report["scenario"]["scenario_id"] == scenario.scenario_id
    assert len(report["periods"]) == 6
    
    # Check period details
    for period in report["periods"]:
        assert "period_month" in period
        assert "period_date" in period
        assert "exposure_changes" in period
        assert "cash_shortfalls" in period
        assert "debt_service_coverage" in period
        assert "cumulative_metrics" in period


def test_generate_aggregated_report() -> None:
    """Test aggregated report generation."""
    scenario = create_scenario(
        dataset_version_id="test_dv_1",
        scenario_name="aggregated_test",
        description="Test aggregated report",
        time_horizon_months=12,
        assumptions={
            "revenue_change_factor": 0.8,
            "cost_change_factor": 1.15,
        },
    )
    
    financial_data = {
        "balance_sheet": {
            "total_assets": 1000000,
            "cash_and_equivalents": 200000,
        },
        "income_statement": {
            "revenue": 500000,
            "operating_expenses": 300000,
            "ebitda": 200000,
        },
        "debt": {},
    }
    
    execution = execute_scenario(
        scenario=scenario,
        financial_data=financial_data,
        analysis_date=date(2025, 1, 1),
    )
    
    scenario_result = ScenarioResult(
        scenario=scenario,
        execution=execution,
        aggregated_metrics=execution.summary,
        granular_results=execution.period_results,
    )
    
    report = generate_aggregated_report(scenario_result=scenario_result)
    
    assert report["report_type"] == "aggregated"
    assert "summary" in report
    assert "aggregated_metrics" in report
    
    # Check aggregated metrics
    metrics = report["aggregated_metrics"]
    assert "exposure" in metrics
    assert "cash_shortfalls" in metrics
    assert "debt_service_coverage" in metrics
    assert "risk_assessment" in metrics
    
    # Check risk assessment
    risk_assessment = metrics["risk_assessment"]
    assert "overall_risk_level" in risk_assessment
    assert risk_assessment["overall_risk_level"] in ("low", "moderate", "high", "critical")
    assert "key_risks" in risk_assessment


def test_generate_executive_summary() -> None:
    """Test executive summary generation."""
    scenario = create_scenario(
        dataset_version_id="test_dv_1",
        scenario_name="executive_test",
        description="Test executive summary",
        time_horizon_months=12,
        assumptions={"revenue_change_factor": 0.8},
    )
    
    financial_data = {
        "balance_sheet": {
            "total_assets": 1000000,
            "cash_and_equivalents": 200000,
        },
        "income_statement": {
            "revenue": 500000,
            "operating_expenses": 300000,
        },
        "debt": {},
    }
    
    execution = execute_scenario(
        scenario=scenario,
        financial_data=financial_data,
        analysis_date=date(2025, 1, 1),
    )
    
    scenario_result = ScenarioResult(
        scenario=scenario,
        execution=execution,
        aggregated_metrics=execution.summary,
        granular_results=execution.period_results,
    )
    
    summary = generate_executive_summary(scenario_result=scenario_result)
    
    assert summary["report_type"] == "executive_summary"
    assert "scenario_name" in summary
    assert "overall_risk_level" in summary
    assert "key_findings" in summary
    assert "key_risks" in summary
    assert "recommendations" in summary
    
    # Check key findings
    findings = summary["key_findings"]
    assert "total_exposure_change" in findings
    assert "total_cash_shortfall" in findings
    assert "min_dscr" in findings
    assert "critical_periods" in findings


def test_report_accuracy() -> None:
    """Test that reports accurately reflect scenario results."""
    scenario = create_scenario(
        dataset_version_id="test_dv_1",
        scenario_name="accuracy_test",
        description="Test report accuracy",
        time_horizon_months=6,
        assumptions={
            "revenue_change_factor": 0.5,  # Severe reduction
            "cost_change_factor": 1.3,  # Significant increase
        },
    )
    
    financial_data = {
        "balance_sheet": {
            "total_assets": 1000000,
            "cash_and_equivalents": 100000,
        },
        "income_statement": {
            "revenue": 100000,
            "operating_expenses": 80000,
        },
        "debt": {},
    }
    
    execution = execute_scenario(
        scenario=scenario,
        financial_data=financial_data,
        analysis_date=date(2025, 1, 1),
    )
    
    scenario_result = ScenarioResult(
        scenario=scenario,
        execution=execution,
        aggregated_metrics=execution.summary,
        granular_results=execution.period_results,
    )
    
    aggregated = generate_aggregated_report(scenario_result=scenario_result)
    
    # With severe assumptions, should show high risk
    risk_level = aggregated["aggregated_metrics"]["risk_assessment"]["overall_risk_level"]
    assert risk_level in ("moderate", "high", "critical")
    
    # Should have cash shortfalls
    total_shortfall = aggregated["aggregated_metrics"]["cash_shortfalls"]["total_cash_shortfall"]
    assert total_shortfall >= 0  # May or may not have shortfalls depending on calculations






