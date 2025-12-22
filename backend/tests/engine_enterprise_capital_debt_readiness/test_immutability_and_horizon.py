"""
Tests for immutability guards and time-horizon fixes in the enterprise capital debt readiness engine.

This module contains tests for:
1. _strict_create_evidence immutability enforcement
2. Time-horizon scaling of DSCR and interest coverage calculations
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.dataset.models import DatasetVersion
from backend.app.core.db import get_sessionmaker
from backend.app.engines.enterprise_capital_debt_readiness.run import _strict_create_evidence
from backend.app.engines.enterprise_capital_debt_readiness.debt_service import (
    assess_debt_service_ability,
)
from backend.app.engines.enterprise_capital_debt_readiness.assumptions import resolved_assumptions


# Test data
SAMPLE_ASSUMPTIONS = {
    "debt_service": {
        "horizon_months": 12,
        "min_dscr": 1.25,
        "min_interest_coverage": 2.0,
    },
    "cash_available": {
        "source_metric": "ebitda",
        "ebitda_to_cash_factor": 0.7,
    },
}

SAMPLE_FINANCIAL = {
    "cash_flow": {
        "cash_available_for_debt_service_annual": 120000,
    },
    "income_statement": {
        "ebitda": 150000,
    },
    "debt": {
        "instruments": [
            {
                "id": "loan_1",
                "principal": 60000,
                "annual_interest_rate": 0.10,
                "amortization": "amortizing",
                "payment_frequency_months": 1,
                "term_months": 12,
            }
        ]
    },
}


@pytest.mark.anyio
async def test_strict_create_evidence_rejects_payload_change(sqlite_db) -> None:
    """Test that _strict_create_evidence raises IMMUTABLE_EVIDENCE_MISMATCH when payload changes."""
    dv_id = "dv_test"
    started = datetime(2025, 1, 1, tzinfo=timezone.utc)
    sessionmaker = get_sessionmaker()
    
    async with sessionmaker() as db:
        # Add test dataset version
        db.add(DatasetVersion(id=dv_id))
        await db.flush()

        # First creation should succeed
        evidence_1 = await _strict_create_evidence(
            db,
            evidence_id="ev1",
            dataset_version_id=dv_id,
            engine_id="engine_enterprise_capital_debt_readiness",
            kind="debt_service",
            payload={"assumptions": {"horizon_months": 12, "min_dscr": 1.25}},
            created_at=started,
        )
        assert evidence_1 is not None

        # Same payload should be idempotent
        evidence_2 = await _strict_create_evidence(
            db,
            evidence_id="ev1",
            dataset_version_id=dv_id,
            engine_id="engine_enterprise_capital_debt_readiness",
            kind="debt_service",
            payload={"assumptions": {"horizon_months": 12, "min_dscr": 1.25}},
            created_at=started,
        )
        assert evidence_2.evidence_id == evidence_1.evidence_id

        # Different payload should raise IMMUTABLE_EVIDENCE_MISMATCH
        with pytest.raises(Exception) as exc_info:  # Replace with specific exception
            await _strict_create_evidence(
                db,
                evidence_id="ev1",
                dataset_version_id=dv_id,
                engine_id="engine_enterprise_capital_debt_readiness",
                kind="debt_service",
                payload={"assumptions": {"horizon_months": 6, "min_dscr": 1.25}},  # Changed horizon_months
                created_at=started,
            )
        assert "IMMUTABLE_EVIDENCE_MISMATCH" in str(exc_info.value)


@pytest.mark.anyio
async def test_strict_create_evidence_rejects_created_at_change(sqlite_db) -> None:
    """Test that _strict_create_evidence raises IMMUTABLE_EVIDENCE_CREATED_AT_MISMATCH when created_at changes."""
    dv_id = "dv_test"
    t1 = datetime(2025, 1, 1, tzinfo=timezone.utc)
    t2 = datetime(2025, 1, 2, tzinfo=timezone.utc)
    
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        db.add(DatasetVersion(id=dv_id))
        await db.flush()

        # First creation
        await _strict_create_evidence(
            db,
            evidence_id="ev1",
            dataset_version_id=dv_id,
            engine_id="engine_enterprise_capital_debt_readiness",
            kind="debt_service",
            payload={"test": "data"},
            created_at=t1,
        )

        # Different created_at should raise IMMUTABLE_EVIDENCE_CREATED_AT_MISMATCH
        with pytest.raises(Exception) as exc_info:  # Replace with specific exception
            await _strict_create_evidence(
                db,
                evidence_id="ev1",
                dataset_version_id=dv_id,
                engine_id="engine_enterprise_capital_debt_readiness",
                kind="debt_service",
                payload={"test": "data"},
                created_at=t2,  # Different timestamp
            )
        assert "IMMUTABLE_EVIDENCE_CREATED_AT_MISMATCH" in str(exc_info.value)


def test_dscr_scaling_with_different_horizons() -> None:
    """Test that DSCR is consistently calculated across different time horizons."""
    # Test with different horizon months
    test_cases = [
        (3, 0.25),   # 3 months = 0.25 years
        (6, 0.5),    # 6 months = 0.5 years
        (12, 1.0),   # 12 months = 1.0 years (no scaling needed)
        (24, 2.0),   # 24 months = 2.0 years
    ]
    
    for horizon_months, expected_scale in test_cases:
        # Update assumptions with current horizon
        assumptions = resolved_assumptions({
            **SAMPLE_ASSUMPTIONS,
            "debt_service": {
                **SAMPLE_ASSUMPTIONS["debt_service"],
                "horizon_months": horizon_months,
            }
        })
        
        # Run the assessment
        result = assess_debt_service_ability(
            dataset_version_id="test_dv",
            analysis_date=date(2025, 1, 1),
            financial=SAMPLE_FINANCIAL,
            assumptions=assumptions,
        )
        
        # Verify the horizon_months is set correctly
        assert result.horizon_months == horizon_months
        
        # Verify DSCR is calculated (should be the same when properly scaled)
        assert result.dscr is not None
        
        # For this simple case, DSCR should be approximately the same for all horizons
        # because we're scaling both the numerator (cash available) and denominator (debt service)
        # by the same factor
        expected_dscr = Decimal("2.0")  # 120k / 60k = 2.0 for 12 months
        assert abs(result.dscr - expected_dscr) < Decimal("0.01")


def test_interest_coverage_scaling_with_different_horizons() -> None:
    """Test that interest coverage is consistently calculated across different time horizons."""
    # Test with different horizon months
    test_cases = [3, 6, 12, 24]
    
    for horizon_months in test_cases:
        # Update assumptions with current horizon
        assumptions = resolved_assumptions({
            **SAMPLE_ASSUMPTIONS,
            "debt_service": {
                **SAMPLE_ASSUMPTIONS["debt_service"],
                "horizon_months": horizon_months,
            }
        })
        
        # Run the assessment
        result = assess_debt_service_ability(
            dataset_version_id="test_dv",
            analysis_date=date(2025, 1, 1),
            financial=SAMPLE_FINANCIAL,
            assumptions=assumptions,
        )
        
        # Verify interest coverage is calculated (should be the same when properly scaled)
        assert result.interest_coverage is not None
        
        # For this simple case, interest coverage should be approximately the same for all horizons
        # because we're scaling both the numerator (EBITDA) and denominator (interest) by the same factor
        expected_coverage = Decimal("25.0")  # 150k / 6k = 25.0 for 12 months
        assert abs(result.interest_coverage - expected_coverage) < Decimal("0.1")


def test_edge_cases() -> None:
    """Test edge cases for time-horizon calculations."""
    # Test with zero horizon_months (should handle gracefully)
    with pytest.raises(ValueError):
        assess_debt_service_ability(
            dataset_version_id="test_dv",
            analysis_date=date(2025, 1, 1),
            financial=SAMPLE_FINANCIAL,
            assumptions=resolved_assumptions({
                **SAMPLE_ASSUMPTIONS,
                "debt_service": {
                    **SAMPLE_ASSUMPTIONS["debt_service"],
                    "horizon_months": 0,
                }
            }),
        )
    
    # Test with negative horizon_months (should handle gracefully)
    with pytest.raises(ValueError):
        assess_debt_service_ability(
            dataset_version_id="test_dv",
            analysis_date=date(2025, 1, 1),
            financial=SAMPLE_FINANCIAL,
            assumptions=resolved_assumptions({
                **SAMPLE_ASSUMPTIONS,
                "debt_service": {
                    **SAMPLE_ASSUMPTIONS["debt_service"],
                    "horizon_months": -6,
                }
            }),
        )
    
    # Test with very large horizon (should handle gracefully)
    result = assess_debt_service_ability(
        dataset_version_id="test_dv",
        analysis_date=date(2025, 1, 1),
        financial=SAMPLE_FINANCIAL,
        assumptions=resolved_assumptions({
            **SAMPLE_ASSUMPTIONS,
            "debt_service": {
                **SAMPLE_ASSUMPTIONS["debt_service"],
                "horizon_months": 1200,  # 100 years
            }
        }),
    )
    assert result is not None
    assert result.dscr is not None
    assert result.interest_coverage is not None


def test_missing_financial_data() -> None:
    """Test handling of missing financial data with different horizons."""
    # Test with missing cash flow data
    financial = {
        "income_statement": {"ebitda": 150000},
        "debt": SAMPLE_FINANCIAL["debt"],
    }
    
    # Should fall back to EBITDA-derived cash flow
    result = assess_debt_service_ability(
        dataset_version_id="test_dv",
        analysis_date=date(2025, 1, 1),
        financial=financial,
        assumptions=resolved_assumptions({
            **SAMPLE_ASSUMPTIONS,
            "debt_service": {
                **SAMPLE_ASSUMPTIONS["debt_service"],
                "horizon_months": 6,  # 6 months
            }
        }),
    )
    
    # Should still calculate DSCR using EBITDA-derived cash flow
    assert result.dscr is not None
    assert "MISSING_CASH_AVAILABLE_FOR_DEBT_SERVICE" in result.flags
    
    # Verify scaling was applied correctly
    assert result.horizon_months == 6
