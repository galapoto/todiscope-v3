"""
Tests for scenario execution functionality.

Verifies scenario execution logic, exposure changes, cash shortfalls, and debt service coverage.
"""

from datetime import date
from decimal import Decimal

import pytest

from backend.app.engines.enterprise_distressed_asset_debt_stress.scenario_creation import create_scenario
from backend.app.engines.enterprise_distressed_asset_debt_stress.scenario_execution import execute_scenario


def test_execute_scenario_basic() -> None:
    """Test basic scenario execution."""
    scenario = create_scenario(
        dataset_version_id="test_dv_1",
        scenario_name="test_execution",
        description="Test execution",
        time_horizon_months=6,
        assumptions={
            "revenue_change_factor": 0.8,
            "cost_change_factor": 1.15,
            "interest_rate_change_factor": 1.3,
            "liquidity_shock_factor": 0.85,
            "market_value_depreciation_factor": 0.9,
        },
    )
    
    financial_data = {
        "balance_sheet": {
            "total_assets": 1000000,
            "cash_and_equivalents": 200000,
            "current_assets": 500000,
        },
        "income_statement": {
            "revenue": 500000,
            "operating_expenses": 300000,
            "ebitda": 200000,
            "interest_expense": 50000,
        },
        "debt": {
            "instruments": [
                {
                    "principal": 500000,
                    "annual_interest_rate": 0.06,
                    "term_months": 12,
                }
            ],
        },
    }
    
    execution = execute_scenario(
        scenario=scenario,
        financial_data=financial_data,
        analysis_date=date(2025, 1, 1),
    )
    
    assert execution.execution_id is not None
    assert execution.scenario_id == scenario.scenario_id
    assert execution.dataset_version_id == scenario.dataset_version_id
    assert len(execution.period_results) == 6  # 6 months
    assert execution.summary is not None


def test_execute_scenario_exposure_changes() -> None:
    """Test that exposure changes are calculated correctly."""
    scenario = create_scenario(
        dataset_version_id="test_dv_1",
        scenario_name="exposure_test",
        description="Test exposure changes",
        time_horizon_months=12,
        assumptions={
            "market_value_depreciation_factor": 0.95,  # 5% depreciation per period
        },
    )
    
    financial_data = {
        "balance_sheet": {
            "total_assets": 1000000,
            "cash_and_equivalents": 100000,
        },
        "income_statement": {},
        "debt": {},
    }
    
    execution = execute_scenario(
        scenario=scenario,
        financial_data=financial_data,
        analysis_date=date(2025, 1, 1),
    )
    
    # Check first period
    first_period = execution.period_results[0]
    assert len(first_period.exposure_changes) > 0
    assert first_period.exposure_changes[0].exposure_before == Decimal("1000000")
    
    # Check that exposure decreases over time
    last_period = execution.period_results[-1]
    assert last_period.cumulative_exposure_change < 0


def test_execute_scenario_cash_shortfalls() -> None:
    """Test that cash shortfalls are calculated correctly."""
    scenario = create_scenario(
        dataset_version_id="test_dv_1",
        scenario_name="shortfall_test",
        description="Test cash shortfalls",
        time_horizon_months=6,
        assumptions={
            "revenue_change_factor": 0.5,  # 50% revenue reduction
            "cost_change_factor": 1.2,  # 20% cost increase
            "liquidity_shock_factor": 0.7,  # 30% liquidity reduction
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
    
    # Should have cash shortfalls due to revenue reduction and cost increase
    periods_with_shortfalls = [
        pr for pr in execution.period_results if pr.cash_shortfalls
    ]
    assert len(periods_with_shortfalls) > 0
    
    # Check shortfall details
    for period in periods_with_shortfalls:
        for shortfall in period.cash_shortfalls:
            assert shortfall.shortfall > 0
            assert shortfall.shortfall_category in ("operating", "debt_service", "capital_expenditure")


def test_execute_scenario_debt_service_coverage() -> None:
    """Test that debt service coverage is calculated correctly."""
    scenario = create_scenario(
        dataset_version_id="test_dv_1",
        scenario_name="dscr_test",
        description="Test debt service coverage",
        time_horizon_months=12,
        assumptions={
            "revenue_change_factor": 0.8,
            "interest_rate_change_factor": 1.5,  # 50% interest rate increase
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
            "interest_expense": 50000,
        },
        "debt": {
            "instruments": [
                {
                    "principal": 500000,
                    "annual_interest_rate": 0.06,
                    "term_months": 12,
                }
            ],
        },
    }
    
    execution = execute_scenario(
        scenario=scenario,
        financial_data=financial_data,
        analysis_date=date(2025, 1, 1),
    )
    
    # Check that DSCR is calculated for each period
    for period in execution.period_results:
        dsc = period.debt_service_coverage
        assert dsc.total_debt_service > 0
        assert dsc.coverage_status in ("adequate", "marginal", "insufficient")
        
        # With interest rate increase, DSCR should be lower
        if dsc.dscr is not None:
            assert dsc.dscr >= 0


def test_execute_scenario_summary() -> None:
    """Test that execution summary is generated correctly."""
    scenario = create_scenario(
        dataset_version_id="test_dv_1",
        scenario_name="summary_test",
        description="Test summary generation",
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
    
    summary = execution.summary
    assert "total_exposure_change" in summary
    assert "total_cash_shortfall" in summary
    assert "periods_with_shortfalls" in summary
    assert "time_horizon_months" in summary
    assert summary["time_horizon_months"] == 12


def test_execute_scenario_all_periods() -> None:
    """Test that all periods are executed correctly."""
    scenario = create_scenario(
        dataset_version_id="test_dv_1",
        scenario_name="periods_test",
        description="Test all periods",
        time_horizon_months=24,  # 24 months
        assumptions={},
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
    
    # Should have 24 periods
    assert len(execution.period_results) == 24
    
    # Check period numbering
    for i, period in enumerate(execution.period_results, start=1):
        assert period.period_month == i
        assert period.period_date >= date(2025, 1, 1)






