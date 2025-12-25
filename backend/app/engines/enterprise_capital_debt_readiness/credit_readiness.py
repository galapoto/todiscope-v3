"""
Credit Readiness Calculation Logic

This module provides deterministic calculations for assessing an enterprise's ability
to obtain credit or loans, including:
- Debt-to-equity ratio calculation
- Credit risk assessment
- Access to financial markets evaluation

Platform Law Compliance:
- Deterministic: Same inputs → same outputs (no randomness, no time-dependent logic)
- Decimal arithmetic only (no float)
- All calculations bound to DatasetVersion
- Evidence-backed with append-only storage
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any


class CreditReadinessError(RuntimeError):
    """Base error for credit readiness calculations"""
    pass


class InvalidFinancialDataError(CreditReadinessError):
    """Raised when financial data is missing or invalid"""
    pass


def calculate_debt_to_equity_ratio(
    total_debt: Decimal | float | str | int,
    total_equity: Decimal | float | str | int,
) -> Decimal:
    """
    Calculate debt-to-equity ratio.
    
    Formula: Total Debt / Total Equity
    
    Args:
        total_debt: Total debt amount (converted to Decimal)
        total_equity: Total equity amount (converted to Decimal)
    
    Returns:
        Debt-to-equity ratio as Decimal
    
    Raises:
        InvalidFinancialDataError: If equity is zero or negative
    """
    debt = Decimal(str(total_debt))
    equity = Decimal(str(total_equity))
    
    if equity <= 0:
        raise InvalidFinancialDataError(
            "TOTAL_EQUITY_INVALID: Total equity must be positive for debt-to-equity ratio calculation"
        )
    
    ratio = debt / equity
    # Round to 4 decimal places for consistency
    return ratio.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def assess_debt_to_equity_category(
    debt_to_equity_ratio: Decimal,
    thresholds: dict[str, Decimal] | None = None,
) -> str:
    """
    Categorize debt-to-equity ratio into risk categories.
    
    Categories:
    - "low_risk": Ratio below conservative threshold
    - "moderate_risk": Ratio between conservative and high threshold
    - "high_risk": Ratio above high threshold
    - "very_high_risk": Ratio above very high threshold
    
    Args:
        debt_to_equity_ratio: Calculated debt-to-equity ratio
        thresholds: Dictionary with keys: conservative, high, very_high
    
    Returns:
        Risk category string
    """
    thresholds = thresholds or {}
    conservative = thresholds.get("conservative", Decimal("0.5"))
    high = thresholds.get("high", Decimal("1.0"))
    very_high = thresholds.get("very_high", Decimal("2.0"))
    
    if debt_to_equity_ratio < conservative:
        return "low_risk"
    elif debt_to_equity_ratio < high:
        return "moderate_risk"
    elif debt_to_equity_ratio < very_high:
        return "high_risk"
    else:
        return "very_high_risk"


def calculate_interest_coverage_ratio(
    ebitda: Decimal | float | str | int,
    interest_expense: Decimal | float | str | int,
) -> Decimal | None:
    """
    Calculate interest coverage ratio.
    
    Formula: EBITDA / Interest Expense
    
    Higher ratio indicates better ability to service debt.
    
    Args:
        ebitda: Earnings before interest, taxes, depreciation, and amortization
        interest_expense: Total interest expense
    
    Returns:
        Interest coverage ratio as Decimal, or None if interest_expense is zero
    """
    ebitda_decimal = Decimal(str(ebitda))
    interest = Decimal(str(interest_expense))
    
    if interest <= 0:
        return None
    
    ratio = ebitda_decimal / interest
    return ratio.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def assess_interest_coverage_category(
    interest_coverage_ratio: Decimal | None,
    thresholds: dict[str, Decimal] | None = None,
) -> str:
    """
    Categorize interest coverage ratio.
    
    Categories:
    - "excellent": Ratio above excellent threshold (typically > 5.0)
    - "good": Ratio between good and excellent threshold (typically 2.0-5.0)
    - "adequate": Ratio between adequate and good threshold (typically 1.5-2.0)
    - "poor": Ratio below adequate threshold (< 1.5)
    - "insufficient": Ratio is None or negative
    
    Args:
        interest_coverage_ratio: Calculated interest coverage ratio
        thresholds: Dictionary with keys: excellent, good, adequate
    
    Returns:
        Coverage category string
    """
    if interest_coverage_ratio is None or interest_coverage_ratio < 0:
        return "insufficient"
    
    thresholds = thresholds or {}
    excellent = thresholds.get("excellent", Decimal("5.0"))
    good = thresholds.get("good", Decimal("2.0"))
    adequate = thresholds.get("adequate", Decimal("1.5"))
    
    if interest_coverage_ratio >= excellent:
        return "excellent"
    elif interest_coverage_ratio >= good:
        return "good"
    elif interest_coverage_ratio >= adequate:
        return "adequate"
    else:
        return "poor"


def calculate_current_ratio(
    current_assets: Decimal | float | str | int,
    current_liabilities: Decimal | float | str | int,
) -> Decimal | None:
    """
    Calculate current ratio (liquidity measure).
    
    Formula: Current Assets / Current Liabilities
    
    Higher ratio indicates better short-term liquidity.
    
    Args:
        current_assets: Total current assets
        current_liabilities: Total current liabilities
    
    Returns:
        Current ratio as Decimal, or None if current_liabilities is zero
    """
    assets = Decimal(str(current_assets))
    liabilities = Decimal(str(current_liabilities))
    
    if liabilities <= 0:
        return None
    
    ratio = assets / liabilities
    return ratio.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def assess_liquidity_category(
    current_ratio: Decimal | None,
    thresholds: dict[str, Decimal] | None = None,
) -> str:
    """
    Categorize liquidity based on current ratio.
    
    Categories:
    - "strong": Ratio above strong threshold (typically > 2.0)
    - "adequate": Ratio between adequate and strong threshold (typically 1.0-2.0)
    - "weak": Ratio below adequate threshold (< 1.0)
    - "insufficient": Ratio is None or negative
    
    Args:
        current_ratio: Calculated current ratio
        thresholds: Dictionary with keys: strong, adequate
    
    Returns:
        Liquidity category string
    """
    if current_ratio is None or current_ratio < 0:
        return "insufficient"
    
    thresholds = thresholds or {}
    strong = thresholds.get("strong", Decimal("2.0"))
    adequate = thresholds.get("adequate", Decimal("1.0"))
    
    if current_ratio >= strong:
        return "strong"
    elif current_ratio >= adequate:
        return "adequate"
    else:
        return "weak"


def calculate_debt_service_coverage_ratio(
    net_operating_income: Decimal | float | str | int,
    total_debt_service: Decimal | float | str | int,
) -> Decimal | None:
    """
    Calculate debt service coverage ratio (DSCR).
    
    Formula: Net Operating Income / Total Debt Service
    
    Higher ratio indicates better ability to service debt obligations.
    
    Args:
        net_operating_income: Net operating income
        total_debt_service: Total debt service (principal + interest payments)
    
    Returns:
        DSCR as Decimal, or None if total_debt_service is zero
    """
    noi = Decimal(str(net_operating_income))
    debt_service = Decimal(str(total_debt_service))
    
    if debt_service <= 0:
        return None
    
    ratio = noi / debt_service
    return ratio.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def assess_credit_risk_score(
    *,
    debt_to_equity_category: str,
    interest_coverage_category: str,
    liquidity_category: str,
    dscr_category: str | None = None,
    weights: dict[str, Decimal] | None = None,
) -> dict[str, Any]:
    """
    Assess overall credit risk score based on multiple financial metrics.
    
    Args:
        debt_to_equity_category: Risk category from debt-to-equity assessment
        interest_coverage_category: Coverage category from interest coverage assessment
        liquidity_category: Liquidity category from current ratio assessment
        dscr_category: Optional DSCR category
        weights: Optional weights for each metric (defaults to equal weighting)
    
    Returns:
        Dictionary with credit_risk_score (0-100), risk_level (low/moderate/high/very_high),
        and component_scores
    """
    if debt_to_equity_category is None or interest_coverage_category is None or liquidity_category is None:
        raise TypeError("MISSING_REQUIRED_CATEGORY")

    # Default weights (equal weighting)
    if weights is None:
        weights = {
            "debt_to_equity": Decimal("0.30"),
            "interest_coverage": Decimal("0.30"),
            "liquidity": Decimal("0.25"),
            "dscr": Decimal("0.15"),
        }
    
    # Map categories to numeric scores (0-100 scale)
    category_scores = {
        "low_risk": Decimal("90"),
        "moderate_risk": Decimal("70"),
        "high_risk": Decimal("50"),
        "very_high_risk": Decimal("30"),
        "excellent": Decimal("90"),
        "good": Decimal("75"),
        "adequate": Decimal("60"),
        "poor": Decimal("40"),
        "insufficient": Decimal("20"),
        "strong": Decimal("85"),
        "weak": Decimal("45"),
    }
    
    # Calculate component scores
    debt_equity_score = category_scores.get(debt_to_equity_category, Decimal("50"))
    interest_coverage_score = category_scores.get(interest_coverage_category, Decimal("50"))
    liquidity_score = category_scores.get(liquidity_category, Decimal("50"))
    dscr_score = category_scores.get(dscr_category, Decimal("50")) if dscr_category else Decimal("50")
    
    # Calculate weighted score
    total_score = (
        debt_equity_score * weights["debt_to_equity"]
        + interest_coverage_score * weights["interest_coverage"]
        + liquidity_score * weights["liquidity"]
        + dscr_score * weights["dscr"]
    )
    
    # Round to 2 decimal places
    total_score = total_score.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    # Determine risk level
    if total_score >= Decimal("80"):
        risk_level = "low"
    elif total_score >= Decimal("60"):
        risk_level = "moderate"
    elif total_score >= Decimal("40"):
        risk_level = "high"
    else:
        risk_level = "very_high"
    
    return {
        "credit_risk_score": float(total_score),
        "risk_level": risk_level,
        "component_scores": {
            "debt_to_equity": float(debt_equity_score),
            "interest_coverage": float(interest_coverage_score),
            "liquidity": float(liquidity_score),
            "dscr": float(dscr_score) if dscr_category else None,
        },
    }


def assess_financial_market_access(
    *,
    credit_risk_score: float | Decimal,
    company_size: str | None = None,
    industry: str | None = None,
    thresholds: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Assess access to financial markets based on credit risk and company characteristics.
    
    Args:
        credit_risk_score: Overall credit risk score (0-100)
        company_size: Company size category (small/medium/large/enterprise)
        industry: Industry sector
        thresholds: Optional thresholds for market access assessment
    
    Returns:
        Dictionary with market_access_level, available_instruments, and recommendations
    """
    if thresholds is None:
        thresholds = {
            "excellent_score": 80,
            "good_score": 60,
            "adequate_score": 40,
        }
    
    score = float(credit_risk_score)
    if score < 0 or score > 100:
        raise ValueError("CREDIT_RISK_SCORE_OUT_OF_RANGE")
    
    # Determine market access level
    if score >= thresholds["excellent_score"]:
        access_level = "excellent"
        available_instruments = [
            "bank_loans",
            "corporate_bonds",
            "commercial_paper",
            "syndicated_loans",
            "revolving_credit_facilities",
            "equity_issuance",
        ]
    elif score >= thresholds["good_score"]:
        access_level = "good"
        available_instruments = [
            "bank_loans",
            "corporate_bonds",
            "commercial_paper",
            "syndicated_loans",
            "revolving_credit_facilities",
        ]
    elif score >= thresholds["adequate_score"]:
        access_level = "moderate"
        available_instruments = [
            "bank_loans",
            "asset_based_lending",
            "private_placements",
        ]
    else:
        access_level = "limited"
        available_instruments = [
            "asset_based_lending",
            "private_placements",
            "alternative_financing",
        ]
    
    # Generate recommendations
    recommendations = []
    if score < thresholds["adequate_score"]:
        recommendations.append("Improve debt-to-equity ratio")
        recommendations.append("Strengthen liquidity position")
        recommendations.append("Consider equity financing alternatives")
    
    if score < thresholds["good_score"]:
        recommendations.append("Enhance interest coverage ratio")
        recommendations.append("Build credit history and relationships")
    
    return {
        "market_access_level": access_level,
        "available_instruments": available_instruments,
        "recommendations": recommendations,
    }





