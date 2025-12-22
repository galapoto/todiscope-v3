# Construction Cost Intelligence Engine - Reporting & Analysis

## Overview

This module provides **reporting and analysis** functionalities for the Enterprise Construction & Infrastructure Cost Intelligence Engine, built on top of Agent 1's core comparison models.

**Agent 2 Responsibilities:**
1. **Cost Variance Detection**: Analyzes variances from `ComparisonResult` and classifies them by severity and category
2. **Time-Phased Reporting**: Generates time-phased cost intelligence reports from `CostLine` models

## Architecture

All reporting functionality:
- **DatasetVersion-bound**: All reports are derived from data bound to specific DatasetVersion for audit-readiness
- **Deterministic**: All calculations and report generation are deterministic and replay-stable
- **Built on Agent 1's primitives**: Uses `ComparisonResult` and `CostLine` models from Agent 1

## Modules

### Variance Detection (`variance/`)

**File**: `variance/detector.py`

Analyzes variances from Agent 1's `ComparisonResult` model and classifies them.

**Key Functions**:
- `detect_cost_variances()`: Extracts variance information from `ComparisonResult`
- `_classify_severity()`: Classifies variance severity (within_tolerance, minor, moderate, major, critical)
- `_determine_direction()`: Determines if variance is over/under budget

**Usage**:
```python
from backend.app.engines.construction_cost_intelligence.variance.detector import detect_cost_variances
from backend.app.engines.construction_cost_intelligence.models import ComparisonResult

# Assume comparison_result is from Agent 1's compare_boq_to_actuals()
variances = detect_cost_variances(
    comparison_result=comparison_result,
    tolerance_threshold=Decimal("5.0"),
    minor_threshold=Decimal("10.0"),
    moderate_threshold=Decimal("25.0"),
    major_threshold=Decimal("50.0"),
    category_field="cost_category",  # Optional: extract category from identity/attributes
)
```

### Time-Phased Reporting (`time_phased/`)

**File**: `time_phased/reporter.py`

Generates time-phased cost intelligence reports from `CostLine` models.

**Key Functions**:
- `generate_time_phased_report()`: Generates time-phased report from `CostLine` objects
- `_get_period_identifier()`: Generates period identifiers (daily, weekly, monthly, quarterly, yearly)
- `_extract_date_from_cost_line()`: Extracts date from CostLine attributes

**Supported Period Types**:
- `daily`: Daily aggregation
- `weekly`: Weekly aggregation (ISO weeks)
- `monthly`: Monthly aggregation
- `quarterly`: Quarterly aggregation
- `yearly`: Yearly aggregation

**Usage**:
```python
from backend.app.engines.construction_cost_intelligence.time_phased.reporter import generate_time_phased_report
from backend.app.engines.construction_cost_intelligence.models import CostLine

# Assume cost_lines is a list of CostLine objects (mix of 'boq' and 'actual')
report = generate_time_phased_report(
    dataset_version_id="dv-uuid-here",
    cost_lines=cost_lines,
    period_type="monthly",
    date_field="date_recorded",  # Field name in CostLine.attributes
    include_item_details=True,
    prefer_total_cost=True,  # Prefer total_cost over quantity * unit_cost
)
```

### Report Assembly (`report/`)

**Files**:
- `report/assembler.py`: Main report assembly logic
- `report/sections.py`: Report section generators

**Key Functions**:
- `assemble_cost_variance_report()`: Assembles cost variance reports from `ComparisonResult`
- `assemble_time_phased_report()`: Assembles time-phased reports from `CostLine` objects
- `assemble_report()`: Main report assembly router

**Report Types**:
1. **cost_variance**: Cost variance analysis report from `ComparisonResult`
2. **time_phased**: Time-phased cost intelligence report from `CostLine` objects

**Usage**:
```python
from backend.app.engines.construction_cost_intelligence.report.assembler import assemble_report
from backend.app.engines.construction_cost_intelligence.models import ComparisonResult, CostLine

# Cost Variance Report
report = await assemble_report(
    db=db,
    dataset_version_id="dv-uuid-here",
    run_id="run-uuid-here",
    report_type="cost_variance",
    parameters={
        "comparison_result": comparison_result,  # From Agent 1
        "tolerance_threshold": "5.0",
        "category_field": "cost_category",
        "evidence_ids": [...],
    },
)

# Time-Phased Report
report = await assemble_report(
    db=db,
    dataset_version_id="dv-uuid-here",
    run_id="run-uuid-here",
    report_type="time_phased",
    parameters={
        "cost_lines": cost_lines,  # List of CostLine objects
        "period_type": "monthly",
        "date_field": "date_recorded",
        "evidence_ids": [...],
    },
)
```

## Integration with Agent 1's Models

### ComparisonResult → Variance Report

Agent 1's `compare_boq_to_actuals()` produces a `ComparisonResult` containing:
- `matched`: `ComparisonMatch` objects with `boq_total_cost`, `actual_total_cost`, `cost_delta`
- `unmatched_boq`: BOQ lines with no matching actuals
- `unmatched_actual`: Actual lines with no matching BOQ

Agent 2's `detect_cost_variances()` processes the `matched` items to:
- Calculate variance percentages

### Scope Creep Detection

Scope creep is detected deterministically from the same `ComparisonResult`:
- Any `unmatched_actual` line is labeled as **scope creep**.
- In the variance report output, scope creep entries include `scope_creep: true` and `severity: "scope_creep"`.
- Scope creep is distinct from variance thresholds; it does not use severity percentage thresholds.

If `core_traceability` is provided to `assemble_report()`, each scope creep entry is augmented with:
- `core_finding_ids`: core `FindingRecord` IDs that reference the unmatched line
- `evidence_ids`: evidence IDs linked to those findings (for audit traceability)
- Classify severity (within_tolerance, minor, moderate, major, critical)
- Determine direction (over_budget, under_budget, on_budget)
- Extract categorization from identity fields or attributes

### CostLine → Time-Phased Report

Agent 1's `CostLine` model contains:
- `kind`: 'boq' or 'actual'
- `total_cost`, `quantity`, `unit_cost`: Cost information
- `attributes`: Additional metadata (including date information)
- `identity`: Identity fields for matching

Agent 2's `generate_time_phased_report()`:
- Extracts dates from `CostLine.attributes` (using `date_field` parameter)
- Groups by time period
- Aggregates costs separately for BOQ and actual
- Calculates period-by-period variances

## Report Sections

### Cost Variance Reports

1. **Executive Summary**: High-level variance overview with totals and severity breakdown
2. **Variance Summary by Severity**: Aggregated metrics grouped by severity level
3. **Variance Summary by Category**: Aggregated metrics grouped by cost category
4. **Cost Variances**: Detailed variance analysis for each matched item
5. **Evidence Index**: References to evidence bundles (if provided)

### Time-Phased Reports

1. **Time-Phased Report**: Period-by-period cost breakdown with totals
2. **Evidence Index**: References to evidence bundles (if provided)

## DatasetVersion Binding

All reports are strictly bound to `dataset_version_id`:
- Reports require explicit `dataset_version_id` parameter
- All `ComparisonResult` and `CostLine` objects must have matching `dataset_version_id`
- Evidence references are validated against `dataset_version_id`
- Report assembly validates DatasetVersion consistency

## Error Handling

**Error Classes** (from `errors.py`):
- `MissingArtifactError`: Required artifacts/data missing
- `DatasetVersionMismatchError`: DatasetVersion mismatch detected
- `ConstructionCostIntelligenceError`: Base exception

## Platform Law Compliance

✅ **Law #1 — Core is mechanics-only**: All reporting logic lives in this engine  
✅ **Law #3 — DatasetVersion is mandatory**: All reports bound to explicit `dataset_version_id`  
✅ **Law #5 — Evidence and review are core-owned**: Evidence referenced via core evidence registry  
✅ **Law #6 — No implicit defaults**: All parameters explicit and validated

## Notes

- This module implements **reporting and analysis only**
- Core comparison logic (`compare_boq_to_actuals`) is provided by Agent 1
- `CostLine` and `ComparisonResult` models are provided by Agent 1
- Evidence linking structure is defined by Agent 1
- All calculations use `Decimal` for precision
- All report generation is deterministic and replay-stable

