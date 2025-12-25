# Enterprise Distressed Asset & Debt Stress Engine

## Overview

The Enterprise Distressed Asset & Debt Stress Engine provides comprehensive scenario management and execution capabilities for financial stress testing. It enables organizations to create, execute, and replay stress test scenarios with full traceability and immutability guarantees.

## Features

### 1. Scenario Creation
- Create custom stress test scenarios with configurable assumptions
- Link scenarios to specific DatasetVersions (mandatory)
- Define time horizons (6-24 months)
- Configure stress assumptions:
  - Revenue change factors
  - Cost change factors
  - Interest rate change factors
  - Liquidity shock factors
  - Market value depreciation factors
  - Collection/payment period adjustments

### 2. Scenario Execution
- Execute stress scenarios period-by-period
- Track exposure changes over time
- Calculate cash shortfalls by category (operating, debt service, capital expenditure)
- Monitor debt service coverage ratios (DSCR, interest coverage, principal coverage)
- Generate cumulative metrics across all periods

### 3. Scenario Storage and Replay
- Store scenarios immutably in the evidence system
- Full traceability of all scenario assumptions and results
- Replay scenarios with exact same assumptions
- Support for replaying with different financial data while preserving assumptions

### 4. Reporting
- **Granular Reports**: Period-by-period detailed results
- **Aggregated Reports**: Summary metrics and risk assessments
- **Executive Summaries**: High-level findings and recommendations

## Architecture

### Core Components

1. **Models** (`models.py`): Immutable data structures for scenarios, executions, and results
2. **Scenario Creation** (`scenario_creation.py`): Functions to create and validate scenarios
3. **Scenario Execution** (`scenario_execution.py`): Logic to execute scenarios and calculate metrics
4. **Scenario Storage** (`scenario_storage.py`): Immutable storage and retrieval of scenarios
5. **Reporting** (`reporting.py`): Report generation (granular, aggregated, executive)
6. **Run** (`run.py`): Main engine entry point
7. **Engine** (`engine.py`): FastAPI router and engine registration

### Immutability

All scenarios and executions are stored immutably:
- Scenarios cannot be modified after creation
- Executions are stored with full traceability
- Replay ensures exact reproducibility with same assumptions

### DatasetVersion Enforcement

- All scenarios must be linked to a DatasetVersion
- DatasetVersion is mandatory for all operations
- Scenarios are validated against DatasetVersion on retrieval

## Usage

### Creating a Scenario

```python
from backend.app.engines.enterprise_distressed_asset_debt_stress.scenario_creation import create_scenario

scenario = create_scenario(
    dataset_version_id="dv_123",
    scenario_name="moderate_stress",
    description="Moderate stress scenario",
    time_horizon_months=12,
    assumptions={
        "revenue_change_factor": 0.8,
        "cost_change_factor": 1.15,
        "interest_rate_change_factor": 1.3,
        "liquidity_shock_factor": 0.85,
        "market_value_depreciation_factor": 0.85,
    },
)
```

### Executing a Scenario

```python
from backend.app.engines.enterprise_distressed_asset_debt_stress.scenario_execution import execute_scenario

execution = execute_scenario(
    scenario=scenario,
    financial_data={
        "balance_sheet": {...},
        "income_statement": {...},
        "debt": {...},
    },
    analysis_date=date(2025, 1, 1),
)
```

### Replaying a Scenario

```python
from backend.app.engines.enterprise_distressed_asset_debt_stress.scenario_storage import replay_scenario

replayed_execution = await replay_scenario(
    db,
    scenario_id=scenario.scenario_id,
    dataset_version_id=dataset_version_id,
    financial_data=financial_data,
    analysis_date=analysis_date.isoformat(),
)
```

## API Endpoints

### POST `/api/v3/engines/enterprise-distressed-asset-debt-stress/run`

Execute the engine with parameters:

```json
{
  "dataset_version_id": "dv_123",
  "started_at": "2025-01-01T00:00:00Z",
  "parameters": {
    "operation": "execute",
    "scenario_name": "moderate_stress",
    "time_horizon_months": 12,
    "assumptions": {...}
  }
}
```

**Operations:**
- `create_scenario`: Create a new scenario
- `execute`: Execute a scenario (creates if not exists)
- `replay`: Replay an existing scenario

## Testing

Comprehensive unit tests are provided:

- `test_scenario_management.py`: Scenario creation and storage
- `test_scenario_execution.py`: Execution logic and metrics calculation
- `test_scenario_replay.py`: Replay functionality and reproducibility
- `test_reporting.py`: Report generation and accuracy

Run tests:
```bash
pytest backend/tests/engine_enterprise_distressed_asset_debt_stress/
```

## Constraints

- **Modular Monolith**: No microservices or distributed systems
- **DatasetVersion Enforcement**: Mandatory for all operations
- **Immutability**: All data structures are immutable
- **Time Horizon**: Must be between 6-24 months
- **No Speculative Abstractions**: Only necessary abstractions

## Output

The engine produces:
1. **Granular Reports**: Detailed period-by-period results
2. **Aggregated Reports**: Summary metrics and risk assessments
3. **Executive Summaries**: High-level findings and recommendations

All outputs are stored immutably in the evidence system with full traceability.






