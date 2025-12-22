"""
Comprehensive unit tests for debt exposure calculations covering edge cases.

Tests verify correctness of debt exposure modeling with various data structures,
edge cases, and stress test scenarios.
"""

from __future__ import annotations

import pytest

from backend.app.engines.enterprise_distressed_asset_debt_stress.models import (
    DEFAULT_STRESS_SCENARIOS,
    apply_stress_scenario,
    calculate_debt_exposure,
)


def test_debt_exposure_zero_debt() -> None:
    """Test debt exposure calculation with zero debt outstanding."""
    payload = {
        "financial": {
            "debt": {"total_outstanding": 0, "interest_rate_pct": 5.0},
            "assets": {"total": 1_000_000},
        },
    }
    exposure = calculate_debt_exposure(normalized_payload=payload)
    
    assert exposure.total_outstanding == 0.0
    assert exposure.interest_payment == 0.0
    assert exposure.collateral_coverage_ratio == 0.0
    assert exposure.leverage_ratio == 0.0
    assert exposure.net_exposure_after_recovery == 0.0


def test_debt_exposure_missing_debt_data() -> None:
    """Test debt exposure calculation with missing debt data."""
    payload = {
        "financial": {
            "assets": {"total": 1_000_000},
        },
    }
    exposure = calculate_debt_exposure(normalized_payload=payload)
    
    assert exposure.total_outstanding == 0.0
    assert exposure.interest_rate_pct == 0.0
    assert exposure.interest_payment == 0.0


def test_debt_exposure_negative_collateral() -> None:
    """Test debt exposure calculation with negative collateral (should be handled gracefully)."""
    payload = {
        "financial": {
            "debt": {
                "total_outstanding": 1_000_000,
                "interest_rate_pct": 5.0,
                "collateral_value": -100_000,  # Invalid but should be handled
            },
            "assets": {"total": 2_000_000},
        },
    }
    exposure = calculate_debt_exposure(normalized_payload=payload)
    
    assert exposure.collateral_value == -100_000.0
    assert exposure.collateral_shortfall > 0
    assert exposure.collateral_coverage_ratio < 0


def test_debt_exposure_zero_assets() -> None:
    """Test debt exposure calculation with zero assets."""
    payload = {
        "financial": {
            "debt": {
                "total_outstanding": 1_000_000,
                "interest_rate_pct": 5.0,
            },
            "assets": {"total": 0},
        },
    }
    exposure = calculate_debt_exposure(normalized_payload=payload)
    
    assert exposure.assets_value == 0.0
    assert exposure.leverage_ratio == 0.0  # Division by zero protection


def test_debt_exposure_multiple_instruments() -> None:
    """Test debt exposure calculation with multiple debt instruments."""
    payload = {
        "financial": {
            "debt": {
                "instruments": [
                    {
                        "principal": 500_000,
                        "interest_rate_pct": 4.0,
                        "collateral_value": 400_000,
                    },
                    {
                        "principal": 300_000,
                        "interest_rate_pct": 6.0,
                        "collateral_value": 250_000,
                    },
                    {
                        "principal": 200_000,
                        "interest_rate_pct": 5.0,
                        "collateral_value": 100_000,
                    },
                ],
            },
            "assets": {"total": 2_000_000},
        },
    }
    exposure = calculate_debt_exposure(normalized_payload=payload)
    
    # Total outstanding should be sum of all principals
    assert exposure.total_outstanding == pytest.approx(1_000_000)
    
    # Weighted average interest rate: (500k*4% + 300k*6% + 200k*5%) / 1000k
    expected_rate = (500_000 * 4.0 + 300_000 * 6.0 + 200_000 * 5.0) / 1_000_000
    assert exposure.interest_rate_pct == pytest.approx(expected_rate)
    
    # Interest payment should match weighted average
    assert exposure.interest_payment == pytest.approx(exposure.total_outstanding * (expected_rate / 100.0))
    
    # Collateral should be sum
    assert exposure.collateral_value == pytest.approx(750_000)
    assert exposure.collateral_coverage_ratio == pytest.approx(0.75)


def test_debt_exposure_mixed_instruments_and_aggregate() -> None:
    """Test that instruments take precedence over aggregate values."""
    payload = {
        "financial": {
            "debt": {
                "total_outstanding": 2_000_000,  # Should be ignored if instruments exist
                "interest_rate_pct": 10.0,  # Should be ignored
                "instruments": [
                    {
                        "principal": 1_000_000,
                        "interest_rate_pct": 5.0,
                    },
                ],
            },
            "assets": {"total": 2_000_000},
        },
    }
    exposure = calculate_debt_exposure(normalized_payload=payload)
    
    # Should use instrument values, not aggregate
    assert exposure.total_outstanding == pytest.approx(1_000_000)
    assert exposure.interest_rate_pct == pytest.approx(5.0)


def test_debt_exposure_invalid_instruments() -> None:
    """Test debt exposure with invalid instrument data."""
    payload = {
        "financial": {
            "debt": {
                "instruments": [
                    {"principal": 0},  # Invalid - zero principal (skipped)
                    {"principal": -100_000},  # Invalid - negative (skipped)
                    {"principal": 500_000, "interest_rate_pct": "invalid"},  # Valid principal, invalid rate (counted with 0% rate)
                    {"principal": 300_000, "interest_rate_pct": 5.0},  # Valid
                ],
            },
            "assets": {"total": 1_000_000},
        },
    }
    exposure = calculate_debt_exposure(normalized_payload=payload)
    
    # Should count instruments with valid principal (even if interest rate is invalid)
    # 500k + 300k = 800k total
    assert exposure.total_outstanding == pytest.approx(800_000)
    # Weighted average: (500k * 0% + 300k * 5%) / 800k = 1.875%
    assert exposure.interest_rate_pct == pytest.approx(1.875)


def test_debt_exposure_no_distressed_assets() -> None:
    """Test debt exposure calculation with no distressed assets."""
    payload = {
        "financial": {
            "debt": {
                "total_outstanding": 1_000_000,
                "interest_rate_pct": 5.0,
                "collateral_value": 750_000,
            },
            "assets": {"total": 2_000_000},
        },
    }
    exposure = calculate_debt_exposure(normalized_payload=payload)
    
    assert exposure.distressed_asset_count == 0
    assert exposure.distressed_asset_value == 0.0
    assert exposure.distressed_asset_recovery == 0.0
    assert exposure.distressed_asset_recovery_ratio == 0.0
    assert exposure.net_exposure_after_recovery == pytest.approx(250_000)  # 1M - 750k collateral


def test_debt_exposure_distressed_assets_in_financial() -> None:
    """Test that distressed assets can be found in financial dict."""
    payload = {
        "financial": {
            "debt": {"total_outstanding": 1_000_000},
            "distressed_assets": [
                {"name": "Asset A", "value": 200_000, "recovery_rate_pct": 35},
            ],
        },
    }
    exposure = calculate_debt_exposure(normalized_payload=payload)
    
    assert exposure.distressed_asset_count == 1
    assert exposure.distressed_asset_value == pytest.approx(200_000)
    assert exposure.distressed_asset_recovery == pytest.approx(70_000)


def test_stress_scenario_zero_base_exposure() -> None:
    """Test stress scenario application with zero base exposure."""
    exposure = calculate_debt_exposure(
        normalized_payload={
            "financial": {
                "debt": {"total_outstanding": 1_000_000, "interest_rate_pct": 5.0, "collateral_value": 1_000_000},
                "assets": {"total": 2_000_000},
            },
        }
    )
    
    # Base net exposure is zero (fully collateralized)
    base_net = exposure.net_exposure_after_recovery
    assert base_net == 0.0
    
    scenario = DEFAULT_STRESS_SCENARIOS[0]
    result = apply_stress_scenario(exposure=exposure, base_net_exposure=base_net, scenario=scenario)
    
    # Loss estimate should be the new net exposure
    assert result.loss_estimate >= 0
    assert result.impact_score >= 0


def test_stress_scenario_extreme_values() -> None:
    """Test stress scenario with extreme market impact values."""
    exposure = calculate_debt_exposure(
        normalized_payload={
            "financial": {
                "debt": {
                    "total_outstanding": 1_000_000,
                    "interest_rate_pct": 5.0,
                    "collateral_value": 500_000,
                },
                "assets": {"total": 2_000_000},
            },
            "distressed_assets": [
                {"value": 200_000, "recovery_rate_pct": 50},
            ],
        }
    )
    
    # Create extreme scenario
    from backend.app.engines.enterprise_distressed_asset_debt_stress.models import StressTestScenario
    
    extreme_scenario = StressTestScenario(
        scenario_id="extreme_crash",
        description="Extreme market crash",
        interest_rate_delta_pct=10.0,  # Very high
        collateral_market_impact_pct=-0.9,  # 90% loss
        recovery_degradation_pct=-0.8,  # 80% degradation
        default_risk_increment_pct=0.2,  # 20% default risk
    )
    
    result = apply_stress_scenario(
        exposure=exposure,
        base_net_exposure=exposure.net_exposure_after_recovery,
        scenario=extreme_scenario,
    )
    
    # Verify calculations are bounded and reasonable
    assert result.adjusted_interest_rate_pct == pytest.approx(15.0)  # 5% + 10%
    assert result.adjusted_collateral_value >= 0.0
    assert result.adjusted_distressed_asset_recovery >= 0.0
    assert result.loss_estimate >= 0.0
    assert 0.0 <= result.impact_score <= 1.0


def test_stress_scenario_all_default_scenarios() -> None:
    """Test that all default stress scenarios produce valid results."""
    exposure = calculate_debt_exposure(
        normalized_payload={
            "financial": {
                "debt": {
                    "total_outstanding": 1_000_000,
                    "interest_rate_pct": 5.0,
                    "collateral_value": 750_000,
                },
                "assets": {"total": 2_000_000},
            },
            "distressed_assets": [
                {"value": 200_000, "recovery_rate_pct": 35},
                {"value": 150_000, "recovery_rate_pct": 50},
            ],
        }
    )
    
    base_net = exposure.net_exposure_after_recovery
    
    for scenario in DEFAULT_STRESS_SCENARIOS:
        result = apply_stress_scenario(exposure=exposure, base_net_exposure=base_net, scenario=scenario)
        
        # Verify all results are valid
        assert result.adjusted_interest_rate_pct >= exposure.interest_rate_pct
        assert result.interest_payment >= 0.0
        assert result.adjusted_collateral_value >= 0.0
        assert result.collateral_loss >= 0.0
        assert result.adjusted_distressed_asset_recovery >= 0.0
        assert result.distressed_asset_loss >= 0.0
        assert result.default_risk_buffer >= 0.0
        assert result.net_exposure_after_recovery >= 0.0
        assert result.loss_estimate >= 0.0
        assert 0.0 <= result.impact_score <= 1.0


def test_debt_exposure_alternative_field_names() -> None:
    """Test that debt exposure handles alternative field name variations."""
    # Test "outstanding" instead of "total_outstanding"
    payload1 = {
        "financial": {
            "debt": {"outstanding": 1_000_000, "interest_rate": 5.0},
        },
    }
    exp1 = calculate_debt_exposure(normalized_payload=payload1)
    assert exp1.total_outstanding == pytest.approx(1_000_000)
    assert exp1.interest_rate_pct == pytest.approx(5.0)
    
    # Test "principal" instead of "total_outstanding"
    payload2 = {
        "financial": {
            "debt": {"principal": 500_000, "rate_pct": 6.0},
        },
    }
    exp2 = calculate_debt_exposure(normalized_payload=payload2)
    assert exp2.total_outstanding == pytest.approx(500_000)
    assert exp2.interest_rate_pct == pytest.approx(6.0)


def test_debt_exposure_assets_alternative_names() -> None:
    """Test that asset value extraction handles alternative field names."""
    # Test "value" instead of "total"
    payload1 = {
        "financial": {
            "debt": {"total_outstanding": 1_000_000},
            "assets": {"value": 2_000_000},
        },
    }
    exp1 = calculate_debt_exposure(normalized_payload=payload1)
    assert exp1.assets_value == pytest.approx(2_000_000)
    
    # Test "amount" instead of "total"
    payload2 = {
        "financial": {
            "debt": {"total_outstanding": 1_000_000},
            "assets": {"amount": 1_500_000},
        },
    }
    exp2 = calculate_debt_exposure(normalized_payload=payload2)
    assert exp2.assets_value == pytest.approx(1_500_000)
    
    # Test "asset_value" at top level
    payload3 = {
        "financial": {
            "debt": {"total_outstanding": 1_000_000},
            "asset_value": 3_000_000,
        },
    }
    exp3 = calculate_debt_exposure(normalized_payload=payload3)
    assert exp3.assets_value == pytest.approx(3_000_000)


def test_stress_scenario_interest_rate_calculation() -> None:
    """Test that interest rate adjustments are calculated correctly."""
    exposure = calculate_debt_exposure(
        normalized_payload={
            "financial": {
                "debt": {"total_outstanding": 1_000_000, "interest_rate_pct": 5.0},
            },
        }
    )
    
    scenario = DEFAULT_STRESS_SCENARIOS[0]  # interest_rate_spike: +2.5%
    result = apply_stress_scenario(
        exposure=exposure,
        base_net_exposure=exposure.net_exposure_after_recovery,
        scenario=scenario,
    )
    
    assert result.adjusted_interest_rate_pct == pytest.approx(7.5)  # 5.0 + 2.5
    assert result.interest_payment == pytest.approx(75_000)  # 1M * 7.5%


def test_stress_scenario_collateral_impact() -> None:
    """Test that collateral market impact is applied correctly."""
    exposure = calculate_debt_exposure(
        normalized_payload={
            "financial": {
                "debt": {
                    "total_outstanding": 1_000_000,
                    "collateral_value": 800_000,
                },
            },
        }
    )
    
    # Market crash scenario: -25% impact
    scenario = DEFAULT_STRESS_SCENARIOS[1]
    result = apply_stress_scenario(
        exposure=exposure,
        base_net_exposure=exposure.net_exposure_after_recovery,
        scenario=scenario,
    )
    
    expected_collateral = 800_000 * (1.0 + (-0.25))  # 600_000
    assert result.adjusted_collateral_value == pytest.approx(expected_collateral)
    assert result.collateral_loss == pytest.approx(200_000)  # 800k - 600k


def test_stress_scenario_recovery_degradation() -> None:
    """Test that recovery degradation is applied correctly."""
    exposure = calculate_debt_exposure(
        normalized_payload={
            "financial": {
                "debt": {"total_outstanding": 1_000_000},
            },
            "distressed_assets": [
                {"value": 500_000, "recovery_rate_pct": 50},  # Base recovery: 250k
            ],
        }
    )
    
    # Default wave scenario: -35% recovery degradation
    scenario = DEFAULT_STRESS_SCENARIOS[2]
    result = apply_stress_scenario(
        exposure=exposure,
        base_net_exposure=exposure.net_exposure_after_recovery,
        scenario=scenario,
    )
    
    # Base recovery: 250k, after -35% degradation: 250k * (1 - 0.35) = 162.5k
    expected_recovery = 250_000 * (1.0 + (-0.35))
    assert result.adjusted_distressed_asset_recovery == pytest.approx(expected_recovery)


def test_stress_scenario_default_risk_buffer() -> None:
    """Test that default risk buffer is calculated correctly."""
    exposure = calculate_debt_exposure(
        normalized_payload={
            "financial": {
                "debt": {"total_outstanding": 1_000_000},
            },
        }
    )
    
    # Default wave scenario: 8% default risk increment
    scenario = DEFAULT_STRESS_SCENARIOS[2]
    result = apply_stress_scenario(
        exposure=exposure,
        base_net_exposure=exposure.net_exposure_after_recovery,
        scenario=scenario,
    )
    
    expected_buffer = 1_000_000 * 0.08  # 80_000
    assert result.default_risk_buffer == pytest.approx(expected_buffer)

