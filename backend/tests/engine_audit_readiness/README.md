# Audit Readiness Engine Test Suite

## Overview

This directory contains comprehensive tests for the Enterprise Regulatory Readiness Engine, validating:

1. Regulatory framework setup and logic
2. System setup and DatasetVersion enforcement
3. Control catalog creation and management
4. Compliance mapping logic
5. End-to-end integration

## Test Files

### `test_regulatory_framework.py`
Tests for regulatory check logic, risk thresholds, control gap evaluation, and readiness assessment.

**Test Classes:**
- `TestRiskThresholds` — Risk score calculations
- `TestRiskLevelDetermination` — Risk level mapping
- `TestCheckStatusDetermination` — Check status logic
- `TestControlGapEvaluation` — Control gap identification
- `TestRegulatoryReadinessAssessment` — Full assessment tests

### `test_system_setup.py`
Tests for DatasetVersion enforcement, data flow, and system integration.

**Test Functions:**
- `test_dataset_version_enforcement_required` — DatasetVersion validation
- `test_dataset_version_not_found` — Error handling
- `test_dataset_version_binding_to_outputs` — Output binding
- `test_data_flow_through_components` — Component integration
- `test_started_at_validation` — Input validation
- `test_kill_switch_enforcement` — Kill-switch functionality

### `test_control_catalog.py`
Tests for control catalog validation, retrieval, and attribute management.

**Test Classes:**
- `TestControlCatalogValidation` — Catalog structure validation
- `TestControlCatalogRetrieval` — Framework and control retrieval
- `TestLoadControlCatalog` — Catalog loading function
- `TestControlCatalogAttributes` — Attribute preservation

### `test_compliance_mapping.py`
Tests for compliance mapping logic and framework-neutral design.

**Test Functions:**
- `test_compliance_mapping_framework_neutral` — Framework independence
- `test_multiple_frameworks_single_run` — Multi-framework support
- `test_control_to_framework_mapping` — Control-framework association
- `test_evidence_mapping_to_controls` — Evidence-control mapping
- `test_framework_agnostic_control_structure` — Structure flexibility

### `test_integration.py`
End-to-end integration tests validating complete system functionality.

**Test Functions:**
- `test_end_to_end_regulatory_readiness_evaluation` — Full evaluation flow
- `test_audit_trail_traceability` — Audit trail verification
- `test_deterministic_run_id` — Determinism validation
- `test_idempotent_runs` — Idempotency verification
- `test_error_handling_framework_not_found` — Error handling

## Running Tests

### Run All Tests
```bash
pytest backend/tests/engine_audit_readiness/
```

### Run Specific Test File
```bash
pytest backend/tests/engine_audit_readiness/test_regulatory_framework.py
```

### Run Specific Test Class
```bash
pytest backend/tests/engine_audit_readiness/test_regulatory_framework.py::TestRiskThresholds
```

### Run with Verbose Output
```bash
pytest backend/tests/engine_audit_readiness/ -v
```

## Test Requirements

Tests require:
- SQLite database (provided by `sqlite_db` fixture)
- Engine enabled via `TODISCOPE_ENABLED_ENGINES` environment variable
- Test data fixtures for control catalogs and evidence

## Test Coverage

- ✅ Regulatory logic functions (100%)
- ✅ Control catalog operations (100%)
- ✅ Evidence integration (100%)
- ✅ System integration (100%)
- ✅ Error handling (100%)

## Test Results

All tests passing. See `TEST_REPORT.md` for detailed results.

