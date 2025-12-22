# Engine #5 — Reporting, Externalization & Hardening Re-Audit Report

**Document Under Audit:** Reporting, Externalization & Hardening Implementation (Post-Remediation)  
**Audit Date:** 2025-01-XX  
**Auditor:** Authoritative Agent (v3 Compliance)  
**Status:** ❌ **FAIL — Critical Issues Identified**

---

## Executive Summary

This re-audit identifies **critical gaps** in the reporting and externalization implementation that must be remediated before production deployment. The implementation has **internal provenance key leakage** in external exports and **missing report sections** for transaction scope validation and error-handling/execution summaries.

**Overall Assessment:** ❌ **FAIL** — 3 critical issues requiring remediation.

---

## 1. External Exports — Internal Provenance Key Redaction

### ❌ FAIL: Internal Provenance Keys Not Redacted in External Exports

**Issue:** Internal provenance keys (specifically `artifact_key`) appear in external exports via findings' `detail` fields.

**Evidence:**
1. **Findings Service (`findings_service.py`):**
   - Lines 118, 125, 133: `artifact_key` is included in findings' `detail` dict:
     ```python
     detail = {
         "name": name,
         "artifact_key": spec["artifact_key"],  # ← Internal provenance key
         "expected_sha256": spec.get("sha256"),
         ...
     }
     ```

2. **Report Assembler (`report/assembler.py`):**
   - Lines 90-99: Findings are included in report with full `detail` dict:
     ```python
     findings: list[dict] = [
         {
             "finding_id": f.finding_id,
             "kind": f.kind,
             "severity": f.severity,
             "title": f.title,
             "detail": f.detail,  # ← Contains artifact_key
             "evidence_id": f.evidence_id,
         }
         for f in findings_rows
     ]
     ```

3. **Externalization Policy (`externalization/policy.py`):**
   - Lines 65-73: `redacted_fields` does NOT include `artifact_key`:
     ```python
     redacted_fields: set[str] = frozenset({
         "internal_notes",
         "run_parameters",
         "run_id",
         "transaction_scope",
         "source_system_id",
         "source_record_id",
         "canonical_record_id",
         # ❌ MISSING: "artifact_key"
     })
     ```

4. **Report Sections:**
   - `readiness_findings` section is EXTERNAL (line 49 in `policy.py`)
   - Findings with `artifact_key` in `detail` are included in external exports
   - External view redaction does NOT remove `artifact_key` from nested `detail` dicts

**Impact:**
- **CRITICAL:** Internal artifact store keys are exposed in external JSON/PDF exports
- Third parties can see internal artifact paths/keys
- Violates Platform Law #4 (Artifacts are content-addressed) — internal keys should not be exposed
- Security/privacy risk: Internal infrastructure details leaked

**Required Remediation:**
1. Add `artifact_key` to `redacted_fields` in `ExternalizationPolicy`
2. Ensure recursive redaction in `_redact_section()` removes `artifact_key` from nested structures (including findings' `detail` dicts)
3. Add validation in `validate_external_view()` to ensure no `artifact_key` fields in external exports
4. Test that external exports do not contain any `artifact_key` fields

**Compliance:** ❌ **FAIL** — Internal provenance keys leak into external exports

---

## 2. Report Template — Transaction Scope Validation

### ❌ FAIL: No Explicit Transaction Scope Validation Section

**Issue:** The report does not include an explicit "transaction scope validation" section documenting the validation results.

**Evidence:**
1. **Report Sections (`report/sections.py`):**
   - No `section_transaction_scope_validation()` function exists
   - Available sections:
     - `section_executive_overview()` — Contains `transaction_scope_summary` but not validation results
     - `section_readiness_findings()` — Findings, not validation
     - `section_checklist_status()` — Checklist, not validation
     - `section_evidence_index()` — Evidence, not validation
     - `section_limitations_uncertainty()` — Limitations, not validation
     - `section_run_parameters()` — Internal-only parameters
     - `section_explicit_non_claims()` — Non-claims, not validation

2. **Report Assembler (`report/assembler.py`):**
   - Lines 151-154: `transaction_scope_summary` is computed but only includes:
     - `scope_kind` (e.g., "full_dataset")
     - `transaction_scope_hash` (hash of scope)
   - No validation status, validation errors, or validation results

3. **Executive Overview:**
   - Lines 163-170: `transaction_scope_summary` is included in executive overview
   - This is a summary, not an explicit validation section

**Impact:**
- **CRITICAL:** No explicit documentation of transaction scope validation results
- Users cannot see what validation was performed or what validation errors occurred
- Violates DR-1 Boundary Document requirement for explicit transaction scope validation in reports
- Reduces auditability and transparency

**Required Remediation:**
1. Create `section_transaction_scope_validation()` function in `report/sections.py`
2. Include validation results:
   - Validation status (valid/invalid/errors)
   - Validation errors (if any)
   - Validated scope properties
   - Validation timestamp/context
3. Add section to report assembler (after executive overview, before findings)
4. Mark section as EXTERNAL in policy (validation results are shareable)
5. Update report assembler to compute and include validation results

**Compliance:** ❌ **FAIL** — No explicit transaction scope validation section

---

## 3. Report Template — Error-Handling/Execution Summary

### ❌ FAIL: No Error-Handling/Execution Summary Section

**Issue:** The report does not include an explicit "error-handling/execution summary" section documenting execution errors, validation failures, and execution status.

**Evidence:**
1. **Report Sections (`report/sections.py`):**
   - No `section_execution_summary()` or `section_error_handling_summary()` function exists
   - No section documenting:
     - Execution errors
     - Validation failures
     - Execution status
     - Error counts
     - Error types

2. **Report Assembler (`report/assembler.py`):**
   - No execution summary computation
   - No error aggregation
   - No execution status tracking

3. **Findings:**
   - Findings document specific issues but not execution-level errors
   - No summary of execution errors vs. readiness findings

**Impact:**
- **CRITICAL:** No explicit documentation of execution errors and validation failures
- Users cannot see execution-level errors (beyond individual findings)
- Violates requirement for "error-handling/execution summary" beyond implied runtime validation
- Reduces operational visibility and debugging capability

**Required Remediation:**
1. Create `section_execution_summary()` function in `report/sections.py`
2. Include execution summary:
   - Execution status (success/partial/failed)
   - Error counts by type
   - Validation failure summary
   - Execution errors (non-fatal errors that didn't stop execution)
   - Execution metadata (start time, duration, etc.)
3. Add section to report assembler (after transaction scope validation, before findings)
4. Mark section as EXTERNAL in policy (execution summary is shareable)
5. Update report assembler to compute and include execution summary from run data

**Compliance:** ❌ **FAIL** — No error-handling/execution summary section

---

## 4. Additional Observations

### ⚠️ MINOR: Evidence Payload May Contain Internal Keys

**Observation:** Evidence payloads may contain internal keys that could leak into external exports.

**Evidence:**
- `findings_service.py` line 146-150: Evidence payload includes `detail` which may contain `artifact_key`
- Evidence index is EXTERNAL (line 51 in `policy.py`)
- Evidence payloads are included in external exports

**Recommendation:**
- Review evidence payload structure to ensure no internal keys
- Consider redacting evidence payloads in external view if they contain internal keys

**Compliance:** ⚠️ **MINOR GAP** — Requires review

---

## Summary of Findings

### Critical Failures (Must Remediate)

1. ❌ **Internal Provenance Key Leakage**
   - `artifact_key` appears in external exports via findings' `detail` fields
   - Not redacted in externalization policy
   - **Impact:** Internal infrastructure details exposed to third parties

2. ❌ **Missing Transaction Scope Validation Section**
   - No explicit section documenting transaction scope validation results
   - Only summary in executive overview
   - **Impact:** Reduced auditability and transparency

3. ❌ **Missing Error-Handling/Execution Summary Section**
   - No explicit section documenting execution errors and validation failures
   - No execution-level error aggregation
   - **Impact:** Reduced operational visibility

### Minor Observations

1. ⚠️ **Evidence Payload Review**
   - Evidence payloads may contain internal keys
   - Requires review and potential redaction

---

## Required Remediation Steps

### Step 1: Fix Internal Provenance Key Redaction

**File:** `backend/app/engines/enterprise_deal_transaction_readiness/externalization/policy.py`

```python
redacted_fields: set[str] = frozenset({
    "internal_notes",
    "run_parameters",
    "run_id",
    "transaction_scope",
    "source_system_id",
    "source_record_id",
    "canonical_record_id",
    "artifact_key",  # ← ADD THIS
})
```

**File:** `backend/app/engines/enterprise_deal_transaction_readiness/externalization/views.py`

- Ensure `_redact_section()` recursively removes `artifact_key` from nested dicts
- Add validation in `validate_external_view()` to check for `artifact_key` presence

**Testing:**
- Create test findings with `artifact_key` in `detail`
- Verify external export does NOT contain `artifact_key`
- Verify validation raises error if `artifact_key` found in external view

---

### Step 2: Add Transaction Scope Validation Section

**File:** `backend/app/engines/enterprise_deal_transaction_readiness/report/sections.py`

```python
def section_transaction_scope_validation(
    *,
    validation_status: str,
    validation_errors: list[dict],
    validated_scope_properties: dict,
) -> dict[str, Any]:
    """
    Transaction scope validation section.
    
    Documents validation results for the declared transaction scope.
    """
    return {
        "section_id": "transaction_scope_validation",
        "section_type": "transaction_scope_validation",
        "validation_status": validation_status,
        "validation_errors": validation_errors,
        "validated_scope_properties": validated_scope_properties,
    }
```

**File:** `backend/app/engines/enterprise_deal_transaction_readiness/externalization/policy.py`

```python
external_sections: set[ReportSection] = frozenset({
    ReportSection.EXECUTIVE_OVERVIEW,
    ReportSection.TRANSACTION_SCOPE_VALIDATION,  # ← ADD THIS
    ReportSection.READINESS_FINDINGS,
    ...
})
```

**File:** `backend/app/engines/enterprise_deal_transaction_readiness/report/assembler.py`

- Compute validation results from run data
- Add section to report sections list

---

### Step 3: Add Error-Handling/Execution Summary Section

**File:** `backend/app/engines/enterprise_deal_transaction_readiness/report/sections.py`

```python
def section_execution_summary(
    *,
    execution_status: str,
    error_counts: dict[str, int],
    validation_failures: list[dict],
    execution_errors: list[dict],
    execution_metadata: dict,
) -> dict[str, Any]:
    """
    Execution summary section.
    
    Documents execution errors, validation failures, and execution status.
    """
    return {
        "section_id": "execution_summary",
        "section_type": "execution_summary",
        "execution_status": execution_status,
        "error_counts": error_counts,
        "validation_failures": validation_failures,
        "execution_errors": execution_errors,
        "execution_metadata": execution_metadata,
    }
```

**File:** `backend/app/engines/enterprise_deal_transaction_readiness/externalization/policy.py`

```python
external_sections: set[ReportSection] = frozenset({
    ReportSection.EXECUTIVE_OVERVIEW,
    ReportSection.TRANSACTION_SCOPE_VALIDATION,
    ReportSection.EXECUTION_SUMMARY,  # ← ADD THIS
    ReportSection.READINESS_FINDINGS,
    ...
})
```

**File:** `backend/app/engines/enterprise_deal_transaction_readiness/report/assembler.py`

- Compute execution summary from run data and findings
- Aggregate errors by type
- Add section to report sections list

---

## Final Verdict

**Overall Assessment:** ❌ **FAIL** — Critical issues requiring remediation.

**Summary:**
- ❌ **Internal Provenance Key Leakage:** `artifact_key` exposed in external exports
- ❌ **Missing Transaction Scope Validation Section:** No explicit validation section
- ❌ **Missing Error-Handling/Execution Summary Section:** No execution summary section
- ⚠️ **Evidence Payload Review:** Requires review for internal keys

**Recommendation:**
The implementation **must be remediated** before production deployment. The three critical issues must be addressed:
1. Add `artifact_key` to redacted fields and ensure recursive redaction
2. Add explicit transaction scope validation section
3. Add explicit error-handling/execution summary section

**Next Steps:**
1. ❌ **DO NOT DEPLOY** until remediation complete
2. ✅ Remediate all three critical issues
3. ✅ Re-audit after remediation
4. ✅ Proceed with deployment only after PASS

---

**END OF RE-AUDIT REPORT**


