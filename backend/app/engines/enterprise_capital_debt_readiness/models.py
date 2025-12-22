from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class DebtInstrument:
    instrument_id: str
    principal: Decimal
    annual_interest_rate: Decimal
    amortization: str  # amortizing | interest_only | bullet
    payment_frequency_months: int
    maturity_date: date


@dataclass(frozen=True)
class DebtPayment:
    payment_date: date
    interest: Decimal
    principal: Decimal
    total: Decimal


@dataclass(frozen=True)
class CapitalAdequacyAssessment:
    dataset_version_id: str
    analysis_date: date
    available_capital: Decimal
    required_capital: Decimal
    coverage_ratio: Decimal | None
    runway_months: Decimal | None
    debt_to_equity_ratio: Decimal | None
    current_ratio: Decimal | None
    adequacy_level: str  # strong | adequate | weak | insufficient_data
    flags: list[str]
    assumptions: list[dict]


@dataclass(frozen=True)
class DebtServiceAssessment:
    dataset_version_id: str
    analysis_date: date
    horizon_months: int
    debt_service_total: Decimal
    interest_total: Decimal
    principal_total: Decimal
    dscr: Decimal | None
    interest_coverage: Decimal | None
    maturity_concentration: Decimal | None
    ability_level: str  # strong | adequate | weak | insufficient_data
    schedule: list[DebtPayment]
    flags: list[str]
    assumptions: list[dict]

