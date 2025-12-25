# ENGINE PAGE SEMANTIC CORRECTNESS — PHASE 2B REMEDIATION

**Date:** 2025-12-24T12:00:00Z  
**Status:** ✅ **COMPLETE**

---

## OBJECTIVE

Ensure engine pages tell the TRUTH — not placeholders. Each engine page must accurately reflect backend reality, including lifecycle stage completion, supported capabilities, and blocked states.

---

## CHANGES IMPLEMENTED

### 1. Workflow State Integration ✅

**File:** `frontend/web/src/lib/api-client.ts`

**Changes:**
- Added `getWorkflowState()` function to query workflow state for lifecycle stages
- Handles 404 errors gracefully (state doesn't exist yet)

**Behavior:**
- Queries `/api/v3/workflow/state` endpoint with `dataset_version_id`, `subject_type="lifecycle"`, and `subject_id` (e.g., "import", "normalize", "calculate:{engine_id}")
- Returns `null` if state doesn't exist (404), otherwise returns state with `current_state`

---

### 2. Lifecycle Stage Status Determination ✅

**File:** `frontend/web/src/components/engines/engine-page.tsx`

**Changes:**
- Added `lifecycleState` query to check workflow state for import, normalize, and calculate stages
- Updated lifecycle stage status logic to check actual completion via workflow state
- Added blocked reasons for all lifecycle stages when blocked
- Fixed audit path to use `/audit` instead of `/workflow/audit`

**Key Improvements:**
- **Import stage:** Checks workflow state (`lifecycle:import`) - shows "completed" only if state is "approved"
- **Normalize stage:** Checks workflow state (`lifecycle:normalize`) and requires import completion - shows "blocked" if import not completed
- **Calculate stage:** Checks workflow state (`lifecycle:calculate:{engine_id}`) and requires normalize completion - shows "blocked" if normalize not completed
- **Report stage:** Checks calculate completion and report endpoint support - shows "blocked" if calculate not completed or endpoint missing
- **Audit stage:** Always available if dataset version exists

**Blocked Reasons Added:**
- Import: "No dataset version selected. Import a dataset first."
- Normalize: "Import must be completed before normalization." or "No dataset version selected."
- Calculate: "Normalization must be completed before calculation." or "No engine run endpoint detected."
- Report: "Calculation must be completed before report generation." or "No engine report endpoint detected."
- Audit: "No dataset version selected."

---

### 3. Engine Registry Updates ✅

**File:** `frontend/web/src/engines/registry.ts`

**Changes:**
- Added detailed descriptions for all 12 engines
- Removed "reports" capability from engines that don't have `/report` endpoints
- Added notes in descriptions for engines without report support

**Engines WITH `/report` endpoints (6):**
- `csrd` - CSRD & ESRS Compliance
- `financial-forensics` - Financial Forensics & Leakage
- `cost-intelligence` - Construction & Infrastructure Cost Intelligence
- `enterprise-capital-debt-readiness` - Capital & Loan Readiness
- `enterprise-deal-transaction-readiness` - Deal & Transaction Readiness
- `litigation-analysis` - Litigation & Dispute Analysis

**Engines WITHOUT `/report` endpoints (6):**
- `audit-readiness` - Audit Readiness & Data Cleanup
- `data-migration-readiness` - Data Migration & ERP Readiness
- `erp-integration-readiness` - ERP Integration Readiness
- `regulatory-readiness` - Regulatory Readiness (Non-CSRD)
- `enterprise-insurance-claim-forensics` - Insurance Claim Forensics
- `distressed-asset-debt-stress` - Distressed Asset & Debt Analysis

**Engine Descriptions:**
All engines now have detailed descriptions explaining:
- What the engine does
- What data it consumes
- What outputs it produces
- Any limitations (e.g., "Note: This engine does not support report generation.")

---

### 4. Engine Page Display Updates ✅

**File:** `frontend/web/src/components/engines/engine-page.tsx`

**Changes:**
- Updated to use `engine.description` from registry (with fallback)
- All lifecycle stages now show blocked reasons when blocked
- Status determination is based on workflow state, not just datasetVersionId existence

---

## LIFECYCLE STAGE STATUS LOGIC

### Import Stage
- **Status:** `completed` if workflow state `lifecycle:import` is "approved"
- **Status:** `available` if datasetVersionId exists but not completed
- **Status:** `pending` if no datasetVersionId
- **Blocked Reason:** "No dataset version selected. Import a dataset first."

### Normalize Stage
- **Status:** `completed` if workflow state `lifecycle:normalize` is "approved"
- **Status:** `available` if import completed
- **Status:** `blocked` if import not completed or no datasetVersionId
- **Blocked Reason:** "Import must be completed before normalization." or "No dataset version selected."

### Calculate Stage
- **Status:** `completed` if workflow state `lifecycle:calculate:{engine_id}` is "approved" OR latestRun exists
- **Status:** `available` if normalize completed AND run endpoint exists
- **Status:** `blocked` if normalize not completed, no run endpoint, or no datasetVersionId
- **Blocked Reason:** "Normalization must be completed before calculation." or "No engine run endpoint detected."

### Report Stage
- **Status:** `completed` if latestReport exists
- **Status:** `available` if calculate completed AND report endpoint exists
- **Status:** `blocked` if calculate not completed, no report endpoint, or no datasetVersionId
- **Blocked Reason:** "Calculation must be completed before report generation." or "No engine report endpoint detected."

### Audit Stage
- **Status:** `available` if datasetVersionId exists
- **Status:** `blocked` if no datasetVersionId
- **Blocked Reason:** "No dataset version selected."

---

## ACCEPTANCE CHECKLIST

- [x] All engine pages render
- [x] Lifecycle stages are accurate (based on workflow state)
- [x] Unsupported stages are explicitly blocked (with reasons)
- [x] No misleading "available" states exist
- [x] No engine appears functional when it is not
- [x] Engine descriptions accurately reflect capabilities
- [x] Report capability only shown for engines with `/report` endpoints

---

## TRUTHFULNESS VERIFICATION

### Before
- Import showed "completed" just if datasetVersionId existed
- Normalize showed "available" just if datasetVersionId existed
- Calculate showed "available" just if datasetVersionId and runSupported
- Report showed "available" just if latestRun existed
- No blocked reasons for import/normalize stages
- Generic descriptions for all engines
- "reports" capability shown for engines without `/report` endpoints

### After
- Import shows "completed" only if workflow state is "approved"
- Normalize shows "available" only if import completed
- Calculate shows "available" only if normalize completed AND run endpoint exists
- Report shows "available" only if calculate completed AND report endpoint exists
- All blocked stages show explicit reasons
- Detailed descriptions for all engines
- "reports" capability only shown for engines with `/report` endpoints

---

## FILES MODIFIED

1. `frontend/web/src/lib/api-client.ts` - Added `getWorkflowState()` function
2. `frontend/web/src/components/engines/engine-page.tsx` - Updated lifecycle stage logic
3. `frontend/web/src/engines/registry.ts` - Added descriptions, removed incorrect capabilities

---

## STATUS

✅ **COMPLETE** - Engine pages now accurately reflect backend reality, lifecycle stage completion, and supported capabilities.


