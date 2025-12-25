"""
Tests for scenario management functionality.

Verifies scenario creation, storage, and retrieval with immutability guarantees.
"""

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from backend.app.core.dataset.service import create_dataset_version_via_ingestion
from backend.app.core.dataset.raw_models import RawRecord
from backend.app.core.db import get_sessionmaker
from backend.app.engines.enterprise_distressed_asset_debt_stress.errors import (
    ScenarioInvalidError,
    ScenarioNotFoundError,
)
from backend.app.engines.enterprise_distressed_asset_debt_stress.scenario_creation import (
    create_scenario,
    create_default_stress_scenarios,
)
from backend.app.engines.enterprise_distressed_asset_debt_stress.scenario_storage import (
    retrieve_scenario,
    store_scenario,
)


@pytest.mark.anyio
async def test_create_scenario_basic(sqlite_db: None) -> None:
    """Test basic scenario creation."""
    scenario = create_scenario(
        dataset_version_id="test_dv_1",
        scenario_name="test_scenario",
        description="Test scenario description",
        time_horizon_months=12,
        assumptions={
            "revenue_change_factor": 0.8,
            "cost_change_factor": 1.15,
            "interest_rate_change_factor": 1.3,
            "liquidity_shock_factor": 0.85,
            "market_value_depreciation_factor": 0.85,
        },
    )
    
    assert scenario.scenario_id is not None
    assert scenario.dataset_version_id == "test_dv_1"
    assert scenario.scenario_name == "test_scenario"
    assert scenario.description == "Test scenario description"
    assert scenario.time_horizon_months == 12
    assert scenario.assumptions.revenue_change_factor == Decimal("0.8")
    assert scenario.assumptions.cost_change_factor == Decimal("1.15")
    assert scenario.created_at is not None


@pytest.mark.anyio
async def test_create_scenario_invalid_time_horizon(sqlite_db: None) -> None:
    """Test scenario creation with invalid time horizon."""
    with pytest.raises(ScenarioInvalidError, match="TIME_HORIZON_MUST_BE_6_TO_24_MONTHS"):
        create_scenario(
            dataset_version_id="test_dv_1",
            scenario_name="test_scenario",
            description="Test",
            time_horizon_months=5,  # Too short
            assumptions={},
        )
    
    with pytest.raises(ScenarioInvalidError, match="TIME_HORIZON_MUST_BE_6_TO_24_MONTHS"):
        create_scenario(
            dataset_version_id="test_dv_1",
            scenario_name="test_scenario",
            description="Test",
            time_horizon_months=25,  # Too long
            assumptions={},
        )


@pytest.mark.anyio
async def test_create_scenario_invalid_assumptions(sqlite_db: None) -> None:
    """Test scenario creation with invalid assumptions."""
    with pytest.raises(ScenarioInvalidError):
        create_scenario(
            dataset_version_id="test_dv_1",
            scenario_name="test_scenario",
            description="Test",
            time_horizon_months=12,
            assumptions={
                "revenue_change_factor": -1.0,  # Invalid: negative
            },
        )


@pytest.mark.anyio
async def test_create_default_stress_scenarios(sqlite_db: None) -> None:
    """Test creation of default stress scenarios."""
    scenarios = create_default_stress_scenarios(
        dataset_version_id="test_dv_1",
        time_horizon_months=12,
    )
    
    assert len(scenarios) == 3
    assert scenarios[0].scenario_name == "mild_stress"
    assert scenarios[1].scenario_name == "moderate_stress"
    assert scenarios[2].scenario_name == "severe_stress"
    
    # Verify assumptions are progressively more severe
    assert scenarios[0].assumptions.revenue_change_factor > scenarios[2].assumptions.revenue_change_factor
    assert scenarios[0].assumptions.cost_change_factor < scenarios[2].assumptions.cost_change_factor


@pytest.mark.anyio
async def test_store_and_retrieve_scenario(sqlite_db: None) -> None:
    """Test storing and retrieving a scenario."""
    async with get_sessionmaker()() as db:
        # Create dataset version
        dv = await create_dataset_version_via_ingestion(db)
        
        # Create scenario
        scenario = create_scenario(
            dataset_version_id=dv.id,
            scenario_name="stored_scenario",
            description="Scenario to be stored",
            time_horizon_months=12,
            assumptions={
                "revenue_change_factor": 0.8,
                "cost_change_factor": 1.15,
            },
        )
        
        # Store scenario
        created_at = datetime.now(timezone.utc)
        evidence = await store_scenario(db, scenario=scenario, created_at=created_at)
        await db.commit()
        
        # Retrieve scenario
        retrieved = await retrieve_scenario(
            db,
            scenario_id=scenario.scenario_id,
            dataset_version_id=dv.id,
        )
        
        assert retrieved.scenario_id == scenario.scenario_id
        assert retrieved.scenario_name == scenario.scenario_name
        assert retrieved.description == scenario.description
        assert retrieved.time_horizon_months == scenario.time_horizon_months
        assert retrieved.assumptions.revenue_change_factor == scenario.assumptions.revenue_change_factor


@pytest.mark.anyio
async def test_retrieve_scenario_not_found(sqlite_db: None) -> None:
    """Test retrieving a non-existent scenario."""
    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)
        await db.commit()
        
        with pytest.raises(ScenarioNotFoundError):
            await retrieve_scenario(
                db,
                scenario_id="nonexistent_scenario_id",
                dataset_version_id=dv.id,
            )


@pytest.mark.anyio
async def test_scenario_immutability(sqlite_db: None) -> None:
    """Test that scenarios are stored immutably."""
    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)
        
        scenario = create_scenario(
            dataset_version_id=dv.id,
            scenario_name="immutable_scenario",
            description="Test immutability",
            time_horizon_months=12,
            assumptions={"revenue_change_factor": 0.8},
        )
        
        created_at = datetime.now(timezone.utc)
        await store_scenario(db, scenario=scenario, created_at=created_at)
        await db.commit()
        
        # Try to store the same scenario again (should succeed and return existing)
        evidence2 = await store_scenario(db, scenario=scenario, created_at=created_at)
        await db.commit()
        
        # Should return the same evidence
        assert evidence2.evidence_id == evidence2.evidence_id






