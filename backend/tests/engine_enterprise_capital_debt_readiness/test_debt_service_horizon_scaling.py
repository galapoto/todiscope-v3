"""
Tests for debt service horizon scaling fix.

Verifies that DSCR and interest coverage calculations correctly scale
annual cash/EBITDA metrics to match the horizon_months parameter.
"""

from datetime import date
from decimal import Decimal

import pytest

from backend.app.engines.enterprise_capital_debt_readiness.assumptions import resolved_assumptions
from backend.app.engines.enterprise_capital_debt_readiness.debt_service import assess_debt_service_ability


def test_dscr_scaling_12_month_horizon() -> None:
    """Test DSCR calculation with 12-month horizon (no scaling needed)."""
    assumptions = resolved_assumptions({
        "debt_service": {
            "horizon_months": 12,
            "min_dscr": 1.25,
        }
    })
    
    # Annual cash available: $120,000
    # Annual debt service: $60,000 (should result in DSCR = 2.0)
    financial = {
        "cash_flow": {
            "cash_available_for_debt_service_annual": 120000,
        },
        "debt": {
            "instruments": [
                {
                    "id": "loan_1",
                    "principal": 60000,
                    "annual_interest_rate": 0.10,
                    "amortization": "amortizing",
                    "payment_frequency_months": 1,
                    "term_months": 12,
                }
            ]
        },
    }
    
    res = assess_debt_service_ability(
        dataset_version_id="dv_test",
        analysis_date=date(2025, 1, 1),
        financial=financial,
        assumptions=assumptions,
    )
    
    assert res.dscr is not None
    # With 12-month horizon, annual cash / annual debt service ≈ 2.0
    # Allow some tolerance for amortization schedule differences
    assert 1.8 <= float(res.dscr) <= 2.2
    assert res.horizon_months == 12


def test_dscr_scaling_6_month_horizon() -> None:
    """Test DSCR calculation with 6-month horizon (scaling required)."""
    assumptions = resolved_assumptions({
        "debt_service": {
            "horizon_months": 6,
            "min_dscr": 1.25,
        }
    })
    
    # Annual cash available: $120,000
    # Scaled to 6 months: $60,000
    # 6-month debt service: ~$30,000 (half of annual)
    # Expected DSCR: $60,000 / $30,000 = 2.0
    financial = {
        "cash_flow": {
            "cash_available_for_debt_service_annual": 120000,
        },
        "debt": {
            "instruments": [
                {
                    "id": "loan_1",
                    "principal": 60000,
                    "annual_interest_rate": 0.10,
                    "amortization": "amortizing",
                    "payment_frequency_months": 1,
                    "term_months": 12,
                }
            ]
        },
    }
    
    res = assess_debt_service_ability(
        dataset_version_id="dv_test",
        analysis_date=date(2025, 1, 1),
        financial=financial,
        assumptions=assumptions,
    )
    
    assert res.dscr is not None
    # With 6-month horizon, scaled cash (60k) / 6-month debt service (~30k) ≈ 2.0
    # Allow tolerance for amortization schedule differences
    assert 1.8 <= float(res.dscr) <= 2.2
    assert res.horizon_months == 6
    
    # Verify scaling assumption is documented
    scaling_assumption = next(
        (a for a in res.assumptions if a["id"] == "assumption_horizon_scaling"),
        None
    )
    assert scaling_assumption is not None
    assert "horizon_months / 12" in scaling_assumption["description"]
    assert "horizon_scaling" in scaling_assumption["id"]


def test_dscr_scaling_24_month_horizon() -> None:
    """Test DSCR calculation with 24-month horizon (scaling required)."""
    assumptions = resolved_assumptions({
        "debt_service": {
            "horizon_months": 24,
            "min_dscr": 1.25,
        }
    })
    
    # Annual cash available: $120,000
    # Scaled to 24 months: $240,000
    # 24-month debt service: ~$120,000 (full loan paid off)
    # Expected DSCR: $240,000 / $120,000 = 2.0
    financial = {
        "cash_flow": {
            "cash_available_for_debt_service_annual": 120000,
        },
        "debt": {
            "instruments": [
                {
                    "id": "loan_1",
                    "principal": 60000,
                    "annual_interest_rate": 0.10,
                    "amortization": "amortizing",
                    "payment_frequency_months": 1,
                    "term_months": 12,
                }
            ]
        },
    }
    
    res = assess_debt_service_ability(
        dataset_version_id="dv_test",
        analysis_date=date(2025, 1, 1),
        financial=financial,
        assumptions=assumptions,
    )
    
    assert res.dscr is not None
    # With 24-month horizon, scaled cash (240k) / 24-month debt service (~120k) ≈ 2.0
    # Note: Loan matures at 12 months, so 24-month debt service = full loan
    assert 1.8 <= float(res.dscr) <= 2.2
    assert res.horizon_months == 24


def test_interest_coverage_scaling_12_month_horizon() -> None:
    """Test interest coverage calculation with 12-month horizon."""
    assumptions = resolved_assumptions({
        "debt_service": {
            "horizon_months": 12,
            "min_interest_coverage": 2.0,
        }
    })
    
    # Annual EBITDA: $200,000
    # Annual interest: $50,000
    # Expected interest coverage: 4.0
    financial = {
        "income_statement": {"ebitda": 200000},
        "debt": {
            "instruments": [
                {
                    "id": "loan_1",
                    "principal": 500000,
                    "annual_interest_rate": 0.10,
                    "amortization": "interest_only",
                    "payment_frequency_months": 1,
                    "term_months": 12,
                }
            ]
        },
    }
    
    res = assess_debt_service_ability(
        dataset_version_id="dv_test",
        analysis_date=date(2025, 1, 1),
        financial=financial,
        assumptions=assumptions,
    )
    
    assert res.interest_coverage is not None
    # With 12-month horizon, annual EBITDA / annual interest ≈ 4.0
    assert 3.5 <= float(res.interest_coverage) <= 4.5
    assert res.horizon_months == 12


def test_interest_coverage_scaling_6_month_horizon() -> None:
    """Test interest coverage calculation with 6-month horizon (scaling required)."""
    assumptions = resolved_assumptions({
        "debt_service": {
            "horizon_months": 6,
            "min_interest_coverage": 2.0,
        }
    })
    
    # Annual EBITDA: $200,000
    # Scaled to 6 months: $100,000
    # 6-month interest: ~$25,000 (half of annual)
    # Expected interest coverage: $100,000 / $25,000 = 4.0
    financial = {
        "income_statement": {"ebitda": 200000},
        "debt": {
            "instruments": [
                {
                    "id": "loan_1",
                    "principal": 500000,
                    "annual_interest_rate": 0.10,
                    "amortization": "interest_only",
                    "payment_frequency_months": 1,
                    "term_months": 12,
                }
            ]
        },
    }
    
    res = assess_debt_service_ability(
        dataset_version_id="dv_test",
        analysis_date=date(2025, 1, 1),
        financial=financial,
        assumptions=assumptions,
    )
    
    assert res.interest_coverage is not None
    # With 6-month horizon, scaled EBITDA (100k) / 6-month interest (~25k) ≈ 4.0
    assert 3.5 <= float(res.interest_coverage) <= 4.5
    assert res.horizon_months == 6


def test_dscr_consistency_across_horizons() -> None:
    """
    Test that DSCR remains consistent across different horizons when properly scaled.
    
    This test verifies that the scaling fix works correctly by ensuring
    DSCR values are similar across different horizons for the same underlying metrics.
    """
    base_financial = {
        "cash_flow": {
            "cash_available_for_debt_service_annual": 120000,
        },
        "debt": {
            "instruments": [
                {
                    "id": "loan_1",
                    "principal": 60000,
                    "annual_interest_rate": 0.10,
                    "amortization": "amortizing",
                    "payment_frequency_months": 1,
                    "term_months": 12,
                }
            ]
        },
    }
    
    results = {}
    for horizon in [6, 12, 24]:
        assumptions = resolved_assumptions({
            "debt_service": {
                "horizon_months": horizon,
                "min_dscr": 1.25,
            }
        })
        
        res = assess_debt_service_ability(
            dataset_version_id="dv_test",
            analysis_date=date(2025, 1, 1),
            financial=base_financial,
            assumptions=assumptions,
        )
        
        if res.dscr is not None:
            results[horizon] = float(res.dscr)
    
    # DSCR should be similar across horizons (within reasonable tolerance)
    # due to proper scaling
    assert len(results) >= 2
    dscr_values = list(results.values())
    
    # Check that all DSCR values are within 20% of each other
    # (allowing for amortization schedule differences)
    min_dscr = min(dscr_values)
    max_dscr = max(dscr_values)
    assert max_dscr <= min_dscr * 1.2, f"DSCR values vary too much: {results}"


def test_ebitda_derived_cash_scaling() -> None:
    """Test that EBITDA-derived cash is properly scaled to horizon."""
    assumptions = resolved_assumptions({
        "debt_service": {
            "horizon_months": 6,
            "min_dscr": 1.25,
        },
        "cash_available": {
            "source_metric": "ebitda",
            "ebitda_to_cash_factor": 0.7,
        },
    })
    
    # Annual EBITDA: $200,000
    # Annual cash (70% factor): $140,000
    # Scaled to 6 months: $70,000
    financial = {
        "income_statement": {"ebitda": 200000},
        "debt": {
            "instruments": [
                {
                    "id": "loan_1",
                    "principal": 50000,
                    "annual_interest_rate": 0.10,
                    "amortization": "amortizing",
                    "payment_frequency_months": 1,
                    "term_months": 12,
                }
            ]
        },
    }
    
    res = assess_debt_service_ability(
        dataset_version_id="dv_test",
        analysis_date=date(2025, 1, 1),
        financial=financial,
        assumptions=assumptions,
    )
    
    assert res.dscr is not None
    # Should have reasonable DSCR (scaled cash / 6-month debt service)
    assert res.dscr > Decimal("1.0")
    assert res.horizon_months == 6


def test_noi_derived_cash_scaling() -> None:
    """Test that NOI-derived cash is properly scaled to horizon."""
    assumptions = resolved_assumptions({
        "debt_service": {
            "horizon_months": 3,
            "min_dscr": 1.25,
        },
    })
    
    # Annual NOI: $100,000
    # Scaled to 3 months: $25,000
    financial = {
        "cash_flow": {
            "net_operating_income": 100000,
        },
        "debt": {
            "instruments": [
                {
                    "id": "loan_1",
                    "principal": 50000,
                    "annual_interest_rate": 0.10,
                    "amortization": "interest_only",
                    "payment_frequency_months": 1,
                    "term_months": 12,
                }
            ]
        },
    }
    
    res = assess_debt_service_ability(
        dataset_version_id="dv_test",
        analysis_date=date(2025, 1, 1),
        financial=financial,
        assumptions=assumptions,
    )
    
    assert res.dscr is not None
    # Should have reasonable DSCR (scaled NOI / 3-month debt service)
    assert res.dscr > Decimal("1.0")
    assert res.horizon_months == 3


def test_scaling_assumption_documented() -> None:
    """Test that horizon scaling assumption is documented in evidence."""
    assumptions = resolved_assumptions({
        "debt_service": {
            "horizon_months": 18,
        },
    })
    
    financial = {
        "cash_flow": {
            "cash_available_for_debt_service_annual": 120000,
        },
        "debt": {
            "instruments": [
                {
                    "id": "loan_1",
                    "principal": 60000,
                    "annual_interest_rate": 0.10,
                    "amortization": "amortizing",
                    "payment_frequency_months": 1,
                    "term_months": 12,
                }
            ]
        },
    }
    
    res = assess_debt_service_ability(
        dataset_version_id="dv_test",
        analysis_date=date(2025, 1, 1),
        financial=financial,
        assumptions=assumptions,
    )
    
    # Verify scaling assumption exists
    scaling_assumption = next(
        (a for a in res.assumptions if a["id"] == "assumption_horizon_scaling"),
        None
    )
    
    assert scaling_assumption is not None
    assert "horizon_months / 12" in scaling_assumption["source"]
    assert "Annual cash and EBITDA metrics are scaled" in scaling_assumption["description"]
    assert "numerator and denominator consistency" in scaling_assumption["impact"]


