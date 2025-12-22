"""
Unit tests for Enterprise Litigation & Dispute Analysis Engine core analysis functions.

Tests cover:
- Damage quantification
- Liability assessment
- Scenario comparison
- Legal consistency evaluation
"""

from __future__ import annotations

import pytest

from backend.app.engines.enterprise_litigation_dispute.analysis import (
    assess_liability,
    compare_scenarios,
    evaluate_legal_consistency,
    quantify_damages,
)


@pytest.mark.parametrize(
    "claims,damages,mitigation,recovery_rate,expected_net,expected_severity",
    [
        # High severity case
        ([{"amount": 2000000}], {"compensatory": 1500000, "punitive": 500000}, 0, 1.0, 2000000.0, "high"),
        # Medium severity case
        ([{"amount": 500000}], {"compensatory": 300000, "punitive": 100000}, 50000, 1.0, 350000.0, "medium"),
        # Low severity case
        ([{"amount": 100000}], {"compensatory": 50000, "punitive": 0}, 10000, 1.0, 40000.0, "low"),
        # With mitigation and recovery rate
        ([{"amount": 1000000}], {"compensatory": 800000, "punitive": 200000}, 200000, 0.5, 900000.0, "medium"),
        # Zero damages
        ([], {"compensatory": 0, "punitive": 0}, 0, 1.0, 0.0, "low"),
    ],
)
def test_quantify_damages(
    claims: list[dict],
    damages: dict,
    mitigation: float,
    recovery_rate: float,
    expected_net: float,
    expected_severity: str,
) -> None:
    """Test damage quantification with various scenarios."""
    dataset_version_id = "test-dv-001"
    dispute_payload = {
        "claims": claims,
        "damages": damages,
        "damages": {**damages, "mitigation": mitigation},
    }
    assumptions = {
        "damage": {
            "recovery_rate": recovery_rate,
            "severity_thresholds": {"high": 1000000.0, "medium": 250000.0},
        },
    }

    result = quantify_damages(
        dataset_version_id=dataset_version_id,
        dispute_payload=dispute_payload,
        assumptions=assumptions,
    )

    assert result.dataset_version_id == dataset_version_id
    assert abs(result.net_damage - expected_net) < 0.01
    assert result.severity == expected_severity
    assert result.confidence in ("high", "medium", "low")
    assert len(result.assumptions) > 0
    assert all("id" in a and "description" in a and "source" in a for a in result.assumptions)


def test_quantify_damages_with_defaults() -> None:
    """Test damage quantification with default assumptions."""
    dataset_version_id = "test-dv-002"
    dispute_payload = {
        "claims": [{"amount": 500000}],
        "damages": {"compensatory": 400000, "punitive": 100000},
    }
    assumptions = {}

    result = quantify_damages(
        dataset_version_id=dataset_version_id,
        dispute_payload=dispute_payload,
        assumptions=assumptions,
    )

    assert result.dataset_version_id == dataset_version_id
    assert result.net_damage >= 0
    assert result.severity in ("high", "medium", "low")
    assert result.total_claim_value == 500000.0
    assert result.gross_damages == 500000.0


@pytest.mark.parametrize(
    "parties,expected_party,expected_pct,expected_strength",
    [
        # Strong evidence
        ([{"party": "Party A", "percent": 80.0, "evidence_strength": 0.9}], "Party A", 80.0, "strong"),
        # Moderate evidence
        ([{"party": "Party B", "percent": 60.0, "evidence_strength": 0.6}], "Party B", 60.0, "moderate"),
        # Weak evidence
        ([{"party": "Party C", "percent": 50.0, "evidence_strength": 0.3}], "Party C", 50.0, "weak"),
        # Multiple parties
        (
            [
                {"party": "Party A", "percent": 40.0, "evidence_strength": 0.5},
                {"party": "Party B", "percent": 60.0, "evidence_strength": 0.7},
            ],
            "Party B",
            60.0,
            "moderate",
        ),
        # Undetermined
        ([], "undetermined", 0.0, "weak"),
    ],
)
def test_assess_liability(
    parties: list[dict],
    expected_party: str,
    expected_pct: float,
    expected_strength: str,
) -> None:
    """Test liability assessment with various party configurations."""
    dataset_version_id = "test-dv-003"
    dispute_payload = {
        "liability": {
            "parties": parties,
        },
    }
    assumptions = {
        "liability": {
            "evidence_strength_thresholds": {"strong": 0.75, "weak": 0.4},
        },
    }

    result = assess_liability(
        dataset_version_id=dataset_version_id,
        dispute_payload=dispute_payload,
        assumptions=assumptions,
    )

    assert result.dataset_version_id == dataset_version_id
    assert result.responsible_party == expected_party
    assert abs(result.responsibility_pct - expected_pct) < 0.01
    assert result.liability_strength == expected_strength
    assert result.confidence in ("high", "medium", "low")
    assert len(result.assumptions) > 0


def test_assess_liability_with_admissions() -> None:
    """Test liability assessment with admissions and regulations."""
    dataset_version_id = "test-dv-004"
    dispute_payload = {
        "liability": {
            "parties": [{"party": "Defendant", "percent": 100.0, "evidence_strength": 0.8}],
            "admissions": ["Admission 1", "Admission 2"],
            "regulations": ["Regulation A", "Regulation B"],
        },
    }
    assumptions = {}

    result = assess_liability(
        dataset_version_id=dataset_version_id,
        dispute_payload=dispute_payload,
        assumptions=assumptions,
    )

    assert result.responsible_party == "Defendant"
    assert len(result.indicators) > 0
    assert any("Admissions" in ind for ind in result.indicators)
    assert any("Regulatory" in ind for ind in result.indicators)


@pytest.mark.parametrize(
    "scenarios,expected_best_name,expected_worst_name",
    [
        # Multiple scenarios
        (
            [
                {"name": "Best", "probability": 0.3, "expected_damages": 100000, "liability_multiplier": 1.0},
                {"name": "Worst", "probability": 0.5, "expected_damages": 500000, "liability_multiplier": 1.5},
                {"name": "Medium", "probability": 0.2, "expected_damages": 250000, "liability_multiplier": 1.2},
            ],
            "Best",
            "Worst",
        ),
        # Single scenario
        (
            [{"name": "Only", "probability": 1.0, "expected_damages": 200000, "liability_multiplier": 1.0}],
            "Only",
            "Only",
        ),
    ],
)
def test_compare_scenarios(
    scenarios: list[dict],
    expected_best_name: str,
    expected_worst_name: str,
) -> None:
    """Test scenario comparison with various scenario configurations."""
    dataset_version_id = "test-dv-005"
    dispute_payload = {"scenarios": scenarios}
    assumptions = {}

    result = compare_scenarios(
        dataset_version_id=dataset_version_id,
        dispute_payload=dispute_payload,
        assumptions=assumptions,
    )

    assert result.dataset_version_id == dataset_version_id
    assert len(result.scenarios) == len(scenarios)
    assert result.best_case is not None
    assert result.worst_case is not None
    assert result.best_case["name"] == expected_best_name
    assert result.worst_case["name"] == expected_worst_name
    assert 0.0 <= result.total_probability <= 1.0
    assert len(result.assumptions) > 0

    # Verify scenario calculations
    for scenario in result.scenarios:
        assert "probability" in scenario
        assert "expected_damages" in scenario
        assert "expected_loss" in scenario
        assert "liability_exposure" in scenario
        assert scenario["expected_loss"] == scenario["probability"] * scenario["expected_damages"]


def test_compare_scenarios_empty() -> None:
    """Test scenario comparison with empty scenarios."""
    dataset_version_id = "test-dv-006"
    dispute_payload = {"scenarios": []}
    assumptions = {}

    result = compare_scenarios(
        dataset_version_id=dataset_version_id,
        dispute_payload=dispute_payload,
        assumptions=assumptions,
    )

    assert result.dataset_version_id == dataset_version_id
    assert len(result.scenarios) == 0
    assert result.best_case is None
    assert result.worst_case is None
    assert result.total_probability == 0.0


@pytest.mark.parametrize(
    "conflicts,missing_support,expected_consistent",
    [
        # Consistent case
        ([], [], True),
        # Conflicts present
        (["Conflict 1", "Conflict 2"], [], False),
        # Missing support
        ([], ["Missing support 1"], False),
        # Both conflicts and missing support
        (["Conflict 1"], ["Missing support 1"], False),
    ],
)
def test_evaluate_legal_consistency(
    conflicts: list[str],
    missing_support: list[str],
    expected_consistent: bool,
) -> None:
    """Test legal consistency evaluation with various conflict scenarios."""
    dataset_version_id = "test-dv-007"
    dispute_payload = {
        "legal_consistency": {
            "conflicts": conflicts,
            "missing_support": missing_support,
        },
    }
    assumptions = {}

    result = evaluate_legal_consistency(
        dataset_version_id=dataset_version_id,
        dispute_payload=dispute_payload,
        assumptions=assumptions,
    )

    assert result.dataset_version_id == dataset_version_id
    assert result.consistent == expected_consistent
    assert len(result.issues) == len(conflicts) + len(missing_support)
    assert result.confidence in ("high", "medium", "low")
    assert len(result.assumptions) > 0

    if conflicts:
        assert any("Conflict" in issue for issue in result.issues)
    if missing_support:
        assert any("Lacking support" in issue for issue in result.issues)


def test_evaluate_legal_consistency_with_requirements() -> None:
    """Test legal consistency with custom completeness requirements."""
    dataset_version_id = "test-dv-008"
    dispute_payload = {
        "legal_consistency": {
            "conflicts": [],
            "missing_support": [],
        },
    }
    assumptions = {
        "legal_consistency": {
            "completeness_requirements": ["statutes", "evidence", "precedents"],
        },
    }

    result = evaluate_legal_consistency(
        dataset_version_id=dataset_version_id,
        dispute_payload=dispute_payload,
        assumptions=assumptions,
    )

    assert result.consistent is True
    assert len(result.issues) == 0
    assert any("completeness_requirements" in a["source"] for a in result.assumptions)


def test_damage_quantification_edge_cases() -> None:
    """Test damage quantification with edge cases."""
    dataset_version_id = "test-dv-009"

    # Negative mitigation (should be handled)
    dispute_payload = {
        "claims": [{"amount": 1000000}],
        "damages": {"compensatory": 800000, "punitive": 200000, "mitigation": -100000},
    }
    assumptions = {}

    result = quantify_damages(
        dataset_version_id=dataset_version_id,
        dispute_payload=dispute_payload,
        assumptions=assumptions,
    )

    assert result.net_damage >= 0  # Should not be negative

    # Very high damages
    dispute_payload2 = {
        "claims": [{"amount": 100000000}],
        "damages": {"compensatory": 50000000, "punitive": 50000000},
    }

    result2 = quantify_damages(
        dataset_version_id=dataset_version_id,
        dispute_payload=dispute_payload2,
        assumptions=assumptions,
    )

    assert result2.severity == "high"
    assert result2.net_damage > 0


def test_liability_assessment_edge_cases() -> None:
    """Test liability assessment with edge cases."""
    dataset_version_id = "test-dv-010"

    # Invalid percentage (>100%)
    dispute_payload = {
        "liability": {
            "parties": [{"party": "Party A", "percent": 150.0, "evidence_strength": 0.8}],
        },
    }
    assumptions = {}

    result = assess_liability(
        dataset_version_id=dataset_version_id,
        dispute_payload=dispute_payload,
        assumptions=assumptions,
    )

    assert result.responsibility_pct <= 100.0  # Should be capped

    # Negative percentage
    dispute_payload2 = {
        "liability": {
            "parties": [{"party": "Party B", "percent": -10.0, "evidence_strength": 0.5}],
        },
    }

    result2 = assess_liability(
        dataset_version_id=dataset_version_id,
        dispute_payload=dispute_payload2,
        assumptions=assumptions,
    )

    assert result2.responsibility_pct >= 0.0  # Should be floored


def test_scenario_comparison_edge_cases() -> None:
    """Test scenario comparison with edge cases."""
    dataset_version_id = "test-dv-011"

    # Probability > 1.0 (should be capped)
    dispute_payload = {
        "scenarios": [
            {"name": "Over", "probability": 1.5, "expected_damages": 100000, "liability_multiplier": 1.0},
        ],
    }
    assumptions = {}

    result = compare_scenarios(
        dataset_version_id=dataset_version_id,
        dispute_payload=dispute_payload,
        assumptions=assumptions,
    )

    assert result.scenarios[0]["probability"] <= 1.0

    # Negative probability (should be floored)
    dispute_payload2 = {
        "scenarios": [
            {"name": "Negative", "probability": -0.5, "expected_damages": 100000, "liability_multiplier": 1.0},
        ],
    }

    result2 = compare_scenarios(
        dataset_version_id=dataset_version_id,
        dispute_payload=dispute_payload2,
        assumptions=assumptions,
    )

    assert result2.scenarios[0]["probability"] >= 0.0

