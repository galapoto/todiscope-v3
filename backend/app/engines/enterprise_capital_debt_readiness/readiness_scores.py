"""
Readiness Scores Calculation

This module calculates composite readiness scores (0-100 scale) that integrate:
- Liquidity ratios (current ratio)
- Solvency (debt-to-equity)
- Debt service ability (DSCR, interest coverage)
- Market factors (external risk conditions)
- Cross-engine data (Financial Forensics, Deal Readiness)

Platform Law Compliance:
- Deterministic: Same inputs → same outputs
- Decimal arithmetic only
- All calculations bound to DatasetVersion
- Simple and interpretable for executive decision-making
"""

from __future__ import annotations

import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy.exc import SQLAlchemyError

from backend.app.engines.enterprise_capital_debt_readiness.credit_readiness import (
    assess_credit_risk_score,
    assess_debt_to_equity_category,
    assess_interest_coverage_category,
    assess_liquidity_category,
    calculate_current_ratio,
    calculate_debt_to_equity_ratio,
    calculate_interest_coverage_ratio,
)
from backend.app.engines.enterprise_capital_debt_readiness.models import (
    CapitalAdequacyAssessment,
    DebtServiceAssessment,
)
from backend.app.engines.enterprise_capital_debt_readiness.integration import (
    load_deal_readiness_insights,
    load_financial_forensics_insights,
)

logger = logging.getLogger(__name__)


class ReadinessScoreError(RuntimeError):
    """Base error for readiness score calculations"""
    pass


def _map_adequacy_level_to_score(level: str) -> Decimal:
    """
    Map adequacy/ability level to numeric score (0-100).
    
    Levels:
    - "strong": 85
    - "adequate": 70
    - "weak": 50
    - "insufficient_data": 30
    """
    mapping = {
        "strong": Decimal("85"),
        "adequate": Decimal("70"),
        "weak": Decimal("50"),
        "insufficient_data": Decimal("30"),
    }
    return mapping.get(level, Decimal("50"))


def _calculate_dscr_category(
    *,
    dscr: Decimal | None,
    min_dscr: Decimal = Decimal("1.25"),
) -> str | None:
    """
    Categorize DSCR into risk categories.
    
    Categories:
    - "excellent": DSCR >= min_dscr + 0.5
    - "good": DSCR >= min_dscr
    - "adequate": DSCR >= min_dscr - 0.25
    - "poor": DSCR < min_dscr - 0.25
    - None: DSCR is None
    """
    if dscr is None:
        return None
    
    excellent_threshold = min_dscr + Decimal("0.5")
    good_threshold = min_dscr
    adequate_threshold = min_dscr - Decimal("0.25")
    
    if dscr >= excellent_threshold:
        return "excellent"
    elif dscr >= good_threshold:
        return "good"
    elif dscr >= adequate_threshold:
        return "adequate"
    else:
        return "poor"


def calculate_composite_readiness_score(
    *,
    capital_adequacy: CapitalAdequacyAssessment,
    debt_service: DebtServiceAssessment,
    financial: dict[str, Any],
    assumptions: dict[str, Any],
    ff_leakage_exposure: Decimal | None = None,
    deal_readiness_score: Decimal | None = None,
    weights: dict[str, Decimal] | None = None,
) -> dict[str, Any]:
    """
    Calculate composite readiness score (0-100) integrating multiple factors.
    
    Components:
    1. Capital Adequacy Score (from capital adequacy assessment)
    2. Debt Service Score (from debt service assessment)
    3. Credit Risk Score (from credit readiness calculations)
    4. Financial Forensics Impact (optional, from FF-2 leakage exposure)
    5. Deal Readiness Impact (optional, from Engine #7)
    
    Args:
        capital_adequacy: Capital adequacy assessment results
        debt_service: Debt service ability assessment results
        financial: Financial data dictionary
        assumptions: Assumptions dictionary
        ff_leakage_exposure: Optional total leakage exposure from Financial Forensics Engine
        deal_readiness_score: Optional readiness score from Deal Readiness Engine
        weights: Optional weights for each component (defaults provided)
    
    Returns:
        Dictionary with:
        - readiness_score: Composite score (0-100)
        - readiness_level: Category (excellent/good/adequate/weak)
        - component_scores: Individual component scores
        - breakdown: Detailed breakdown of calculations
    """
    from decimal import Decimal
    
    # Default weights
    if weights is None:
        weights = {
            "capital_adequacy": Decimal("0.30"),
            "debt_service": Decimal("0.30"),
            "credit_risk": Decimal("0.25"),
            "financial_forensics": Decimal("0.10"),
            "deal_readiness": Decimal("0.05"),
        }
    
    # 1. Capital Adequacy Score
    capital_adequacy_score = _map_adequacy_level_to_score(capital_adequacy.adequacy_level)
    
    # 2. Debt Service Score
    debt_service_score = _map_adequacy_level_to_score(debt_service.ability_level)
    
    # 3. Credit Risk Score (using credit_readiness module)
    balance = financial.get("balance_sheet", {})
    income = financial.get("income_statement", {})
    debt_data = financial.get("debt", {})
    
    # Calculate debt-to-equity ratio and category
    # capital_adequacy.debt_to_equity_ratio is already the calculated ratio
    debt_to_equity_ratio = capital_adequacy.debt_to_equity_ratio
    
    debt_to_equity_category = "moderate_risk"
    if debt_to_equity_ratio is not None:
        debt_equity_thresholds = assumptions.get("credit_readiness", {}).get("debt_to_equity_thresholds", {})
        if not debt_equity_thresholds:
            debt_equity_thresholds = {
                "conservative": Decimal("0.5"),
                "high": Decimal("1.0"),
                "very_high": Decimal("2.0"),
            }
        else:
            debt_equity_thresholds = {
                k: Decimal(str(v)) for k, v in debt_equity_thresholds.items()
            }
        debt_to_equity_category = assess_debt_to_equity_category(
            debt_to_equity_ratio=debt_to_equity_ratio,
            thresholds=debt_equity_thresholds,
        )
    
    # Calculate interest coverage ratio and category
    ebitda = None
    if income.get("ebitda") is not None:
        ebitda = Decimal(str(income.get("ebitda")))
    
    interest_coverage_category = "adequate"
    if ebitda is not None and debt_service.interest_total is not None and debt_service.interest_total > 0:
        interest_coverage = calculate_interest_coverage_ratio(
            ebitda=ebitda,
            interest_expense=debt_service.interest_total,
        )
        if interest_coverage is not None:
            interest_coverage_thresholds = assumptions.get("credit_readiness", {}).get("interest_coverage_thresholds", {})
            if not interest_coverage_thresholds:
                interest_coverage_thresholds = {
                    "excellent": Decimal("5.0"),
                    "good": Decimal("2.0"),
                    "adequate": Decimal("1.5"),
                }
            else:
                interest_coverage_thresholds = {
                    k: Decimal(str(v)) for k, v in interest_coverage_thresholds.items()
                }
            interest_coverage_category = assess_interest_coverage_category(
                interest_coverage_ratio=interest_coverage,
                thresholds=interest_coverage_thresholds,
            )
    
    # Calculate liquidity category
    liquidity_category = "adequate"
    if capital_adequacy.current_ratio is not None:
        liquidity_thresholds = assumptions.get("credit_readiness", {}).get("liquidity_thresholds", {})
        if not liquidity_thresholds:
            liquidity_thresholds = {
                "strong": Decimal("2.0"),
                "adequate": Decimal("1.0"),
            }
        else:
            liquidity_thresholds = {
                k: Decimal(str(v)) for k, v in liquidity_thresholds.items()
            }
        liquidity_category = assess_liquidity_category(
            current_ratio=capital_adequacy.current_ratio,
            thresholds=liquidity_thresholds,
        )
    
    # Calculate DSCR category
    dscr_category = None
    if debt_service.dscr is not None:
        min_dscr = Decimal(str(assumptions.get("debt_service", {}).get("min_dscr", 1.25)))
        dscr_category = _calculate_dscr_category(
            dscr=debt_service.dscr,
            min_dscr=min_dscr,
        )
    
    # Calculate credit risk score
    credit_risk_weights = assumptions.get("credit_readiness", {}).get("credit_risk_weights", {})
    if credit_risk_weights:
        credit_risk_weights = {
            k: Decimal(str(v)) for k, v in credit_risk_weights.items()
        }
    else:
        credit_risk_weights = None
    
    credit_risk_result = assess_credit_risk_score(
        debt_to_equity_category=debt_to_equity_category,
        interest_coverage_category=interest_coverage_category,
        liquidity_category=liquidity_category,
        dscr_category=dscr_category,
        weights=credit_risk_weights,
    )
    credit_risk_score = Decimal(str(credit_risk_result["credit_risk_score"]))
    
    # 4. Financial Forensics Impact Score
    ff_impact_score = Decimal("75")  # Default neutral score
    if ff_leakage_exposure is not None:
        # Convert exposure to impact score
        # Higher exposure = lower score
        # Simple linear mapping: exposure / 1000000 = penalty points (max 30 points)
        exposure_millions = ff_leakage_exposure / Decimal("1000000")
        penalty = min(exposure_millions * Decimal("2"), Decimal("30"))  # Max 30 point penalty
        ff_impact_score = max(Decimal("45"), Decimal("75") - penalty)  # Floor at 45
    
    # 5. Deal Readiness Impact Score
    deal_readiness_impact_score = Decimal("75")  # Default neutral score
    if deal_readiness_score is not None:
        # Use deal readiness score directly (assuming it's 0-100)
        deal_readiness_impact_score = Decimal(str(deal_readiness_score))
    
    # Calculate weighted composite score
    composite_score = (
        capital_adequacy_score * weights["capital_adequacy"]
        + debt_service_score * weights["debt_service"]
        + credit_risk_score * weights["credit_risk"]
        + ff_impact_score * weights["financial_forensics"]
        + deal_readiness_impact_score * weights["deal_readiness"]
    )
    
    # Round to 2 decimal places
    composite_score = composite_score.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    # Determine readiness level
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
            "capital_adequacy": float(capital_adequacy_score),
            "debt_service": float(debt_service_score),
            "credit_risk": float(credit_risk_score),
            "financial_forensics": float(ff_impact_score),
            "deal_readiness": float(deal_readiness_impact_score) if deal_readiness_score is not None else None,
        },
        "credit_risk_details": credit_risk_result,
        "breakdown": {
            "capital_adequacy_level": capital_adequacy.adequacy_level,
            "debt_service_level": debt_service.ability_level,
            "credit_risk_level": credit_risk_result["risk_level"],
            "debt_to_equity_category": debt_to_equity_category,
            "interest_coverage_category": interest_coverage_category,
            "liquidity_category": liquidity_category,
            "dscr_category": dscr_category,
        },
    }


async def load_financial_forensics_data(
    db,
    *,
    dataset_version_id: str,
) -> dict[str, Any]:
    """
    Load Financial Forensics Engine data for the given DatasetVersion.
    
    Returns:
        Dictionary with:
        - total_leakage_exposure: Total exposure from leakage items
        - findings_count: Number of FF findings
        - has_data: Whether FF data exists
    """
    try:
        insights = await load_financial_forensics_insights(
            db,
            dataset_version_id=dataset_version_id,
        )
        if not insights:
            return {
                "total_leakage_exposure": None,
                "findings_count": 0,
                "has_data": False,
            }

        total_exposure_abs = insights.get("total_exposure_abs")
        total_exposure = Decimal(str(total_exposure_abs)) if total_exposure_abs is not None else None
        findings = insights.get("source_findings") or []
        has_data = bool(insights.get("items")) or bool(findings)

        return {
            "total_leakage_exposure": total_exposure,
            "findings_count": len(findings),
            "has_data": has_data,
        }
    except SQLAlchemyError as exc:
        logger.warning(
            "CAPDEBT_FF_DATA_LOAD_FAILED dataset_version_id=%s error=%s",
            dataset_version_id,
            exc,
        )
        return {
            "total_leakage_exposure": None,
            "findings_count": 0,
            "has_data": False,
        }


async def load_deal_readiness_data(
    db,
    *,
    dataset_version_id: str,
) -> dict[str, Any]:
    """
    Load Deal Readiness Engine (Engine #7) data for the given DatasetVersion.
    
    Returns:
        Dictionary with:
        - readiness_score: Composite readiness score derived from Deal Readiness findings
        - findings_count: Number of deal readiness findings
        - high_severity_count: Number of high severity findings
        - medium_severity_count: Number of medium severity findings
        - has_data: Whether deal readiness data exists
    """
    try:
        insights = await load_deal_readiness_insights(
            db,
            dataset_version_id=dataset_version_id,
        )
        if not insights:
            return {
                "readiness_score": None,
                "findings_count": 0,
                "high_severity_count": 0,
                "medium_severity_count": 0,
                "has_data": False,
            }

        findings = insights.get("findings") or []
        high_severity_count = sum(1 for f in findings if (f.get("severity") or "").lower() == "high")
        medium_severity_count = sum(1 for f in findings if (f.get("severity") or "").lower() == "medium")
        base_score = Decimal("80")
        penalty = (Decimal(str(high_severity_count)) * Decimal("5")) + (
            Decimal(str(medium_severity_count)) * Decimal("2")
        )
        readiness_score = max(Decimal("30"), base_score - penalty)

        return {
            "readiness_score": readiness_score,
            "findings_count": len(findings),
            "high_severity_count": high_severity_count,
            "medium_severity_count": medium_severity_count,
            "has_data": bool(findings),
        }
    except SQLAlchemyError as exc:
        logger.warning(
            "CAPDEBT_DEAL_READINESS_DATA_LOAD_FAILED dataset_version_id=%s error=%s",
            dataset_version_id,
            exc,
        )
        return {
            "readiness_score": None,
            "findings_count": 0,
            "high_severity_count": 0,
            "medium_severity_count": 0,
            "has_data": False,
        }
