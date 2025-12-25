# Audit Review Report: Recent Changes Validation

**Date:** 2025-01-XX  
**Reviewer:** Senior Platform Auditor  
**Scope:** Parameter Payload, Normalization Warnings, Audit Logs, Workflow RBAC, User Identity  
**Status:** ⚠️ **ISSUES FOUND - REMEDIATION REQUIRED**

---

## Executive Summary

This report reviews recent changes to address audit findings. **3 critical issues** and **2 minor issues** were identified that require remediation before production deployment.

---

## 1. Parameter Payload Field ⚠️ **ISSUE FOUND**

### 1.1 Duplicate Fields in CalculationRun Model ❌

**Location:** `backend/app/core/calculation/models.py`

**Issue:**
- **Line 39:** `parameters: Mapped[dict] = mapped_column(JSON, nullable=False)`
- **Line 40:** `parameter_payload: Mapped[dict] = mapped_column(JSON, nullable=False)`
- **Both fields store the same data** (see `backend/app/core/calculation/service.py:69-70`)

**Impact:**
- **High:** Database schema has redundant columns
- **Medium:** Confusion about which field to use
- **Low:** Storage overhead (duplicate data)

**Evidence:**
```python
# backend/app/core/calculation/service.py:69-70
parameters=parameters,  # Legacy payload storage
parameter_payload=parameters,  # Full payload for reproducibility
```

**Recommendation:**
1. **Remove `parameters` field** (keep `parameter_payload`)
2. **Update service** to only use `parameter_payload`
3. **Create database migration** to drop `parameters` column

**Status:** ❌ **REQUIRES FIX**

---

### 1.2 Traceability and Reproducibility ✅

**Verification:**
- ✅ `parameter_payload` stores complete parameter JSON
- ✅ `parameters_hash` provides deterministic hash for reproducibility
- ✅ Both fields are linked correctly in service layer
- ✅ Hash is computed from `parameter_payload` (via `_hash_parameters()`)

**Status:** ✅ **VERIFIED** (once duplicate is removed)

---

## 2. Normalization Process Enhancements ✅ **VERIFIED**

### 2.1 Fuzzy Match Warnings ✅

**Location:** `backend/app/core/normalization/workflow.py`

**Implementation:**
- ✅ `create_fuzzy_match_warning()` imported (line 25)
- ✅ `_generate_core_warnings()` generates fuzzy match warnings (lines 397-413)
- ✅ Fuzzy match detection uses similarity ratio (>= 0.9)
- ✅ Warnings include: `field_name`, `original_value`, `suggested_value`, `confidence`

**Evidence:**
```python
# Lines 397-413
for i, left in enumerate(field_names):
    for right in field_names[i + 1 :]:
        if left == right:
            continue
        ratio = _similarity_ratio(left, right)
        if ratio >= 0.9:
            warnings.append(
                create_fuzzy_match_warning(
                    raw_record_id=raw_record.raw_record_id,
                    field_name=left,
                    original_value=left,
                    suggested_value=right,
                    confidence=ratio,
                )
            )
```

**Status:** ✅ **VERIFIED** - Fuzzy match warnings are generated

---

### 2.2 Engine-Specific Warnings ✅

**Location:** `backend/app/core/normalization/workflow.py`

**Implementation:**
- ✅ `normalization_rule` parameter accepts engine-specific functions (line 32)
- ✅ Engine rules can return warnings (line 149-151, 234-236, 321-323)
- ✅ Engine warnings are combined with core warnings (line 152, 236, 324)
- ✅ Warnings are included in preview, validation, and commit results

**Evidence:**
```python
# Lines 147-152
if normalization_rule:
    # Use engine-specific normalization rule
    normalized_payload, warnings = normalization_rule(
        raw_record.payload, dataset_version_id
    )
    warnings = warnings + _generate_core_warnings(raw_record)
```

**Status:** ✅ **VERIFIED** - Engine-specific warnings are supported

---

### 2.3 Warning Display in Preview/Validation ✅

**Verification:**
- ✅ `preview_normalization()` returns warnings in `NormalizationPreview` (line 191)
- ✅ `validate_normalization()` returns warnings as tuple (line 260)
- ✅ Warnings include: `code`, `severity`, `message`, `affected_record_id`, `affected_field`, `details`, `recommendation`
- ✅ Warnings are serialized via `to_dict()` method

**Status:** ✅ **VERIFIED** - Warnings are displayed in preview/validation

---

## 3. Missing Audit Logs ✅ **VERIFIED**

### 3.1 Flag Legacy Missing Checksums Endpoint ✅

**Location:** `backend/app/core/dataset/api.py`

**Implementation:**
- ✅ Endpoint: `POST /raw-records/flag-legacy-missing-checksums` (line 158)
- ✅ Audit logging: Lines 164-185
- ✅ Logs linked to `DatasetVersion` via `dataset_version_id` (line 177)
- ✅ Logs include `raw_record_id` in context (line 180)
- ✅ Metadata includes: `raw_record_id`, `checksum_status`, `user_context` (lines 179-183)
- ✅ `actor_id` extracted from principal (line 165)

**Evidence:**
```python
# Lines 164-185
from backend.app.core.audit.service import log_action
actor_id = getattr(principal, "subject", "system")
for record in flagged:
    await log_action(
        db,
        actor_id=actor_id,
        actor_type="user",
        action_type="integrity",
        action_label="Flag legacy missing checksums",
        dataset_version_id=record.dataset_version_id,
        reason="Flagged RawRecord entry with missing checksum as legacy",
        context={
            "raw_record_id": record.raw_record_id,
            "checksum_status": "legacy_missing",
            "user_context": user_context,
        },
        status="warning",
    )
```

**Status:** ✅ **VERIFIED** - Audit logs properly implemented

---

### 3.2 Backfill Checksums Endpoint ✅

**Location:** `backend/app/core/dataset/api.py`

**Implementation:**
- ✅ Endpoint: `POST /raw-records/backfill-checksums` (line 189)
- ✅ Audit logging: Lines 199-222
- ✅ Logs linked to `DatasetVersion` via `dataset_version_id` (line 213)
- ✅ Logs include `raw_record_id` in context (line 216)
- ✅ Metadata includes: `raw_record_id`, `checksum_status`, `user_context` (lines 215-219)
- ✅ `actor_id` extracted from principal (line 200)
- ✅ Status set based on outcome (line 206)

**Evidence:**
```python
# Lines 199-222
from backend.app.core.audit.service import log_action
actor_id = getattr(principal, "subject", "system")
for outcome in report.outcomes:
    status = "success" if outcome.checksum_status == "backfilled" else "warning"
    await log_action(
        db,
        actor_id=actor_id,
        actor_type="user",
        action_type="maintenance",
        action_label="Backfill raw-record checksums",
        dataset_version_id=outcome.dataset_version_id,
        reason=outcome.reason or "Backfilled RawRecord checksum",
        context={
            "raw_record_id": outcome.raw_record_id,
            "checksum_status": outcome.checksum_status,
            "user_context": user_context,
        },
        status=status,
        error_message=outcome.reason,
    )
```

**Status:** ✅ **VERIFIED** - Audit logs properly implemented

---

## 4. Workflow State Management Refinements ⚠️ **ISSUE FOUND**

### 4.1 RBAC Enforcement ✅

**Location:** `backend/app/core/workflows/api.py`

**Implementation:**
- ✅ `transition_state_endpoint()` checks for `Role.ADMIN` (line 214)
- ✅ Transitions to `approved` or `locked` require ADMIN role
- ✅ Raises `HTTPException(status_code=403)` for unauthorized transitions

**Evidence:**
```python
# Lines 213-215
actor_roles = principal.roles or ()
if normalized_to_state in ("approved", "locked") and Role.ADMIN.value not in actor_roles:
    raise HTTPException(status_code=403, detail="WORKFLOW_TRANSITION_FORBIDDEN")
```

**Status:** ✅ **VERIFIED** - RBAC enforcement implemented

---

### 4.2 Workflow State Machine RBAC ✅

**Location:** `backend/app/core/workflows/state_machine.py`

**Implementation:**
- ✅ `transition_workflow_state()` accepts `actor_roles` parameter (line 275)
- ✅ `_has_approval_for_actor()` validates ADMIN role (lines 261-264)
- ✅ Prerequisites are automatically derived from DB/auth context (lines 337-343)
- ✅ Evidence checking is automatic via `_has_evidence_for_subject()` (lines 337-342)
- ✅ Approval checking uses `actor_roles` from principal (line 343)

**Evidence:**
```python
# Lines 275, 343
actor_roles: tuple[str, ...] | None = None,
has_approval = _has_approval_for_actor(actor_roles)

# Lines 261-264
def _has_approval_for_actor(actor_roles: tuple[str, ...] | None) -> bool:
    if not actor_roles:
        return False
    return Role.ADMIN.value in actor_roles
```

**Status:** ✅ **VERIFIED** - RBAC enforcement fully implemented

---

### 4.3 Transition Logging ✅

**Verification:**
- ✅ All transitions logged via `log_workflow_action()` (line 331 in `state_machine.py`)
- ✅ Logs include: `actor_id`, `from_state`, `to_state`, `reason`, `metadata`
- ✅ Transition history tracked in `WorkflowTransition` model

**Status:** ✅ **VERIFIED** - Transitions are logged

---

## 5. User Identity in Audit Logs ⚠️ **ISSUES FOUND**

### 5.1 Consistent Actor ID Capture ⚠️

**Location:** Multiple files

**Issues Found:**

#### ❌ **Issue 1: Calculation Actions Use Engine ID**
- **Location:** `backend/app/core/calculation/service.py:79`
- **Issue:** `actor_id=engine_id` (should be user ID)
- **Impact:** **Medium** - Calculation actions don't track actual user

**Evidence:**
```python
# Line 79
await log_calculation_action(
    db,
    actor_id=engine_id,  # Should be user ID, not engine ID
    ...
)
```

**Recommendation:**
- Pass `actor_id` parameter to `create_calculation_run()`
- Use user ID from principal, not engine ID

---

#### ⚠️ **Issue 2: Inconsistent Principal Extraction**
- **Location:** Multiple endpoints
- **Pattern 1:** `getattr(principal, "subject", "system")` (most endpoints)
- **Pattern 2:** `principal.subject` (normalization, workflow endpoints)
- **Issue:** Inconsistent fallback handling

**Evidence:**
```python
# Pattern 1 (dataset/api.py)
actor_id = getattr(principal, "subject", "system")

# Pattern 2 (normalization/api.py, workflows/api.py)
actor_id=principal.subject  # No fallback
```

**Recommendation:**
- Standardize on `getattr(principal, "subject", "system")` pattern
- Ensure all endpoints have fallback

---

#### ✅ **Issue 3: Workflow State Creation**
- **Location:** `backend/app/core/workflows/api.py:101`
- **Issue:** `actor_id` is optional in payload (line 101)
- **Impact:** **Low** - State creation may not have actor ID

**Status:** ⚠️ **MINOR** - Should extract from principal instead

---

### 5.2 No Action Without User Context ✅

**Verification:**
- ✅ All API endpoints require `require_principal()` dependency
- ✅ All audit log functions require `actor_id` parameter
- ✅ `log_action()` validates `actor_id` is non-empty (line 60-61 in `service.py`)

**Status:** ✅ **VERIFIED** - No actions logged without user context

---

## Summary of Issues

### Critical Issues (Must Fix)

1. ❌ **Duplicate `parameters` and `parameter_payload` fields** in `CalculationRun` model
2. ⚠️ **Calculation actions use engine ID** instead of user ID for `actor_id`

### Minor Issues (Should Fix)

4. ⚠️ **Inconsistent principal extraction** patterns across endpoints
5. ⚠️ **Workflow state creation** should extract `actor_id` from principal

---

## Recommendations

### Priority 1 (Critical)

1. **Remove duplicate `parameters` field:**
   - Remove `parameters` from `CalculationRun` model
   - Update service to only use `parameter_payload`
   - Create database migration

2. **Fix calculation action actor ID:**
   - Add `actor_id` parameter to `create_calculation_run()`
   - Pass user ID from principal, not engine ID
   - Update all callers

### Priority 2 (Minor)

4. **Standardize principal extraction:**
   - Use `getattr(principal, "subject", "system")` everywhere
   - Ensure consistent fallback handling

5. **Extract actor ID from principal in workflow state creation:**
   - Don't rely on payload `actor_id`
   - Extract from `principal.subject`

---

## Final Status

**Overall Assessment:** ⚠️ **REMEDIATION REQUIRED**

- ✅ **Normalization warnings:** Fully implemented
- ✅ **Audit logs for flag/backfill:** Properly implemented
- ✅ **RBAC enforcement:** Fully implemented (API and state machine)
- ❌ **Parameter payload field:** Duplicate fields need removal
- ⚠️ **User identity:** Calculation actions use engine ID instead of user ID

**Platform Status:** ⚠️ **NOT READY FOR PRODUCTION** - 2 critical issues must be fixed first.

---

**Review Complete** ⚠️  
**Date:** 2025-01-XX  
**Reviewer:** Senior Platform Auditor

