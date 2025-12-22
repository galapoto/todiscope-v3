# Audit Report — Engine #5 Reporting, Externalization & Hardening

**Engine:** Engine #5 — Enterprise Deal & Transaction Readiness  
**Scope:** Reporting, Externalization (JSON/PDF), Hardening  
**Code Reviewed:** `backend/app/engines/enterprise_deal_transaction_readiness/`  
**Boundary Reference:** `docs/engines/enterprise_deal_transaction_readiness/DR1_BOUNDARY.md`  
**Audit Date:** 2025-12-21  
**Status:** ❌ **FAIL — REMEDIATION REQUIRED**

---

## Executive Summary

Engine #5 has a working reporting pipeline, external view creation, and deterministic JSON/PDF export to the core artifact store. Kill-switch checks exist at mount-time and runtime, and optional inputs can produce findings/evidence without hard-failing.

The build is **not audit-passable** for external sharing because the external report can leak internal artifact store keys and other sensitive provenance details via evidence payloads. Additionally, the report template does not include an explicit, structured **transaction scope validation summary** or a dedicated **error-handling summary** section as required by this audit’s scope.

---

## 1) Reporting Audit

### What Exists (✅)

- Deterministic report assembler with structured `sections`: `backend/app/engines/enterprise_deal_transaction_readiness/report/assembler.py`
- Required report sections present:
  - Executive overview, findings, checklist status (placeholder), evidence index, limitations/uncertainty, explicit non-claims
  - Internal-only run parameters section: `backend/app/engines/enterprise_deal_transaction_readiness/report/sections.py`
- Evidence linkage is present:
  - Findings include `evidence_id`
  - Evidence index includes evidence records and payloads

### Gaps (⚠️)

- **Transaction scope validation summary is implicit only.**
  - The engine validates `transaction_scope` at run time, but the report does not include an explicit “validation outcome” section/field (e.g., schema version, validated keys, validation status).
- **Error-handling summary is not explicit.**
  - Missing/invalid optional inputs produce findings, but the report lacks a dedicated “errors / execution summary” section (counts by type, mandatory-vs-optional classification, validation failures prevented at entry, etc.).
- Checklist is present as a section but currently a placeholder (`checklist_items` empty); acceptable only if explicitly treated as “not implemented” in release criteria.

**Reporting Result:** ⚠️ **PARTIAL** (structure + evidence links OK, but missing explicit summaries required by audit scope)

---

## 2) Externalization Audit (PDF + JSON)

### What Exists (✅)

- External view policy and enforcement:
  - Policy: `backend/app/engines/enterprise_deal_transaction_readiness/externalization/policy.py`
  - View creation + validation: `backend/app/engines/enterprise_deal_transaction_readiness/externalization/views.py`
- Export supports JSON + PDF and stores immutably in core artifact store:
  - Exporter: `backend/app/engines/enterprise_deal_transaction_readiness/externalization/exporter.py`
  - Immutable write mechanics: `backend/app/core/artifacts/externalization_service.py`
  - Deterministic PDF generation: `backend/app/engines/enterprise_deal_transaction_readiness/pdf.py`
- API surface:
  - `/report` supports `view_type` internal/external
  - `/export` supports `formats: ["json","pdf"]` and returns artifact URIs
  - `backend/app/engines/enterprise_deal_transaction_readiness/engine.py`

### Critical Finding (❌)

**External view can leak internal artifact store keys and provenance details via evidence payloads.**

- Evidence payloads currently include fields like `artifact_key` under `detail` for optional input findings.
- The externalization policy does **not** redact `artifact_key` (or other provenance keys) in nested structures:
  - `backend/app/engines/enterprise_deal_transaction_readiness/externalization/policy.py`
  - Validation only checks keys listed in `redacted_fields`: `backend/app/engines/enterprise_deal_transaction_readiness/externalization/views.py`
- Since `evidence_index` is an external-shareable section, the external JSON export can include these internal keys.

**Externalization Result:** ❌ **FAIL** (external sharing safety violation)

---

## 3) Hardening Audit

### Kill-Switch (✅)

- Mount-time gating: `backend/app/core/engine_registry/mount.py`
- Runtime gating at all engine endpoints: `backend/app/engines/enterprise_deal_transaction_readiness/engine.py`
- Runtime gating inside callable `run_engine` before side effects: `backend/app/engines/enterprise_deal_transaction_readiness/run.py`

### Edge Case Handling (⚠️)

- Optional input validation requires `sha256` (strict) and enforces hex length; good for determinism.
- `started_at` is required/timezone aware; good.
- Report/export endpoints validate `dataset_version_id` format (UUIDv7) but do not explicitly verify dataset existence; practically acceptable because reports are bound to persisted runs, but should be consistent with “hard-fail on unknown DatasetVersion” expectations if report routes can be invoked independently.

### Performance/Scalability (✅/⚠️)

- Queries are filtered by indexed fields (`dataset_version_id`, `result_set_id`); stable ordering is applied.
- No large dataset processing yet; scalability cannot be fully assessed until checklists and pack manifests exist.

**Hardening Result:** ⚠️ **PARTIAL** (kill-switch OK; some consistency gaps)

---

## PASS/FAIL Determination

**FAIL** due to externalization safety violation (leaking `artifact_key` / provenance details in external exports), plus missing explicit transaction scope validation and error-summary sections in the report template (per this audit scope).

---

## Required Remediation (Must Fix Before Re-Audit)

1. **External view redaction hardening**
   - Add redaction/anonymization for provenance keys inside evidence payloads (at minimum: `artifact_key`, `expected_sha256`, and any internal source identifiers).
   - Ensure recursive validation catches those keys (extend `redacted_fields` and/or add a stricter validator for evidence payload structures).

2. **Report template completeness**
   - Add an explicit **transaction scope validation** section/summary (validated status + scope identifier + hash).
   - Add an explicit **error-handling / execution summary** section (mandatory input validation pass, optional prereq findings counts by kind, export status).

3. **Export determinism + external safety regression tests**
   - Add tests asserting external exports do not contain banned keys (e.g., `"artifact_key"` anywhere in the exported JSON).

---

## Notes (Implemented Correctly)

- Deterministic export bytes for same input set via `result_set_id` and canonical JSON serialization.
- Immutable export semantics enforced by `put_bytes_immutable` (rejects overwrites with different bytes).
- Evidence is core-owned (`evidence_records`) and referenced by findings, consistent with platform law boundaries.

