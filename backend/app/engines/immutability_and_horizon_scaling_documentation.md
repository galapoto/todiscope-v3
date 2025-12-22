# Immutability Enforcement and Horizon Scaling Documentation

## Overview
This document captures how the Enterprise Capital & Debt Readiness Engine locks down evidence creation and scales debt service ratios across arbitrary horizons. Every datapoint is bound to a single `DatasetVersion`, and footprints are preserved via append-only evidence.

## Strict Immutability Enforcement
Collection and linking logic all go through `install_immutability_guards()` inside `run_engine()`, which ensures dataset-level validation hooks stay in place for every subsequent `create_evidence()`, `create_finding()`, and `link_finding_to_evidence()` call.

### `_strict_create_evidence()` Contract
- **DatasetVersion + Engine binding**: The incoming `dataset_version_id`, `engine_id`, and `kind` must match exactly with any existing record for the same `evidence_id`. Any deviation raises `ImmutableConflictError("EVIDENCE_ID_COLLISION")` before a new payload is persisted.
- **Created-at immutability**: Timestamps are normalized to UTC for comparison; a mismatch raises `ImmutableConflictError("IMMUTABLE_EVIDENCE_CREATED_AT_MISMATCH")`. This guarantees metadata consistency even when SQLite round-trips strip time zones.
- **Payload stability**: Changing the payload despite matching IDs and metadata triggers `ImmutableConflictError("IMMUTABLE_EVIDENCE_MISMATCH")`, so any assumption or calculation update must emit a brand-new evidence ID.
- **Traceability**: `_strict_create_finding()` and `_strict_link()` mirror the same pattern. Links remain fixed once created, and changes to assumptions require new link records bound to the same `DatasetVersion`.

## Horizon Scaling Assumptions
The time-horizon fix keeps DSCR and interest coverage comparable across 6-, 12-, 24-, or other-sized horizons by scaling cash/EBITDA inputs to the same timeframe as the debt service schedule.

- **Scaling factor**: `horizon_scale_factor = horizon_months / 12`. Annual cash available (or derived EBITDA) is multiplied by this factor before the ratios run so the numerator shares the horizon of the denominator.
- **Ratio formulas**:
  - `dscr = cash_available_horizon / debt_service_for_ratio`
  - `interest_coverage = ebitda_horizon / interest_for_ratio`
  Both numerators are horizon-adjusted, while the denominators already reflect the `horizon_months` window from `assess_debt_service_ability()`.
- **Assumption documentation**: The payload lists `assumption_debt_service_horizon` (controls schedule construction) and `assumption_horizon_scaling` (documents the scaling formula, source, impact, and sensitivity). This makes the transformation explicit for auditors.
- **6-month example**: Setting `horizon_months = 6` yields `horizon_scale_factor = 0.5`, so a $120k annual cash input becomes $60k in the DSCR numerator, matching exactly six months of scheduled payments; the ratio therefore remains consistent with the 12-month default.

## Validation and Maintenance
- **Immutability verification**: `backend/tests/engine_csrd/test_csrd_strict_immutability.py` covers exact duplicates, payload changes, and timestamp drift to show that `_strict_create_evidence()` and `_strict_create_finding()` reject any mutation while respecting dataset bindings.
- **Horizon scaling coverage**: `backend/tests/engine_enterprise_capital_debt_readiness/test_debt_service_horizon_scaling.py` proves that DSCR and interest coverage stay identical across 6-, 12-, and 24-month horizons once the scaling factor is applied uniformly.
- **Operational guidance**: Record every new assumption/horizon ID in the payload and never reuse an evidence ID once an immutability conflict surfaces. For dataset reviewers, the payload explains both the scaling formula and the assumption IDs that triggered it.

This document serves as the production-ready reference for the immutability guards and horizon scaling approach, so future reviewers can see exactly which assumptions were enforced and why the time-horizon mismatch fix keeps ratios consistent.
