from __future__ import annotations

import calendar
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

from backend.app.engines.enterprise_capital_debt_readiness.models import DebtInstrument, DebtPayment, DebtServiceAssessment


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


def _add_months(d: date, months: int) -> date:
    year = d.year + (d.month - 1 + months) // 12
    month = (d.month - 1 + months) % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _parse_date(value: object, *, default: date | None = None) -> date | None:
    if isinstance(value, date):
        return value
    if not isinstance(value, str) or not value.strip():
        return default
    try:
        # Accept YYYY-MM-DD and ISO timestamps; we only keep the date portion.
        return date.fromisoformat(value[:10])
    except ValueError:
        return default


def _instrument_from_dict(
    *,
    raw: dict[str, Any],
    analysis_date: date,
    defaults: dict[str, Any],
) -> DebtInstrument | None:
    instrument_id = str(raw.get("id") or raw.get("instrument_id") or raw.get("name") or "").strip()
    if not instrument_id:
        return None

    principal = _d(raw.get("principal"))
    if principal is None or principal <= 0:
        return None

    rate = _d(raw.get("annual_interest_rate"), _d(defaults.get("default_annual_interest_rate"), Decimal("0.08")))
    if rate is None or rate < 0:
        rate = Decimal("0")

    amortization = str(raw.get("amortization") or defaults.get("default_amortization") or "amortizing").strip()
    if amortization not in ("amortizing", "interest_only", "bullet"):
        amortization = "amortizing"

    freq = raw.get("payment_frequency_months", defaults.get("default_payment_frequency_months", 1))
    try:
        payment_frequency_months = int(freq)
    except (TypeError, ValueError):
        payment_frequency_months = 1
    if payment_frequency_months <= 0:
        payment_frequency_months = 1

    maturity = _parse_date(raw.get("maturity_date"))
    if maturity is None:
        term_months = raw.get("term_months") or raw.get("remaining_term_months")
        try:
            term_months_int = int(term_months) if term_months is not None else None
        except (TypeError, ValueError):
            term_months_int = None
        if term_months_int is None or term_months_int <= 0:
            return None
        maturity = _add_months(analysis_date, term_months_int)

    if maturity <= analysis_date:
        return None

    return DebtInstrument(
        instrument_id=instrument_id,
        principal=principal,
        annual_interest_rate=rate,
        amortization=amortization,
        payment_frequency_months=payment_frequency_months,
        maturity_date=maturity,
    )


def _payment_dates(*, analysis_date: date, maturity_date: date, horizon_end: date, frequency_months: int) -> list[date]:
    end = min(maturity_date, horizon_end)
    dates: list[date] = []

    i = 1
    while True:
        candidate = _add_months(analysis_date, i * frequency_months)
        if candidate > end:
            break
        dates.append(candidate)
        i += 1

    if maturity_date <= horizon_end and (not dates or dates[-1] != maturity_date):
        dates.append(maturity_date)
    return dates


def _annuity_payment(*, principal: Decimal, periodic_rate: Decimal, periods: int) -> Decimal:
    if periods <= 0:
        return Decimal("0")
    if periodic_rate <= 0:
        return principal / Decimal(str(periods))
    one = Decimal("1")
    denom = one - (one + periodic_rate) ** (-periods)
    if denom == 0:
        return principal
    return principal * periodic_rate / denom


def build_debt_service_schedule(
    *,
    instrument: DebtInstrument,
    analysis_date: date,
    horizon_end: date,
) -> list[DebtPayment]:
    payment_dates = _payment_dates(
        analysis_date=analysis_date,
        maturity_date=instrument.maturity_date,
        horizon_end=horizon_end,
        frequency_months=instrument.payment_frequency_months,
    )
    if not payment_dates:
        return []

    periods_total = len(
        _payment_dates(
            analysis_date=analysis_date,
            maturity_date=instrument.maturity_date,
            horizon_end=instrument.maturity_date,
            frequency_months=instrument.payment_frequency_months,
        )
    )
    periodic_rate = instrument.annual_interest_rate / (Decimal("12") / Decimal(str(instrument.payment_frequency_months)))

    outstanding = instrument.principal
    payments: list[DebtPayment] = []

    if instrument.amortization == "amortizing":
        pmt = _annuity_payment(principal=outstanding, periodic_rate=periodic_rate, periods=periods_total)
        for idx, pay_date in enumerate(payment_dates, start=1):
            interest = outstanding * periodic_rate
            principal_component = max(Decimal("0"), pmt - interest)
            if idx == periods_total or pay_date == instrument.maturity_date:
                principal_component = outstanding
            total = interest + principal_component
            payments.append(
                DebtPayment(
                    payment_date=pay_date,
                    interest=_q(interest, "0.01"),
                    principal=_q(principal_component, "0.01"),
                    total=_q(total, "0.01"),
                )
            )
            outstanding = max(Decimal("0"), outstanding - principal_component)
            if outstanding == 0:
                break
        return payments

    if instrument.amortization == "interest_only":
        for pay_date in payment_dates:
            interest = outstanding * periodic_rate
            principal_component = Decimal("0")
            if pay_date == instrument.maturity_date:
                principal_component = outstanding
            total = interest + principal_component
            payments.append(
                DebtPayment(
                    payment_date=pay_date,
                    interest=_q(interest, "0.01"),
                    principal=_q(principal_component, "0.01"),
                    total=_q(total, "0.01"),
                )
            )
        return payments

    # bullet
    for pay_date in payment_dates:
        interest = outstanding * periodic_rate
        principal_component = Decimal("0")
        if pay_date == instrument.maturity_date:
            principal_component = outstanding
        total = interest + principal_component
        payments.append(
            DebtPayment(
                payment_date=pay_date,
                interest=_q(interest, "0.01"),
                principal=_q(principal_component, "0.01"),
                total=_q(total, "0.01"),
            )
        )
    return payments


def assess_debt_service_ability(
    *,
    dataset_version_id: str,
    analysis_date: date,
    financial: dict[str, Any],
    assumptions: dict[str, Any],
) -> DebtServiceAssessment:
    debt_cfg = assumptions.get("debt_service") if isinstance(assumptions.get("debt_service"), dict) else {}
    horizon_months = int(debt_cfg.get("horizon_months", 12))
    min_dscr = _d(debt_cfg.get("min_dscr"), Decimal("1.25")) or Decimal("1.25")
    min_interest_coverage = _d(debt_cfg.get("min_interest_coverage"), Decimal("2.0")) or Decimal("2.0")
    if horizon_months <= 0:
        raise ValueError("HORIZON_MONTHS_INVALID")

    horizon_end = _add_months(analysis_date, horizon_months)
    debt = financial.get("debt") if isinstance(financial.get("debt"), dict) else {}
    instruments_raw = debt.get("instruments") if isinstance(debt.get("instruments"), list) else []

    instruments: list[DebtInstrument] = []
    for item in instruments_raw:
        if isinstance(item, dict):
            inst = _instrument_from_dict(raw=item, analysis_date=analysis_date, defaults=debt_cfg)
            if inst is not None:
                instruments.append(inst)

    principal_annual = sum((inst.principal for inst in instruments), Decimal("0"))
    interest_annual = sum((inst.principal * inst.annual_interest_rate) for inst in instruments if inst.annual_interest_rate is not None)

    schedule: list[DebtPayment] = []
    for inst in instruments:
        schedule.extend(build_debt_service_schedule(instrument=inst, analysis_date=analysis_date, horizon_end=horizon_end))
    schedule.sort(key=lambda p: (p.payment_date.isoformat(), p.total))

    debt_service_total = sum((p.total for p in schedule), Decimal("0"))
    interest_total = sum((p.interest for p in schedule), Decimal("0"))
    principal_total = sum((p.principal for p in schedule), Decimal("0"))

    total_principal = sum((i.principal for i in instruments), Decimal("0"))
    maturity_concentration: Decimal | None = None
    if total_principal > 0:
        maturity_concentration = principal_total / total_principal

    income = financial.get("income_statement") if isinstance(financial.get("income_statement"), dict) else {}
    cashflow = financial.get("cash_flow") if isinstance(financial.get("cash_flow"), dict) else {}

    cash_cfg = assumptions.get("cash_available") if isinstance(assumptions.get("cash_available"), dict) else {}
    source_metric = str(cash_cfg.get("source_metric", "ebitda"))
    ebitda_factor = _d(cash_cfg.get("ebitda_to_cash_factor"), Decimal("0.7")) or Decimal("0.7")

    ebitda_annual = _d(income.get("ebitda"), None)
    cash_available_source: str | None = None
    cash_available_annual = _d(cashflow.get("cash_available_for_debt_service_annual"), None)
    if cash_available_annual is not None:
        cash_available_source = "cash_flow"
    else:
        cash_available_annual = _d(cashflow.get("net_operating_income"), None)
        if cash_available_annual is not None:
            cash_available_source = "net_operating_income"
        elif source_metric == "ebitda" and ebitda_annual is not None:
            cash_available_annual = ebitda_annual * ebitda_factor
            cash_available_source = "ebitda"

    # Scale annual cash available to match horizon_months
    horizon_scale_factor = Decimal(str(horizon_months)) / Decimal("12")
    cash_available_horizon: Decimal | None = None
    if cash_available_annual is not None:
        cash_available_horizon = cash_available_annual * horizon_scale_factor

    dscr: Decimal | None = None
    if cash_available_annual is not None and principal_annual > 0:
        dscr = cash_available_annual / principal_annual

    interest_coverage: Decimal | None = None
    if ebitda_annual is not None and interest_annual > 0:
        interest_coverage = ebitda_annual / interest_annual

    flags: list[str] = []
    if not instruments:
        flags.append("MISSING_DEBT_INSTRUMENTS")
    if cash_available_source != "cash_flow":
        flags.append("MISSING_CASH_AVAILABLE_FOR_DEBT_SERVICE")
    if ebitda_annual is None:
        flags.append("MISSING_EBITDA")

    ability_level = "insufficient_data" if (not instruments and debt_service_total == 0) else "adequate"
    if ability_level != "insufficient_data":
        if dscr is not None and dscr < min_dscr:
            ability_level = "weak"
            flags.append("DSCR_BELOW_THRESHOLD")
        if interest_coverage is not None and interest_coverage < min_interest_coverage:
            ability_level = "weak"
            flags.append("INTEREST_COVERAGE_BELOW_THRESHOLD")
        if ability_level == "adequate" and dscr is not None and dscr >= (min_dscr + Decimal("0.50")):
            ability_level = "strong"

    assumption_records = [
        {
            "id": "assumption_debt_service_horizon",
            "description": "Debt service horizon in months for schedule construction and coverage tests.",
            "source": f"assumptions.debt_service.horizon_months (default {horizon_months})",
            "impact": "Controls which payments are included in the assessment horizon. Annual cash/EBITDA metrics are scaled to match this horizon.",
            "sensitivity": "Medium - longer horizons increase debt service totals.",
        },
        {
            "id": "assumption_cash_available_source",
            "description": "Primary metric used to estimate cash available for debt service when not explicitly provided.",
            "source": f"assumptions.cash_available.source_metric (default {source_metric})",
            "impact": "Affects DSCR estimation when cash_available_for_debt_service_annual is missing.",
            "sensitivity": "High - depends on the quality of EBITDA/NOI inputs.",
        },
        {
            "id": "assumption_horizon_scaling",
            "description": "Annual cash and EBITDA metrics are scaled to match the debt service horizon. Annual values are multiplied by (horizon_months / 12) to ensure numerator and denominator consistency in DSCR and interest coverage calculations.",
            "source": f"Internal calculation: annual_value * (horizon_months / 12)",
            "impact": "Ensures numerator and denominator consistency for DSCR and interest coverage across non-12-month horizons. Without scaling, annual metrics would be compared against horizon-scaled debt service, causing inaccuracies.",
            "sensitivity": "High - critical for accurate ratio calculations when horizon_months != 12.",
        },
    ]

    return DebtServiceAssessment(
        dataset_version_id=dataset_version_id,
        analysis_date=analysis_date,
        horizon_months=horizon_months,
        debt_service_total=_q(debt_service_total, "0.01"),
        interest_total=_q(interest_total, "0.01"),
        principal_total=_q(principal_total, "0.01"),
        dscr=_q(dscr, "0.0001") if dscr is not None else None,
        interest_coverage=_q(interest_coverage, "0.0001") if interest_coverage is not None else None,
        maturity_concentration=_q(maturity_concentration, "0.0001") if maturity_concentration is not None else None,
        ability_level=ability_level,
        schedule=schedule,
        flags=sorted(set(flags)),
        assumptions=assumption_records,
    )


def debt_service_payload(assessment: DebtServiceAssessment) -> dict[str, Any]:
    return {
        "dataset_version_id": assessment.dataset_version_id,
        "analysis_date": assessment.analysis_date.isoformat(),
        "horizon_months": assessment.horizon_months,
        "debt_service_total": _f(assessment.debt_service_total),
        "interest_total": _f(assessment.interest_total),
        "principal_total": _f(assessment.principal_total),
        "dscr": _f(assessment.dscr),
        "interest_coverage": _f(assessment.interest_coverage),
        "maturity_concentration": _f(assessment.maturity_concentration),
        "ability_level": assessment.ability_level,
        "flags": assessment.flags,
        "assumptions": assessment.assumptions,
        "schedule": [
            {
                "payment_date": p.payment_date.isoformat(),
                "interest": _f(p.interest),
                "principal": _f(p.principal),
                "total": _f(p.total),
            }
            for p in assessment.schedule
        ],
    }
