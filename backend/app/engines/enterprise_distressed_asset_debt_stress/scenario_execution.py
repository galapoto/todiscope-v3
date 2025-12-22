from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from backend.app.engines.enterprise_distressed_asset_debt_stress.errors import (
    ScenarioExecutionError,
)
from backend.app.engines.enterprise_distressed_asset_debt_stress.ids import deterministic_id
from backend.app.engines.enterprise_distressed_asset_debt_stress.models import (
    CashShortfall,
    DebtServiceCoverage,
    ExposureChange,
    PeriodResult,
    Scenario,
    ScenarioExecution,
    StressAssumptions,
)


def execute_scenario(
    *,
    scenario: Scenario,
    financial_data: dict[str, Any],
    analysis_date: date,
    executed_by: str | None = None,
) -> ScenarioExecution:
    """
    Execute a stress test scenario.
    
    Args:
        scenario: The scenario to execute
        financial_data: Financial data dictionary containing balance sheet, income statement, debt, etc.
        analysis_date: Base date for the analysis
        executed_by: Optional identifier of who executed the scenario
    
    Returns:
        Immutable ScenarioExecution with period-by-period results
    
    Raises:
        ScenarioExecutionError: If execution fails
    """
    try:
        period_results: list[PeriodResult] = []
        
        # Extract base financial metrics
        base_exposure = _extract_total_exposure(financial_data)
        base_cash = _extract_cash_and_equivalents(financial_data)
        base_revenue = _extract_revenue(financial_data)
        base_costs = _extract_operating_costs(financial_data)
        debt_instruments = _extract_debt_instruments(financial_data)
        
        cumulative_exposure_change = Decimal("0")
        cumulative_cash_shortfall = Decimal("0")
        
        # Execute scenario period by period
        for month in range(1, scenario.time_horizon_months + 1):
            period_date = _calculate_period_date(analysis_date, month)
            
            # Calculate exposure changes
            exposure_changes = _calculate_exposure_changes(
                base_exposure=base_exposure,
                assumptions=scenario.assumptions,
                period_month=month,
                period_date=period_date,
            )
            
            # Calculate cash shortfalls
            cash_shortfalls = _calculate_cash_shortfalls(
                base_cash=base_cash,
                base_revenue=base_revenue,
                base_costs=base_costs,
                assumptions=scenario.assumptions,
                period_month=month,
                period_date=period_date,
            )
            
            # Calculate debt service coverage
            debt_service_coverage = _calculate_debt_service_coverage(
                financial_data=financial_data,
                assumptions=scenario.assumptions,
                period_month=month,
                period_date=period_date,
                debt_instruments=debt_instruments,
            )
            
            # Update cumulative metrics
            period_exposure_change = sum(ec.exposure_change for ec in exposure_changes)
            period_cash_shortfall = sum(cs.shortfall for cs in cash_shortfalls if cs.shortfall > 0)
            
            cumulative_exposure_change += period_exposure_change
            cumulative_cash_shortfall += period_cash_shortfall
            
            period_result = PeriodResult(
                period_month=month,
                period_date=period_date,
                exposure_changes=exposure_changes,
                cash_shortfalls=cash_shortfalls,
                debt_service_coverage=debt_service_coverage,
                cumulative_exposure_change=cumulative_exposure_change,
                cumulative_cash_shortfall=cumulative_cash_shortfall,
            )
            period_results.append(period_result)
        
        # Generate summary
        summary = _generate_summary(period_results, scenario)
        
        # Create execution record
        execution_id = deterministic_id(
            scenario.scenario_id,
            "execution",
            analysis_date.isoformat(),
        )
        executed_at = datetime.now(timezone.utc).isoformat()
        
        return ScenarioExecution(
            execution_id=execution_id,
            scenario_id=scenario.scenario_id,
            dataset_version_id=scenario.dataset_version_id,
            executed_at=executed_at,
            executed_by=executed_by,
            assumptions_used=scenario.assumptions,
            period_results=period_results,
            summary=summary,
        )
    except Exception as e:
        raise ScenarioExecutionError(f"SCENARIO_EXECUTION_FAILED: {e}") from e


def _calculate_period_date(base_date: date, month: int) -> date:
    """Calculate the date for a specific period month."""
    # Add months to base date
    year = base_date.year
    month_num = base_date.month + month
    while month_num > 12:
        year += 1
        month_num -= 12
    day = min(base_date.day, 28)  # Avoid month-end issues
    return date(year, month_num, day)


def _extract_total_exposure(financial_data: dict[str, Any]) -> Decimal:
    """Extract total exposure from financial data."""
    balance_sheet = financial_data.get("balance_sheet", {})
    # Sum of assets that could be distressed
    total_assets = balance_sheet.get("total_assets", 0)
    current_assets = balance_sheet.get("current_assets", 0)
    # Use total assets as base exposure
    return Decimal(str(total_assets or current_assets or 0))


def _extract_cash_and_equivalents(financial_data: dict[str, Any]) -> Decimal:
    """Extract cash and equivalents from financial data."""
    balance_sheet = financial_data.get("balance_sheet", {})
    cash = balance_sheet.get("cash_and_equivalents", 0)
    return Decimal(str(cash or 0))


def _extract_revenue(financial_data: dict[str, Any]) -> Decimal:
    """Extract revenue from financial data."""
    income_statement = financial_data.get("income_statement", {})
    revenue = income_statement.get("revenue") or income_statement.get("total_revenue") or income_statement.get("net_revenue", 0)
    return Decimal(str(revenue or 0))


def _extract_operating_costs(financial_data: dict[str, Any]) -> Decimal:
    """Extract operating costs from financial data."""
    income_statement = financial_data.get("income_statement", {})
    costs = income_statement.get("operating_expenses") or income_statement.get("total_expenses", 0)
    return Decimal(str(costs or 0))


def _extract_debt_instruments(financial_data: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract debt instruments from financial data."""
    debt = financial_data.get("debt", {})
    instruments = debt.get("instruments", [])
    if not isinstance(instruments, list):
        return []
    return instruments


def _calculate_exposure_changes(
    *,
    base_exposure: Decimal,
    assumptions: StressAssumptions,
    period_month: int,
    period_date: date,
) -> list[ExposureChange]:
    """Calculate exposure changes for a period."""
    # Apply market value depreciation over time (compounding)
    depreciation_factor = assumptions.market_value_depreciation_factor ** period_month
    exposure_after = base_exposure * depreciation_factor
    exposure_change = exposure_after - base_exposure
    exposure_change_percent = (
        (exposure_change / base_exposure * Decimal("100"))
        if base_exposure > 0
        else Decimal("0")
    )
    
    return [
        ExposureChange(
            period_month=period_month,
            period_date=period_date,
            exposure_before=base_exposure,
            exposure_after=exposure_after,
            exposure_change=exposure_change,
            exposure_change_percent=exposure_change_percent,
            asset_category="total_assets",
        )
    ]


def _calculate_cash_shortfalls(
    *,
    base_cash: Decimal,
    base_revenue: Decimal,
    base_costs: Decimal,
    assumptions: StressAssumptions,
    period_month: int,
    period_date: date,
) -> list[CashShortfall]:
    """Calculate cash shortfalls for a period."""
    shortfalls: list[CashShortfall] = []
    
    # Calculate adjusted revenue and costs
    adjusted_revenue = base_revenue * assumptions.revenue_change_factor
    adjusted_costs = base_costs * assumptions.cost_change_factor
    
    # Operating cash flow
    operating_cash_flow = adjusted_revenue - adjusted_costs
    
    # Apply liquidity shock to available cash
    available_cash = base_cash * assumptions.liquidity_shock_factor
    
    # Operating shortfall
    if operating_cash_flow < 0:
        shortfall = abs(operating_cash_flow)
        shortfall_percent = (
            (shortfall / adjusted_revenue * Decimal("100"))
            if adjusted_revenue > 0
            else Decimal("100")
        )
        shortfalls.append(
            CashShortfall(
                period_month=period_month,
                period_date=period_date,
                cash_available=available_cash,
                cash_required=abs(operating_cash_flow),
                shortfall=shortfall,
                shortfall_percent=shortfall_percent,
                shortfall_category="operating",
            )
        )
    
    # Debt service shortfall (simplified - would need actual debt schedule)
    # This is a placeholder - in real implementation, would calculate from debt instruments
    estimated_debt_service = base_costs * Decimal("0.1")  # Rough estimate
    if available_cash < estimated_debt_service:
        shortfall = estimated_debt_service - available_cash
        shortfall_percent = (
            (shortfall / estimated_debt_service * Decimal("100"))
            if estimated_debt_service > 0
            else Decimal("0")
        )
        shortfalls.append(
            CashShortfall(
                period_month=period_month,
                period_date=period_date,
                cash_available=available_cash,
                cash_required=estimated_debt_service,
                shortfall=shortfall,
                shortfall_percent=shortfall_percent,
                shortfall_category="debt_service",
            )
        )
    
    return shortfalls


def _calculate_debt_service_coverage(
    *,
    financial_data: dict[str, Any],
    assumptions: StressAssumptions,
    period_month: int,
    period_date: date,
    debt_instruments: list[dict[str, Any]],
) -> DebtServiceCoverage:
    """Calculate debt service coverage for a period."""
    # Extract base metrics
    income_statement = financial_data.get("income_statement", {})
    ebitda = Decimal(str(income_statement.get("ebitda", 0) or 0))
    interest_expense = Decimal(str(income_statement.get("interest_expense", 0) or 0))
    
    # Apply stress assumptions
    adjusted_ebitda = ebitda * assumptions.revenue_change_factor
    adjusted_interest = interest_expense * assumptions.interest_rate_change_factor
    
    # Calculate debt service (simplified)
    total_debt_service = adjusted_interest
    if debt_instruments:
        # Sum principal payments (simplified monthly calculation)
        for instrument in debt_instruments:
            principal = Decimal(str(instrument.get("principal", 0) or 0))
            term_months = int(instrument.get("term_months", 12) or 12)
            if term_months > 0:
                monthly_principal = principal / Decimal(str(term_months))
                total_debt_service += monthly_principal
    
    # Cash available for debt service (simplified)
    cash_available_for_debt_service = adjusted_ebitda * Decimal("0.7")  # Rough estimate
    
    # Calculate coverage ratios
    dscr = (
        cash_available_for_debt_service / total_debt_service
        if total_debt_service > 0
        else None
    )
    interest_coverage = (
        adjusted_ebitda / adjusted_interest
        if adjusted_interest > 0
        else None
    )
    principal_coverage = (
        cash_available_for_debt_service / (total_debt_service - adjusted_interest)
        if (total_debt_service - adjusted_interest) > 0
        else None
    )
    
    # Determine coverage status
    if dscr is None:
        coverage_status = "insufficient"
    elif dscr >= Decimal("1.25"):
        coverage_status = "adequate"
    elif dscr >= Decimal("1.0"):
        coverage_status = "marginal"
    else:
        coverage_status = "insufficient"
    
    return DebtServiceCoverage(
        period_month=period_month,
        period_date=period_date,
        dscr=dscr,
        interest_coverage=interest_coverage,
        principal_coverage=principal_coverage,
        total_debt_service=total_debt_service,
        cash_available_for_debt_service=cash_available_for_debt_service,
        coverage_status=coverage_status,
    )


def _generate_summary(
    period_results: list[PeriodResult],
    scenario: Scenario,
) -> dict[str, Any]:
    """Generate aggregated summary from period results."""
    if not period_results:
        return {}
    
    # Aggregate metrics
    total_exposure_change = period_results[-1].cumulative_exposure_change
    total_cash_shortfall = period_results[-1].cumulative_cash_shortfall
    
    # Count periods with shortfalls
    periods_with_shortfalls = sum(
        1 for pr in period_results if pr.cash_shortfalls
    )
    
    # Count periods with insufficient coverage
    periods_insufficient_coverage = sum(
        1 for pr in period_results
        if pr.debt_service_coverage.coverage_status == "insufficient"
    )
    
    # Average DSCR
    dscr_values = [
        pr.debt_service_coverage.dscr
        for pr in period_results
        if pr.debt_service_coverage.dscr is not None
    ]
    avg_dscr = (
        sum(dscr_values) / Decimal(str(len(dscr_values)))
        if dscr_values
        else None
    )
    
    # Min DSCR
    min_dscr = min(dscr_values) if dscr_values else None
    
    return {
        "total_exposure_change": float(total_exposure_change),
        "total_cash_shortfall": float(total_cash_shortfall),
        "periods_with_shortfalls": periods_with_shortfalls,
        "periods_insufficient_coverage": periods_insufficient_coverage,
        "average_dscr": float(avg_dscr) if avg_dscr is not None else None,
        "min_dscr": float(min_dscr) if min_dscr is not None else None,
        "time_horizon_months": scenario.time_horizon_months,
        "scenario_name": scenario.scenario_name,
    }

