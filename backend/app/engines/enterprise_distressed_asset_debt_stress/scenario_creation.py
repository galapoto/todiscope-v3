from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from backend.app.engines.enterprise_distressed_asset_debt_stress.errors import (
    ScenarioInvalidError,
)
from backend.app.engines.enterprise_distressed_asset_debt_stress.ids import deterministic_id
from backend.app.engines.enterprise_distressed_asset_debt_stress.models import (
    Scenario,
    StressAssumptions,
)


def create_scenario(
    *,
    dataset_version_id: str,
    scenario_name: str,
    description: str,
    time_horizon_months: int,
    assumptions: dict[str, Any],
    created_by: str | None = None,
) -> Scenario:
    """
    Create a new stress test scenario.
    
    Args:
        dataset_version_id: The DatasetVersion this scenario is linked to (mandatory)
        scenario_name: Human-readable name for the scenario
        description: Description of the scenario
        time_horizon_months: Time horizon in months (must be 6-24)
        assumptions: Dictionary of stress assumptions
        created_by: Optional identifier of who created the scenario
    
    Returns:
        Immutable Scenario object
    
    Raises:
        ScenarioInvalidError: If validation fails
    """
    if not dataset_version_id or not isinstance(dataset_version_id, str) or not dataset_version_id.strip():
        raise ScenarioInvalidError("DATASET_VERSION_ID_REQUIRED")
    
    if not scenario_name or not isinstance(scenario_name, str) or not scenario_name.strip():
        raise ScenarioInvalidError("SCENARIO_NAME_REQUIRED")
    
    if not isinstance(time_horizon_months, int) or time_horizon_months < 6 or time_horizon_months > 24:
        raise ScenarioInvalidError("TIME_HORIZON_MUST_BE_6_TO_24_MONTHS")
    
    # Parse and validate assumptions
    stress_assumptions = _parse_assumptions(assumptions)
    
    # Generate deterministic scenario ID
    scenario_id = deterministic_id(
        dataset_version_id,
        "scenario",
        scenario_name,
        str(time_horizon_months),
        str(stress_assumptions.revenue_change_factor),
        str(stress_assumptions.cost_change_factor),
        str(stress_assumptions.interest_rate_change_factor),
    )
    
    created_at = datetime.now(timezone.utc).isoformat()
    
    return Scenario(
        scenario_id=scenario_id,
        dataset_version_id=dataset_version_id,
        scenario_name=scenario_name,
        description=description,
        time_horizon_months=time_horizon_months,
        assumptions=stress_assumptions,
        created_at=created_at,
        created_by=created_by,
    )


def _parse_assumptions(assumptions: dict[str, Any]) -> StressAssumptions:
    """Parse and validate stress assumptions from dictionary."""
    try:
        revenue_change = Decimal(str(assumptions.get("revenue_change_factor", 1.0)))
        cost_change = Decimal(str(assumptions.get("cost_change_factor", 1.0)))
        interest_rate_change = Decimal(str(assumptions.get("interest_rate_change_factor", 1.0)))
        liquidity_shock = Decimal(str(assumptions.get("liquidity_shock_factor", 1.0)))
        market_value_depreciation = Decimal(str(assumptions.get("market_value_depreciation_factor", 1.0)))
        collection_period_extension = int(assumptions.get("collection_period_extension_days", 0))
        payment_period_reduction = int(assumptions.get("payment_period_reduction_days", 0))
        
        # Validate ranges
        if revenue_change < Decimal("0") or revenue_change > Decimal("2"):
            raise ScenarioInvalidError("REVENUE_CHANGE_FACTOR_MUST_BE_0_TO_2")
        if cost_change < Decimal("0") or cost_change > Decimal("3"):
            raise ScenarioInvalidError("COST_CHANGE_FACTOR_MUST_BE_0_TO_3")
        if interest_rate_change < Decimal("0") or interest_rate_change > Decimal("5"):
            raise ScenarioInvalidError("INTEREST_RATE_CHANGE_FACTOR_MUST_BE_0_TO_5")
        if liquidity_shock < Decimal("0") or liquidity_shock > Decimal("1"):
            raise ScenarioInvalidError("LIQUIDITY_SHOCK_FACTOR_MUST_BE_0_TO_1")
        if market_value_depreciation < Decimal("0") or market_value_depreciation > Decimal("1"):
            raise ScenarioInvalidError("MARKET_VALUE_DEPRECIATION_FACTOR_MUST_BE_0_TO_1")
        
        return StressAssumptions(
            revenue_change_factor=revenue_change,
            cost_change_factor=cost_change,
            interest_rate_change_factor=interest_rate_change,
            liquidity_shock_factor=liquidity_shock,
            market_value_depreciation_factor=market_value_depreciation,
            collection_period_extension_days=collection_period_extension,
            payment_period_reduction_days=payment_period_reduction,
        )
    except (ValueError, TypeError, KeyError) as e:
        raise ScenarioInvalidError(f"INVALID_ASSUMPTIONS: {e}") from e


def create_default_stress_scenarios(
    *,
    dataset_version_id: str,
    time_horizon_months: int = 12,
    created_by: str | None = None,
) -> list[Scenario]:
    """
    Create a set of default stress test scenarios.
    
    Returns:
        List of default scenarios (mild, moderate, severe)
    """
    scenarios = []
    
    # Mild stress scenario
    scenarios.append(
        create_scenario(
            dataset_version_id=dataset_version_id,
            scenario_name="mild_stress",
            description="Mild stress scenario with 10% revenue reduction and 5% cost increase",
            time_horizon_months=time_horizon_months,
            assumptions={
                "revenue_change_factor": Decimal("0.9"),
                "cost_change_factor": Decimal("1.05"),
                "interest_rate_change_factor": Decimal("1.1"),
                "liquidity_shock_factor": Decimal("0.95"),
                "market_value_depreciation_factor": Decimal("0.95"),
                "collection_period_extension_days": 15,
                "payment_period_reduction_days": -5,
            },
            created_by=created_by,
        )
    )
    
    # Moderate stress scenario
    scenarios.append(
        create_scenario(
            dataset_version_id=dataset_version_id,
            scenario_name="moderate_stress",
            description="Moderate stress scenario with 20% revenue reduction and 15% cost increase",
            time_horizon_months=time_horizon_months,
            assumptions={
                "revenue_change_factor": Decimal("0.8"),
                "cost_change_factor": Decimal("1.15"),
                "interest_rate_change_factor": Decimal("1.3"),
                "liquidity_shock_factor": Decimal("0.85"),
                "market_value_depreciation_factor": Decimal("0.85"),
                "collection_period_extension_days": 30,
                "payment_period_reduction_days": -10,
            },
            created_by=created_by,
        )
    )
    
    # Severe stress scenario
    scenarios.append(
        create_scenario(
            dataset_version_id=dataset_version_id,
            scenario_name="severe_stress",
            description="Severe stress scenario with 40% revenue reduction and 30% cost increase",
            time_horizon_months=time_horizon_months,
            assumptions={
                "revenue_change_factor": Decimal("0.6"),
                "cost_change_factor": Decimal("1.3"),
                "interest_rate_change_factor": Decimal("2.0"),
                "liquidity_shock_factor": Decimal("0.7"),
                "market_value_depreciation_factor": Decimal("0.7"),
                "collection_period_extension_days": 60,
                "payment_period_reduction_days": -20,
            },
            created_by=created_by,
        )
    )
    
    return scenarios

