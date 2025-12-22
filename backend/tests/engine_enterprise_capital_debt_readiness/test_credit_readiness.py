"""
Tests for credit readiness and capital raising strategies logic.

This module contains comprehensive tests for the credit readiness assessment
and capital raising strategies implemented in the enterprise capital debt readiness engine.
"""

import pytest
from decimal import Decimal
from datetime import date
from typing import Any, Dict

from backend.app.engines.enterprise_capital_debt_readiness.credit_readiness import (
    calculate_debt_to_equity_ratio,
    assess_debt_to_equity_category,
    calculate_interest_coverage_ratio,
    assess_interest_coverage_category,
    calculate_current_ratio,
    assess_liquidity_category,
    calculate_debt_service_coverage_ratio,
    assess_credit_risk_score,
    assess_financial_market_access,
    CreditReadinessError,
    InvalidFinancialDataError,
)
from backend.app.engines.enterprise_capital_debt_readiness.assumptions import resolved_assumptions

# Test data constants
SAMPLE_FINANCIAL_DATA = {
    "balance_sheet": {
        "total_assets": 2000000,
        "total_liabilities": 1200000,
        "total_equity": 800000,
        "current_assets": 900000,
        "current_liabilities": 400000,
        "cash_and_equivalents": 300000,
    },
    "income_statement": {
        "revenue": 5000000,
        "operating_income": 800000,
        "ebitda": 1000000,
        "interest_expense": 150000,
        "net_income": 450000,
    },
    "cash_flow": {
        "operating_cash_flow": 750000,
        "capital_expenditures": -250000,
        "free_cash_flow": 500000,
    },
    "debt": {
        "total_debt": 1000000,
        "short_term_debt": 300000,
        "long_term_debt": 700000,
        "undrawn_credit_lines": 500000,
    },
}

class TestCreditReadinessCalculations:
    """Test suite for credit readiness calculations."""
    
    def test_calculate_debt_to_equity_ratio(self):
        """Test debt-to-equity ratio calculation."""
        # Test with sample data
        result = calculate_debt_to_equity_ratio(
            total_debt=SAMPLE_FINANCIAL_DATA["debt"]["total_debt"],
            total_equity=SAMPLE_FINANCIAL_DATA["balance_sheet"]["total_equity"]
        )
        assert result == Decimal('1.2500')  # 1,000,000 / 800,000 = 1.25
        
        # Test with zero equity (should raise error)
        with pytest.raises(InvalidFinancialDataError):
            calculate_debt_to_equity_ratio(total_debt=1000000, total_equity=0)
            
    def test_assess_debt_to_equity_category(self):
        """Test debt-to-equity risk categorization."""
        # Test with custom thresholds
        thresholds = {
            "conservative": Decimal('0.5'),
            "high": Decimal('1.0'),
            "very_high": Decimal('2.0')
        }
        
        assert assess_debt_to_equity_category(Decimal('0.3'), thresholds) == "low_risk"
        assert assess_debt_to_equity_category(Decimal('0.7'), thresholds) == "moderate_risk"
        assert assess_debt_to_equity_category(Decimal('1.5'), thresholds) == "high_risk"
        assert assess_debt_to_equity_category(Decimal('3.0'), thresholds) == "very_high_risk"
        
    def test_calculate_interest_coverage_ratio(self):
        """Test interest coverage ratio calculation."""
        result = calculate_interest_coverage_ratio(
            ebitda=SAMPLE_FINANCIAL_DATA["income_statement"]["ebitda"],
            interest_expense=SAMPLE_FINANCIAL_DATA["income_statement"]["interest_expense"]
        )
        # 1,000,000 / 150,000 = 6.6667
        assert result == Decimal('6.6667')
        
        # Test with zero interest expense (should return None)
        assert calculate_interest_coverage_ratio(1000000, 0) is None
        
    def test_assess_interest_coverage_category(self):
        """Test interest coverage categorization."""
        thresholds = {
            "excellent": Decimal('5.0'),
            "good": Decimal('2.0'),
            "adequate": Decimal('1.5')
        }
        
        assert assess_interest_coverage_category(Decimal('6.0'), thresholds) == "excellent"
        assert assess_interest_coverage_category(Decimal('3.0'), thresholds) == "good"
        assert assess_interest_coverage_category(Decimal('1.6'), thresholds) == "adequate"
        assert assess_interest_coverage_category(Decimal('1.0'), thresholds) == "poor"
        assert assess_interest_coverage_category(None, thresholds) == "insufficient"
        
    def test_calculate_current_ratio(self):
        """Test current ratio calculation."""
        result = calculate_current_ratio(
            current_assets=SAMPLE_FINANCIAL_DATA["balance_sheet"]["current_assets"],
            current_liabilities=SAMPLE_FINANCIAL_DATA["balance_sheet"]["current_liabilities"]
        )
        # 900,000 / 400,000 = 2.25
        assert result == Decimal('2.2500')
        
        # Test with zero current liabilities (should return None)
        assert calculate_current_ratio(1000000, 0) is None


class TestCreditRiskScoring:
    """Test suite for credit risk scoring and market access assessment."""
    
    def test_assess_credit_risk_score(self):
        """Test credit risk score calculation."""
        result = assess_credit_risk_score(
            debt_to_equity_category="moderate_risk",
            interest_coverage_category="excellent",
            liquidity_category="strong"
        )
        
        # Verify the structure of the result
        assert "credit_risk_score" in result
        assert "risk_level" in result
        assert "component_scores" in result
        
        # Verify the component scores
        assert 0 <= result["credit_risk_score"] <= 100
        assert result["component_scores"]["debt_to_equity"] > 0
        assert result["component_scores"]["interest_coverage"] > 0
        assert result["component_scores"]["liquidity"] > 0
        
    def test_assess_credit_risk_score_custom_weights(self):
        """Test credit risk score with custom weights."""
        custom_weights = {
            "debt_to_equity": Decimal('0.4'),
            "interest_coverage": Decimal('0.3'),
            "liquidity": Decimal('0.2'),
            "dscr": Decimal('0.1')
        }
        
        result = assess_credit_risk_score(
            debt_to_equity_category="moderate_risk",
            interest_coverage_category="good",
            liquidity_category="adequate",
            dscr_category="adequate",
            weights=custom_weights
        )
        
        assert "credit_risk_score" in result
        assert 0 <= result["credit_risk_score"] <= 100
        
    def test_assess_financial_market_access(self):
        """Test financial market access assessment."""
        # Test with excellent credit score
        excellent_access = assess_financial_market_access(credit_risk_score=85)
        assert excellent_access["market_access_level"] == "excellent"
        assert "equity_issuance" in excellent_access["available_instruments"]
        
        # Test with good credit score
        good_access = assess_financial_market_access(credit_risk_score=70)
        assert good_access["market_access_level"] == "good"
        assert "corporate_bonds" in good_access["available_instruments"]
        
        # Test with moderate credit score
        moderate_access = assess_financial_market_access(credit_risk_score=50)
        assert moderate_access["market_access_level"] == "moderate"
        assert "private_placements" in moderate_access["available_instruments"]
        
        # Test with limited credit score
        limited_access = assess_financial_market_access(credit_risk_score=30)
        assert limited_access["market_access_level"] == "limited"
        assert "alternative_financing" in limited_access["available_instruments"]
        assert len(limited_access["recommendations"]) > 0


class TestEdgeCasesAndErrorHandling:
    """Test suite for edge cases and error handling."""
    
    def test_invalid_credit_score(self):
        """Test with invalid credit score values."""
        with pytest.raises(ValueError):
            assess_financial_market_access(credit_risk_score=-10)
            
        with pytest.raises(ValueError):
            assess_financial_market_access(credit_risk_score=150)
    
    def test_missing_required_parameters(self):
        """Test with missing required parameters."""
        with pytest.raises(TypeError):
            assess_credit_risk_score(
                debt_to_equity_category=None,
                interest_coverage_category="good",
                liquidity_category="strong"
            )
    
    def test_invalid_financial_data(self):
        """Test with invalid financial data."""
        with pytest.raises(InvalidFinancialDataError):
            calculate_debt_to_equity_ratio(total_debt=1000000, total_equity=0)
            
        with pytest.raises(InvalidFinancialDataError):
            calculate_debt_to_equity_ratio(total_debt=1000000, total_equity=-500000)


class TestIntegrationWithDatasetVersion:
    """Test integration with DatasetVersion and real data."""
    
    def test_end_to_end_credit_assessment(self):
        """Test the complete credit assessment workflow with sample data."""
        # Calculate financial ratios
        debt_equity_ratio = calculate_debt_to_equity_ratio(
            total_debt=SAMPLE_FINANCIAL_DATA["debt"]["total_debt"],
            total_equity=SAMPLE_FINANCIAL_DATA["balance_sheet"]["total_equity"]
        )
        
        interest_coverage = calculate_interest_coverage_ratio(
            ebitda=SAMPLE_FINANCIAL_DATA["income_statement"]["ebitda"],
            interest_expense=SAMPLE_FINANCIAL_DATA["income_statement"]["interest_expense"]
        )
        
        current_ratio = calculate_current_ratio(
            current_assets=SAMPLE_FINANCIAL_DATA["balance_sheet"]["current_assets"],
            current_liabilities=SAMPLE_FINANCIAL_DATA["balance_sheet"]["current_liabilities"]
        )
        
        # Assess categories
        debt_equity_category = assess_debt_to_equity_category(debt_equity_ratio)
        interest_coverage_category = assess_interest_coverage_category(
            interest_coverage, 
            {"excellent": Decimal('5.0'), "good": Decimal('2.0'), "adequate": Decimal('1.5')}
        )
        liquidity_category = assess_liquidity_category(
            current_ratio,
            {"strong": Decimal('2.0'), "adequate": Decimal('1.0')}
        )
        
        # Calculate credit risk score
        risk_assessment = assess_credit_risk_score(
            debt_to_equity_category=debt_equity_category,
            interest_coverage_category=interest_coverage_category,
            liquidity_category=liquidity_category
        )
        
        # Assess market access
        market_access = assess_financial_market_access(
            credit_risk_score=risk_assessment["credit_risk_score"],
            company_size="medium",
            industry="manufacturing"
        )
        
        # Verify results
        assert debt_equity_ratio > 0
        assert interest_coverage > 0
        assert current_ratio > 0
        assert risk_assessment["credit_risk_score"] > 0
        assert risk_assessment["risk_level"] in ["low", "moderate", "high", "very_high"]
        assert isinstance(market_access["available_instruments"], list)
        assert isinstance(market_access["recommendations"], list)
        
        # Print summary for verification
        print("\n--- Credit Assessment Summary ---")
        print(f"Debt-to-Equity Ratio: {debt_equity_ratio} ({debt_equity_category})")
        print(f"Interest Coverage Ratio: {interest_coverage} ({interest_coverage_category})")
        print(f"Current Ratio: {current_ratio} ({liquidity_category})")
        print(f"Credit Risk Score: {risk_assessment['credit_risk_score']} ({risk_assessment['risk_level']})")
        print(f"Market Access Level: {market_access['market_access_level']}")
        print("Available Instruments:", ", ".join(market_access['available_instruments']))
        if market_access["recommendations"]:
            print("Recommendations:", ", ".join(market_access['recommendations']))


if __name__ == "__main__":
    # Run the integration test directly for debugging
    tester = TestIntegrationWithDatasetVersion()
    tester.test_end_to_end_credit_assessment()
