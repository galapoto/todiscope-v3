"""
Test Regulatory Framework Setup

Tests for regulatory check modules to ensure they correctly implement
regulatory framework setup and perform proper regulatory checks.
"""
from __future__ import annotations

import pytest

from backend.app.engines.audit_readiness.regulatory_logic import (
    assess_regulatory_readiness,
    calculate_risk_score,
    determine_check_status,
    determine_risk_level,
    evaluate_control_gaps,
)


class TestRiskThresholds:
    """Test risk threshold calculations."""

    def test_calculate_risk_score_no_controls(self):
        """Test risk score when no controls are assessed."""
        score = calculate_risk_score(controls_passing=0, controls_total=0, gap_severities=[])
        assert score == 1.0, "No controls assessed should result in maximum risk"

    def test_calculate_risk_score_all_passing(self):
        """Test risk score when all controls pass."""
        score = calculate_risk_score(controls_passing=10, controls_total=10, gap_severities=[])
        assert score == 0.0, "All controls passing should result in minimum risk"

    def test_calculate_risk_score_half_passing(self):
        """Test risk score when half controls pass."""
        score = calculate_risk_score(controls_passing=5, controls_total=10, gap_severities=[])
        # With 50% pass rate and no gaps: coverage_score = 0.5, severity_impact = 0.0
        # risk_score = (0.5 * 0.6) + (0.0 * 0.4) = 0.3
        assert 0.25 <= score <= 0.35, "Half controls passing with no gaps should result in ~0.3 risk score"

    def test_calculate_risk_score_with_critical_gaps(self):
        """Test risk score with critical severity gaps."""
        score = calculate_risk_score(
            controls_passing=5,
            controls_total=10,
            gap_severities=["critical", "critical", "high"]
        )
        assert score > 0.6, "Critical gaps should significantly increase risk score"

    def test_calculate_risk_score_with_low_gaps(self):
        """Test risk score with low severity gaps."""
        score = calculate_risk_score(
            controls_passing=8,
            controls_total=10,
            gap_severities=["low", "low"]
        )
        assert score < 0.4, "Low severity gaps should result in lower risk score"

    def test_calculate_risk_score_bounds(self):
        """Test that risk score is always between 0.0 and 1.0."""
        for passing in range(0, 11):
            for total in range(1, 11):
                if passing <= total:
                    score = calculate_risk_score(
                        controls_passing=passing,
                        controls_total=total,
                        gap_severities=["critical", "high", "medium", "low"]
                    )
                    assert 0.0 <= score <= 1.0, f"Risk score {score} out of bounds"


class TestRiskLevelDetermination:
    """Test risk level determination from risk scores."""

    def test_determine_risk_level_critical(self):
        """Test critical risk level determination."""
        assert determine_risk_level(0.85) == "critical"
        assert determine_risk_level(0.90) == "critical"
        assert determine_risk_level(1.0) == "critical"

    def test_determine_risk_level_high(self):
        """Test high risk level determination."""
        assert determine_risk_level(0.70) == "high"
        assert determine_risk_level(0.65) == "high"
        assert determine_risk_level(0.60) == "high"

    def test_determine_risk_level_medium(self):
        """Test medium risk level determination."""
        assert determine_risk_level(0.50) == "medium"
        assert determine_risk_level(0.45) == "medium"
        assert determine_risk_level(0.40) == "medium"

    def test_determine_risk_level_low(self):
        """Test low risk level determination."""
        assert determine_risk_level(0.30) == "low"
        assert determine_risk_level(0.25) == "low"
        assert determine_risk_level(0.20) == "low"

    def test_determine_risk_level_none(self):
        """Test none risk level determination."""
        assert determine_risk_level(0.15) == "none"
        assert determine_risk_level(0.10) == "none"
        assert determine_risk_level(0.0) == "none"


class TestCheckStatusDetermination:
    """Test check status determination."""

    def test_determine_check_status_unknown(self):
        """Test unknown status when no controls assessed."""
        assert determine_check_status(0, 0, "critical") == "unknown"

    def test_determine_check_status_not_ready_critical(self):
        """Test not_ready status for critical risk."""
        assert determine_check_status(5, 10, "critical") == "not_ready"
        assert determine_check_status(9, 10, "critical") == "not_ready"

    def test_determine_check_status_not_ready_high(self):
        """Test not_ready status for high risk."""
        assert determine_check_status(5, 10, "high") == "not_ready"
        assert determine_check_status(6, 10, "high") == "not_ready"

    def test_determine_check_status_partial_medium(self):
        """Test partial status for medium risk with good pass rate."""
        assert determine_check_status(8, 10, "medium") == "partial"
        assert determine_check_status(7, 10, "medium") == "partial"

    def test_determine_check_status_not_ready_medium_low_pass_rate(self):
        """Test not_ready status for medium risk with low pass rate."""
        assert determine_check_status(6, 10, "medium") == "not_ready"
        assert determine_check_status(5, 10, "medium") == "not_ready"

    def test_determine_check_status_ready_low_risk(self):
        """Test ready status for low risk with high pass rate."""
        assert determine_check_status(10, 10, "low") == "ready"
        assert determine_check_status(9, 10, "low") == "ready"
        assert determine_check_status(9, 10, "none") == "ready"

    def test_determine_check_status_partial_low_risk(self):
        """Test partial status for low risk with medium pass rate."""
        assert determine_check_status(8, 10, "low") == "partial"
        assert determine_check_status(7, 10, "low") == "partial"


class TestControlGapEvaluation:
    """Test control gap evaluation logic."""

    def test_evaluate_control_gaps_no_gaps(self):
        """Test gap evaluation when all evidence is present."""
        control_catalog = {
            "controls": [
                {
                    "control_id": "ctrl_001",
                    "control_name": "Access Control",
                    "critical": False,
                }
            ],
            "required_evidence_types": {
                "ctrl_001": ["evidence_type_1", "evidence_type_2"]
            }
        }
        evidence_map = {
            "ctrl_001": ["evidence_type_1", "evidence_type_2"]
        }
        
        gaps = evaluate_control_gaps("framework_1", control_catalog, evidence_map)
        assert len(gaps) == 0, "No gaps should be identified when all evidence is present"

    def test_evaluate_control_gaps_missing_all_evidence(self):
        """Test gap evaluation when all evidence is missing."""
        control_catalog = {
            "controls": [
                {
                    "control_id": "ctrl_001",
                    "control_name": "Access Control",
                    "critical": True,
                }
            ],
            "required_evidence_types": {
                "ctrl_001": ["evidence_type_1", "evidence_type_2"]
            }
        }
        evidence_map = {}
        
        gaps = evaluate_control_gaps("framework_1", control_catalog, evidence_map)
        assert len(gaps) == 1, "Should identify one gap"
        assert gaps[0].control_id == "ctrl_001"
        assert gaps[0].gap_type == "missing"
        assert gaps[0].severity == "critical"

    def test_evaluate_control_gaps_partial_evidence(self):
        """Test gap evaluation when some evidence is missing."""
        control_catalog = {
            "controls": [
                {
                    "control_id": "ctrl_001",
                    "control_name": "Access Control",
                    "critical": False,
                }
            ],
            "required_evidence_types": {
                "ctrl_001": ["evidence_type_1", "evidence_type_2", "evidence_type_3"]
            }
        }
        evidence_map = {
            "ctrl_001": ["evidence_type_1"]  # Only 1 of 3 required
        }
        
        gaps = evaluate_control_gaps("framework_1", control_catalog, evidence_map)
        assert len(gaps) == 1, "Should identify one gap"
        assert gaps[0].gap_type == "incomplete"
        assert gaps[0].severity in ["high", "medium"]

    def test_evaluate_control_gaps_no_evidence_but_not_critical(self):
        """Test gap evaluation when no evidence but control is not critical."""
        control_catalog = {
            "controls": [
                {
                    "control_id": "ctrl_001",
                    "control_name": "Access Control",
                    "critical": False,
                }
            ],
            "required_evidence_types": {
                "ctrl_001": ["evidence_type_1"]
            }
        }
        evidence_map = {}
        
        gaps = evaluate_control_gaps("framework_1", control_catalog, evidence_map)
        assert len(gaps) == 1, "Should identify one gap"
        assert gaps[0].gap_type == "insufficient"
        assert gaps[0].severity == "low"

    def test_evaluate_control_gaps_multiple_controls(self):
        """Test gap evaluation with multiple controls."""
        control_catalog = {
            "controls": [
                {
                    "control_id": "ctrl_001",
                    "control_name": "Access Control",
                    "critical": True,
                },
                {
                    "control_id": "ctrl_002",
                    "control_name": "Data Encryption",
                    "critical": False,
                }
            ],
            "required_evidence_types": {
                "ctrl_001": ["evidence_type_1"],
                "ctrl_002": ["evidence_type_2"]
            }
        }
        evidence_map = {
            "ctrl_001": ["evidence_type_1"],  # Has evidence
            "ctrl_002": []  # Missing evidence
        }
        
        gaps = evaluate_control_gaps("framework_1", control_catalog, evidence_map)
        assert len(gaps) == 1, "Should identify one gap for ctrl_002"
        assert gaps[0].control_id == "ctrl_002"


class TestRegulatoryReadinessAssessment:
    """Test full regulatory readiness assessment."""

    def test_assess_regulatory_readiness_ready(self):
        """Test assessment when all controls pass."""
        control_catalog = {
            "controls": [
                {
                    "control_id": "ctrl_001",
                    "control_name": "Access Control",
                    "critical": False,
                },
                {
                    "control_id": "ctrl_002",
                    "control_name": "Data Encryption",
                    "critical": False,
                }
            ],
            "required_evidence_types": {
                "ctrl_001": ["evidence_type_1"],
                "ctrl_002": ["evidence_type_2"]
            }
        }
        evidence_map = {
            "ctrl_001": ["evidence_type_1"],
            "ctrl_002": ["evidence_type_2"]
        }
        
        result = assess_regulatory_readiness(
            framework_id="framework_1",
            framework_name="Test Framework",
            framework_version="v1",
            dataset_version_id="dv_001",
            control_catalog=control_catalog,
            evidence_map=evidence_map,
            assessment_timestamp="2025-01-01T00:00:00Z",
        )
        
        assert result.framework_id == "framework_1"
        assert result.check_status == "ready"
        assert result.controls_assessed == 2
        assert result.controls_passing == 2
        assert result.controls_failing == 0
        assert result.risk_score < 0.2
        assert result.risk_level in ["low", "none"]

    def test_assess_regulatory_readiness_not_ready(self):
        """Test assessment when controls fail."""
        control_catalog = {
            "controls": [
                {
                    "control_id": "ctrl_001",
                    "control_name": "Access Control",
                    "critical": True,
                }
            ],
            "required_evidence_types": {
                "ctrl_001": ["evidence_type_1"]
            }
        }
        evidence_map = {}
        
        result = assess_regulatory_readiness(
            framework_id="framework_1",
            framework_name="Test Framework",
            framework_version="v1",
            dataset_version_id="dv_001",
            control_catalog=control_catalog,
            evidence_map=evidence_map,
            assessment_timestamp="2025-01-01T00:00:00Z",
        )
        
        assert result.check_status == "not_ready"
        assert result.controls_assessed == 1
        assert result.controls_passing == 0
        assert result.controls_failing == 1
        assert len(result.control_gaps) == 1
        assert result.risk_score > 0.6

    def test_assess_regulatory_readiness_partial(self):
        """Test assessment with partial readiness."""
        control_catalog = {
            "controls": [
                {
                    "control_id": "ctrl_001",
                    "control_name": "Access Control",
                    "critical": False,
                },
                {
                    "control_id": "ctrl_002",
                    "control_name": "Data Encryption",
                    "critical": False,
                },
                {
                    "control_id": "ctrl_003",
                    "control_name": "Audit Logging",
                    "critical": False,
                }
            ],
            "required_evidence_types": {
                "ctrl_001": ["evidence_type_1"],
                "ctrl_002": ["evidence_type_2"],
                "ctrl_003": ["evidence_type_3"]
            }
        }
        evidence_map = {
            "ctrl_001": ["evidence_type_1"],
            "ctrl_002": ["evidence_type_2"],
            # ctrl_003 missing
        }
        
        result = assess_regulatory_readiness(
            framework_id="framework_1",
            framework_name="Test Framework",
            framework_version="v1",
            dataset_version_id="dv_001",
            control_catalog=control_catalog,
            evidence_map=evidence_map,
            assessment_timestamp="2025-01-01T00:00:00Z",
        )
        
        assert result.check_status in ["partial", "not_ready"]
        assert result.controls_assessed == 3
        assert result.controls_passing == 2
        assert result.controls_failing == 1
        assert len(result.control_gaps) == 1

    def test_assess_regulatory_readiness_evidence_ids_collected(self):
        """Test that evidence IDs are properly collected."""
        control_catalog = {
            "controls": [
                {
                    "control_id": "ctrl_001",
                    "control_name": "Access Control",
                    "critical": False,
                }
            ],
            "required_evidence_types": {
                "ctrl_001": ["evidence_type_1"]
            }
        }
        evidence_map = {
            "ctrl_001": ["ev_001", "ev_002", "ev_003"]
        }
        
        result = assess_regulatory_readiness(
            framework_id="framework_1",
            framework_name="Test Framework",
            framework_version="v1",
            dataset_version_id="dv_001",
            control_catalog=control_catalog,
            evidence_map=evidence_map,
            assessment_timestamp="2025-01-01T00:00:00Z",
        )
        
        assert len(result.evidence_ids) == 3
        assert "ev_001" in result.evidence_ids
        assert "ev_002" in result.evidence_ids
        assert "ev_003" in result.evidence_ids

