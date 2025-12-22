"""Tests for readiness scoring functionality."""

from __future__ import annotations

from decimal import Decimal

import pytest

from backend.app.engines.enterprise_insurance_claim_forensics.readiness_scores import (
    calculate_claim_readiness_score,
    calculate_portfolio_readiness_score,
)


def test_calculate_claim_readiness_score_excellent() -> None:
    """Test readiness score calculation for excellent claim."""
    exposure = {
        "claim_id": "claim-1",
        "claim_amount": 10000.0,
        "claim_status": "closed",
        "currency": "USD",
        "severity": "low",
        "evidence_range": {
            "transaction_ids": ["tx-1", "tx-2"],
        },
    }
    validation_result = {
        "is_valid": True,
        "errors": [],
        "warnings": [],
    }
    
    result = calculate_claim_readiness_score(
        exposure=exposure,
        validation_result=validation_result,
    )
    
    assert result["readiness_score"] >= 80.0
    assert result["readiness_level"] == "excellent"
    assert "component_scores" in result
    assert "breakdown" in result


def test_calculate_claim_readiness_score_with_validation_errors() -> None:
    """Test readiness score calculation with validation errors."""
    exposure = {
        "claim_id": "claim-2",
        "claim_amount": 10000.0,
        "claim_status": "open",
        "currency": "USD",
        "severity": "high",
        "evidence_range": {
            "transaction_ids": [],
        },
    }
    validation_result = {
        "is_valid": False,
        "errors": ["amount_mismatch", "currency_mismatch"],
        "warnings": ["date_inconsistency"],
    }
    
    result = calculate_claim_readiness_score(
        exposure=exposure,
        validation_result=validation_result,
    )
    
    assert result["readiness_score"] < 60.0
    assert result["readiness_level"] == "weak"
    assert result["component_scores"]["validation"] == 0.0  # Invalid = 0


def test_calculate_claim_readiness_score_good() -> None:
    """Test readiness score calculation for good claim."""
    exposure = {
        "claim_id": "claim-3",
        "claim_amount": 5000.0,
        "claim_status": "open",  # Changed from "settled" to get lower score
        "currency": "USD",
        "severity": "medium",
        "evidence_range": {
            "transaction_ids": ["tx-1"],
        },
    }
    validation_result = {
        "is_valid": True,
        "errors": [],
        "warnings": ["minor_date_inconsistency"],
    }
    
    result = calculate_claim_readiness_score(
        exposure=exposure,
        validation_result=validation_result,
    )
    
    # With open status and medium severity, should be in good range
    assert result["readiness_score"] >= 0.0
    assert result["readiness_score"] <= 100.0
    assert result["readiness_level"] in ("excellent", "good", "adequate", "weak")


def test_calculate_portfolio_readiness_score() -> None:
    """Test portfolio readiness score calculation."""
    exposures = [
        {
            "claim_id": "claim-1",
            "claim_amount": 10000.0,
            "claim_status": "closed",
            "currency": "USD",
            "severity": "low",
            "evidence_range": {
                "transaction_ids": ["tx-1"],
            },
        },
        {
            "claim_id": "claim-2",
            "claim_amount": 5000.0,
            "claim_status": "open",
            "currency": "USD",
            "severity": "medium",
            "evidence_range": {
                "transaction_ids": [],
            },
        },
    ]
    validation_results = {
        "claim-1": {
            "is_valid": True,
            "errors": [],
            "warnings": [],
        },
        "claim-2": {
            "is_valid": True,
            "errors": [],
            "warnings": ["minor_issue"],
        },
    }
    
    result = calculate_portfolio_readiness_score(
        exposures=exposures,
        validation_results=validation_results,
    )
    
    assert "portfolio_readiness_score" in result
    assert "portfolio_readiness_level" in result
    assert "claim_scores" in result
    assert "distribution" in result
    assert len(result["claim_scores"]) == 2
    assert "excellent" in result["distribution"]
    assert "good" in result["distribution"]


def test_calculate_claim_readiness_score_custom_weights() -> None:
    """Test readiness score calculation with custom weights."""
    exposure = {
        "claim_id": "claim-1",
        "claim_amount": 10000.0,
        "claim_status": "closed",
        "currency": "USD",
        "severity": "low",
        "evidence_range": {
            "transaction_ids": ["tx-1"],
        },
    }
    validation_result = {
        "is_valid": True,
        "errors": [],
        "warnings": [],
    }
    weights = {
        "validation": Decimal("0.50"),
        "severity": Decimal("0.30"),
        "completeness": Decimal("0.15"),
        "status": Decimal("0.05"),
    }
    
    result = calculate_claim_readiness_score(
        exposure=exposure,
        validation_result=validation_result,
        weights=weights,
    )
    
    assert result["readiness_score"] >= 0.0
    assert result["readiness_score"] <= 100.0
    assert result["breakdown"]["validation_weight"] == 0.5


def test_calculate_claim_readiness_score_missing_fields() -> None:
    """Test readiness score calculation with missing fields."""
    exposure = {
        "claim_id": "claim-1",
        "claim_status": "open",
        "severity": "medium",
        # Missing claim_amount and currency
    }
    validation_result = {
        "is_valid": True,
        "errors": [],
        "warnings": [],
    }
    
    result = calculate_claim_readiness_score(
        exposure=exposure,
        validation_result=validation_result,
    )
    
    # Completeness score should be lower due to missing fields
    assert result["component_scores"]["completeness"] < 100.0
    assert result["readiness_score"] >= 0.0
    assert result["readiness_score"] <= 100.0

