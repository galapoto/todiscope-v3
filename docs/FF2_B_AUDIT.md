# FF-2.B — Agent 2 (Audit Track B)

## Architecture & Risk Auditor — FF-2 Structural Correctness Audit

**Date:** 2025-01-XX  
**Auditor:** Agent 2 — Architecture & Risk Auditor  
**Scope:** FF-2 structural audit against v3 platform laws

---

## BINARY CHECKS

### Check 1: artifact_store Ownership

**Requirement:** Only core accesses artifact_store; engine uses core FX service only.

**Evidence:**
- Core FX service (`backend/app/core/artifacts/fx_service.py`) accesses `artifact_store` ✓
- Engine (`backend/app/engines/financial_forensics/run.py`) imports from `backend.app.core.artifacts.fx_service` ✓
- Engine uses `load_fx_artifact_for_dataset()` from core service ✓
- No direct `get_artifact_store()` calls in engine code ✓
- Engine conversion logic (`fx_convert.py`) has no artifact_store access ✓

**Result:** **PASS**

---

### Check 2: Immutability Enforcement

**Requirement:** FX artifact payload immutable; no overwrite or mutation paths.

**Evidence:**
- Core FX service checks for existing artifact by `dataset_version_id` + `checksum` before creating ✓
- If existing artifact found with same checksum, returns existing (idempotent) ✓
- Artifact key includes checksum: `core/fx/{dataset_version_id}/{checksum}.json` ✓
- Checksum verification on load: `verify_sha256(raw, row.checksum)` ✓
- No update/overwrite methods in FX service ✓

**Potential Issue:**
- Core FX service uses `datetime.now(timezone.utc)` for `created_at` timestamp (line 92)
- This is metadata-only (not part of payload checksum), but violates "no datetime.now()" rule

**Result:** **FAIL** (datetime.now() usage in core FX service)

---

### Check 3: DatasetVersion Law

**Requirement:** FX artifacts bound to dataset_version_id; no implicit dataset usage.

**Evidence:**
- FX artifact model has `dataset_version_id` as required FK ✓
- `create_fx_artifact()` requires `dataset_version_id` parameter ✓
- `load_fx_artifact_for_dataset()` verifies `dataset_version_id` matches ✓
- Engine validates `dataset_version_id` at entry ✓
- No "latest dataset" helpers found ✓

**Result:** **PASS**

---

### Check 4: Scope Discipline

**Requirement:** No analytics, matching, or leakage code present; no report persistence beyond in-memory.

**Evidence:**
- No matching logic found in engine code ✓
- No leakage/analytics code found ✓
- No findings generation code found ✓
- Report sections returned in-memory only (no artifact persistence) ✓
- Normalization code is pure transformation (no aggregation) ✓

**Result:** **PASS**

---

### Check 5: Forbidden Patterns

**Requirement:** No live FX fetching; no datetime.now() or environment time usage; no float arithmetic in FX conversion.

**Evidence:**
- **Live FX fetching:** No `requests`, `urllib`, `aiohttp`, `httpx` imports in engine ✓
- **datetime.now() usage:** 
  - Engine `run.py` line 95: `started_at=datetime.now(timezone.utc)` — **VIOLATION** (run metadata timestamp)
  - Core FX service line 92: `created_at=datetime.now(timezone.utc)` — **VIOLATION** (artifact metadata timestamp)
- **Float arithmetic:** 
  - `fx_convert.py` uses `Decimal` only, no float arithmetic ✓
  - Conversion logic: `(amount_original * rate).quantize(...)` uses Decimal ✓

**Result:** **FAIL** (datetime.now() violations)

---

## OVERALL VERDICT

**Status:** **REMEDIATION REQUIRED**

**Pass:** 3/5  
**Fail:** 2/5

---

## VIOLATIONS FOUND

### Violation 1: datetime.now() Usage in Engine Run Metadata

**File:** `backend/app/engines/financial_forensics/run.py`  
**Line:** 95

**Issue:**
```python
started_at=datetime.now(timezone.utc),
```

**Why it violates v3:**
- FF-2 forbidden patterns explicitly prohibit `datetime.now()` usage
- Time-dependent logic breaks determinism
- Run metadata timestamps should be provided as input or use deterministic source

**Required Fix:**
- Accept `started_at` as parameter (with default None for backward compatibility)
- Or use deterministic timestamp source (e.g., from run_id UUID timestamp if UUIDv7)
- Or remove timestamp requirement for FF-2 (metadata-only, not part of replay)

**Blocking:** **YES** — Violates forbidden patterns requirement

---

### Violation 2: datetime.now() Usage in Core FX Service

**File:** `backend/app/core/artifacts/fx_service.py`  
**Line:** 92

**Issue:**
```python
created_at=datetime.now(timezone.utc),
```

**Why it violates v3:**
- FF-2 forbidden patterns explicitly prohibit `datetime.now()` usage
- Even in core, timestamp creation breaks determinism
- Artifact metadata timestamps should be deterministic or provided as input

**Required Fix:**
- Accept `created_at` as parameter (optional, defaults to deterministic source)
- Or use deterministic timestamp (e.g., from artifact_id UUID if UUIDv7)
- Or remove timestamp requirement for FF-2 (metadata-only, not part of checksum)

**Blocking:** **YES** — Violates forbidden patterns requirement

---

## POSITIVE FINDINGS

### ✅ artifact_store Ownership Correct

Engine correctly uses core FX service (`fx_service.py`) instead of directly accessing `artifact_store`. This is the correct architectural pattern.

### ✅ Immutability Enforcement Correct

FX artifacts are content-addressed by checksum, preventing overwrite. Idempotent creation ensures same payload → same artifact.

### ✅ DatasetVersion Law Enforced

All FX artifacts are bound to `dataset_version_id` with explicit validation and verification.

### ✅ Scope Discipline Maintained

No analytics, matching, or leakage code present. Reports are in-memory only.

### ✅ No Float Arithmetic

FX conversion uses `Decimal` exclusively, ensuring deterministic arithmetic.

---

## CONCLUSION

**Status:** REMEDIATION REQUIRED

**DO NOT PROCEED to FF-3 until:**
- `datetime.now()` usage removed from engine run metadata
- `datetime.now()` usage removed from core FX service metadata
- Timestamps use deterministic sources or are provided as inputs

**Remediation Priority:** **HIGH** — Both violations are in metadata creation, which should be deterministic for replay integrity.

---

**END OF FF-2.B AUDIT**


