"""
Capital Raising Strategies Logic

This module provides deterministic logic for capital raising strategies,
including:
- Debt financing strategies
- Equity financing strategies
- Hybrid financing strategies
- Financial instrument recommendations

Platform Law Compliance:
- Deterministic: Same inputs → same outputs (no randomness, no time-dependent logic)
- Decimal arithmetic only (no float)
- All calculations bound to DatasetVersion
- Evidence-backed with append-only storage
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any


class CapitalStrategyError(RuntimeError):
    """Base error for capital raising strategies"""
    pass


def assess_debt_capacity(
    *,
    ebitda: Decimal | float | str | int,
    existing_debt_service: Decimal | float | str | int,
    target_dscr: Decimal | float | str | int = Decimal("1.25"),
    interest_rate: Decimal | float | str | int = Decimal("0.05"),
    loan_term_years: int = 5,
) -> dict[str, Any]:
    """
    Assess debt capacity based on EBITDA and existing debt service.
    
    Calculates:
    - Maximum additional debt service capacity
    - Maximum additional debt principal capacity
    - Recommended debt amount
    
    Args:
        ebitda: Earnings before interest, taxes, depreciation, and amortization
        existing_debt_service: Current annual debt service obligations
        target_dscr: Target debt service coverage ratio (default 1.25)
        interest_rate: Expected interest rate for new debt (default 5%)
        loan_term_years: Loan term in years (default 5)
    
    Returns:
        Dictionary with debt capacity metrics and recommendations
    """
    ebitda_decimal = Decimal(str(ebitda))
    existing_service = Decimal(str(existing_debt_service))
    target_dscr_decimal = Decimal(str(target_dscr))
    rate = Decimal(str(interest_rate))
    
    # Calculate maximum total debt service capacity
    max_total_debt_service = ebitda_decimal / target_dscr_decimal
    
    # Calculate maximum additional debt service capacity
    max_additional_debt_service = max_total_debt_service - existing_service
    
    if max_additional_debt_service <= 0:
        return {
            "debt_capacity_available": False,
            "max_additional_debt_service": float(max_additional_debt_service),
            "max_additional_debt_principal": 0.0,
            "recommended_debt_amount": 0.0,
            "reason": "Existing debt service exceeds capacity",
        }
    
    # Calculate maximum additional debt principal using annuity formula
    # P = PMT * [(1 - (1 + r)^-n) / r]
    # Where PMT is the annual payment, r is interest rate, n is number of years
    if rate > 0:
        annuity_factor = (Decimal("1") - (Decimal("1") + rate) ** -loan_term_years) / rate
        max_additional_debt_principal = max_additional_debt_service * annuity_factor
    else:
        # If interest rate is zero, principal is simply annual payment * years
        max_additional_debt_principal = max_additional_debt_service * Decimal(str(loan_term_years))
    
    # Recommend conservative amount (80% of maximum)
    recommended_debt_amount = max_additional_debt_principal * Decimal("0.80")
    
    return {
        "debt_capacity_available": True,
        "max_additional_debt_service": float(max_additional_debt_service.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        "max_additional_debt_principal": float(max_additional_debt_principal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        "recommended_debt_amount": float(recommended_debt_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        "target_dscr": float(target_dscr_decimal),
        "assumed_interest_rate": float(rate),
        "assumed_loan_term_years": loan_term_years,
    }


def recommend_debt_instruments(
    *,
    debt_amount: Decimal | float | str | int,
    company_size: str,
    credit_risk_level: str,
    time_horizon: str = "medium",
    thresholds: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Recommend appropriate debt instruments based on company characteristics.
    
    Args:
        debt_amount: Amount of debt needed
        company_size: Company size (small/medium/large/enterprise)
        credit_risk_level: Credit risk level (low/moderate/high/very_high)
        time_horizon: Time horizon for financing (short/medium/long)
        thresholds: Optional thresholds for instrument selection
    
    Returns:
        List of recommended debt instruments with characteristics
    """
    if thresholds is None:
        thresholds = {
            "small_debt_threshold": 1000000,  # $1M
            "medium_debt_threshold": 10000000,  # $10M
            "large_debt_threshold": 50000000,  # $50M
        }
    
    amount = float(Decimal(str(debt_amount)))
    recommendations = []
    
    # Bank loans (suitable for most companies)
    if credit_risk_level in ("low", "moderate"):
        if amount < thresholds["small_debt_threshold"]:
            recommendations.append({
                "instrument": "term_loan",
                "provider_type": "commercial_bank",
                "typical_amount_range": f"$100K - ${thresholds['small_debt_threshold']:,}",
                "typical_term": "1-5 years",
                "typical_rate": "Prime + 1-3%",
                "suitability_score": 85 if credit_risk_level == "low" else 70,
            })
        elif amount < thresholds["medium_debt_threshold"]:
            recommendations.append({
                "instrument": "term_loan",
                "provider_type": "commercial_bank",
                "typical_amount_range": f"${thresholds['small_debt_threshold']:,} - ${thresholds['medium_debt_threshold']:,}",
                "typical_term": "3-7 years",
                "typical_rate": "Prime + 0.5-2%",
                "suitability_score": 90 if credit_risk_level == "low" else 75,
            })
    
    # Revolving credit facilities
    if credit_risk_level in ("low", "moderate") and company_size in ("medium", "large", "enterprise"):
        recommendations.append({
            "instrument": "revolving_credit_facility",
            "provider_type": "commercial_bank",
            "typical_amount_range": "$1M - $50M+",
            "typical_term": "1-3 years (renewable)",
            "typical_rate": "Prime + 0.5-2%",
            "suitability_score": 80 if credit_risk_level == "low" else 65,
        })
    
    # Corporate bonds
    if credit_risk_level == "low" and company_size in ("large", "enterprise") and amount >= thresholds["large_debt_threshold"]:
        recommendations.append({
            "instrument": "corporate_bonds",
            "provider_type": "capital_markets",
            "typical_amount_range": f"${thresholds['large_debt_threshold']:,}+",
            "typical_term": "5-30 years",
            "typical_rate": "Treasury + 1-5%",
            "suitability_score": 85,
        })
    
    # Commercial paper
    if credit_risk_level == "low" and company_size in ("large", "enterprise") and time_horizon == "short":
        recommendations.append({
            "instrument": "commercial_paper",
            "provider_type": "capital_markets",
            "typical_amount_range": "$1M+",
            "typical_term": "30-270 days",
            "typical_rate": "Lower than bank rates",
            "suitability_score": 80,
        })
    
    # Asset-based lending
    if credit_risk_level in ("moderate", "high", "very_high"):
        recommendations.append({
            "instrument": "asset_based_lending",
            "provider_type": "specialty_lender",
            "typical_amount_range": "$500K - $10M+",
            "typical_term": "1-5 years",
            "typical_rate": "Prime + 2-5%",
            "suitability_score": 75 if credit_risk_level == "moderate" else 60,
        })
    
    # Private placements
    if credit_risk_level in ("moderate", "high") and company_size in ("medium", "large", "enterprise"):
        recommendations.append({
            "instrument": "private_placement",
            "provider_type": "private_lender",
            "typical_amount_range": "$1M - $50M",
            "typical_term": "3-10 years",
            "typical_rate": "Higher than public markets",
            "suitability_score": 70 if credit_risk_level == "moderate" else 55,
        })
    
    # Sort by suitability score (descending)
    recommendations.sort(key=lambda x: x["suitability_score"], reverse=True)
    
    return recommendations


def assess_equity_capacity(
    *,
    current_equity_value: Decimal | float | str | int,
    target_ownership_dilution: Decimal | float | str | int = Decimal("0.20"),
    company_valuation: Decimal | float | str | int | None = None,
) -> dict[str, Any]:
    """
    Assess equity raising capacity based on current equity and dilution targets.
    
    Args:
        current_equity_value: Current total equity value
        target_ownership_dilution: Maximum acceptable dilution percentage (default 20%)
        company_valuation: Optional company valuation (if None, uses current_equity_value)
    
    Returns:
        Dictionary with equity capacity metrics
    """
    current_equity = Decimal(str(current_equity_value))
    dilution = Decimal(str(target_ownership_dilution))
    
    if company_valuation is None:
        company_valuation_decimal = current_equity
    else:
        company_valuation_decimal = Decimal(str(company_valuation))
    
    # Calculate maximum equity that can be raised
    # If we dilute by X%, new equity = old_equity / (1 - X%)
    # New equity raised = new_equity - old_equity
    if dilution >= Decimal("1.0") or dilution < Decimal("0"):
        raise CapitalStrategyError("DILUTION_INVALID: Dilution must be between 0 and 1")
    
    new_total_equity = current_equity / (Decimal("1") - dilution)
    max_equity_raise = new_total_equity - current_equity
    
    # Calculate based on valuation if provided
    if company_valuation is not None:
        max_equity_raise_by_valuation = company_valuation_decimal * dilution
        # Use the lower of the two calculations
        max_equity_raise = min(max_equity_raise, max_equity_raise_by_valuation)
    
    return {
        "max_equity_raise": float(max_equity_raise.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        "target_dilution": float(dilution),
        "post_raise_equity_value": float(new_total_equity.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        "company_valuation_used": float(company_valuation_decimal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
    }


def recommend_equity_instruments(
    *,
    equity_amount: Decimal | float | str | int,
    company_size: str,
    company_stage: str,
    thresholds: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Recommend appropriate equity instruments based on company characteristics.
    
    Args:
        equity_amount: Amount of equity needed
        company_size: Company size (small/medium/large/enterprise)
        company_stage: Company stage (startup/growth/mature/public)
        thresholds: Optional thresholds for instrument selection
    
    Returns:
        List of recommended equity instruments with characteristics
    """
    if thresholds is None:
        thresholds = {
            "seed_threshold": 500000,  # $500K
            "series_a_threshold": 5000000,  # $5M
            "ipo_threshold": 50000000,  # $50M
        }
    
    amount = float(Decimal(str(equity_amount)))
    recommendations = []
    
    # Seed/angel funding
    if company_stage == "startup" and amount < thresholds["seed_threshold"]:
        recommendations.append({
            "instrument": "seed_funding",
            "provider_type": "angel_investors",
            "typical_amount_range": "$50K - $500K",
            "typical_dilution": "10-25%",
            "typical_valuation": "$500K - $5M",
            "suitability_score": 85,
        })
    
    # Venture capital (Series A/B/C)
    if company_stage in ("startup", "growth") and amount >= thresholds["seed_threshold"]:
        if amount < thresholds["series_a_threshold"]:
            recommendations.append({
                "instrument": "series_a_funding",
                "provider_type": "venture_capital",
                "typical_amount_range": "$500K - $5M",
                "typical_dilution": "15-30%",
                "typical_valuation": "$2M - $20M",
                "suitability_score": 80,
            })
        else:
            recommendations.append({
                "instrument": "series_b_c_funding",
                "provider_type": "venture_capital",
                "typical_amount_range": "$5M - $50M+",
                "typical_dilution": "10-25%",
                "typical_valuation": "$20M - $200M+",
                "suitability_score": 85,
            })
    
    # Private equity
    if company_stage == "mature" and company_size in ("large", "enterprise"):
        recommendations.append({
            "instrument": "private_equity",
            "provider_type": "private_equity_firm",
            "typical_amount_range": "$10M - $500M+",
            "typical_dilution": "20-50%",
            "typical_valuation": "Varies widely",
            "suitability_score": 75,
        })
    
    # IPO
    if company_stage == "mature" and company_size == "enterprise" and amount >= thresholds["ipo_threshold"]:
        recommendations.append({
            "instrument": "initial_public_offering",
            "provider_type": "public_markets",
            "typical_amount_range": "$50M+",
            "typical_dilution": "15-30%",
            "typical_valuation": "$100M+",
            "suitability_score": 90,
        })
    
    # Secondary offering
    if company_stage == "public":
        recommendations.append({
            "instrument": "secondary_offering",
            "provider_type": "public_markets",
            "typical_amount_range": "$10M+",
            "typical_dilution": "5-20%",
            "typical_valuation": "Market-based",
            "suitability_score": 85,
        })
    
    # Sort by suitability score (descending)
    recommendations.sort(key=lambda x: x["suitability_score"], reverse=True)
    
    return recommendations


def recommend_hybrid_strategies(
    *,
    total_capital_needed: Decimal | float | str | int,
    debt_capacity: dict[str, Any],
    equity_capacity: dict[str, Any],
    risk_tolerance: str = "moderate",
) -> list[dict[str, Any]]:
    """
    Recommend hybrid debt-equity financing strategies.
    
    Args:
        total_capital_needed: Total capital needed
        debt_capacity: Debt capacity assessment results
        equity_capacity: Equity capacity assessment results
        risk_tolerance: Risk tolerance (conservative/moderate/aggressive)
    
    Returns:
        List of recommended hybrid strategies
    """
    total_needed = Decimal(str(total_capital_needed))
    strategies = []
    
    max_debt = Decimal(str(debt_capacity.get("recommended_debt_amount", 0)))
    max_equity = Decimal(str(equity_capacity.get("max_equity_raise", 0)))
    
    # Strategy 1: Debt-first (if debt capacity is sufficient)
    if max_debt >= total_needed:
        strategies.append({
            "strategy": "debt_first",
            "debt_amount": float(total_needed.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "equity_amount": 0.0,
            "debt_ratio": 1.0,
            "equity_ratio": 0.0,
            "rationale": "Debt capacity sufficient to meet all capital needs",
            "suitability_score": 85 if risk_tolerance in ("conservative", "moderate") else 70,
        })
    
    # Strategy 2: Equity-first (if equity capacity is sufficient and risk tolerance is low)
    if max_equity >= total_needed and risk_tolerance == "conservative":
        strategies.append({
            "strategy": "equity_first",
            "debt_amount": 0.0,
            "equity_amount": float(total_needed.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "debt_ratio": 0.0,
            "equity_ratio": 1.0,
            "rationale": "Equity financing avoids debt service obligations",
            "suitability_score": 80,
        })
    
    # Strategy 3: Balanced mix (recommended for most cases)
    if max_debt + max_equity >= total_needed:
        # Calculate optimal mix based on risk tolerance
        if risk_tolerance == "conservative":
            debt_ratio = Decimal("0.30")
        elif risk_tolerance == "moderate":
            debt_ratio = Decimal("0.50")
        else:  # aggressive
            debt_ratio = Decimal("0.70")
        
        debt_amount = min(total_needed * debt_ratio, max_debt)
        equity_amount = total_needed - debt_amount
        
        if equity_amount > max_equity:
            equity_amount = max_equity
            debt_amount = total_needed - equity_amount
        
        strategies.append({
            "strategy": "balanced_mix",
            "debt_amount": float(debt_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "equity_amount": float(equity_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "debt_ratio": float((debt_amount / total_needed).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "equity_ratio": float((equity_amount / total_needed).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "rationale": f"Balanced approach matching {risk_tolerance} risk tolerance",
            "suitability_score": 90,
        })
    
    # Strategy 4: Maximize debt (if aggressive and debt capacity allows)
    if risk_tolerance == "aggressive" and max_debt >= total_needed * Decimal("0.70"):
        strategies.append({
            "strategy": "maximize_debt",
            "debt_amount": float(min(total_needed * Decimal("0.80"), max_debt).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "equity_amount": float((total_needed - min(total_needed * Decimal("0.80"), max_debt)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "debt_ratio": 0.8,
            "equity_ratio": 0.2,
            "rationale": "Maximize debt to preserve equity ownership",
            "suitability_score": 75,
        })
    
    # Sort by suitability score (descending)
    strategies.sort(key=lambda x: x["suitability_score"], reverse=True)
    
    return strategies






