from datetime import date

from backend.app.engines.enterprise_capital_debt_readiness.assumptions import resolved_assumptions
from backend.app.engines.enterprise_capital_debt_readiness.capital_adequacy import assess_capital_adequacy
from backend.app.engines.enterprise_capital_debt_readiness.debt_service import assess_debt_service_ability


def test_capital_adequacy_strong_when_buffer_covered() -> None:
    assumptions = resolved_assumptions({})
    financial = {
        "balance_sheet": {
            "cash_and_equivalents": 500000,
            "current_assets": 900000,
            "current_liabilities": 400000,
            "total_equity": 600000,
        },
        "income_statement": {"operating_expenses": 600000},
        "debt": {"total_debt": 400000, "undrawn_credit_lines": 200000},
        "capex_plan_12m": 50000,
    }
    res = assess_capital_adequacy(
        dataset_version_id="dv_test",
        analysis_date=date(2025, 1, 1),
        financial=financial,
        assumptions=assumptions,
    )
    assert res.coverage_ratio is not None
    assert res.coverage_ratio >= 1
    assert res.adequacy_level in ("adequate", "strong")


def test_debt_service_schedule_and_dscr_for_amortizing_loan() -> None:
    assumptions = resolved_assumptions({})
    financial = {
        "income_statement": {"ebitda": 300000},
        "debt": {
            "instruments": [
                {
                    "id": "loan_a",
                    "principal": 120000,
                    "annual_interest_rate": 0.12,
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
    assert res.debt_service_total > 0
    assert len(res.schedule) >= 12
    # With high EBITDA relative to this loan size, coverage should not be weak.
    assert res.ability_level in ("adequate", "strong", "insufficient_data")

