"""Unit tests for the litigation/dispute analysis algorithms."""

import pytest

from backend.app.engines.enterprise_litigation_dispute.analysis import (
    assess_liability,
    compare_scenarios,
    evaluate_legal_consistency,
    quantify_damages,
)


def sample_dispute_payload() -> dict:
    return {
        "claims": [
            {"amount": 1_000_000},
            {"amount": 500_000},
        ],
        "damages": {"compensatory": 2_000_000, "punitive": 500_000, "mitigation": 250_000},
        "liability": {
            "parties": [
                {"party": "Company A", "percent": 90, "evidence_strength": 0.85},
                {"party": "Company B", "percent": 10, "evidence_strength": 0.2},
            ],
            "admissions": True,
            "regulations": ["contract"],
        },
        "scenarios": [
            {"name": "best", "probability": 0.8, "expected_damages": 300_000, "liability_multiplier": 0.9},
            {"name": "worst", "probability": 0.2, "expected_damages": 1_200_000, "liability_multiplier": 1.1},
        ],
        "legal_consistency": {"conflicts": ["statute overlap"], "missing_support": ["witness statements"]},
    }


@pytest.mark.parametrize("recovery_rate", (0.5, 1.0))
def test_quantify_damages_tracks_net_exposure(recovery_rate: float) -> None:
    assumptions = {
        "damage": {
            "recovery_rate": recovery_rate,
            "severity_thresholds": {"high": 1_500_000, "medium": 500_000},
        }
    }
    payload = sample_dispute_payload()
    result = quantify_damages(dataset_version_id="dv-1", dispute_payload=payload, assumptions=assumptions)

    assert result.net_damage >= 0
    severity_expected = "high" if result.net_damage >= 1_500_000 else "medium"
    assert result.severity == severity_expected
    assert result.total_claim_value == 1_500_000
    assert result.confidence in {"high", "medium"}
    assert any(a["id"].startswith("assumption_damage") for a in result.assumptions)


def test_assess_liability_identifies_dominant_party() -> None:
    payload = sample_dispute_payload()
    assumptions = {"liability": {"evidence_strength_thresholds": {"strong": 0.75, "weak": 0.4}}}
    result = assess_liability(dataset_version_id="dv-2", dispute_payload=payload, assumptions=assumptions)

    assert result.responsible_party == "Company A"
    assert result.responsibility_pct == 90
    assert result.liability_strength == "strong"
    assert "Dominant responsibility assigned to Company A" in result.indicators
    assert result.confidence == "high"


def test_compare_scenarios_ranks_exposures() -> None:
    payload = sample_dispute_payload()
    assumptions = {"scenario": {"probabilities": 1.0}}
    result = compare_scenarios(dataset_version_id="dv-3", dispute_payload=payload, assumptions=assumptions)

    assert result.best_case is not None
    assert result.worst_case is not None
    assert result.total_probability == pytest.approx(1.0)
    assert result.best_case["expected_loss"] <= result.worst_case["expected_loss"]
    assert result.scenarios[0]["probability"] == 0.8


def test_evaluate_legal_consistency_detects_conflicts() -> None:
    payload = sample_dispute_payload()
    assumptions = {"legal_consistency": {"completeness_requirements": ["statutes", "evidence"]}}
    result = evaluate_legal_consistency(dataset_version_id="dv-4", dispute_payload=payload, assumptions=assumptions)

    assert not result.consistent
    assert "Conflict:" in result.issues[0]
    assert result.confidence == "low"
