from __future__ import annotations

import pytest

from backend.app.engines.enterprise_distressed_asset_debt_stress.models import (
    DEFAULT_STRESS_SCENARIOS,
    apply_stress_scenario,
    calculate_debt_exposure,
)


def _normalized_payload() -> dict:
    return {
        "financial": {
            "debt": {
                "total_outstanding": 1_000_000,
                "interest_rate_pct": 5.0,
                "collateral_value": 750_000,
            },
            "assets": {"total": 2_000_000},
        },
        "distressed_assets": [
            {"name": "Asset A", "value": 200_000, "recovery_rate_pct": 35},
            {"name": "Asset B", "value": 150_000, "recovery_rate_pct": 50},
        ],
    }


def test_calculate_debt_exposure_aggregates_data() -> None:
    payload = _normalized_payload()
    exposure = calculate_debt_exposure(normalized_payload=payload)
    assert exposure.interest_payment == pytest.approx(50_000)
    assert exposure.collateral_coverage_ratio == pytest.approx(0.75)
    assert exposure.leverage_ratio == pytest.approx(0.5)
    assert exposure.net_exposure_after_recovery == pytest.approx(105_000)
    assert exposure.distressed_asset_value == pytest.approx(350_000)
    assert exposure.distressed_asset_recovery == pytest.approx(145_000)


def test_apply_interest_rate_spike_stress_scenario() -> None:
    payload = _normalized_payload()
    exposure = calculate_debt_exposure(normalized_payload=payload)
    scenario = DEFAULT_STRESS_SCENARIOS[0]  # interest_rate_spike
    result = apply_stress_scenario(
        exposure=exposure,
        base_net_exposure=exposure.net_exposure_after_recovery,
        scenario=scenario,
    )
    assert result.adjusted_interest_rate_pct == pytest.approx(7.5)
    assert result.collateral_loss == pytest.approx(37_500)
    assert result.distressed_asset_loss == pytest.approx(17_500)
    assert result.default_risk_buffer == pytest.approx(20_000)
    assert result.loss_estimate == pytest.approx(64_750)
    assert result.impact_score == pytest.approx(0.06475)
