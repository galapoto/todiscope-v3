# Readiness Scores Implementation

## Overview

This document describes the implementation of **composite readiness scores** for the Enterprise Capital & Debt Readiness Engine. The readiness score is a 0-100 scale metric that integrates multiple financial factors to provide an executive-level assessment of a company's capital and debt readiness.

## Implementation Details

### Core Module: `readiness_scores.py`

The `readiness_scores.py` module provides:

1. **`calculate_composite_readiness_score()`**: Main function that calculates the composite readiness score
2. **`load_financial_forensics_data()`**: Async function to load Financial Forensics Engine data
3. **`load_deal_readiness_data()`**: Async function to load Deal Readiness Engine data

### Score Components

The composite readiness score integrates five components with default weights:

1. **Capital Adequacy (30%)**: Based on `CapitalAdequacyAssessment.adequacy_level`
   - Maps to scores: strong=85, adequate=70, weak=50, insufficient_data=30

2. **Debt Service (30%)**: Based on `DebtServiceAssessment.ability_level`
   - Maps to scores: strong=85, adequate=70, weak=50, insufficient_data=30

3. **Credit Risk (25%)**: Calculated using `credit_readiness.assess_credit_risk_score()`
   - Integrates:
     - Debt-to-equity ratio category
     - Interest coverage ratio category
     - Liquidity (current ratio) category
     - DSCR category (if available)

4. **Financial Forensics Impact (10%)**: Based on leakage exposure from FF-2 engine
   - Default neutral score: 75
   - Penalty calculation: `max(45, 75 - (exposure_millions * 2))` (max 30 point penalty)

5. **Deal Readiness Impact (5%)**: Based on findings from Deal Readiness Engine
   - Default neutral score: 75
   - Score calculation: `max(30, 80 - (high_severity * 5) - (medium_severity * 2))`

### Readiness Levels

The composite score maps to readiness levels:

- **excellent**: score >= 80
- **good**: score >= 70
- **adequate**: score >= 60
- **weak**: score < 60

### Integration with `run.py`

The readiness score calculation is integrated into the engine's `run_engine()` function:

1. After calculating capital adequacy and debt service assessments
2. Loads cross-engine data (Financial Forensics, Deal Readiness)
3. Calculates composite readiness score
4. Creates a readiness score finding
5. Creates readiness score evidence record
6. Includes readiness score in summary output

### Output Structure

The engine's output now includes:

```python
{
    "readiness_score": 75.5,  # Composite score (0-100)
    "readiness_level": "good",  # Category
    "readiness_breakdown": {
        "component_scores": {
            "capital_adequacy": 70.0,
            "debt_service": 85.0,
            "credit_risk": 72.5,
            "financial_forensics": 75.0,
            "deal_readiness": 80.0
        },
        "credit_risk_details": {...},
        "breakdown": {
            "capital_adequacy_level": "adequate",
            "debt_service_level": "strong",
            "credit_risk_level": "moderate",
            ...
        },
        "cross_engine_data": {
            "financial_forensics": {...},
            "deal_readiness": {...}
        }
    }
}
```

## Platform Law Compliance

- **Deterministic**: Same inputs → same outputs (uses Decimal arithmetic only)
- **DatasetVersion Binding**: All calculations bound to specific DatasetVersion
- **Immutability**: Evidence records are append-only
- **Simple & Interpretable**: Designed for executive decision-making

## Testing

Comprehensive unit tests are provided in `test_readiness_scores.py`:

- Test with strong capital and debt service
- Test with weak capital
- Test with Financial Forensics exposure
- Test with Deal Readiness data
- Test component breakdown
- Test custom weights
- Test edge cases (insufficient data)
- Test determinism

All tests pass successfully.

## Usage Example

```python
from backend.app.engines.enterprise_capital_debt_readiness.readiness_scores import (
    calculate_composite_readiness_score,
)

result = calculate_composite_readiness_score(
    capital_adequacy=cap_assessment,
    debt_service=debt_assessment,
    financial=financial_data,
    assumptions=assumptions,
    ff_leakage_exposure=Decimal("5000000"),  # Optional
    deal_readiness_score=Decimal("85"),  # Optional
)

print(f"Readiness Score: {result['readiness_score']}")
print(f"Readiness Level: {result['readiness_level']}")
```

## Future Enhancements

Potential improvements:

1. Configurable weights via assumptions/parameters
2. Industry-specific scoring adjustments
3. Time-series trend analysis
4. More sophisticated cross-engine data integration
5. Additional market factors (e.g., interest rate environment)


