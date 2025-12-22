from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

from backend.app.engines.enterprise_capital_debt_readiness.models import CapitalAdequacyAssessment
from backend.app.engines.enterprise_capital_debt_readiness.credit_readiness import (
    calculate_current_ratio,
    calculate_debt_to_equity_ratio,
)


def _d(value: object, default: Decimal | None = None) -> Decimal | None:
    if value is None:
        return default
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return default


def _q(value: Decimal, quantum: str = "0.0001") -> Decimal:
    return value.quantize(Decimal(quantum), rounding=ROUND_HALF_UP)


def _f(value: Decimal | None) -> float | None:
    return float(value) if value is not None else None


def assess_capital_adequacy(
    *,
    dataset_version_id: str,
    analysis_date: date,
    financial: dict[str, Any],
    assumptions: dict[str, Any],
) -> CapitalAdequacyAssessment:
    cap_cfg = assumptions.get("capital_adequacy") if isinstance(assumptions.get("capital_adequacy"), dict) else {}
    buffer_months = int(cap_cfg.get("operating_buffer_months", 3))
    min_runway_months = _d(cap_cfg.get("min_runway_months"), Decimal("3")) or Decimal("3")
    liquid_wc_factor = _d(cap_cfg.get("liquid_working_capital_factor"), Decimal("0.5")) or Decimal("0.5")
    max_debt_to_equity = _d(cap_cfg.get("max_debt_to_equity"), Decimal("2.0")) or Decimal("2.0")
    min_current_ratio = _d(cap_cfg.get("min_current_ratio"), Decimal("1.0")) or Decimal("1.0")

    balance = financial.get("balance_sheet") if isinstance(financial.get("balance_sheet"), dict) else {}
    income = financial.get("income_statement") if isinstance(financial.get("income_statement"), dict) else {}
    cashflow = financial.get("cash_flow") if isinstance(financial.get("cash_flow"), dict) else {}
    debt = financial.get("debt") if isinstance(financial.get("debt"), dict) else {}

    cash = _d(balance.get("cash_and_equivalents"), Decimal("0")) or Decimal("0")
    current_assets = _d(balance.get("current_assets"), None)
    current_liabilities = _d(balance.get("current_liabilities"), None)
    total_equity = _d(balance.get("total_equity"), None)
    total_debt = _d(debt.get("total_debt"), _d(balance.get("total_debt"), None))
    undrawn_credit_lines = _d(debt.get("undrawn_credit_lines"), Decimal("0")) or Decimal("0")

    capex_12m = _d(financial.get("capex_plan_12m"), _d(cashflow.get("capex_12m"), Decimal("0"))) or Decimal("0")
    operating_expenses_annual = _d(income.get("operating_expenses"), None)
    if operating_expenses_annual is None:
        operating_expenses_annual = _d(income.get("opex"), Decimal("0")) or Decimal("0")

    monthly_opex = operating_expenses_annual / Decimal("12") if operating_expenses_annual > 0 else Decimal("0")
    operating_buffer = monthly_opex * Decimal(str(buffer_months))

    working_capital: Decimal | None = None
    if current_assets is not None and current_liabilities is not None:
        working_capital = current_assets - current_liabilities

    liquid_working_capital = (max(Decimal("0"), working_capital) * liquid_wc_factor) if working_capital is not None else Decimal("0")
    available_capital = cash + liquid_working_capital + undrawn_credit_lines

    required_capital = operating_buffer + capex_12m
    coverage_ratio: Decimal | None = None
    if required_capital > 0:
        coverage_ratio = available_capital / required_capital

    runway_months: Decimal | None = None
    if monthly_opex > 0:
        runway_months = cash / monthly_opex

    debt_to_equity_ratio: Decimal | None = None
    if total_debt is not None and total_equity is not None and total_equity > 0:
        debt_to_equity_ratio = calculate_debt_to_equity_ratio(total_debt=total_debt, total_equity=total_equity)

    current_ratio: Decimal | None = None
    if current_assets is not None and current_liabilities is not None:
        current_ratio = calculate_current_ratio(current_assets=current_assets, current_liabilities=current_liabilities)

    flags: list[str] = []
    if total_equity is None:
        flags.append("MISSING_TOTAL_EQUITY")
    if total_debt is None:
        flags.append("MISSING_TOTAL_DEBT")
    if current_assets is None or current_liabilities is None:
        flags.append("MISSING_WORKING_CAPITAL_INPUTS")
    if operating_expenses_annual <= 0:
        flags.append("MISSING_OPERATING_EXPENSES")

    adequacy_level = "insufficient_data" if flags and len(flags) >= 2 else "adequate"
    if adequacy_level != "insufficient_data":
        if runway_months is not None and runway_months < min_runway_months:
            adequacy_level = "weak"
            flags.append("LOW_CASH_RUNWAY")
        if coverage_ratio is not None and coverage_ratio < Decimal("1.0"):
            adequacy_level = "weak"
            flags.append("CAPITAL_COVERAGE_BELOW_1X")
        if debt_to_equity_ratio is not None and debt_to_equity_ratio > max_debt_to_equity:
            adequacy_level = "weak"
            flags.append("DEBT_TO_EQUITY_TOO_HIGH")
        if current_ratio is not None and current_ratio < min_current_ratio:
            adequacy_level = "weak"
            flags.append("CURRENT_RATIO_TOO_LOW")
        if adequacy_level == "adequate" and coverage_ratio is not None and coverage_ratio >= Decimal("1.5"):
            adequacy_level = "strong"

    assumption_records = [
        {
            "id": "assumption_operating_buffer_months",
            "description": "Operating liquidity buffer in months of operating expenses.",
            "source": f"assumptions.capital_adequacy.operating_buffer_months (default {buffer_months})",
            "impact": "Directly increases required capital for near-term operations.",
            "sensitivity": "Medium - linear with operating expenses.",
        },
        {
            "id": "assumption_liquid_working_capital_factor",
            "description": "Fraction of positive working capital considered liquid/available.",
            "source": f"assumptions.capital_adequacy.liquid_working_capital_factor (default {liquid_wc_factor})",
            "impact": "Affects available capital estimate from working capital.",
            "sensitivity": "Medium - linear with working capital.",
        },
    ]

    return CapitalAdequacyAssessment(
        dataset_version_id=dataset_version_id,
        analysis_date=analysis_date,
        available_capital=_q(available_capital, "0.01"),
        required_capital=_q(required_capital, "0.01"),
        coverage_ratio=_q(coverage_ratio, "0.0001") if coverage_ratio is not None else None,
        runway_months=_q(runway_months, "0.01") if runway_months is not None else None,
        debt_to_equity_ratio=_q(debt_to_equity_ratio, "0.0001") if debt_to_equity_ratio is not None else None,
        current_ratio=_q(current_ratio, "0.0001") if current_ratio is not None else None,
        adequacy_level=adequacy_level,
        flags=sorted(set(flags)),
        assumptions=assumption_records,
    )


def capital_adequacy_payload(assessment: CapitalAdequacyAssessment) -> dict[str, Any]:
    return {
        "dataset_version_id": assessment.dataset_version_id,
        "analysis_date": assessment.analysis_date.isoformat(),
        "available_capital": _f(assessment.available_capital),
        "required_capital": _f(assessment.required_capital),
        "coverage_ratio": _f(assessment.coverage_ratio),
        "runway_months": _f(assessment.runway_months),
        "debt_to_equity_ratio": _f(assessment.debt_to_equity_ratio),
        "current_ratio": _f(assessment.current_ratio),
        "adequacy_level": assessment.adequacy_level,
        "flags": assessment.flags,
        "assumptions": assessment.assumptions,
    }

