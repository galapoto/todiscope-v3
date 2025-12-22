"""Readiness Scores Calculation for Enterprise Insurance Claim Forensics Engine.

This module calculates composite readiness scores (0-100 scale) that integrate:
- Validation pass rate (data quality)
- Exposure severity distribution
- Claim status distribution
- Data completeness

Platform Law Compliance:
- Deterministic: Same inputs → same outputs
- Decimal arithmetic only
- All calculations bound to DatasetVersion
- Simple and interpretable for executive decision-making
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any


def _map_severity_to_score(severity: str) -> Decimal:
    """Map exposure severity to a score component (0-100)."""
    mapping = {
        "low": Decimal("85"),
        "medium": Decimal("70"),
        "high": Decimal("50"),
    }
    return mapping.get(severity.lower(), Decimal("50"))


def _map_status_to_score(status: str) -> Decimal:
    """Map claim status to a score component (0-100)."""
    # Closed/settled claims are better than open/pending
    closed_statuses = {"closed", "settled", "paid", "approved", "resolved"}
    open_statuses = {"open", "pending", "escalated", "under_review"}
    
    status_lower = status.lower()
    if status_lower in closed_statuses:
        return Decimal("90")
    elif status_lower in open_statuses:
        return Decimal("60")
    else:
        return Decimal("70")  # Unknown status


def _calculate_validation_score(validation_result: dict[str, Any]) -> Decimal:
    """Calculate validation score component (0-100) based on validation result."""
    if validation_result.get("is_valid", False):
        errors = len(validation_result.get("errors", []))
        warnings = len(validation_result.get("warnings", []))
        
        # Perfect validation = 100
        # Each error = -20 points
        # Each warning = -5 points
        score = Decimal("100") - (Decimal(str(errors)) * Decimal("20")) - (Decimal(str(warnings)) * Decimal("5"))
        return max(Decimal("0"), min(Decimal("100"), score))
    else:
        # Invalid claims get 0
        return Decimal("0")


def _calculate_completeness_score(exposure: dict[str, Any]) -> Decimal:
    """Calculate data completeness score (0-100) based on exposure data."""
    # Check for required fields presence
    required_fields = ["claim_id", "claim_amount", "claim_status", "currency"]
    present_fields = sum(1 for field in required_fields if exposure.get(field) is not None)
    
    # Base completeness from required fields
    base_score = (Decimal(str(present_fields)) / Decimal(str(len(required_fields)))) * Decimal("100")
    
    # Bonus for having transactions
    has_transactions = len(exposure.get("evidence_range", {}).get("transaction_ids", [])) > 0
    if has_transactions:
        base_score = min(Decimal("100"), base_score + Decimal("10"))
    
    return base_score


def calculate_claim_readiness_score(
    *,
    exposure: dict[str, Any],
    validation_result: dict[str, Any],
    weights: dict[str, Decimal] | None = None,
) -> dict[str, Any]:
    """
    Calculate composite readiness score (0-100) for a single claim.
    
    Components:
    1. Validation Score (40%): Based on validation pass/fail and errors/warnings
    2. Exposure Severity Score (30%): Based on exposure severity (low/medium/high)
    3. Completeness Score (20%): Based on data completeness
    4. Status Score (10%): Based on claim status
    
    Args:
        exposure: Exposure dictionary from model_loss_exposure()
        validation_result: Validation result dictionary
        weights: Optional weights for each component (defaults provided)
    
    Returns:
        Dictionary with:
        - readiness_score: Composite score (0-100)
        - readiness_level: Category (excellent/good/adequate/weak)
        - component_scores: Individual component scores
        - breakdown: Detailed breakdown of calculations
    """
    # Default weights
    if weights is None:
        weights = {
            "validation": Decimal("0.40"),
            "severity": Decimal("0.30"),
            "completeness": Decimal("0.20"),
            "status": Decimal("0.10"),
        }
    
    # Calculate component scores
    validation_score = _calculate_validation_score(validation_result)
    severity_score = _map_severity_to_score(exposure.get("severity", "medium"))
    completeness_score = _calculate_completeness_score(exposure)
    status_score = _map_status_to_score(exposure.get("claim_status", "unknown"))
    
    # Calculate weighted composite score
    composite_score = (
        validation_score * weights["validation"]
        + severity_score * weights["severity"]
        + completeness_score * weights["completeness"]
        + status_score * weights["status"]
    )
    
    # Round to 2 decimal places
    composite_score = composite_score.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    # Map to readiness level
    if composite_score >= Decimal("80"):
        readiness_level = "excellent"
    elif composite_score >= Decimal("70"):
        readiness_level = "good"
    elif composite_score >= Decimal("60"):
        readiness_level = "adequate"
    else:
        readiness_level = "weak"
    
    return {
        "readiness_score": float(composite_score),
        "readiness_level": readiness_level,
        "component_scores": {
            "validation": float(validation_score),
            "severity": float(severity_score),
            "completeness": float(completeness_score),
            "status": float(status_score),
        },
        "breakdown": {
            "validation_weight": float(weights["validation"]),
            "severity_weight": float(weights["severity"]),
            "completeness_weight": float(weights["completeness"]),
            "status_weight": float(weights["status"]),
        },
    }


def calculate_portfolio_readiness_score(
    *,
    exposures: list[dict[str, Any]],
    validation_results: dict[str, dict[str, Any]],
    weights: dict[str, Decimal] | None = None,
) -> dict[str, Any]:
    """
    Calculate aggregate readiness score for the entire claim portfolio.
    
    Args:
        exposures: List of exposure dictionaries
        validation_results: Dictionary mapping claim_id to validation results
        weights: Optional weights for individual claim scoring
    
    Returns:
        Dictionary with:
        - portfolio_readiness_score: Average readiness score across all claims
        - portfolio_readiness_level: Overall portfolio level
        - claim_scores: Dictionary mapping claim_id to individual scores
        - distribution: Distribution of readiness levels
    """
    claim_scores: dict[str, dict[str, Any]] = {}
    total_score = Decimal("0")
    level_counts: dict[str, int] = {"excellent": 0, "good": 0, "adequate": 0, "weak": 0}
    
    for exposure in exposures:
        claim_id = exposure.get("claim_id")
        if not claim_id:
            continue
        
        validation_result = validation_results.get(claim_id, {})
        score_result = calculate_claim_readiness_score(
            exposure=exposure,
            validation_result=validation_result,
            weights=weights,
        )
        
        claim_scores[claim_id] = score_result
        total_score += Decimal(str(score_result["readiness_score"]))
        level_counts[score_result["readiness_level"]] += 1
    
    # Calculate average
    claim_count = len(claim_scores)
    if claim_count > 0:
        portfolio_score = (total_score / Decimal(str(claim_count))).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    else:
        portfolio_score = Decimal("0")
    
    # Map to portfolio level
    if portfolio_score >= Decimal("80"):
        portfolio_level = "excellent"
    elif portfolio_score >= Decimal("70"):
        portfolio_level = "good"
    elif portfolio_score >= Decimal("60"):
        portfolio_level = "adequate"
    else:
        portfolio_level = "weak"
    
    return {
        "portfolio_readiness_score": float(portfolio_score),
        "portfolio_readiness_level": portfolio_level,
        "claim_scores": claim_scores,
        "distribution": {
            "excellent": level_counts["excellent"],
            "good": level_counts["good"],
            "adequate": level_counts["adequate"],
            "weak": level_counts["weak"],
        },
    }


