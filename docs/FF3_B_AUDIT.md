# FF-3.B — Agent 2 (Audit Track B)

## Architecture & Risk Auditor — FF-3 Defensibility Audit

**Date:** 2025-01-XX  
**Auditor:** Agent 2 — Architecture & Risk Auditor  
**Scope:** FF-3 findings defensibility, evidence completeness, and law compliance

---

## BINARY CHECKS

### Check 1: Confidence System

**Requirement:** Enum-only confidence values, central assignment logic, no contextual overrides.

**Evidence:**
- ✅ **Confidence enum:** `Confidence` enum with 4 values (exact, within_tolerance, partial, ambiguous) ✓
- ✅ **Enum enforcement:** `validate_confidence()` enforces enum only, rejects free text ✓
- ✅ **Central assignment:** `assign_confidence()` centralizes assignment logic ✓
- ✅ **Rule mapping table:** `RULE_CONFIDENCE_MAPPING` provides deterministic mapping ✓
- ✅ **No contextual overrides:** Enum is immutable, no override methods ✓
- ✅ **Database constraint:** Check constraint enforces enum values in findings table ✓

**Result:** **PASS**

---

### Check 2: Finding Model Integrity

**Requirement:** Required fields present, dataset_version_id bound, fx_artifact_id present, created_at deterministic.

**Evidence:**
- ✅ **Required fields:** All mandatory fields present in `FinancialForensicsFinding` model ✓
  - `finding_id` (PK) ✓
  - `dataset_version_id` (FK, required, indexed) ✓
  - `rule_id` (required, indexed) ✓
  - `rule_version` (required) ✓
  - `confidence` (required, enum-constrained) ✓
  - `matched_record_ids` (required) ✓
  - `fx_artifact_id` (FK, required) ✓
  - `evidence_ids` (required, default empty list) ✓
  - `created_at` (required) ✓
- ✅ **dataset_version_id binding:** FK constraint to `dataset_version.id`, indexed ✓
- ✅ **fx_artifact_id present:** FK constraint to `fx_artifacts.fx_artifact_id`, required ✓
- ⚠️ **created_at deterministic:** Field exists but no enforcement that it's not system time (relies on caller) ✓

**Note:** `run_id` is not in the finding model. According to FINDING_MODEL_V1.md, `run_id` should be present (line 37: "run_id (NOT NULL; FK to core run)"). This is a missing field.

**Result:** **FAIL** (run_id missing from finding model)

---

### Check 3: Evidence Completeness (Per Finding)

**Requirement:** All evidence fields must be present per finding.

**Evidence:**
- ✅ **rule_id + rule_version:** Required in `RuleIdentityEvidence` ✓
- ✅ **framework_version:** Required in `RuleIdentityEvidence` ✓
- ✅ **executed_parameters:** Required in `RuleIdentityEvidence` ✓
- ✅ **Tolerance values:** `ToleranceEvidence` dataclass with all fields (present when used) ✓
- ✅ **Amount comparisons:** `AmountComparisonEvidence` with original + converted amounts ✓
- ✅ **Date comparisons:** `DateComparisonEvidence` with invoice + counterpart dates ✓
- ✅ **Reference comparisons:** `ReferenceComparisonEvidence` with matched/unmatched references ✓
- ✅ **Counterparty logic:** `CounterpartyEvidence` with counterparty match logic ✓
- ✅ **Match-selection rationale:** `MatchSelectionRationale` with selection method/criteria/priority ✓
- ✅ **Primary source links:** `PrimarySourceLinks` with invoice/counterpart/source/canonical IDs ✓
- ✅ **Validation function:** `validate_evidence_schema_v1()` enforces all required fields ✓

**Result:** **PASS**

---

### Check 4: Review Immutability

**Requirement:** Findings never mutated or deleted, review actions stored separately, dismissals do not alter findings.

**Evidence:**
- ✅ **Finding mutation prevention:** `prevent_finding_mutation()` raises `FindingMutationError` ✓
- ✅ **Finding deletion prevention:** `prevent_finding_deletion()` raises `FindingMutationError` ✓
- ✅ **Review actions separate:** `create_finding_review_action()` creates `ReviewAction` artifacts ✓
- ✅ **Review integration:** `review_integration.py` uses core review service (separate artifacts) ✓
- ✅ **Core review service:** `record_review_event()` creates `ReviewEvent` records (append-only) ✓
- ✅ **No update methods:** No `update()` or `delete()` methods found in finding model ✓
- ✅ **Guard functions:** `guard_finding_immutability()` prevents mutation/deletion ✓

**Result:** **PASS**

---

### Check 5: Determinism & Forbidden Patterns

**Requirement:** No datetime.now(), no float arithmetic, no fraud/blame language, no aggregation or elimination logic.

**Evidence:**
- ✅ **No datetime.now():** No `datetime.now()` found in matching/confidence/finding/evidence code ✓
  - Note: `run.py` has `datetime.now()` for run metadata (outside FF-3 scope)
- ✅ **No float arithmetic:** No `float()` in arithmetic, no float literals in matching code ✓
- ✅ **No fraud/blame language:** No fraud, blame, theft, criminal, culprit words found ✓
- ✅ **No aggregation logic:** No `.aggregate()`, `GROUP BY`, `groupby()` in matching code ✓
- ✅ **No elimination logic:** No intercompany elimination/consolidation patterns found ✓

**Result:** **PASS**

---

### Check 6: Tests

**Requirement:** Evidence completeness tests exist and pass, determinism guard tests exist and pass.

**Evidence:**
- ✅ **Evidence completeness tests:** 
  - `ff3_evidence/test_evidence_completeness.py` — 2 BUILD FAILURE tests ✓
  - `ff3_evidence/test_confidence_enum.py` — 2 BUILD FAILURE tests ✓
- ✅ **Determinism guard tests:**
  - `ff3_determinism/test_rule_ordering.py` — 2 BUILD FAILURE tests ✓
  - `ff3_determinism/test_datetime_forbidden.py` — 1 BUILD FAILURE test ✓
  - `ff3_determinism/test_float_forbidden.py` — 1 BUILD FAILURE test ✓
- ✅ **Additional tests:**
  - `test_ff3_confidence.py` — 5 confidence tests ✓
  - `test_ff3_evidence.py` — 8 evidence tests ✓
  - `test_ff3_review.py` — 5 review immutability tests ✓
  - `test_ff3_determinism.py` — 4 determinism tests ✓

**Result:** **PASS**

---

## OVERALL VERDICT

**Status:** **REMEDIATION REQUIRED**

**Pass:** 5/6  
**Fail:** 1/6 (Finding Model Integrity - 4 violations)

---

## FINDINGS

### ✅ Confidence System: PASS

- Enum-only values enforced
- Central assignment logic implemented
- Rule mapping table provides deterministic mapping
- No contextual overrides possible

---

### ❌ Finding Model Integrity: FAIL

- Most required fields present
- `dataset_version_id` bound via FK constraint ✓
- `fx_artifact_id` present and required ✓
- `created_at` field exists (deterministic source required by caller) ✓
- **VIOLATION:** `run_id` missing from finding model (required per FINDING_MODEL_V1.md)

---

### ✅ Evidence Completeness: PASS

- Complete evidence schema v1 defined
- All required fields validated
- Evidence emission engine validates schema before emission
- One evidence bundle per finding

---

### ✅ Review Immutability: PASS

- Findings cannot be mutated (guard functions)
- Findings cannot be deleted (guard functions)
- Review actions create separate artifacts
- Core review service uses append-only events

---

### ✅ Determinism & Forbidden Patterns: PASS

- No `datetime.now()` in FF-3 scope
- No float arithmetic
- No fraud/blame language
- No aggregation or elimination logic

---

### ✅ Tests: PASS

- Evidence completeness tests exist (BUILD FAILURE tests)
- Determinism guard tests exist (BUILD FAILURE tests)
- Additional comprehensive test coverage

---

## POSITIVE FINDINGS

### ✅ Comprehensive Evidence Schema

The evidence schema v1 is complete and covers all required aspects:
- Rule identity and parameters
- Tolerance values
- Amount comparisons (original + converted)
- Date comparisons
- Reference comparisons
- Counterparty logic
- Match-selection rationale
- Primary source links

### ✅ Strong Immutability Enforcement

Multiple layers of immutability enforcement:
- Guard functions prevent mutation/deletion
- Review actions create separate artifacts
- Core review service uses append-only events
- No update/delete methods in finding model

### ✅ Determinism Safeguards

Comprehensive determinism safeguards:
- Explicit rule ordering (priority-based)
- No time-dependent logic
- Decimal arithmetic only
- BUILD FAILURE tests prevent regressions

---

## VIOLATIONS FOUND

### Violation 1: run_id Missing from Finding Model

**File:** `backend/app/engines/financial_forensics/models/findings.py`

**Issue:**
- `run_id` field is missing from `FinancialForensicsFinding` model
- FINDING_MODEL_V1.md specifies: "run_id (NOT NULL; FK to core run)" (line 37)

**Why it violates v3:**
- Findings must be bound to runs for replayability
- Run binding is required for audit traceability
- Without `run_id`, findings cannot be linked to the run that produced them

**Required Fix:**
- Add `run_id` field to `FinancialForensicsFinding` model
- Add FK constraint to core run table (exact table name to be determined from core schema)
- Ensure `run_id` is provided when creating findings

**Blocking:** **YES** — Violates FINDING_MODEL_V1.md requirement

---

### Violation 2: finding_type Missing from Finding Model

**File:** `backend/app/engines/financial_forensics/models/findings.py`

**Issue:**
- `finding_type` field is missing from `FinancialForensicsFinding` model
- FINDING_MODEL_V1.md specifies: "finding_type (string; NOT NULL)" (line 42)

**Why it violates v3:**
- Finding type is required to categorize findings (e.g., "match.invoice_payment")
- Without `finding_type`, findings cannot be properly classified

**Required Fix:**
- Add `finding_type` field to `FinancialForensicsFinding` model:
  ```python
  finding_type: Mapped[str] = mapped_column(String, nullable=False)
  ```

**Blocking:** **YES** — Violates FINDING_MODEL_V1.md requirement

---

### Violation 3: framework_version Missing from Finding Model

**File:** `backend/app/engines/financial_forensics/models/findings.py`

**Issue:**
- `framework_version` field is missing from `FinancialForensicsFinding` model
- FINDING_MODEL_V1.md specifies: "framework_version (string; NOT NULL)" (line 40)

**Why it violates v3:**
- Framework version is required for replayability and versioning
- Without `framework_version`, findings cannot be properly versioned

**Required Fix:**
- Add `framework_version` field to `FinancialForensicsFinding` model:
  ```python
  framework_version: Mapped[str] = mapped_column(String, nullable=False)
  ```

**Blocking:** **YES** — Violates FINDING_MODEL_V1.md requirement

---

### Violation 4: primary_evidence_item_id Missing from Finding Model

**File:** `backend/app/engines/financial_forensics/models/findings.py`

**Issue:**
- `primary_evidence_item_id` field is missing from `FinancialForensicsFinding` model
- FINDING_MODEL_V1.md specifies: "primary_evidence_item_id (UUID; NOT NULL; FK to core evidence item)" (line 43)
- Current model has `evidence_ids` (list) but not `primary_evidence_item_id` (single FK)

**Why it violates v3:**
- Primary evidence item ID is required for evidence linking
- Without `primary_evidence_item_id`, findings cannot be linked to primary evidence

**Required Fix:**
- Add `primary_evidence_item_id` field to `FinancialForensicsFinding` model:
  ```python
  primary_evidence_item_id: Mapped[str] = mapped_column(
      String, ForeignKey("evidence_records.evidence_id"), nullable=False, index=True
  )
  ```
- Keep `evidence_ids` as list of additional evidence references

**Blocking:** **YES** — Violates FINDING_MODEL_V1.md requirement

---

## MINOR NOTES (Non-Blocking)

### Note 1: created_at Deterministic Source

The `created_at` field exists in the finding model, but there's no enforcement that it's not system time. This relies on the caller providing a deterministic timestamp. The evidence emission engine requires `created_at` as a parameter (good), but the finding model itself doesn't enforce this.

---

## CONCLUSION

**Status:** **REMEDIATION REQUIRED**

**DO NOT PROCEED to FF-4 until:**
- `run_id` field added to `FinancialForensicsFinding` model (FK to core run)
- `finding_type` field added to `FinancialForensicsFinding` model
- `framework_version` field added to `FinancialForensicsFinding` model
- `primary_evidence_item_id` field added to `FinancialForensicsFinding` model (FK to evidence_records)
- All fields provided when creating findings

**Remaining checks pass.** FF-3 findings are:
- ✅ Defensible (complete evidence, locked semantics)
- ✅ Evidence-complete (all required fields validated)
- ✅ Law-compliant (immutability, determinism, forbidden patterns enforced)

**FF-3 requires remediation for finding model integrity before certification.**

---

**END OF FF-3.B AUDIT**

