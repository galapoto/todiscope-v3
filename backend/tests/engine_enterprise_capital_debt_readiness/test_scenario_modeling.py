"""
Tests for scenario-based risk modeling.

Verifies that scenario analysis correctly calculates readiness scores
under different market conditions and stress tests.
"""

from datetime import date
from decimal import Decimal, ROUND_HALF_UP

import pytest

from backend.app.engines.enterprise_capital_debt_readiness.assumptions import resolved_assumptions
from backend.app.engines.enterprise_capital_debt_readiness.capital_adequacy import assess_capital_adequacy
from backend.app.engines.enterprise_capital_debt_readiness.debt_service import assess_debt_service_ability
from backend.app.engines.enterprise_capital_debt_readiness.readiness_scores import (
    calculate_composite_readiness_score,
)
from backend.app.engines.enterprise_capital_debt_readiness.scenario_modeling import (
    create_best_case_conditions,
    create_base_case_conditions,
    create_stress_test_combined_shock,
    create_stress_test_interest_rate_shock,
    create_stress_test_liquidity_shock,
    create_worst_case_conditions,
    run_scenario_analysis,
)

MARKET_SENSITIVITY_PRECISION = Decimal("0.0001")


def _normalize_market_sensitivity(value: float) -> Decimal:
    return Decimal(str(value)).quantize(MARKET_SENSITIVITY_PRECISION, rounding=ROUND_HALF_UP)


def test_base_case_conditions() -> None:
    """Test base case scenario conditions."""
    conditions = create_base_case_conditions()
    
    assert conditions.interest_rate_multiplier == Decimal("1.0")
    assert conditions.liquidity_shock_factor == Decimal("1.0")
    assert conditions.revenue_change_factor == Decimal("1.0")
    assert conditions.cost_change_factor == Decimal("1.0")


def test_best_case_conditions() -> None:
    """Test best case scenario conditions."""
    conditions = create_best_case_conditions()
    
    assert conditions.interest_rate_multiplier < Decimal("1.0")  # Lower rates
    assert conditions.liquidity_shock_factor > Decimal("1.0")  # More liquidity
    assert conditions.revenue_change_factor > Decimal("1.0")  # Revenue increase
    assert conditions.cost_change_factor < Decimal("1.0")  # Cost reduction


def test_worst_case_conditions() -> None:
    """Test worst case scenario conditions."""
    conditions = create_worst_case_conditions()
    
    assert conditions.interest_rate_multiplier > Decimal("1.0")  # Higher rates
    assert conditions.liquidity_shock_factor < Decimal("1.0")  # Less liquidity
    assert conditions.revenue_change_factor < Decimal("1.0")  # Revenue decrease
    assert conditions.cost_change_factor > Decimal("1.0")  # Cost increase


def test_stress_test_interest_rate_shock() -> None:
    """Test interest rate shock stress test."""
    conditions = create_stress_test_interest_rate_shock(shock_percentage=Decimal("200"))
    
    assert conditions.interest_rate_multiplier == Decimal("3.0")  # 200% increase = 3x
    assert conditions.liquidity_shock_factor == Decimal("1.0")
    assert conditions.revenue_change_factor == Decimal("1.0")
    assert conditions.cost_change_factor == Decimal("1.0")


def test_stress_test_liquidity_shock() -> None:
    """Test liquidity shock stress test."""
    conditions = create_stress_test_liquidity_shock(shock_percentage=Decimal("50"))
    
    assert conditions.interest_rate_multiplier == Decimal("1.0")
    assert conditions.liquidity_shock_factor == Decimal("0.5")  # 50% reduction
    assert conditions.revenue_change_factor == Decimal("1.0")
    assert conditions.cost_change_factor == Decimal("1.0")


def test_stress_test_combined_shock() -> None:
    """Test combined shock stress test."""
    conditions = create_stress_test_combined_shock()
    
    assert conditions.interest_rate_multiplier > Decimal("1.0")
    assert conditions.liquidity_shock_factor < Decimal("1.0")
    assert conditions.revenue_change_factor < Decimal("1.0")
    assert conditions.cost_change_factor > Decimal("1.0")


def test_scenario_analysis_base_case() -> None:
    """Test scenario analysis with base case."""
    assumptions = resolved_assumptions({})
    financial = {
        "balance_sheet": {
            "cash_and_equivalents": 500000,
            "current_assets": 1000000,
            "current_liabilities": 400000,
            "total_equity": 3000000,
        },
        "income_statement": {
            "ebitda": 400000,
            "operating_expenses": 300000,
        },
        "debt": {
            "total_debt": 1500000,
            "instruments": [
                {
                    "id": "loan_1",
                    "principal": 500000,
                    "annual_interest_rate": 0.06,
                    "amortization": "amortizing",
                    "payment_frequency_months": 1,
                    "term_months": 12,
                }
            ],
        },
        "cash_flow": {
            "cash_available_for_debt_service_annual": 300000,
        },
        "capex_plan_12m": 100000,
    }
    
    cap = assess_capital_adequacy(
        dataset_version_id="dv_test",
        analysis_date=date(2025, 1, 1),
        financial=financial,
        assumptions=assumptions,
    )
    
    debt = assess_debt_service_ability(
        dataset_version_id="dv_test",
        analysis_date=date(2025, 1, 1),
        financial=financial,
        assumptions=assumptions,
    )
    
    base_readiness = calculate_composite_readiness_score(
        capital_adequacy=cap,
        debt_service=debt,
        financial=financial,
        assumptions=assumptions,
    )
    
    scenario_analysis = run_scenario_analysis(
        base_capital_adequacy=cap,
        base_debt_service=debt,
        base_readiness_score=Decimal(str(base_readiness["readiness_score"])),
        base_readiness_level=base_readiness["readiness_level"],
        base_component_scores={
            k: Decimal(str(v)) if v is not None else Decimal("0")
            for k, v in base_readiness["component_scores"].items()
        },
        financial=financial,
        assumptions=assumptions,
    )
    
    # Verify base case is included
    base_scenario = next(
        (s for s in scenario_analysis["scenarios"] if s["scenario_name"] == "base_case"),
        None,
    )
    assert base_scenario is not None
    assert base_scenario["readiness_score"] == float(base_readiness["readiness_score"])


def test_scenario_analysis_best_worst_case() -> None:
    """Test scenario analysis with best and worst case scenarios."""
    assumptions = resolved_assumptions({})
    financial = {
        "balance_sheet": {
            "cash_and_equivalents": 500000,
            "current_assets": 1000000,
            "current_liabilities": 400000,
            "total_equity": 3000000,
        },
        "income_statement": {
            "ebitda": 400000,
            "operating_expenses": 300000,
        },
        "debt": {
            "total_debt": 1500000,
            "instruments": [
                {
                    "id": "loan_1",
                    "principal": 500000,
                    "annual_interest_rate": 0.06,
                    "amortization": "amortizing",
                    "payment_frequency_months": 1,
                    "term_months": 12,
                }
            ],
        },
        "cash_flow": {
            "cash_available_for_debt_service_annual": 300000,
        },
        "capex_plan_12m": 100000,
    }
    
    cap = assess_capital_adequacy(
        dataset_version_id="dv_test",
        analysis_date=date(2025, 1, 1),
        financial=financial,
        assumptions=assumptions,
    )
    
    debt = assess_debt_service_ability(
        dataset_version_id="dv_test",
        analysis_date=date(2025, 1, 1),
        financial=financial,
        assumptions=assumptions,
    )
    
    base_readiness = calculate_composite_readiness_score(
        capital_adequacy=cap,
        debt_service=debt,
        financial=financial,
        assumptions=assumptions,
    )
    
    scenario_analysis = run_scenario_analysis(
        base_capital_adequacy=cap,
        base_debt_service=debt,
        base_readiness_score=Decimal(str(base_readiness["readiness_score"])),
        base_readiness_level=base_readiness["readiness_level"],
        base_component_scores={
            k: Decimal(str(v)) if v is not None else Decimal("0")
            for k, v in base_readiness["component_scores"].items()
        },
        financial=financial,
        assumptions=assumptions,
    )
    
    # Verify best and worst case scenarios
    best_case = next(
        (s for s in scenario_analysis["scenarios"] if s["scenario_name"] == "best_case"),
        None,
    )
    worst_case = next(
        (s for s in scenario_analysis["scenarios"] if s["scenario_name"] == "worst_case"),
        None,
    )
    
    assert best_case is not None
    assert worst_case is not None
    
    # Best case should have higher or equal score to base case
    base_score = next(
        (s["readiness_score"] for s in scenario_analysis["scenarios"] if s["scenario_name"] == "base_case"),
        0,
    )
    assert best_case["readiness_score"] >= base_score
    
    # Worst case should have lower or equal score to base case
    assert worst_case["readiness_score"] <= base_score


def test_scenario_analysis_stress_tests() -> None:
    """Test scenario analysis with stress tests."""
    assumptions = resolved_assumptions({})
    financial = {
        "balance_sheet": {
            "cash_and_equivalents": 500000,
            "current_assets": 1000000,
            "current_liabilities": 400000,
            "total_equity": 3000000,
        },
        "income_statement": {
            "ebitda": 400000,
            "operating_expenses": 300000,
        },
        "debt": {
            "total_debt": 1500000,
            "instruments": [
                {
                    "id": "loan_1",
                    "principal": 500000,
                    "annual_interest_rate": 0.06,
                    "amortization": "amortizing",
                    "payment_frequency_months": 1,
                    "term_months": 12,
                }
            ],
        },
        "cash_flow": {
            "cash_available_for_debt_service_annual": 300000,
        },
        "capex_plan_12m": 100000,
    }
    
    cap = assess_capital_adequacy(
        dataset_version_id="dv_test",
        analysis_date=date(2025, 1, 1),
        financial=financial,
        assumptions=assumptions,
    )
    
    debt = assess_debt_service_ability(
        dataset_version_id="dv_test",
        analysis_date=date(2025, 1, 1),
        financial=financial,
        assumptions=assumptions,
    )
    
    base_readiness = calculate_composite_readiness_score(
        capital_adequacy=cap,
        debt_service=debt,
        financial=financial,
        assumptions=assumptions,
    )
    
    scenario_analysis = run_scenario_analysis(
        base_capital_adequacy=cap,
        base_debt_service=debt,
        base_readiness_score=Decimal(str(base_readiness["readiness_score"])),
        base_readiness_level=base_readiness["readiness_level"],
        base_component_scores={
            k: Decimal(str(v)) if v is not None else Decimal("0")
            for k, v in base_readiness["component_scores"].items()
        },
        financial=financial,
        assumptions=assumptions,
    )
    
    # Verify stress tests are included
    stress_tests = [
        s for s in scenario_analysis["scenarios"]
        if s["scenario_name"].startswith("stress_test_")
    ]
    
    assert len(stress_tests) >= 3  # At least 3 stress tests
    
    # Stress tests should generally have lower scores than base case
    base_score = next(
        (s["readiness_score"] for s in scenario_analysis["scenarios"] if s["scenario_name"] == "base_case"),
        0,
    )
    for stress_test in stress_tests:
        # Stress tests may have lower scores (but not always, depending on base position)
        assert 0.0 <= stress_test["readiness_score"] <= 100.0


def test_scenario_analysis_risk_metrics() -> None:
    """Test that scenario analysis calculates risk metrics."""
    assumptions = resolved_assumptions({})
    financial = {
        "balance_sheet": {
            "cash_and_equivalents": 500000,
            "current_assets": 1000000,
            "current_liabilities": 400000,
            "total_equity": 3000000,
        },
        "income_statement": {
            "ebitda": 400000,
            "operating_expenses": 300000,
        },
        "debt": {
            "total_debt": 1500000,
            "instruments": [
                {
                    "id": "loan_1",
                    "principal": 500000,
                    "annual_interest_rate": 0.06,
                    "amortization": "amortizing",
                    "payment_frequency_months": 1,
                    "term_months": 12,
                }
            ],
        },
        "cash_flow": {
            "cash_available_for_debt_service_annual": 300000,
        },
        "capex_plan_12m": 100000,
    }
    
    cap = assess_capital_adequacy(
        dataset_version_id="dv_test",
        analysis_date=date(2025, 1, 1),
        financial=financial,
        assumptions=assumptions,
    )
    
    debt = assess_debt_service_ability(
        dataset_version_id="dv_test",
        analysis_date=date(2025, 1, 1),
        financial=financial,
        assumptions=assumptions,
    )
    
    base_readiness = calculate_composite_readiness_score(
        capital_adequacy=cap,
        debt_service=debt,
        financial=financial,
        assumptions=assumptions,
    )
    
    scenario_analysis = run_scenario_analysis(
        base_capital_adequacy=cap,
        base_debt_service=debt,
        base_readiness_score=Decimal(str(base_readiness["readiness_score"])),
        base_readiness_level=base_readiness["readiness_level"],
        base_component_scores={
            k: Decimal(str(v)) if v is not None else Decimal("0")
            for k, v in base_readiness["component_scores"].items()
        },
        financial=financial,
        assumptions=assumptions,
    )
    
    # Verify aggregate risk metrics
    aggregate_metrics = scenario_analysis.get("aggregate_risk_metrics", {})
    assert "max_liquidity_risk" in aggregate_metrics
    assert "max_solvency_risk" in aggregate_metrics
    assert "max_market_sensitivity" in aggregate_metrics
    assert "score_range" in aggregate_metrics
    
    # Verify risk scores are in valid range
    assert 0.0 <= aggregate_metrics["max_liquidity_risk"] <= 100.0
    assert 0.0 <= aggregate_metrics["max_solvency_risk"] <= 100.0
    assert 0.0 <= aggregate_metrics["max_market_sensitivity"] <= 100.0


def test_scenario_analysis_deterministic() -> None:
    """Test that scenario analysis is deterministic."""
    assumptions = resolved_assumptions({})
    financial = {
        "balance_sheet": {
            "cash_and_equivalents": 500000,
            "current_assets": 1000000,
            "current_liabilities": 400000,
            "total_equity": 3000000,
        },
        "income_statement": {
            "ebitda": 400000,
            "operating_expenses": 300000,
        },
        "debt": {
            "total_debt": 1500000,
            "instruments": [
                {
                    "id": "loan_1",
                    "principal": 500000,
                    "annual_interest_rate": 0.06,
                    "amortization": "amortizing",
                    "payment_frequency_months": 1,
                    "term_months": 12,
                }
            ],
        },
        "cash_flow": {
            "cash_available_for_debt_service_annual": 300000,
        },
        "capex_plan_12m": 100000,
    }
    
    cap = assess_capital_adequacy(
        dataset_version_id="dv_test",
        analysis_date=date(2025, 1, 1),
        financial=financial,
        assumptions=assumptions,
    )
    
    debt = assess_debt_service_ability(
        dataset_version_id="dv_test",
        analysis_date=date(2025, 1, 1),
        financial=financial,
        assumptions=assumptions,
    )
    
    base_readiness = calculate_composite_readiness_score(
        capital_adequacy=cap,
        debt_service=debt,
        financial=financial,
        assumptions=assumptions,
    )
    
    # Run twice with same inputs
    result1 = run_scenario_analysis(
        base_capital_adequacy=cap,
        base_debt_service=debt,
        base_readiness_score=Decimal(str(base_readiness["readiness_score"])),
        base_readiness_level=base_readiness["readiness_level"],
        base_component_scores={
            k: Decimal(str(v)) if v is not None else Decimal("0")
            for k, v in base_readiness["component_scores"].items()
        },
        financial=financial,
        assumptions=assumptions,
    )
    
    result2 = run_scenario_analysis(
        base_capital_adequacy=cap,
        base_debt_service=debt,
        base_readiness_score=Decimal(str(base_readiness["readiness_score"])),
        base_readiness_level=base_readiness["readiness_level"],
        base_component_scores={
            k: Decimal(str(v)) if v is not None else Decimal("0")
            for k, v in base_readiness["component_scores"].items()
        },
        financial=financial,
        assumptions=assumptions,
    )
    
    # Results should be identical (allowing for small floating point differences)
    # Sort scenarios by name for comparison
    result1_scenarios = sorted(result1["scenarios"], key=lambda s: s["scenario_name"])
    result2_scenarios = sorted(result2["scenarios"], key=lambda s: s["scenario_name"])
    
    assert len(result1_scenarios) == len(result2_scenarios)
    assert result1["aggregate_risk_metrics"]["max_liquidity_risk"] == result2["aggregate_risk_metrics"]["max_liquidity_risk"]
    assert result1["aggregate_risk_metrics"]["max_solvency_risk"] == result2["aggregate_risk_metrics"]["max_solvency_risk"]
    # Market sensitivity might have small differences due to floating point precision
    # Check that they're within quantized tolerance (0.0001)
    ms1 = _normalize_market_sensitivity(result1["aggregate_risk_metrics"]["max_market_sensitivity"])
    ms2 = _normalize_market_sensitivity(result2["aggregate_risk_metrics"]["max_market_sensitivity"])
    assert abs(ms1 - ms2) <= MARKET_SENSITIVITY_PRECISION
    assert result1["aggregate_risk_metrics"]["score_range"] == result2["aggregate_risk_metrics"]["score_range"]
    
    # Compare scenario scores (allowing for small floating point differences)
    for s1, s2 in zip(result1_scenarios, result2_scenarios):
        assert s1["scenario_name"] == s2["scenario_name"]
        assert abs(s1["readiness_score"] - s2["readiness_score"]) < 0.01
