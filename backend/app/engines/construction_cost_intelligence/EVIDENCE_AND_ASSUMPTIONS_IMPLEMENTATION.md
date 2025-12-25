# Evidence and Assumptions Handling - Implementation Summary

**Status:** ✅ **COMPLETE**

---

## Overview

This document summarizes the implementation of evidence linkage and assumption transparency for the Construction Cost Intelligence Engine reporting and analysis modules.

---

## 1. Evidence Emission

### Evidence Module (`evidence.py`)

**Functions:**
- `emit_variance_analysis_evidence()`: Emits evidence bundle for variance analysis
- `emit_time_phased_report_evidence()`: Emits evidence bundle for time-phased reports

**Key Features:**
- All evidence is bound to DatasetVersion
- Evidence IDs are deterministic using `deterministic_evidence_id()`
- Evidence payloads include assumptions registry
- Immutable and replay-stable

**Evidence Kinds:**
- `variance_analysis`: Evidence for cost variance detection reports
- `time_phased_report`: Evidence for time-phased cost reports

---

## 2. Assumptions Registry

### Assumptions Module (`assumptions.py`)

**Components:**
- `Assumption`: Individual assumption with category, description, source, and value
- `Exclusion`: Explicit exclusion (what the engine does not do)
- `ValidityScope`: Scope of validity for engine outputs
- `AssumptionRegistry`: Machine-readable registry of assumptions and exclusions

**Key Functions:**
- `create_default_assumption_registry()`: Creates registry with standard exclusions
- `add_variance_threshold_assumptions()`: Adds variance threshold assumptions
- `add_category_field_assumption()`: Adds categorization assumption
- `add_time_phased_assumptions()`: Adds time-phased reporting assumptions

**Assumption Categories:**
- `variance_threshold`: Threshold values for severity classification
- `categorization`: Field used for variance categorization
- `period_type`: Type of time period aggregation
- `date_extraction`: Field used for date extraction
- `cost_basis`: Cost calculation preference
- `date_filter`: Date range filters

**Standard Exclusions:**
- `no_causality`: Engine does not determine causes of variances
- `no_decisions`: Engine does not make budget or project management decisions
- `no_budget_revision`: Engine does not revise or approve budgets
- `no_cost_control`: Engine does not implement cost control measures

---

## 3. Deterministic ID Generation

### IDs Module (`ids.py`)

**Functions:**
- `deterministic_comparison_result_stable_key()`: Generates stable key for ComparisonResult
- `deterministic_time_phased_report_stable_key()`: Generates stable key for time-phased reports

**Key Features:**
- Stable keys include all parameters that affect report outputs
- Used as `stable_key` parameter for `deterministic_evidence_id()`
- Ensures replay-stability: same inputs → same evidence IDs

---

## 4. Report Assembly Integration

### Updated Report Assembler (`report/assembler.py`)

**Changes:**
1. **Evidence Emission**: Both report types now emit evidence bundles automatically
2. **Assumptions Tracking**: Assumptions are collected and included in evidence payloads
3. **Limitations Section**: Explicit limitations added to all reports
4. **Evidence Index**: Evidence IDs are included in report evidence index

**New Parameters:**
- `created_at`: Deterministic timestamp for evidence creation
- `emit_evidence`: Boolean flag to control evidence emission (default: True)

**Report Sections Added:**
- `section_limitations_assumptions()`: Includes limitations and assumptions in reports

---

## 5. Evidence Payload Structure

### Variance Analysis Evidence

```python
{
    "comparison_result_id": "<stable_key>",
    "variance_count": <int>,
    "assumptions": {
        "assumptions": [
            {
                "assumption_id": "variance_tolerance_threshold",
                "category": "variance_threshold",
                "description": "Variance tolerance threshold: 5.0%",
                "source": "run_parameters",
                "value": "5.0"
            },
            // ... more assumptions
        ],
        "exclusions": [
            {
                "exclusion_id": "no_causality",
                "category": "causality",
                "description": "Engine does not determine causes of cost variances",
                "rationale": "Variance analysis is descriptive only..."
            },
            // ... more exclusions
        ],
        "validity_scope": {
            "dataset_version_id": "<uuid>",
            "run_id": "<uuid>",
            "created_at": "<iso_timestamp>"
        }
    }
}
```

### Time-Phased Report Evidence

```python
{
    "report_id": "<stable_key>",
    "period_type": "monthly",
    "period_count": <int>,
    "assumptions": {
        "assumptions": [
            {
                "assumption_id": "period_type",
                "category": "period_type",
                "description": "Time period aggregation type: monthly",
                "source": "run_parameters",
                "value": "monthly"
            },
            // ... more assumptions
        ],
        "exclusions": [...],
        "validity_scope": {...}
    }
}
```

---

## 6. Report Sections

### Limitations and Assumptions Section

All reports now include a `limitations_assumptions` section containing:
- **Limitations**: Explicit limitations on what the analysis covers
- **Assumptions**: Machine-readable assumptions registry with:
  - Assumptions list (thresholds, parameters, etc.)
  - Exclusions list (what the engine does not do)
  - Validity scope (DatasetVersion, run_id, created_at)

---

## 7. Usage Example

### Cost Variance Report with Evidence

```python
from datetime import datetime, timezone
from backend.app.engines.construction_cost_intelligence.report.assembler import assemble_report

report = await assemble_report(
    db=db,
    dataset_version_id="dv-uuid",
    run_id="run-uuid",
    report_type="cost_variance",
    parameters={
        "comparison_result": comparison_result,
        "tolerance_threshold": "5.0",
        "minor_threshold": "10.0",
        "moderate_threshold": "25.0",
        "major_threshold": "50.0",
        "category_field": "cost_category",
    },
    created_at=datetime.now(timezone.utc),
    emit_evidence=True,
)
```

The report will:
1. Create assumptions registry with threshold and categorization assumptions
2. Emit evidence bundle with assumptions
3. Include limitations and assumptions section in report
4. Include evidence index with evidence IDs

---

## 8. Compliance

✅ **DatasetVersion Binding**: All evidence is bound to DatasetVersion  
✅ **Immutability**: Evidence records are append-only  
✅ **Determinism**: Evidence IDs are deterministic and replay-stable  
✅ **Transparency**: All assumptions are explicitly documented  
✅ **Traceability**: Evidence IDs link reports to assumptions and parameters

---

## 9. Integration Points

### With Agent 1's Models

- Uses `ComparisonResult` for variance analysis
- Uses `CostLine` models for time-phased reports
- Respects DatasetVersion binding from Agent 1's models

### With Core Evidence Service

- Uses `deterministic_evidence_id()` from core
- Uses `create_evidence()` from core
- Evidence stored in core `evidence_records` table

---

## Summary

✅ Evidence emission implemented for both report types  
✅ Assumptions registry implemented with machine-readable format  
✅ Limitations and assumptions included in all reports  
✅ Evidence IDs linked to reports via evidence index  
✅ All evidence bound to DatasetVersion  
✅ All assumptions explicitly documented and transparent






