"""
Scenario-Based Risk Modeling

This module implements scenario analysis and stress testing for the Enterprise Capital & Debt Readiness Engine.
It provides base/best/worst case scenarios and stress tests under varying market conditions.

Platform Law Compliance:
- Deterministic: Same inputs → same outputs
- Decimal arithmetic only
- All calculations bound to DatasetVersion
- Simple and interpretable for executive decision-making
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from backend.app.engines.enterprise_capital_debt_readiness.models import (
    CapitalAdequacyAssessment,
    DebtServiceAssessment,
)
from backend.app.engines.enterprise_capital_debt_readiness.readiness_scores import (
    calculate_composite_readiness_score,
)


@dataclass(frozen=True)
class ScenarioConditions:
    """Market conditions for a scenario."""
    interest_rate_multiplier: Decimal  # e.g., 1.0 = base, 1.5 = 50% increase
    liquidity_shock_factor: Decimal  # e.g., 1.0 = no shock, 0.7 = 30% reduction
    revenue_change_factor: Decimal  # e.g., 1.0 = no change, 0.8 = 20% reduction
    cost_change_factor: Decimal  # e.g., 1.0 = no change, 1.2 = 20% increase


@dataclass(frozen=True)
class ScenarioResult:
    """Results of a scenario analysis."""
    scenario_name: str
    conditions: ScenarioConditions
    readiness_score: Decimal
    readiness_level: str
    capital_adequacy_impact: Decimal  # Change from base case
    debt_service_impact: Decimal  # Change from base case
    liquidity_risk_score: Decimal  # 0-100, higher = more risk
    solvency_risk_score: Decimal  # 0-100, higher = more risk
    market_sensitivity: Decimal  # 0-100, higher = more sensitive
    component_scores: dict[str, Decimal]
    flags: list[str]


MARKET_SENSITIVITY_PRECISION = Decimal("0.0001")

def _apply_interest_rate_shock(
    *,
    base_rate: Decimal,
    multiplier: Decimal,
) -> Decimal:
    """Apply interest rate shock multiplier."""
    return base_rate * multiplier


def _apply_liquidity_shock(
    *,
    base_cash: Decimal,
    shock_factor: Decimal,
) -> Decimal:
    """Apply liquidity shock to cash position."""
    return base_cash * shock_factor


def _apply_revenue_shock(
    *,
    base_ebitda: Decimal | None,
    revenue_factor: Decimal,
) -> Decimal | None:
    """Apply revenue shock to EBITDA."""
    if base_ebitda is None:
        return None
    return base_ebitda * revenue_factor


def _apply_cost_shock(
    *,
    base_opex: Decimal | None,
    cost_factor: Decimal,
) -> Decimal | None:
    """Apply cost shock to operating expenses."""
    if base_opex is None:
        return None
    return base_opex * cost_factor


def create_base_case_conditions() -> ScenarioConditions:
    """Create base case scenario conditions (current market conditions)."""
    return ScenarioConditions(
        interest_rate_multiplier=Decimal("1.0"),
        liquidity_shock_factor=Decimal("1.0"),
        revenue_change_factor=Decimal("1.0"),
        cost_change_factor=Decimal("1.0"),
    )


def create_best_case_conditions() -> ScenarioConditions:
    """Create best case scenario conditions (favorable market conditions)."""
    return ScenarioConditions(
        interest_rate_multiplier=Decimal("0.85"),  # 15% lower interest rates
        liquidity_shock_factor=Decimal("1.15"),  # 15% more liquidity
        revenue_change_factor=Decimal("1.10"),  # 10% revenue increase
        cost_change_factor=Decimal("0.95"),  # 5% cost reduction
    )


def create_worst_case_conditions() -> ScenarioConditions:
    """Create worst case scenario conditions (adverse market conditions)."""
    return ScenarioConditions(
        interest_rate_multiplier=Decimal("1.50"),  # 50% higher interest rates
        liquidity_shock_factor=Decimal("0.70"),  # 30% liquidity reduction
        revenue_change_factor=Decimal("0.80"),  # 20% revenue reduction
        cost_change_factor=Decimal("1.20"),  # 20% cost increase
    )


def create_stress_test_interest_rate_shock(
    *,
    shock_percentage: Decimal = Decimal("200"),  # 200% increase
) -> ScenarioConditions:
    """Create stress test scenario with severe interest rate shock."""
    return ScenarioConditions(
        interest_rate_multiplier=Decimal("1.0") + (shock_percentage / Decimal("100")),
        liquidity_shock_factor=Decimal("1.0"),
        revenue_change_factor=Decimal("1.0"),
        cost_change_factor=Decimal("1.0"),
    )


def create_stress_test_liquidity_shock(
    *,
    shock_percentage: Decimal = Decimal("50"),  # 50% reduction
) -> ScenarioConditions:
    """Create stress test scenario with severe liquidity shock."""
    return ScenarioConditions(
        interest_rate_multiplier=Decimal("1.0"),
        liquidity_shock_factor=Decimal("1.0") - (shock_percentage / Decimal("100")),
        revenue_change_factor=Decimal("1.0"),
        cost_change_factor=Decimal("1.0"),
    )


def create_stress_test_combined_shock() -> ScenarioConditions:
    """Create stress test scenario with combined shocks."""
    return ScenarioConditions(
        interest_rate_multiplier=Decimal("1.75"),  # 75% higher interest rates
        liquidity_shock_factor=Decimal("0.60"),  # 40% liquidity reduction
        revenue_change_factor=Decimal("0.75"),  # 25% revenue reduction
        cost_change_factor=Decimal("1.25"),  # 25% cost increase
    )


def calculate_scenario_readiness(
    *,
    base_capital_adequacy: CapitalAdequacyAssessment,
    base_debt_service: DebtServiceAssessment,
    base_readiness_score: Decimal,
    base_readiness_level: str,
    base_component_scores: dict[str, Decimal],
    financial: dict[str, Any],
    assumptions: dict[str, Any],
    conditions: ScenarioConditions,
    scenario_name: str,
) -> ScenarioResult:
    """
    Calculate readiness score under scenario conditions.
    
    Args:
        base_capital_adequacy: Base case capital adequacy assessment
        base_debt_service: Base case debt service assessment
        base_readiness_score: Base case readiness score
        base_readiness_level: Base case readiness level
        base_component_scores: Base case component scores
        financial: Financial data dictionary
        assumptions: Assumptions dictionary
        conditions: Scenario conditions to apply
        scenario_name: Name of the scenario
    
    Returns:
        ScenarioResult with scenario-adjusted metrics
    """
    # Apply scenario conditions to financial data
    adjusted_financial = _apply_scenario_to_financial(
        financial=financial,
        conditions=conditions,
        base_capital_adequacy=base_capital_adequacy,
        base_debt_service=base_debt_service,
    )
    
    # Recalculate capital adequacy with adjusted financials
    from backend.app.engines.enterprise_capital_debt_readiness.capital_adequacy import (
        assess_capital_adequacy,
    )
    
    scenario_capital = assess_capital_adequacy(
        dataset_version_id=base_capital_adequacy.dataset_version_id,
        analysis_date=base_capital_adequacy.analysis_date,
        financial=adjusted_financial,
        assumptions=assumptions,
    )
    
    # Recalculate debt service with adjusted financials and interest rates
    from backend.app.engines.enterprise_capital_debt_readiness.debt_service import (
        assess_debt_service_ability,
    )
    
    scenario_debt = assess_debt_service_ability(
        dataset_version_id=base_debt_service.dataset_version_id,
        analysis_date=base_debt_service.analysis_date,
        financial=adjusted_financial,
        assumptions=assumptions,
    )
    
    # Recalculate readiness score
    scenario_readiness = calculate_composite_readiness_score(
        capital_adequacy=scenario_capital,
        debt_service=scenario_debt,
        financial=adjusted_financial,
        assumptions=assumptions,
    )
    
    scenario_score = Decimal(str(scenario_readiness["readiness_score"]))
    
    # Calculate impacts
    capital_adequacy_impact = (
        Decimal(str(scenario_readiness["component_scores"]["capital_adequacy"]))
        - base_component_scores["capital_adequacy"]
    )
    debt_service_impact = (
        Decimal(str(scenario_readiness["component_scores"]["debt_service"]))
        - base_component_scores["debt_service"]
    )
    
    # Calculate risk metrics
    liquidity_risk_score = _calculate_liquidity_risk(
        base_capital=base_capital_adequacy,
        scenario_capital=scenario_capital,
        conditions=conditions,
    )
    
    solvency_risk_score = _calculate_solvency_risk(
        base_capital=base_capital_adequacy,
        scenario_capital=scenario_capital,
        base_debt=base_debt_service,
        scenario_debt=scenario_debt,
        conditions=conditions,
    )
    
    market_sensitivity = _calculate_market_sensitivity(
        base_score=base_readiness_score,
        scenario_score=scenario_score,
        conditions=conditions,
    )
    
    # Collect flags
    flags: list[str] = []
    if scenario_score < base_readiness_score:
        flags.append("SCENARIO_DEGRADES_READINESS")
    if liquidity_risk_score > Decimal("70"):
        flags.append("HIGH_LIQUIDITY_RISK")
    if solvency_risk_score > Decimal("70"):
        flags.append("HIGH_SOLVENCY_RISK")
    if market_sensitivity > Decimal("80"):
        flags.append("HIGH_MARKET_SENSITIVITY")
    
    return ScenarioResult(
        scenario_name=scenario_name,
        conditions=conditions,
        readiness_score=scenario_score,
        readiness_level=scenario_readiness["readiness_level"],
        capital_adequacy_impact=capital_adequacy_impact,
        debt_service_impact=debt_service_impact,
        liquidity_risk_score=liquidity_risk_score,
        solvency_risk_score=solvency_risk_score,
        market_sensitivity=market_sensitivity,
        component_scores={
            k: Decimal(str(v)) if v is not None else Decimal("0")
            for k, v in scenario_readiness["component_scores"].items()
        },
        flags=sorted(set(flags)),
    )


def _apply_scenario_to_financial(
    *,
    financial: dict[str, Any],
    conditions: ScenarioConditions,
    base_capital_adequacy: CapitalAdequacyAssessment,
    base_debt_service: DebtServiceAssessment,
) -> dict[str, Any]:
    """Apply scenario conditions to financial data."""
    adjusted = deepcopy(financial)
    
    # Apply liquidity shock to cash
    balance = adjusted.get("balance_sheet", {})
    if balance.get("cash_and_equivalents") is not None:
        base_cash = Decimal(str(balance["cash_and_equivalents"]))
        adjusted_cash = _apply_liquidity_shock(
            base_cash=base_cash,
            shock_factor=conditions.liquidity_shock_factor,
        )
        if "balance_sheet" not in adjusted:
            adjusted["balance_sheet"] = {}
        adjusted["balance_sheet"]["cash_and_equivalents"] = float(adjusted_cash)
    
    # Apply revenue shock to EBITDA
    income = adjusted.get("income_statement", {})
    if income.get("ebitda") is not None:
        base_ebitda = Decimal(str(income["ebitda"]))
        adjusted_ebitda = _apply_revenue_shock(
            base_ebitda=base_ebitda,
            revenue_factor=conditions.revenue_change_factor,
        )
        if adjusted_ebitda is not None:
            if "income_statement" not in adjusted:
                adjusted["income_statement"] = {}
            adjusted["income_statement"]["ebitda"] = float(adjusted_ebitda)
    
    # Apply cost shock to operating expenses
    if income.get("operating_expenses") is not None:
        base_opex = Decimal(str(income["operating_expenses"]))
        adjusted_opex = _apply_cost_shock(
            base_opex=base_opex,
            cost_factor=conditions.cost_change_factor,
        )
        if adjusted_opex is not None:
            if "income_statement" not in adjusted:
                adjusted["income_statement"] = {}
            adjusted["income_statement"]["operating_expenses"] = float(adjusted_opex)
    
    # Apply interest rate shock to debt instruments
    debt = adjusted.get("debt", {})
    if debt.get("instruments") and isinstance(debt["instruments"], list):
        adjusted_instruments = []
        for inst in debt["instruments"]:
            adjusted_inst = dict(inst)
            if "annual_interest_rate" in adjusted_inst:
                base_rate = Decimal(str(adjusted_inst["annual_interest_rate"]))
                adjusted_rate = _apply_interest_rate_shock(
                    base_rate=base_rate,
                    multiplier=conditions.interest_rate_multiplier,
                )
                adjusted_inst["annual_interest_rate"] = float(adjusted_rate)
            adjusted_instruments.append(adjusted_inst)
        if "debt" not in adjusted:
            adjusted["debt"] = {}
        adjusted["debt"]["instruments"] = adjusted_instruments
    
    # Apply revenue shock to cash available
    cashflow = adjusted.get("cash_flow", {})
    if cashflow.get("cash_available_for_debt_service_annual") is not None:
        base_cash_avail = Decimal(str(cashflow["cash_available_for_debt_service_annual"]))
        # Cash available is affected by both revenue and cost changes
        net_factor = conditions.revenue_change_factor - (
            (conditions.cost_change_factor - Decimal("1.0")) * Decimal("0.5")
        )  # Partial cost pass-through
        adjusted_cash_avail = base_cash_avail * net_factor
        if "cash_flow" not in adjusted:
            adjusted["cash_flow"] = {}
        adjusted["cash_flow"]["cash_available_for_debt_service_annual"] = float(adjusted_cash_avail)
    
    return adjusted


def _calculate_liquidity_risk(
    *,
    base_capital: CapitalAdequacyAssessment,
    scenario_capital: CapitalAdequacyAssessment,
    conditions: ScenarioConditions,
) -> Decimal:
    """
    Calculate liquidity risk score (0-100, higher = more risk).
    
    Based on:
    - Cash runway degradation
    - Coverage ratio degradation
    - Liquidity shock severity
    """
    # Base risk from liquidity shock
    liquidity_shock_risk = (Decimal("1.0") - conditions.liquidity_shock_factor) * Decimal("100")
    
    # Coverage ratio degradation
    coverage_degradation = Decimal("0")
    if base_capital.coverage_ratio is not None and scenario_capital.coverage_ratio is not None:
        degradation = base_capital.coverage_ratio - scenario_capital.coverage_ratio
        if degradation > 0:
            coverage_degradation = min(degradation * Decimal("50"), Decimal("50"))
    
    # Runway degradation
    runway_degradation = Decimal("0")
    if base_capital.runway_months is not None and scenario_capital.runway_months is not None:
        degradation = base_capital.runway_months - scenario_capital.runway_months
        if degradation > 0:
            runway_degradation = min(degradation * Decimal("10"), Decimal("30"))
    
    total_risk = liquidity_shock_risk + coverage_degradation + runway_degradation
    return min(total_risk, Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _calculate_solvency_risk(
    *,
    base_capital: CapitalAdequacyAssessment,
    scenario_capital: CapitalAdequacyAssessment,
    base_debt: DebtServiceAssessment,
    scenario_debt: DebtServiceAssessment,
    conditions: ScenarioConditions,
) -> Decimal:
    """
    Calculate solvency risk score (0-100, higher = more risk).
    
    Based on:
    - Debt-to-equity ratio degradation
    - DSCR degradation
    - Interest coverage degradation
    """
    # Interest rate shock risk
    interest_rate_risk = (conditions.interest_rate_multiplier - Decimal("1.0")) * Decimal("50")
    
    # DSCR degradation
    dscr_degradation = Decimal("0")
    if base_debt.dscr is not None and scenario_debt.dscr is not None:
        degradation = base_debt.dscr - scenario_debt.dscr
        if degradation > 0:
            dscr_degradation = min(degradation * Decimal("30"), Decimal("40"))
    
    # Interest coverage degradation
    interest_coverage_degradation = Decimal("0")
    if base_debt.interest_coverage is not None and scenario_debt.interest_coverage is not None:
        degradation = base_debt.interest_coverage - scenario_debt.interest_coverage
        if degradation > 0:
            interest_coverage_degradation = min(degradation * Decimal("20"), Decimal("30"))
    
    # Debt-to-equity degradation
    debt_equity_degradation = Decimal("0")
    if base_capital.debt_to_equity_ratio is not None and scenario_capital.debt_to_equity_ratio is not None:
        degradation = scenario_capital.debt_to_equity_ratio - base_capital.debt_to_equity_ratio
        if degradation > 0:
            debt_equity_degradation = min(degradation * Decimal("15"), Decimal("20"))
    
    total_risk = interest_rate_risk + dscr_degradation + interest_coverage_degradation + debt_equity_degradation
    return min(total_risk, Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _calculate_market_sensitivity(
    *,
    base_score: Decimal,
    scenario_score: Decimal,
    conditions: ScenarioConditions,
) -> Decimal:
    """
    Calculate market sensitivity score (0-100, higher = more sensitive).
    
    Based on the magnitude of readiness score change relative to scenario conditions.
    """
    base_score = base_score.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    scenario_score = scenario_score.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    score_change = abs(base_score - scenario_score).quantize(MARKET_SENSITIVITY_PRECISION, rounding=ROUND_HALF_UP)
    
    # Normalize by scenario severity
    scenario_severity = (
        abs(conditions.interest_rate_multiplier - Decimal("1.0"))
        + abs(conditions.liquidity_shock_factor - Decimal("1.0"))
        + abs(conditions.revenue_change_factor - Decimal("1.0"))
        + abs(conditions.cost_change_factor - Decimal("1.0"))
    )
    scenario_severity = scenario_severity.quantize(MARKET_SENSITIVITY_PRECISION, rounding=ROUND_HALF_UP)
    
    if scenario_severity == 0:
        return Decimal("0")
    
    # Sensitivity = score change per unit of scenario severity
    sensitivity = (score_change / scenario_severity) * Decimal("10")
    bounded = min(sensitivity, Decimal("100"))
    return bounded.quantize(MARKET_SENSITIVITY_PRECISION, rounding=ROUND_HALF_UP)


def run_scenario_analysis(
    *,
    base_capital_adequacy: CapitalAdequacyAssessment,
    base_debt_service: DebtServiceAssessment,
    base_readiness_score: Decimal,
    base_readiness_level: str,
    base_component_scores: dict[str, Decimal],
    financial: dict[str, Any],
    assumptions: dict[str, Any],
) -> dict[str, Any]:
    """
    Run comprehensive scenario analysis including base/best/worst cases and stress tests.
    
    Returns:
        Dictionary with scenario results and risk metrics
    """
    scenarios: list[ScenarioResult] = []
    
    # Base case (already calculated, but include for completeness)
    base_conditions = create_base_case_conditions()
    base_result = ScenarioResult(
        scenario_name="base_case",
        conditions=base_conditions,
        readiness_score=base_readiness_score,
        readiness_level=base_readiness_level,
        capital_adequacy_impact=Decimal("0"),
        debt_service_impact=Decimal("0"),
        liquidity_risk_score=Decimal("0"),
        solvency_risk_score=Decimal("0"),
        market_sensitivity=Decimal("0"),
        component_scores=base_component_scores,
        flags=[],
    )
    scenarios.append(base_result)
    
    # Best case
    best_conditions = create_best_case_conditions()
    best_result = calculate_scenario_readiness(
        base_capital_adequacy=base_capital_adequacy,
        base_debt_service=base_debt_service,
        base_readiness_score=base_readiness_score,
        base_readiness_level=base_readiness_level,
        base_component_scores=base_component_scores,
        financial=financial,
        assumptions=assumptions,
        conditions=best_conditions,
        scenario_name="best_case",
    )
    scenarios.append(best_result)
    
    # Worst case
    worst_conditions = create_worst_case_conditions()
    worst_result = calculate_scenario_readiness(
        base_capital_adequacy=base_capital_adequacy,
        base_debt_service=base_debt_service,
        base_readiness_score=base_readiness_score,
        base_readiness_level=base_readiness_level,
        base_component_scores=base_component_scores,
        financial=financial,
        assumptions=assumptions,
        conditions=worst_conditions,
        scenario_name="worst_case",
    )
    scenarios.append(worst_result)
    
    # Stress tests
    stress_interest = create_stress_test_interest_rate_shock()
    stress_interest_result = calculate_scenario_readiness(
        base_capital_adequacy=base_capital_adequacy,
        base_debt_service=base_debt_service,
        base_readiness_score=base_readiness_score,
        base_readiness_level=base_readiness_level,
        base_component_scores=base_component_scores,
        financial=financial,
        assumptions=assumptions,
        conditions=stress_interest,
        scenario_name="stress_test_interest_rate_shock",
    )
    scenarios.append(stress_interest_result)
    
    stress_liquidity = create_stress_test_liquidity_shock()
    stress_liquidity_result = calculate_scenario_readiness(
        base_capital_adequacy=base_capital_adequacy,
        base_debt_service=base_debt_service,
        base_readiness_score=base_readiness_score,
        base_readiness_level=base_readiness_level,
        base_component_scores=base_component_scores,
        financial=financial,
        assumptions=assumptions,
        conditions=stress_liquidity,
        scenario_name="stress_test_liquidity_shock",
    )
    scenarios.append(stress_liquidity_result)
    
    stress_combined = create_stress_test_combined_shock()
    stress_combined_result = calculate_scenario_readiness(
        base_capital_adequacy=base_capital_adequacy,
        base_debt_service=base_debt_service,
        base_readiness_score=base_readiness_score,
        base_readiness_level=base_readiness_level,
        base_component_scores=base_component_scores,
        financial=financial,
        assumptions=assumptions,
        conditions=stress_combined,
        scenario_name="stress_test_combined_shock",
    )
    scenarios.append(stress_combined_result)
    
    # Aggregate risk metrics (sort scenarios by name for determinism)
    sorted_scenarios = sorted(scenarios, key=lambda s: s.scenario_name)
    max_liquidity_risk = max((s.liquidity_risk_score for s in sorted_scenarios), default=Decimal("0"))
    max_solvency_risk = max((s.solvency_risk_score for s in sorted_scenarios), default=Decimal("0"))
    max_market_sensitivity = max((s.market_sensitivity for s in sorted_scenarios), default=Decimal("0"))
    
    # Score range
    min_score = min((s.readiness_score for s in sorted_scenarios), default=base_readiness_score)
    max_score = max((s.readiness_score for s in sorted_scenarios), default=base_readiness_score)
    score_range = max_score - min_score
    
    return {
        "scenarios": [
            {
                "scenario_name": s.scenario_name,
                "readiness_score": float(s.readiness_score),
                "readiness_level": s.readiness_level,
                "capital_adequacy_impact": float(s.capital_adequacy_impact),
                "debt_service_impact": float(s.debt_service_impact),
                "liquidity_risk_score": float(s.liquidity_risk_score),
                "solvency_risk_score": float(s.solvency_risk_score),
                "market_sensitivity": float(s.market_sensitivity),
                "component_scores": {k: float(v) for k, v in s.component_scores.items()},
                "conditions": {
                    "interest_rate_multiplier": float(s.conditions.interest_rate_multiplier),
                    "liquidity_shock_factor": float(s.conditions.liquidity_shock_factor),
                    "revenue_change_factor": float(s.conditions.revenue_change_factor),
                    "cost_change_factor": float(s.conditions.cost_change_factor),
                },
                "flags": s.flags,
            }
            for s in sorted_scenarios
        ],
        "aggregate_risk_metrics": {
            "max_liquidity_risk": float(max_liquidity_risk),
            "max_solvency_risk": float(max_solvency_risk),
            "max_market_sensitivity": float(max_market_sensitivity),
            "score_range": float(score_range),
            "min_score": float(min_score),
            "max_score": float(max_score),
        },
    }
