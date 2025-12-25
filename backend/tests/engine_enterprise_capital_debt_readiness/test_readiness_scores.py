"""
Tests for readiness scores calculation.

Verifies that composite readiness scores are correctly calculated
integrating capital adequacy, debt service, credit risk, and cross-engine data.
"""

from datetime import date
from decimal import Decimal

import pytest

from backend.app.engines.enterprise_capital_debt_readiness.assumptions import resolved_assumptions
from backend.app.engines.enterprise_capital_debt_readiness.capital_adequacy import assess_capital_adequacy
from backend.app.engines.enterprise_capital_debt_readiness.debt_service import assess_debt_service_ability
from backend.app.engines.enterprise_capital_debt_readiness.readiness_scores import (
    calculate_composite_readiness_score,
)


def test_readiness_score_strong_capital_and_debt() -> None:
    """Test readiness score calculation with strong capital and debt service."""
    assumptions = resolved_assumptions({})
    financial = {
        "balance_sheet": {
            "cash_and_equivalents": 1000000,
            "current_assets": 2000000,
            "current_liabilities": 500000,
            "total_equity": 5000000,
        },
        "income_statement": {
            "ebitda": 800000,
            "operating_expenses": 400000,
        },
        "debt": {
            "total_debt": 2000000,
            "instruments": [
                {
                    "id": "loan_1",
                    "principal": 1000000,
                    "annual_interest_rate": 0.05,
                    "amortization": "amortizing",
                    "payment_frequency_months": 1,
                    "term_months": 12,
                }
            ],
        },
        "cash_flow": {
            "cash_available_for_debt_service_annual": 600000,
        },
        "capex_plan_12m": 200000,
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
    
    # Calculate readiness score
    result = calculate_composite_readiness_score(
        capital_adequacy=cap,
        debt_service=debt,
        financial=financial,
        assumptions=assumptions,
    )
    
    assert result["readiness_score"] >= 70.0  # Should be good or excellent
    assert result["readiness_level"] in ("excellent", "good")
    assert "component_scores" in result
    assert "capital_adequacy" in result["component_scores"]
    assert "debt_service" in result["component_scores"]
    assert "credit_risk" in result["component_scores"]


def test_readiness_score_weak_capital() -> None:
    """Test readiness score calculation with weak capital adequacy."""
    assumptions = resolved_assumptions({})
    financial = {
        "balance_sheet": {
            "cash_and_equivalents": 50000,  # Low cash
            "current_assets": 200000,
            "current_liabilities": 300000,  # Negative working capital
            "total_equity": 1000000,
        },
        "income_statement": {
            "ebitda": 200000,
            "operating_expenses": 500000,
        },
        "debt": {
            "total_debt": 500000,
            "instruments": [],
        },
        "cash_flow": {},
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
    
    result = calculate_composite_readiness_score(
        capital_adequacy=cap,
        debt_service=debt,
        financial=financial,
        assumptions=assumptions,
    )
    
    # Weak capital should lower the score
    assert result["readiness_score"] < 70.0
    assert result["readiness_level"] in ("adequate", "weak")
    assert result["component_scores"]["capital_adequacy"] < 70.0


def test_readiness_score_with_ff_exposure() -> None:
    """Test readiness score calculation with Financial Forensics leakage exposure."""
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
    
    # Test with FF exposure
    result_with_exposure = calculate_composite_readiness_score(
        capital_adequacy=cap,
        debt_service=debt,
        financial=financial,
        assumptions=assumptions,
        ff_leakage_exposure=Decimal("5000000"),  # $5M exposure
    )
    
    # Test without FF exposure
    result_without_exposure = calculate_composite_readiness_score(
        capital_adequacy=cap,
        debt_service=debt,
        financial=financial,
        assumptions=assumptions,
        ff_leakage_exposure=None,
    )
    
    # Score with exposure should be lower
    assert result_with_exposure["readiness_score"] < result_without_exposure["readiness_score"]
    assert result_with_exposure["component_scores"]["financial_forensics"] < result_without_exposure["component_scores"]["financial_forensics"]


def test_readiness_score_with_deal_readiness() -> None:
    """Test readiness score calculation with Deal Readiness Engine data."""
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
    
    # Test with deal readiness score
    result_with_deal = calculate_composite_readiness_score(
        capital_adequacy=cap,
        debt_service=debt,
        financial=financial,
        assumptions=assumptions,
        deal_readiness_score=Decimal("85"),  # High deal readiness
    )
    
    # Test without deal readiness score
    result_without_deal = calculate_composite_readiness_score(
        capital_adequacy=cap,
        debt_service=debt,
        financial=financial,
        assumptions=assumptions,
        deal_readiness_score=None,
    )
    
    # Score with high deal readiness should be slightly higher
    assert result_with_deal["readiness_score"] >= result_without_deal["readiness_score"]
    assert result_with_deal["component_scores"]["deal_readiness"] == 85.0


def test_readiness_score_component_breakdown() -> None:
    """Test that readiness score includes detailed component breakdown."""
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
    
    result = calculate_composite_readiness_score(
        capital_adequacy=cap,
        debt_service=debt,
        financial=financial,
        assumptions=assumptions,
    )
    
    # Verify component scores exist
    assert "component_scores" in result
    assert "capital_adequacy" in result["component_scores"]
    assert "debt_service" in result["component_scores"]
    assert "credit_risk" in result["component_scores"]
    assert "financial_forensics" in result["component_scores"]
    assert "deal_readiness" in result["component_scores"]
    
    # Verify breakdown exists
    assert "breakdown" in result
    assert "capital_adequacy_level" in result["breakdown"]
    assert "debt_service_level" in result["breakdown"]
    assert "credit_risk_level" in result["breakdown"]
    
    # Verify credit risk details
    assert "credit_risk_details" in result
    assert "credit_risk_score" in result["credit_risk_details"]
    assert "risk_level" in result["credit_risk_details"]


def test_readiness_score_custom_weights() -> None:
    """Test readiness score calculation with custom weights."""
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
    
    # Test with custom weights (emphasize capital adequacy)
    custom_weights = {
        "capital_adequacy": Decimal("0.50"),
        "debt_service": Decimal("0.30"),
        "credit_risk": Decimal("0.15"),
        "financial_forensics": Decimal("0.05"),
        "deal_readiness": Decimal("0.00"),
    }
    
    result = calculate_composite_readiness_score(
        capital_adequacy=cap,
        debt_service=debt,
        financial=financial,
        assumptions=assumptions,
        weights=custom_weights,
    )
    
    # Verify score is calculated
    assert 0.0 <= result["readiness_score"] <= 100.0
    assert result["readiness_level"] in ("excellent", "good", "adequate", "weak")


def test_readiness_score_edge_case_insufficient_data() -> None:
    """Test readiness score calculation with insufficient data."""
    assumptions = resolved_assumptions({})
    financial = {
        "balance_sheet": {},
        "income_statement": {},
        "debt": {},
        "cash_flow": {},
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
    
    result = calculate_composite_readiness_score(
        capital_adequacy=cap,
        debt_service=debt,
        financial=financial,
        assumptions=assumptions,
    )
    
    # Should still calculate a score (defaults to moderate)
    assert 0.0 <= result["readiness_score"] <= 100.0
    assert result["readiness_level"] in ("excellent", "good", "adequate", "weak")
    # With insufficient data, scores should be lower
    assert result["component_scores"]["capital_adequacy"] <= 50.0


def test_readiness_score_deterministic() -> None:
    """Test that readiness score calculation is deterministic."""
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
    
    # Calculate twice with same inputs
    result1 = calculate_composite_readiness_score(
        capital_adequacy=cap,
        debt_service=debt,
        financial=financial,
        assumptions=assumptions,
    )
    
    result2 = calculate_composite_readiness_score(
        capital_adequacy=cap,
        debt_service=debt,
        financial=financial,
        assumptions=assumptions,
    )
    
    # Results should be identical
    assert result1["readiness_score"] == result2["readiness_score"]
    assert result1["readiness_level"] == result2["readiness_level"]
    assert result1["component_scores"] == result2["component_scores"]






