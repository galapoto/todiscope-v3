from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any


def _as_float(value: object, default: float = 0.0) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class DistressedAsset:
    name: str | None
    value: float
    recovery_rate_pct: float

    @property
    def recovery_value(self) -> float:
        return self.value * (self.recovery_rate_pct / 100.0)


def _normalize_assets_value(value: object) -> float:
    if isinstance(value, dict):
        for candidate in ("total", "value", "amount"):
            if candidate in value:
                return _as_float(value.get(candidate))
        return _as_float(value.get("estimated_value")) if "estimated_value" in value else 0.0
    return _as_float(value)


def _extract_distressed_assets(payload: object, financial: dict) -> list[DistressedAsset]:
    entries: list[object] = []
    if isinstance(payload, dict):
        raw = payload.get("distressed_assets")
        if isinstance(raw, list):
            entries = raw
    if not entries and isinstance(financial.get("distressed_assets"), list):
        entries = financial["distressed_assets"]
    result: list[DistressedAsset] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        value = _as_float(entry.get("value"))
        name = str(entry.get("name")).strip() if entry.get("name") else None
        recovery_pct = _as_float(
            entry.get("recovery_rate_pct")
            or entry.get("recovery_rate")
            or entry.get("recovery"),
            0.0,
        )
        result.append(
            DistressedAsset(name=name if name else None, value=value, recovery_rate_pct=recovery_pct)
        )
    return result


@dataclass(frozen=True)
class DebtExposure:
    total_outstanding: float
    interest_rate_pct: float
    interest_payment: float
    collateral_value: float
    collateral_shortfall: float
    collateral_coverage_ratio: float
    assets_value: float
    leverage_ratio: float
    distressed_asset_value: float
    distressed_asset_recovery: float
    distressed_asset_recovery_ratio: float
    distressed_asset_count: int
    net_exposure_after_recovery: float

    def to_payload(self) -> dict[str, float | int]:
        return {
            "total_outstanding": self.total_outstanding,
            "interest_rate_pct": self.interest_rate_pct,
            "interest_payment": self.interest_payment,
            "collateral_value": self.collateral_value,
            "collateral_shortfall": self.collateral_shortfall,
            "collateral_coverage_ratio": self.collateral_coverage_ratio,
            "assets_value": self.assets_value,
            "leverage_ratio": self.leverage_ratio,
            "distressed_asset_value": self.distressed_asset_value,
            "distressed_asset_recovery": self.distressed_asset_recovery,
            "distressed_asset_recovery_ratio": self.distressed_asset_recovery_ratio,
            "distressed_asset_count": self.distressed_asset_count,
            "net_exposure_after_recovery": self.net_exposure_after_recovery,
        }


@dataclass(frozen=True)
class StressTestScenario:
    scenario_id: str
    description: str
    interest_rate_delta_pct: float
    collateral_market_impact_pct: float
    recovery_degradation_pct: float
    default_risk_increment_pct: float

    def to_payload(self) -> dict[str, float | str]:
        return {
            "scenario_id": self.scenario_id,
            "description": self.description,
            "interest_rate_delta_pct": self.interest_rate_delta_pct,
            "collateral_market_impact_pct": self.collateral_market_impact_pct,
            "recovery_degradation_pct": self.recovery_degradation_pct,
            "default_risk_increment_pct": self.default_risk_increment_pct,
        }


DEFAULT_STRESS_SCENARIOS: tuple[StressTestScenario, ...] = (
    StressTestScenario(
        scenario_id="interest_rate_spike",
        description="Interest rate hike with modest refinancing pressure.",
        interest_rate_delta_pct=2.5,
        collateral_market_impact_pct=-0.05,
        recovery_degradation_pct=-0.05,
        default_risk_increment_pct=0.02,
    ),
    StressTestScenario(
        scenario_id="market_crash",
        description="Market shock reduces collateral and distressed asset values.",
        interest_rate_delta_pct=0.5,
        collateral_market_impact_pct=-0.25,
        recovery_degradation_pct=-0.15,
        default_risk_increment_pct=0.05,
    ),
    StressTestScenario(
        scenario_id="default_wave",
        description="Elevated default risk further erodes recoveries.",
        interest_rate_delta_pct=1.0,
        collateral_market_impact_pct=-0.1,
        recovery_degradation_pct=-0.35,
        default_risk_increment_pct=0.08,
    ),
)


@dataclass(frozen=True)
class StressTestResult:
    scenario: StressTestScenario
    adjusted_interest_rate_pct: float
    interest_payment: float
    adjusted_collateral_value: float
    collateral_loss: float
    adjusted_distressed_asset_value: float
    distressed_asset_loss: float
    adjusted_distressed_asset_recovery: float
    default_risk_buffer: float
    net_exposure_after_recovery: float
    loss_estimate: float
    impact_score: float

    def to_payload(self) -> dict[str, float | str]:
        return {
            "scenario_id": self.scenario.scenario_id,
            "description": self.scenario.description,
            "interest_rate_pct": self.adjusted_interest_rate_pct,
            "interest_payment": self.interest_payment,
            "collateral_value": self.adjusted_collateral_value,
            "collateral_loss": self.collateral_loss,
            "distressed_asset_value": self.adjusted_distressed_asset_value,
            "distressed_asset_loss": self.distressed_asset_loss,
            "distressed_asset_recovery": self.adjusted_distressed_asset_recovery,
            "default_risk_buffer": self.default_risk_buffer,
            "net_exposure_after_recovery": self.net_exposure_after_recovery,
            "loss_estimate": self.loss_estimate,
            "impact_score": self.impact_score,
        }


def _aggregate_debt_instruments(instruments: list[dict]) -> tuple[float, float, float]:
    """Aggregate multiple debt instruments into totals and weighted average rate."""
    if not instruments:
        return 0.0, 0.0, 0.0

    total_outstanding = 0.0
    total_interest_weighted = 0.0
    total_collateral = 0.0

    for inst in instruments:
        if not isinstance(inst, dict):
            continue

        principal = _as_float(inst.get("principal") or inst.get("outstanding") or inst.get("amount"), 0.0)
        if principal <= 0:
            continue

        interest_rate = _as_float(
            inst.get("interest_rate_pct") or inst.get("annual_interest_rate") or inst.get("rate_pct"),
            0.0,
        )
        if interest_rate < 0:
            interest_rate = 0.0

        collateral = _as_float(
            inst.get("collateral_value") or inst.get("collateral") or inst.get("security_value"),
            0.0,
        )

        total_outstanding += principal
        total_interest_weighted += principal * interest_rate
        total_collateral += collateral

    weighted_avg_rate = (total_interest_weighted / total_outstanding) if total_outstanding > 0 else 0.0
    return total_outstanding, weighted_avg_rate, total_collateral


def calculate_debt_exposure(*, normalized_payload: dict) -> DebtExposure:
    """Calculate debt exposure from normalized payload (simple or multi-instrument)."""
    financial = normalized_payload.get("financial")
    financial = financial if isinstance(financial, dict) else {}
    debt = financial.get("debt")
    debt = debt if isinstance(debt, dict) else {}

    instruments = debt.get("instruments") if isinstance(debt.get("instruments"), list) else []

    if instruments:
        total_outstanding, interest_rate_pct, collateral_from_instruments = _aggregate_debt_instruments(instruments)
        collateral_value = _as_float(
            debt.get("collateral_value") or debt.get("collateral") or debt.get("security_value"),
            collateral_from_instruments,
        )
    else:
        total_outstanding = _as_float(
            debt.get("total_outstanding") or debt.get("outstanding") or debt.get("principal")
        )
        interest_rate_pct = _as_float(
            debt.get("interest_rate_pct") or debt.get("interest_rate") or debt.get("rate_pct"),
            0.0,
        )
        collateral_value = _as_float(
            debt.get("collateral_value") or debt.get("collateral") or debt.get("security_value"),
            0.0,
        )

    assets_value = _normalize_assets_value(
        financial.get("assets") or financial.get("asset_value") or normalized_payload.get("assets")
    )
    distressed_assets = _extract_distressed_assets(normalized_payload, financial)
    distressed_asset_value = sum(asset.value for asset in distressed_assets)
    distressed_asset_recovery = sum(asset.recovery_value for asset in distressed_assets)
    interest_payment = total_outstanding * (interest_rate_pct / 100.0)
    collateral_shortfall = max(total_outstanding - collateral_value, 0.0)
    collateral_coverage_ratio = (collateral_value / total_outstanding) if total_outstanding > 0 else 0.0
    leverage_ratio = (total_outstanding / assets_value) if assets_value > 0 else 0.0
    distressed_asset_recovery_ratio = (
        (distressed_asset_recovery / distressed_asset_value) if distressed_asset_value > 0 else 0.0
    )
    net_exposure_after_recovery = max(total_outstanding - (collateral_value + distressed_asset_recovery), 0.0)
    return DebtExposure(
        total_outstanding=total_outstanding,
        interest_rate_pct=interest_rate_pct,
        interest_payment=interest_payment,
        collateral_value=collateral_value,
        collateral_shortfall=collateral_shortfall,
        collateral_coverage_ratio=collateral_coverage_ratio,
        assets_value=assets_value,
        leverage_ratio=leverage_ratio,
        distressed_asset_value=distressed_asset_value,
        distressed_asset_recovery=distressed_asset_recovery,
        distressed_asset_recovery_ratio=distressed_asset_recovery_ratio,
        distressed_asset_count=len(distressed_assets),
        net_exposure_after_recovery=net_exposure_after_recovery,
    )


def apply_stress_scenario(
    *,
    exposure: DebtExposure,
    base_net_exposure: float,
    scenario: StressTestScenario,
) -> StressTestResult:
    adjusted_interest_rate_pct = exposure.interest_rate_pct + scenario.interest_rate_delta_pct
    interest_payment = exposure.total_outstanding * (adjusted_interest_rate_pct / 100.0)
    adjusted_collateral_value = max(
        0.0, exposure.collateral_value * (1.0 + scenario.collateral_market_impact_pct)
    )
    adjusted_distressed_asset_value = max(
        0.0, exposure.distressed_asset_value * (1.0 + scenario.collateral_market_impact_pct)
    )
    adjusted_distressed_asset_recovery = max(
        0.0, exposure.distressed_asset_recovery * (1.0 + scenario.recovery_degradation_pct)
    )
    collateral_loss = max(0.0, exposure.collateral_value - adjusted_collateral_value)
    distressed_asset_loss = max(0.0, exposure.distressed_asset_value - adjusted_distressed_asset_value)
    scenario_net_exposure = max(
        0.0, exposure.total_outstanding - (adjusted_collateral_value + adjusted_distressed_asset_recovery)
    )
    default_risk_buffer = max(0.0, exposure.total_outstanding * scenario.default_risk_increment_pct)
    net_exposure = scenario_net_exposure + default_risk_buffer
    loss_estimate = max(0.0, net_exposure - base_net_exposure)
    impact_score = min(1.0, loss_estimate / max(1.0, exposure.total_outstanding))
    return StressTestResult(
        scenario=scenario,
        adjusted_interest_rate_pct=adjusted_interest_rate_pct,
        interest_payment=interest_payment,
        adjusted_collateral_value=adjusted_collateral_value,
        collateral_loss=collateral_loss,
        adjusted_distressed_asset_value=adjusted_distressed_asset_value,
        distressed_asset_loss=distressed_asset_loss,
        adjusted_distressed_asset_recovery=adjusted_distressed_asset_recovery,
        default_risk_buffer=default_risk_buffer,
        net_exposure_after_recovery=net_exposure,
        loss_estimate=loss_estimate,
        impact_score=impact_score,
    )


# ---------------------------------------------------------------------------
# Enterprise scenario management & execution models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StressAssumptions:
    """Immutable set of stress assumptions used for scenario execution."""

    revenue_change_factor: Decimal
    cost_change_factor: Decimal
    interest_rate_change_factor: Decimal
    liquidity_shock_factor: Decimal
    market_value_depreciation_factor: Decimal
    collection_period_extension_days: int
    payment_period_reduction_days: int


@dataclass(frozen=True)
class Scenario:
    """Immutable stress test scenario definition bound to a DatasetVersion."""

    scenario_id: str
    dataset_version_id: str
    scenario_name: str
    description: str
    time_horizon_months: int
    assumptions: StressAssumptions
    created_at: str
    created_by: str | None


@dataclass(frozen=True)
class ExposureChange:
    period_month: int
    period_date: date
    exposure_before: Decimal
    exposure_after: Decimal
    exposure_change: Decimal
    exposure_change_percent: Decimal
    asset_category: str | None


@dataclass(frozen=True)
class CashShortfall:
    period_month: int
    period_date: date
    cash_available: Decimal
    cash_required: Decimal
    shortfall: Decimal
    shortfall_percent: Decimal
    shortfall_category: str


@dataclass(frozen=True)
class DebtServiceCoverage:
    period_month: int
    period_date: date
    dscr: Decimal | None
    interest_coverage: Decimal | None
    principal_coverage: Decimal | None
    total_debt_service: Decimal
    cash_available_for_debt_service: Decimal
    coverage_status: str


@dataclass(frozen=True)
class PeriodResult:
    period_month: int
    period_date: date
    exposure_changes: list[ExposureChange]
    cash_shortfalls: list[CashShortfall]
    debt_service_coverage: DebtServiceCoverage
    cumulative_exposure_change: Decimal
    cumulative_cash_shortfall: Decimal


@dataclass(frozen=True)
class ScenarioExecution:
    execution_id: str
    scenario_id: str
    dataset_version_id: str
    executed_at: str
    executed_by: str | None
    assumptions_used: StressAssumptions
    period_results: list[PeriodResult]
    summary: dict[str, Any]


@dataclass(frozen=True)
class ScenarioResult:
    """Bundle of scenario definition, execution, and results for reporting."""

    scenario: Scenario
    execution: ScenarioExecution
    aggregated_metrics: dict[str, Any]
    granular_results: list[PeriodResult]
