# FF-4 v1 Lock Enforcement Tests Summary

## Task 4 — Coverage Enforcement Tests (Completed)

### Purpose
These tests **FAIL** if critical FF-4 v1 behaviors are changed, permanently locking the v1 implementation.

---

## Tests Implemented

### 1. Typology Enum v1 Lock
**Test:** `test_typology_enum_v1_lock()`

**Fails if:**
- Any typology is added to the enum
- Any typology is removed from the enum
- Typology names change

**Locked v1 set:**
- `UNMATCHED_INVOICE`
- `UNMATCHED_PAYMENT`
- `OVERPAYMENT`
- `UNDERPAYMENT`
- `TIMING_MISMATCH`
- `PARTIAL_SETTLEMENT_RESIDUAL`

---

### 2. Timing Mismatch Rule v1 Lock
**Tests:**
- `test_timing_mismatch_rule_v1_lock()`: Functional test that timing mismatch rule works
- `test_timing_mismatch_rule_code_exists()`: Structural test that timing mismatch code exists

**Fails if:**
- Timing mismatch rule is removed from classifier
- `_check_timing_mismatch()` function is removed
- `timing_inconsistency_days_threshold` parameter is removed
- `TIMING_MISMATCH` typology reference is removed
- Timing mismatch no longer produces `TIMING_MISMATCH` typology

**Locked behavior:**
- Matched amounts with date delta beyond threshold → `TIMING_MISMATCH`
- Rule 2 priority (after partial_match, before amount-based)

---

### 3. Partial Exposure Binding v1 Lock
**Tests:**
- `test_partial_exposure_binding_v1_lock()`: Functional test that partial_match maps correctly
- `test_partial_exposure_binding_priority_v1_lock()`: Test that partial_match takes priority

**Fails if:**
- `partial_match` findings no longer map to `PARTIAL_SETTLEMENT_RESIDUAL`
- Partial match binding priority changes (must be Rule 1, highest priority)
- Partial match rationale changes

**Locked behavior:**
- `partial_match` → `PARTIAL_SETTLEMENT_RESIDUAL` (Rule 1, highest priority)
- Takes priority over timing mismatch and amount-based classification

---

### 4. Exposure Source v1 Lock
**Tests:**
- `test_exposure_source_diff_converted_v1_lock()`: Functional test that diff_converted is used
- `test_exposure_source_code_uses_diff_converted()`: Structural test that code uses diff_converted

**Fails if:**
- Classifier switches to computing exposure from `invoice_amount - sum_counterpart_amount`
- `_extract_diff_converted()` function is removed
- Code no longer references `diff_converted` from evidence
- Exposure is computed from comparison math instead of using stored `diff_converted`

**Locked behavior:**
- Must use `diff_converted` from `evidence_payload["amount_comparison"]["diff_converted"]`
- Must NOT compute exposure from `invoice_amount_original - sum_counterpart_amount_original`
- Exposure source is locked to evidence payload, not computed values

---

### 5. Classification Rules Order v1 Lock
**Test:** `test_classification_rules_order_v1_lock()`

**Fails if:**
- Rule priority order changes
- Rule 1 (partial_match) no longer has highest priority
- Rule 2 (timing_mismatch) no longer has priority over Rule 3 (amount-based)

**Locked order:**
1. Rule 1: Partial match → `PARTIAL_SETTLEMENT_RESIDUAL` (highest priority)
2. Rule 2: Timing mismatch → `TIMING_MISMATCH` (if threshold exceeded)
3. Rule 3: Amount-based → `OVERPAYMENT` (diff < 0) or `UNDERPAYMENT` (diff > 0)

---

### 6. All Typologies Have Mapping Rules
**Test:** `test_all_v1_typologies_have_mapping_rules()`

**Fails if:**
- Any typology loses its mapping rule
- Any typology cannot be produced from a finding
- Mapping rules are broken or removed

**Locked mappings:**
- `PARTIAL_SETTLEMENT_RESIDUAL`: Rule 1 (partial_match)
- `TIMING_MISMATCH`: Rule 2 (date delta > threshold)
- `OVERPAYMENT`: Rule 3 (diff < 0)
- `UNDERPAYMENT`: Rule 3 (diff > 0)
- `UNMATCHED_INVOICE` / `UNMATCHED_PAYMENT`: Not from findings (handled separately)

---

## Test File

**Location:** `backend/tests/engine_financial_forensics/ff4_classifier/test_v1_lock_enforcement.py`

**Total Tests:** 8 tests that lock FF-4 v1 behavior

---

## Enforcement Strategy

These tests use a combination of:
1. **Functional tests**: Verify behavior works as expected
2. **Structural tests**: Verify code structure (function names, parameters, references)
3. **Enum validation**: Verify typology enum matches locked set
4. **Priority tests**: Verify rule order and priority

All tests include clear error messages explaining what was changed and why it's locked.

---

## Status

✅ **Complete** — All v1 lock enforcement tests implemented

**FF-4 v1 is now permanently locked against:**
- Typology enum changes
- Timing mismatch rule removal
- Partial exposure binding changes
- Exposure source switching to comparison math
- Rule order changes
- Mapping rule removal


