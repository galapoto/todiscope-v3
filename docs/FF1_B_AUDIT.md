# FF-1.B — Agent 2 Audit Report
## Architecture & Risk Auditor — FF-1 Structural Correctness Verification

**Date:** 2025-01-XX  
**Auditor:** Agent 2 — Architecture & Risk Auditor  
**Scope:** FF-1 structural audit (binary checks)

---

## BINARY CHECKS

### Check 1: Core / Engine Separation

**Requirement:** Engine code lives only under engines/; no domain logic leaked into core.

**Evidence:**
- Engine code located in `backend/app/engines/financial_forensics/` ✓
- Core directory structure verified: `backend/app/core/` contains only mechanics ✓
- Grep search for domain nouns (financial, finance, invoice, payment, leakage) in core: **0 matches** ✓

**Result:** **PASS**

---

### Check 2: Kill-Switch Strength

**Requirement:** Disabled engine exposes no routes; disabled engine performs zero DB writes.

**Evidence:**
- `mount_enabled_engine_routers()` only mounts routers if `is_engine_enabled()` returns True ✓
- `run_engine()` checks `is_engine_enabled()` before any DB operations ✓
- Test `test_engine_disabled_run_fails` verifies disabled engine returns 404 ✓
- Disabled engine cannot reach `run_engine()` function (route not mounted) ✓

**Result:** **PASS**

---

### Check 3: Owned-Table Isolation

**Requirement:** Engine writes only to declared run table; no access to other engine tables; no access to core tables except via allowed interfaces.

**Evidence:**
- Engine declares owned table: `("engine_financial_forensics_runs",)` ✓
- Model enforces table name: `__tablename__ = "engine_financial_forensics_runs"` ✓
- Only DB write operation: `db.add(run)` where `run` is `FinancialForensicsRun` ✓
- Test `test_engine_writes_only_run_table` verifies only owned table exists after run ✓
- No writes to other engine tables (no other engine models imported) ✓
- No direct writes to core tables (only reads DatasetVersion via select) ✓

**Result:** **PASS**

---

### Check 4: DatasetVersion Law

**Requirement:** Engine never infers or defaults dataset_version_id; no "latest dataset" helpers exist.

**Evidence:**
- `_validate_dataset_version_id()` explicitly validates at entry (no defaults) ✓
- `run_engine()` requires explicit `dataset_version_id` parameter (no default) ✓
- No "latest dataset" helpers found in engine code ✓
- No `dataset_version_id = None` defaults found ✓
- Test `test_missing_dataset_version_id_hard_fails` verifies missing ID fails ✓

**Result:** **PASS**

---

### Check 5: Absence of Future Logic

**Requirement:** No FX handling; no normalization logic; no matching/analytics.

**Evidence:**
- No FX/currency handling found (grep: 0 matches) ✓
- No normalization logic found (grep: 0 matches) ✓
- No matching/analytics found (grep: 0 matches for match, matching, finding, leakage, exposure, typology) ✓
- Only "findings: 0" in stub report (acceptable for FF-1 skeleton) ✓

**Result:** **PASS**

---

### Check 6: Forbidden Patterns

**Requirement:** No imports from other engines; no artifact_store usage; no review workflow usage.

**Evidence:**
- **Cross-engine imports:** No imports from other engines (only imports from same engine: `engine.py`, `models.py`) ✓
- **artifact_store usage:** **VIOLATION FOUND**
  - File: `backend/app/engines/financial_forensics/run.py`
  - Line 9: `from backend.app.core.artifacts.store import get_artifact_store`
  - Line 106: `store = get_artifact_store()`
  - Note: Code has comment saying "allowed in FF-1 for stub reports" but requirement is explicit: "No artifact_store usage"
- **Review workflow usage:** No review workflow imports or usage found ✓

**Result:** **FAIL** (artifact_store usage violation)

---

## OVERALL VERDICT

**Status:** **REMEDIATION REQUIRED**

**Pass:** 5/6  
**Fail:** 1/6

---

## VIOLATIONS

### Violation 1: artifact_store Usage

**File:** `backend/app/engines/financial_forensics/run.py`

**Lines:** 9, 106

**Issue:**
- Engine directly imports and uses `get_artifact_store()`
- Requirement states: "No artifact_store usage"
- Code comment says "allowed in FF-1 for stub reports" but requirement is explicit

**Required Fix:**
- Remove direct `artifact_store` access from engine
- Use core service that wraps artifact_store (if needed for FF-1)
- Or remove artifact_store usage entirely for FF-1 skeleton

**Blocking:** **YES** — Violates forbidden patterns requirement

---

## REMEDIATION REQUIRED

**DO NOT PROCEED** to FF-2 until violation is resolved.

**Required Action:**
1. Remove `get_artifact_store()` import and usage from `run.py`
2. Either:
   - Remove artifact storage from FF-1 (stub report can be in-memory only)
   - Or create core service wrapper that engine can use (if artifact storage is required for FF-1)

**Estimated Time:** 1-2 hours

---

**END OF FF-1.B AUDIT**


