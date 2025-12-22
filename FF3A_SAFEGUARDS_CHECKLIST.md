# FF-3.A — Defensive Constraints Checklist (Canonical Implementation)

**Date:** 2025-01-XX  
**Implementer:** Agent 2 — Build Track B  
**Goal:** Canonical models, schemas, emitters, and enforcement tests for FF-3

---

## 1. CONFIDENCE SYSTEM (CANONICAL)

### ✅ Implemented

**File:** `backend/app/engines/financial_forensics/confidence.py`

**Features:**
- ✅ Confidence enum (exact | within_tolerance | partial | ambiguous)
- ✅ Central assignment function (`assign_confidence()`)
- ✅ Rule → confidence mapping table (`RULE_CONFIDENCE_MAPPING`)
- ✅ Rule mapping function (`map_rule_to_confidence()`)

**Rules:**
- ✅ No free text (enum only)
- ✅ No contextual override (enum is immutable)
- ✅ Deterministic mapping only (table-based)

**Tests:** `backend/tests/engine_financial_forensics/ff3_evidence/test_confidence_enum.py`
- `test_confidence_must_be_enum()` — BUILD FAILURE if free text allowed
- `test_confidence_enum_values_locked()` — BUILD FAILURE if enum values change

---

## 2. FINDING MODEL (ENGINE-OWNED)

### ✅ Implemented

**File:** `backend/app/engines/financial_forensics/models/findings.py`

**Fields (all mandatory):**
- ✅ `finding_id` (PK)
- ✅ `dataset_version_id` (FK, required, indexed)
- ✅ `rule_id` (required, indexed)
- ✅ `rule_version` (required)
- ✅ `confidence` (required, enum-constrained)
- ✅ `matched_record_ids` (required, JSON array)
- ✅ `unmatched_amount` (optional, Decimal as string)
- ✅ `fx_artifact_id` (FK, required)
- ✅ `evidence_ids` (required, JSON array, default empty)
- ✅ `created_at` (required, deterministic source)

**Constraints:**
- ✅ Confidence check constraint (enum values only)
- ✅ All fields documented as mandatory/optional

---

## 3. EVIDENCE SCHEMA V1 (HARD REQUIREMENT)

### ✅ Implemented

**File:** `backend/app/engines/financial_forensics/evidence_schema_v1.py`

**Schema Components:**
- ✅ `RuleIdentityEvidence` — Rule identity + version + executed parameters
- ✅ `ToleranceEvidence` — Tolerance values (if used)
- ✅ `AmountComparisonEvidence` — Amount comparisons (original + converted)
- ✅ `DateComparisonEvidence` — Date comparisons
- ✅ `ReferenceComparisonEvidence` — Reference comparisons
- ✅ `CounterpartyEvidence` — Counterparty logic
- ✅ `MatchSelectionRationale` — Match-selection rationale
- ✅ `PrimarySourceLinks` — Primary source links

**Validation:**
- ✅ `validate_evidence_schema_v1()` — Comprehensive validation
- ✅ All required fields validated
- ✅ Nested field validation

**Tests:** `backend/tests/engine_financial_forensics/ff3_evidence/test_evidence_completeness.py`
- `test_evidence_schema_must_be_complete()` — BUILD FAILURE if incomplete
- `test_evidence_must_have_all_required_fields()` — BUILD FAILURE if fields missing

---

## 4. EVIDENCE EMISSION ENGINE

### ✅ Implemented

**File:** `backend/app/engines/financial_forensics/evidence.py`

**Features:**
- ✅ `emit_finding_evidence()` — One evidence bundle per finding
- ✅ Evidence schema validation before emission
- ✅ Deterministic evidence ID generation
- ✅ Immutable evidence records
- ✅ Dataset-bound evidence
- ✅ Replayable (deterministic ID)

**Integration:**
- ✅ Uses core evidence service (`create_evidence()`)
- ✅ Validates evidence schema v1 before emission
- ✅ Converts evidence schema to payload dict

---

## 5. REVIEW-FIRST INTEGRATION

### ✅ Implemented

**File:** `backend/app/engines/financial_forensics/review_integration.py`

**Features:**
- ✅ Immutable findings (no mutation/deletion)
- ✅ Review actions as separate artifacts (`create_finding_review_action()`)
- ✅ Guard functions (`guard_finding_immutability()`)
- ✅ Default review state creation (`ensure_default_review_state()`)

**Integration:**
- ✅ Uses core review service (`ensure_review_item()`)
- ✅ Review actions create new artifacts only
- ✅ Findings never mutated or deleted

---

## 6. DETERMINISM ENFORCEMENT TESTS

### ✅ Implemented

**Directory:** `backend/tests/engine_financial_forensics/ff3_determinism/`

**Tests (BUILD FAILURE on violations):**

**Rule Ordering:**
- ✅ `test_rule_ordering_must_be_explicit()` — FAILS if priority not explicit
- ✅ `test_no_dict_set_iteration()` — FAILS if dict/set used for ordering

**File:** `backend/tests/engine_financial_forensics/ff3_determinism/test_rule_ordering.py`

**DateTime Forbidden:**
- ✅ `test_no_datetime_now_in_matching()` — FAILS if datetime.now() found

**File:** `backend/tests/engine_financial_forensics/ff3_determinism/test_datetime_forbidden.py`

**Float Arithmetic Forbidden:**
- ✅ `test_no_float_arithmetic_in_matching()` — FAILS if float arithmetic found

**File:** `backend/tests/engine_financial_forensics/ff3_determinism/test_float_forbidden.py`

**Evidence Completeness:**
- ✅ `test_evidence_schema_must_be_complete()` — FAILS if evidence incomplete
- ✅ `test_evidence_must_have_all_required_fields()` — FAILS if fields missing

**File:** `backend/tests/engine_financial_forensics/ff3_evidence/test_evidence_completeness.py`

**Confidence Enum:**
- ✅ `test_confidence_must_be_enum()` — FAILS if free text allowed
- ✅ `test_confidence_enum_values_locked()` — FAILS if enum values change

**File:** `backend/tests/engine_financial_forensics/ff3_evidence/test_confidence_enum.py`

---

## SUMMARY

### Files Created/Enhanced

1. **`backend/app/engines/financial_forensics/confidence.py`** — Enhanced with rule mapping table
2. **`backend/app/engines/financial_forensics/models/findings.py`** — Enhanced with all mandatory fields
3. **`backend/app/engines/financial_forensics/evidence_schema_v1.py`** — Complete evidence schema v1
4. **`backend/app/engines/financial_forensics/evidence.py`** — Enhanced evidence emission engine
5. **`backend/app/engines/financial_forensics/review_integration.py`** — Enhanced review-first integration
6. **`backend/tests/engine_financial_forensics/ff3_determinism/test_rule_ordering.py`** — Rule ordering tests
7. **`backend/tests/engine_financial_forensics/ff3_determinism/test_datetime_forbidden.py`** — DateTime tests
8. **`backend/tests/engine_financial_forensics/ff3_determinism/test_float_forbidden.py`** — Float arithmetic tests
9. **`backend/tests/engine_financial_forensics/ff3_evidence/test_evidence_completeness.py`** — Evidence completeness tests
10. **`backend/tests/engine_financial_forensics/ff3_evidence/test_confidence_enum.py`** — Confidence enum tests

### Safeguards Implemented

✅ **Confidence System:** Canonical enum, rule mapping table, no free text  
✅ **Finding Model:** Engine-owned table with all mandatory fields  
✅ **Evidence Schema v1:** Complete schema with all required fields  
✅ **Evidence Emission:** One bundle per finding, immutable, dataset-bound  
✅ **Review-First Integration:** Immutable findings, review as artifacts  
✅ **Determinism Enforcement:** BUILD FAILURE tests for all violations

### Test Coverage

- **Rule Ordering:** 2 BUILD FAILURE tests
- **DateTime Forbidden:** 1 BUILD FAILURE test
- **Float Arithmetic Forbidden:** 1 BUILD FAILURE test
- **Evidence Completeness:** 2 BUILD FAILURE tests
- **Confidence Enum:** 2 BUILD FAILURE tests

**Total: 8 BUILD FAILURE tests**

---

## STOP CONDITION

**FF-3 cannot produce a finding without full evidence + locked semantics.**

All canonical models, schemas, emitters, and enforcement tests implemented. FF-3 is protected against:
- Non-deterministic rule ordering
- Free-text confidence values
- Incomplete evidence
- datetime.now() usage
- Float arithmetic
- Finding mutation/deletion

**BUILD WILL FAIL if any violation is detected.**

---

**END OF FF-3.A CHECKLIST**


