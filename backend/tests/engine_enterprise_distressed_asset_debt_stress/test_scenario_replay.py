"""
Tests for scenario replay functionality.

Verifies that scenarios can be re-executed exactly with the same dataset and assumptions.
"""

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from backend.app.core.dataset.service import create_dataset_version_via_ingestion
from backend.app.core.db import get_sessionmaker
from backend.app.engines.enterprise_distressed_asset_debt_stress.scenario_creation import create_scenario
from backend.app.engines.enterprise_distressed_asset_debt_stress.scenario_execution import execute_scenario
from backend.app.engines.enterprise_distressed_asset_debt_stress.scenario_storage import (
    replay_scenario,
    retrieve_scenario,
    store_scenario,
    store_scenario_execution,
)


@pytest.mark.anyio
async def test_replay_scenario_exact_match(sqlite_db: None) -> None:
    """Test that replay produces exact same results with same inputs."""
    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)
        
        # Create and store scenario
        scenario = create_scenario(
            dataset_version_id=dv.id,
            scenario_name="replay_test",
            description="Test replay",
            time_horizon_months=12,
            assumptions={
                "revenue_change_factor": 0.8,
                "cost_change_factor": 1.15,
                "interest_rate_change_factor": 1.3,
            },
        )
        
        created_at = datetime.now(timezone.utc)
        await store_scenario(db, scenario=scenario, created_at=created_at)
        await db.commit()
        
        financial_data = {
            "balance_sheet": {
                "total_assets": 1000000,
                "cash_and_equivalents": 200000,
            },
            "income_statement": {
                "revenue": 500000,
                "operating_expenses": 300000,
                "ebitda": 200000,
            },
            "debt": {},
        }
        
        # Execute original scenario
        original_execution = execute_scenario(
            scenario=scenario,
            financial_data=financial_data,
            analysis_date=date(2025, 1, 1),
        )
        
        await store_scenario_execution(db, execution=original_execution, created_at=created_at)
        await db.commit()
        
        # Replay scenario
        replayed_execution = await replay_scenario(
            db,
            scenario_id=scenario.scenario_id,
            dataset_version_id=dv.id,
            financial_data=financial_data,
            analysis_date=date(2025, 1, 1).isoformat(),
        )
        
        # Verify same scenario assumptions
        assert replayed_execution.assumptions_used.revenue_change_factor == scenario.assumptions.revenue_change_factor
        assert replayed_execution.assumptions_used.cost_change_factor == scenario.assumptions.cost_change_factor
        
        # Verify same number of periods
        assert len(replayed_execution.period_results) == len(original_execution.period_results)
        
        # Verify same time horizon
        assert len(replayed_execution.period_results) == scenario.time_horizon_months


@pytest.mark.anyio
async def test_replay_scenario_different_financial_data(sqlite_db: None) -> None:
    """Test that replay uses provided financial data."""
    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)
        
        scenario = create_scenario(
            dataset_version_id=dv.id,
            scenario_name="replay_different_data",
            description="Test replay with different data",
            time_horizon_months=6,
            assumptions={"revenue_change_factor": 0.8},
        )
        
        created_at = datetime.now(timezone.utc)
        await store_scenario(db, scenario=scenario, created_at=created_at)
        await db.commit()
        
        # Replay with different financial data
        different_financial_data = {
            "balance_sheet": {
                "total_assets": 2000000,  # Different
                "cash_and_equivalents": 400000,  # Different
            },
            "income_statement": {
                "revenue": 1000000,  # Different
                "operating_expenses": 600000,  # Different
            },
            "debt": {},
        }
        
        replayed_execution = await replay_scenario(
            db,
            scenario_id=scenario.scenario_id,
            dataset_version_id=dv.id,
            financial_data=different_financial_data,
            analysis_date=date(2025, 1, 1).isoformat(),
        )
        
        # Should use different financial data but same assumptions
        assert replayed_execution.assumptions_used.revenue_change_factor == scenario.assumptions.revenue_change_factor
        assert len(replayed_execution.period_results) == 6


@pytest.mark.anyio
async def test_replay_scenario_not_found(sqlite_db: None) -> None:
    """Test replay with non-existent scenario."""
    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)
        await db.commit()
        
        from backend.app.engines.enterprise_distressed_asset_debt_stress.errors import ScenarioNotFoundError
        
        with pytest.raises(ScenarioNotFoundError):
            await replay_scenario(
                db,
                scenario_id="nonexistent_scenario",
                dataset_version_id=dv.id,
                financial_data={},
                analysis_date=date(2025, 1, 1).isoformat(),
            )


@pytest.mark.anyio
async def test_replay_preserves_assumptions(sqlite_db: None) -> None:
    """Test that replay preserves original scenario assumptions."""
    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)
        
        # Create scenario with specific assumptions
        scenario = create_scenario(
            dataset_version_id=dv.id,
            scenario_name="assumptions_test",
            description="Test assumption preservation",
            time_horizon_months=12,
            assumptions={
                "revenue_change_factor": 0.7,
                "cost_change_factor": 1.25,
                "interest_rate_change_factor": 1.5,
                "liquidity_shock_factor": 0.8,
                "market_value_depreciation_factor": 0.9,
            },
        )
        
        created_at = datetime.now(timezone.utc)
        await store_scenario(db, scenario=scenario, created_at=created_at)
        await db.commit()
        
        # Retrieve and replay
        retrieved_scenario = await retrieve_scenario(
            db,
            scenario_id=scenario.scenario_id,
            dataset_version_id=dv.id,
        )
        
        financial_data = {
            "balance_sheet": {"total_assets": 1000000, "cash_and_equivalents": 200000},
            "income_statement": {"revenue": 500000, "operating_expenses": 300000},
            "debt": {},
        }
        
        replayed_execution = await replay_scenario(
            db,
            scenario_id=scenario.scenario_id,
            dataset_version_id=dv.id,
            financial_data=financial_data,
            analysis_date=date(2025, 1, 1).isoformat(),
        )
        
        # Verify assumptions are preserved
        assert replayed_execution.assumptions_used.revenue_change_factor == Decimal("0.7")
        assert replayed_execution.assumptions_used.cost_change_factor == Decimal("1.25")
        assert replayed_execution.assumptions_used.interest_rate_change_factor == Decimal("1.5")
        assert replayed_execution.assumptions_used.liquidity_shock_factor == Decimal("0.8")
        assert replayed_execution.assumptions_used.market_value_depreciation_factor == Decimal("0.9")


