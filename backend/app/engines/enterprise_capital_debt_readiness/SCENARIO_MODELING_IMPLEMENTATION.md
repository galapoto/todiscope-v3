# Scenario-Based Risk Modeling Implementation

## Overview

This document describes the implementation of **scenario-based risk modeling** for the Enterprise Capital & Debt Readiness Engine. The scenario modeling provides base/best/worst case scenarios and stress testing under varying market conditions.

## Implementation Details

### Core Module: `scenario_modeling.py`

The `scenario_modeling.py` module provides:

1. **Scenario Conditions**: Market condition definitions (interest rates, liquidity, revenue, costs)
2. **Scenario Creation Functions**: Factory functions for base/best/worst case and stress tests
3. **Scenario Calculation**: `calculate_scenario_readiness()` - calculates readiness under scenario conditions
4. **Risk Metrics**: Liquidity risk, solvency risk, and market sensitivity calculations
5. **Scenario Analysis**: `run_scenario_analysis()` - comprehensive scenario analysis

### Scenario Types

1. **Base Case**: Current market conditions (no changes)
2. **Best Case**: Favorable conditions
   - 15% lower interest rates
   - 15% more liquidity
   - 10% revenue increase
   - 5% cost reduction

3. **Worst Case**: Adverse conditions
   - 50% higher interest rates
   - 30% liquidity reduction
   - 20% revenue reduction
   - 20% cost increase

4. **Stress Tests**:
   - Interest Rate Shock: 200% interest rate increase
   - Liquidity Shock: 50% liquidity reduction
   - Combined Shock: Multiple simultaneous adverse conditions

### Risk Metrics

1. **Liquidity Risk Score (0-100)**: Based on:
   - Cash runway degradation
   - Coverage ratio degradation
   - Liquidity shock severity

2. **Solvency Risk Score (0-100)**: Based on:
   - Debt-to-equity ratio degradation
   - DSCR degradation
   - Interest coverage degradation
   - Interest rate shock severity

3. **Market Sensitivity (0-100)**: Based on:
   - Magnitude of readiness score change relative to scenario severity
   - Higher sensitivity = more vulnerable to market changes

### Integration

The scenario analysis is integrated into `run.py`:

1. After calculating base readiness score
2. Runs comprehensive scenario analysis
3. Creates scenario analysis evidence record
4. Includes scenario analysis in summary output

### Report Integration

The report module (`report/sections.py`) includes:

1. **Scenario Analysis Section**: Detailed scenario results
2. **Risk Insights**: Automated risk findings based on aggregate metrics
3. **Scenario Comparison**: Base vs best vs worst case comparison
4. **Key Findings**: Executive-level insights

### Output Structure

The scenario analysis output includes:

```python
{
    "scenarios": [
        {
            "scenario_name": "base_case",
            "readiness_score": 75.5,
            "readiness_level": "good",
            "capital_adequacy_impact": 0.0,
            "debt_service_impact": 0.0,
            "liquidity_risk_score": 0.0,
            "solvency_risk_score": 0.0,
            "market_sensitivity": 0.0,
            "component_scores": {...},
            "conditions": {...},
            "flags": []
        },
        ...
    ],
    "aggregate_risk_metrics": {
        "max_liquidity_risk": 85.0,
        "max_solvency_risk": 90.0,
        "max_market_sensitivity": 75.0,
        "score_range": 25.0,
        "min_score": 50.0,
        "max_score": 75.0
    }
}
```

## Platform Law Compliance

- **Deterministic**: Same inputs → same outputs (uses Decimal arithmetic)
- **DatasetVersion Binding**: All calculations bound to specific DatasetVersion
- **Immutability**: Evidence records are append-only
- **Simple & Interpretable**: Designed for executive decision-making

## Testing

Comprehensive unit tests are provided in `test_scenario_modeling.py`:

- Test scenario condition creation
- Test base/best/worst case scenarios
- Test stress tests
- Test risk metrics calculation
- Test determinism (with tolerance for floating point precision)

## Usage Example

```python
from backend.app.engines.enterprise_capital_debt_readiness.scenario_modeling import (
    run_scenario_analysis,
)

scenario_analysis = run_scenario_analysis(
    base_capital_adequacy=cap_assessment,
    base_debt_service=debt_assessment,
    base_readiness_score=Decimal("75.5"),
    base_readiness_level="good",
    base_component_scores={...},
    financial=financial_data,
    assumptions=assumptions,
)

print(f"Worst case score: {scenario_analysis['scenarios'][2]['readiness_score']}")
print(f"Max liquidity risk: {scenario_analysis['aggregate_risk_metrics']['max_liquidity_risk']}")
```

## Configuration

Scenario conditions can be adjusted by modifying the factory functions:
- `create_best_case_conditions()`
- `create_worst_case_conditions()`
- `create_stress_test_interest_rate_shock()`
- `create_stress_test_liquidity_shock()`
- `create_stress_test_combined_shock()`

## Future Enhancements

Potential improvements:

1. Configurable scenario parameters via assumptions
2. Industry-specific scenario adjustments
3. Monte Carlo simulation for probabilistic scenarios
4. Time-series scenario analysis
5. Additional stress test scenarios (e.g., credit crunch, market crash)






