# FF-2.A — Defensive Constraints Checklist

**Date:** 2025-01-XX  
**Implementer:** Agent 2 — Build Track B  
**Goal:** Ensure determinism, immutability, and no hidden defaults in FF-2

---

## 1. FX IMMUTABILITY GUARDS

### ✅ Implemented

**File:** `backend/app/core/artifacts/guards.py`

**Functions:**
- `store_fx_artifact_immutable()` — Prevents overwrite, verifies checksum
- `get_fx_artifact_with_verification()` — Verifies checksum on retrieval

**Guards:**
- ✅ Prevents FX artifact mutation (immutable storage)
- ✅ Disallows overwrite of artifact payload (raises `FXArtifactOverwriteError`)
- ✅ Fails if checksum mismatch (raises `FXArtifactChecksumMismatchError`)

**Tests:** `backend/tests/engine_financial_forensics/test_ff2_fx_immutability.py`
- `test_fx_artifact_immutable_no_overwrite()` — Verifies overwrite prevention
- `test_fx_artifact_checksum_verification()` — Verifies checksum validation

---

## 2. EXPLICIT-FAILURE ENFORCEMENT

### ✅ Implemented

**File:** `backend/app/engines/financial_forensics/fx.py`

**Error Classes:**
- `FXArtifactMissingError` — Missing FX artifact
- `FXArtifactNotFoundError` — FX artifact not found
- `UnknownCurrencyError` — Unknown currency code
- `DuplicateFXArtifactIDError` — Duplicate artifact ID

**Guards:**
- ✅ Missing FX artifact → hard fail (`FXArtifactMissingError`)
- ✅ Unknown currency → hard fail (`UnknownCurrencyError`)
- ✅ Duplicate FX artifact ID → reject (`DuplicateFXArtifactIDError`)

**Tests:** `backend/tests/engine_financial_forensics/test_ff2_fx_immutability.py`
- `test_fx_artifact_missing_hard_fails()` — Verifies missing artifact fails
- `test_fx_artifact_not_found_hard_fails()` — Verifies not found fails
- `test_unknown_currency_hard_fails()` — Verifies invalid currency fails
- `test_duplicate_fx_artifact_id_rejected()` — Verifies duplicate ID rejection

---

## 3. CANONICAL SCOPE GUARDS

### ✅ Implemented

**File:** `backend/app/engines/financial_forensics/normalization.py`

**Error Classes:**
- `EnrichmentImportError` — Enrichment import attempted
- `AccountingAssumptionError` — Accounting assumption made
- `CanonicalTypeInvalidError` — Invalid record type
- `CanonicalCurrencyInvalidError` — Invalid currency
- `CanonicalDirectionInvalidError` — Invalid direction

**Guards:**
- ✅ No enrichment imports (structural check — no enrichment modules imported)
- ✅ No accounting assumptions (direction normalized, not computed)
- ✅ No aggregation logic (single record processing only)

**Tests:** `backend/tests/engine_financial_forensics/test_ff2_canonical_scope.py`
- `test_canonical_normalization_no_enrichment()` — Verifies no enrichment fields
- `test_canonical_normalization_no_accounting_assumptions()` — Verifies no accounting logic
- `test_canonical_normalization_no_aggregation()` — Verifies no aggregation
- `test_canonical_invalid_type_hard_fails()` — Verifies invalid type fails
- `test_canonical_invalid_currency_hard_fails()` — Verifies invalid currency fails
- `test_canonical_invalid_direction_hard_fails()` — Verifies invalid direction fails
- `test_canonical_uses_decimal_not_float()` — Verifies Decimal usage

---

## 4. REPLAY SAFETY TESTS

### ✅ Implemented

**File:** `backend/tests/engine_financial_forensics/test_ff2_replay_safety.py`

**Tests:**
- ✅ `test_same_inputs_identical_outputs()` — Same inputs → bitwise-identical outputs
- ✅ `test_different_fx_artifact_different_outputs()` — Different FX artifact → different outputs
- ✅ `test_fx_artifact_sha256_deterministic()` — Canonicalization produces deterministic sha256

**Verification:**
- Same `dataset_version_id` + same `parameters` + same FX artifact sha256 → identical outputs
- Different FX artifact sha256 → different outputs

---

## 5. FORBIDDEN PATTERNS

### ✅ Implemented

**File:** `backend/tests/test_ff2_forbidden_patterns.py`

**Structural Assertions:**
- ✅ `test_no_live_fx_calls()` — No live FX API calls (requests, urllib, aiohttp, etc.)
- ✅ `test_no_datetime_now_usage()` — No `datetime.now()`, `date.today()`, `time.time()`
- ✅ `test_no_float_arithmetic_in_fx()` — FX conversion uses Decimal, not float
- ✅ `test_fx_conversion_uses_decimal_type()` — Runtime verification of Decimal type

**Runtime Verification:**
- FX conversion uses `Decimal` arithmetic only (no float)
- No live FX API calls in engine code
- No time-dependent logic (`datetime.now()`)

**Tests:** `backend/tests/engine_financial_forensics/test_ff2_fx_immutability.py`
- `test_fx_conversion_deterministic()` — Verifies deterministic conversion
- `test_fx_conversion_uses_decimal_not_float()` — Verifies Decimal usage

---

## SUMMARY

### Files Created

1. **`backend/app/core/artifacts/guards.py`** — FX immutability guards
2. **`backend/app/engines/financial_forensics/fx.py`** — FX artifact handling
3. **`backend/app/engines/financial_forensics/normalization.py`** — Canonical normalization
4. **`backend/tests/engine_financial_forensics/test_ff2_fx_immutability.py`** — FX immutability tests
5. **`backend/tests/engine_financial_forensics/test_ff2_canonical_scope.py`** — Canonical scope tests
6. **`backend/tests/engine_financial_forensics/test_ff2_replay_safety.py`** — Replay safety tests
7. **`backend/tests/test_ff2_forbidden_patterns.py`** — Forbidden patterns tests

### Safeguards Implemented

✅ **FX Immutability:** Overwrite prevention, checksum verification  
✅ **Explicit Failures:** Missing artifact, unknown currency, duplicate ID  
✅ **Canonical Scope:** No enrichment, no accounting assumptions, no aggregation  
✅ **Replay Safety:** Deterministic outputs, FX artifact binding  
✅ **Forbidden Patterns:** No live FX, no datetime.now(), no float arithmetic

### Test Coverage

- **FX Immutability:** 8 tests
- **Canonical Scope:** 7 tests
- **Replay Safety:** 3 tests
- **Forbidden Patterns:** 4 structural assertions

---

## STOP CONDITION

**FF-2 cannot drift into non-determinism.**

All safeguards implemented and tested. FF-2 is protected against:
- FX artifact mutation
- Hidden defaults
- Non-deterministic behavior
- Live FX calls
- Float arithmetic
- Time-dependent logic

---

**END OF FF-2.A CHECKLIST**


