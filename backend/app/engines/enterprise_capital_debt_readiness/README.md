# Enterprise Capital & Debt Readiness Engine

## Overview

This engine provides **credit readiness assessment** and **capital raising strategies** logic for enterprises. It evaluates a company's ability to obtain credit and provides actionable insights into capital raising strategies.

## Purpose

The engine calculates:
1. **Credit Readiness**: Assesses the enterprise's ability to obtain credit or loans
2. **Capital Raising Strategies**: Provides recommendations for managing and raising capital

## Key Features

### Credit Readiness Calculations

- **Debt-to-Equity Ratio**: Calculates and categorizes debt-to-equity ratio
- **Interest Coverage Ratio**: Assesses ability to service debt obligations
- **Current Ratio**: Evaluates short-term liquidity position
- **Debt Service Coverage Ratio (DSCR)**: Measures ability to service debt payments
- **Credit Risk Score**: Composite score based on multiple financial metrics
- **Financial Market Access**: Assesses access to various financial instruments

### Capital Raising Strategies

- **Debt Capacity Assessment**: Calculates maximum debt capacity based on EBITDA
- **Equity Capacity Assessment**: Evaluates equity raising capacity with dilution analysis
- **Debt Instrument Recommendations**: Recommends appropriate debt instruments (loans, bonds, etc.)
- **Equity Instrument Recommendations**: Recommends equity instruments (VC, PE, IPO, etc.)
- **Hybrid Strategies**: Recommends balanced debt-equity financing approaches

## Platform Law Compliance

This engine complies with all TodiScope v3 Platform Laws:

1. **Law #1 — Core is mechanics-only**: All domain logic lives in this engine
2. **Law #2 — Engines are detachable**: Engine can be disabled without impacting core
3. **Law #3 — DatasetVersion is mandatory**: All calculations bound to `dataset_version_id`
4. **Law #4 — Artifacts are content-addressed**: Evidence stored via core evidence service
5. **Law #5 — Evidence and review are core-owned**: Evidence written to core evidence registry
6. **Law #6 — No implicit defaults**: All parameters explicit and validated

## Determinism Guarantees

- **No randomness**: All calculations are deterministic
- **No time-dependent logic**: No system time usage
- **Decimal arithmetic**: All financial calculations use Decimal (no float)
- **Stable ordering**: All iterations use sorted order
- **Idempotent evidence**: Same inputs produce same evidence IDs

## Module Structure

```
enterprise_capital_debt_readiness/
├── __init__.py                 # Module exports
├── credit_readiness.py         # Credit readiness calculations
├── capital_strategies.py       # Capital raising strategies
├── evidence.py                 # Evidence creation functions
├── config/
│   ├── __init__.py
│   └── assumptions.yaml       # Configuration and thresholds
└── README.md                   # This file
```

## Usage Example

### Credit Readiness Assessment

```python
from decimal import Decimal
from backend.app.engines.enterprise_capital_debt_readiness import credit_readiness

# Calculate debt-to-equity ratio
debt_to_equity = credit_readiness.calculate_debt_to_equity_ratio(
    total_debt=Decimal("5000000"),
    total_equity=Decimal("10000000"),
)

# Assess debt-to-equity category
thresholds = {
    "conservative": Decimal("0.5"),
    "high": Decimal("1.0"),
    "very_high": Decimal("2.0"),
}
category = credit_readiness.assess_debt_to_equity_category(
    debt_to_equity_ratio=debt_to_equity,
    thresholds=thresholds,
)

# Calculate interest coverage ratio
interest_coverage = credit_readiness.calculate_interest_coverage_ratio(
    ebitda=Decimal("2000000"),
    interest_expense=Decimal("250000"),
)

# Assess overall credit risk
credit_risk = credit_readiness.assess_credit_risk_score(
    debt_to_equity_category=category,
    interest_coverage_category="good",
    liquidity_category="adequate",
)
```

### Capital Raising Strategies

```python
from backend.app.engines.enterprise_capital_debt_readiness import capital_strategies

# Assess debt capacity
debt_capacity = capital_strategies.assess_debt_capacity(
    ebitda=Decimal("2000000"),
    existing_debt_service=Decimal("500000"),
    target_dscr=Decimal("1.25"),
    interest_rate=Decimal("0.05"),
    loan_term_years=5,
)

# Recommend debt instruments
debt_instruments = capital_strategies.recommend_debt_instruments(
    debt_amount=Decimal("3000000"),
    company_size="medium",
    credit_risk_level="moderate",
    time_horizon="medium",
)

# Assess equity capacity
equity_capacity = capital_strategies.assess_equity_capacity(
    current_equity_value=Decimal("10000000"),
    target_ownership_dilution=Decimal("0.20"),
)

# Recommend hybrid strategies
hybrid_strategies = capital_strategies.recommend_hybrid_strategies(
    total_capital_needed=Decimal("5000000"),
    debt_capacity=debt_capacity,
    equity_capacity=equity_capacity,
    risk_tolerance="moderate",
)
```

### Evidence Creation

```python
from backend.app.engines.enterprise_capital_debt_readiness import evidence

# Create credit readiness evidence
evidence_id = await evidence.create_credit_readiness_evidence(
    db=db,
    dataset_version_id=dataset_version_id,
    stable_key="credit_assessment_2024",
    credit_readiness_data={
        "debt_to_equity_ratio": 0.5,
        "credit_risk_score": 75.0,
        "risk_level": "moderate",
    },
)

# Create capital strategy evidence
strategy_evidence_id = await evidence.create_capital_strategy_evidence(
    db=db,
    dataset_version_id=dataset_version_id,
    stable_key="capital_strategy_2024",
    capital_strategy_data={
        "recommended_debt_amount": 3000000.0,
        "recommended_equity_amount": 2000000.0,
        "strategy": "balanced_mix",
    },
)
```

## Configuration

Configuration is stored in `config/assumptions.yaml` and includes:

- **Debt-to-equity thresholds**: Risk category boundaries
- **Interest coverage thresholds**: Coverage ratio categories
- **Liquidity thresholds**: Current ratio categories
- **Credit risk weights**: Component weights for composite score
- **Market access thresholds**: Score boundaries for market access levels
- **Debt capacity assumptions**: Default DSCR, interest rates, loan terms
- **Equity capacity assumptions**: Default dilution targets
- **Instrument thresholds**: Amount thresholds for different instruments

All thresholds can be overridden via function parameters.

## Input Data Requirements

### For Credit Readiness Assessment

- **Total Debt**: Total outstanding debt
- **Total Equity**: Total equity value
- **EBITDA**: Earnings before interest, taxes, depreciation, and amortization
- **Interest Expense**: Total annual interest expense
- **Current Assets**: Total current assets
- **Current Liabilities**: Total current liabilities
- **Net Operating Income**: Net operating income (for DSCR)
- **Total Debt Service**: Principal + interest payments (for DSCR)

### For Capital Raising Strategies

- **EBITDA**: For debt capacity calculation
- **Existing Debt Service**: Current annual debt service
- **Current Equity Value**: For equity capacity calculation
- **Company Size**: small/medium/large/enterprise
- **Company Stage**: startup/growth/mature/public
- **Risk Tolerance**: conservative/moderate/aggressive
- **Time Horizon**: short/medium/long

## Output Format

All calculations return structured dictionaries with:

- **Numeric values**: Decimal or float (as appropriate)
- **Categories**: String enums (e.g., "low_risk", "moderate_risk")
- **Recommendations**: Lists of recommended instruments or strategies
- **Rationale**: Explanations for recommendations

## Error Handling

The engine raises typed exceptions:

- `CreditReadinessError`: Base error for credit readiness calculations
- `InvalidFinancialDataError`: Raised when financial data is invalid
- `CapitalStrategyError`: Base error for capital strategy calculations

All errors include descriptive messages following the platform error format.

## Testing

Tests should verify:

1. **Determinism**: Same inputs produce same outputs
2. **Decimal arithmetic**: No float precision issues
3. **DatasetVersion binding**: All evidence bound to DatasetVersion
4. **Immutability**: Evidence creation is idempotent
5. **Threshold validation**: Invalid thresholds raise errors
6. **Edge cases**: Zero/negative values handled appropriately

## Future Enhancements

Potential enhancements (not yet implemented):

- Industry-specific benchmarks
- Regional market variations
- Historical trend analysis
- Scenario modeling (best case/worst case/base case)
- Integration with external credit rating services
- Real-time market rate integration

## References

- Platform Laws: `docs/NON_NEGOTIABLE_PLATFORM_LAWS.md`
- Engine Execution Template: `docs/ENGINE_EXECUTION_TEMPLATE.md`
- Evidence Safety Rules: `docs/engines/audit_readiness/EVIDENCE_SAFETY_RULES.md`


