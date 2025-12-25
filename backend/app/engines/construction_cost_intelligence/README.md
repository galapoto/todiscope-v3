# Construction Cost Intelligence Engine - Reporting & Analysis

## Overview

This engine provides **reporting and analysis** functionalities for the Enterprise Construction & Infrastructure Cost Intelligence Engine, specifically:

1. **Cost Variance Detection**: Detects and analyzes variances between BOQ (Bill of Quantities) estimates and actual costs
2. **Time-Phased Reporting**: Generates time-phased cost intelligence reports for ongoing construction projects

## Architecture

All reporting functionality is:
- **DatasetVersion-bound**: All reports are derived from data bound to specific DatasetVersion for audit-readiness
- **Deterministic**: All calculations and report generation are deterministic and replay-stable
- **Engine-owned**: Reporting logic lives in this engine (Platform Law #1)

## Modules

### Variance Detection (`variance/`)

**File**: `variance/detector.py`

Detects and calculates cost variances between BOQ estimates and actual costs.

**Key Functions**:
- `detect_cost_variances()`: Main variance detection function
- `_classify_severity()`: Classifies variance severity (within_tolerance, minor, moderate, major, critical)
- `_calculate_variance_percentage()`: Calculates variance as percentage

**Usage**:
```python
from backend.app.engines.construction_cost_intelligence.variance.detector import detect_cost_variances

variances = detect_cost_variances(
    boq_estimates=[
        {
            "item_id": "ITEM001",
            "estimated_cost": "10000.00",
            "category": "Materials",
            "unit": "kg",
            "quantity": "100",
        }
    ],
    actual_costs=[
        {
            "item_id": "ITEM001",
            "actual_cost": "10500.00",
            "date_recorded": "2024-01-15T00:00:00",
            "quantity": "105",
        }
    ],
    tolerance_threshold=Decimal("5.0"),
)
```

### Time-Phased Reporting (`time_phased/`)

**File**: `time_phased/reporter.py`

Generates time-phased cost intelligence reports aggregated by time periods.

**Key Functions**:
- `generate_time_phased_report()`: Main time-phased report generation function
- `_get_period_identifier()`: Generates period identifiers (daily, weekly, monthly, quarterly, yearly)
- `_get_period_bounds()`: Calculates period start/end dates

**Supported Period Types**:
- `daily`: Daily aggregation
- `weekly`: Weekly aggregation (ISO weeks)
- `monthly`: Monthly aggregation
- `quarterly`: Quarterly aggregation
- `yearly`: Yearly aggregation

**Usage**:
```python
from backend.app.engines.construction_cost_intelligence.time_phased.reporter import generate_time_phased_report

report = generate_time_phased_report(
    project_id="PROJ001",
    cost_records=[
        {
            "item_id": "ITEM001",
            "date_recorded": "2024-01-15T00:00:00",
            "estimated_cost": "10000.00",
            "actual_cost": "10500.00",
        }
    ],
    period_type="monthly",
    include_item_details=True,
)
```

### Report Assembly (`report/`)

**Files**:
- `report/assembler.py`: Main report assembly logic
- `report/sections.py`: Report section generators

**Key Functions**:
- `assemble_cost_variance_report()`: Assembles cost variance reports
- `assemble_time_phased_report()`: Assembles time-phased reports
- `assemble_report()`: Main report assembly router

**Report Types**:
1. **cost_variance**: Cost variance analysis report
2. **time_phased**: Time-phased cost intelligence report

**Usage**:
```python
from backend.app.engines.construction_cost_intelligence.report.assembler import assemble_report

report = await assemble_report(
    db=db,
    dataset_version_id="dv-uuid-here",
    run_id="run-uuid-here",
    report_type="cost_variance",
    project_id="PROJ001",
    parameters={
        "boq_estimates": [...],
        "actual_costs": [...],
        "tolerance_threshold": "5.0",
        "evidence_ids": [...],
    },
)
```

## Report Sections

### Cost Variance Reports

1. **Executive Summary**: High-level variance overview with totals and severity breakdown
2. **Variance Summary by Severity**: Aggregated metrics grouped by severity level
3. **Variance Summary by Category**: Aggregated metrics grouped by cost category
4. **Cost Variances**: Detailed variance analysis for each item
5. **Evidence Index**: References to evidence bundles (if provided)

### Time-Phased Reports

1. **Time-Phased Report**: Period-by-period cost breakdown with totals
2. **Evidence Index**: References to evidence bundles (if provided)

## Data Model Assumptions

This implementation assumes Agent 1 has created data models with the following structure:

### BOQ Estimates
- `item_id`: str (required, unique identifier)
- `estimated_cost`: Decimal or str (required)
- `category`: str (optional)
- `unit`: str (optional)
- `quantity`: Decimal or str (optional)
- `project_phase`: str (optional)

### Actual Costs
- `item_id`: str (required, must match BOQ item_id)
- `actual_cost`: Decimal or str (required)
- `date_recorded`: str (optional, ISO format)
- `quantity`: Decimal or str (optional)
- `project_phase`: str (optional)

### Cost Records (for time-phased reports)
- `item_id`: str (required)
- `date_recorded`: str (required, ISO format)
- `estimated_cost`: Decimal or str (required)
- `actual_cost`: Decimal or str (required)
- `category`: str (optional)
- `project_phase`: str (optional)

## DatasetVersion Binding

All reports are strictly bound to `dataset_version_id`:
- Reports require explicit `dataset_version_id` parameter
- All evidence references are validated against `dataset_version_id`
- Report assembly validates DatasetVersion consistency

## Error Handling

**Error Classes** (`errors.py`):
- `MissingArtifactError`: Required artifacts/data missing
- `InconsistentReferenceError`: DatasetVersion mismatch detected
- `InvalidParameterError`: Invalid parameters provided

## Platform Law Compliance

✅ **Law #1 — Core is mechanics-only**: All reporting logic lives in this engine  
✅ **Law #3 — DatasetVersion is mandatory**: All reports bound to explicit `dataset_version_id`  
✅ **Law #5 — Evidence and review are core-owned**: Evidence referenced via core evidence registry  
✅ **Law #6 — No implicit defaults**: All parameters explicit and validated

## Notes

- This module implements **reporting and analysis only**
- Core engine models and DatasetVersion logic are handled by Agent 1
- Evidence linking structure is defined by Agent 1
- All calculations use `Decimal` for precision
- All report generation is deterministic and replay-stable

## Platform Runtime

The engine is integrated into the platform runtime and is mounted only when enabled:
- Enable via `TODISCOPE_ENABLED_ENGINES=engine_construction_cost_intelligence`
- Routes are exposed under `POST /api/v3/engines/cost-intelligence/run` and `POST /api/v3/engines/cost-intelligence/report`
- Kill-switch is enforced per-request; if disabled after mount, endpoints return `503 ENGINE_DISABLED`





