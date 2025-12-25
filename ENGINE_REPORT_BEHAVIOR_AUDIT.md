# ENGINE REPORT BEHAVIOR COMPLIANCE AUDIT

**Date:** 2025-01-25  
**Auditor:** Platform Compliance Agent  
**Scope:** All engines in TodiScope v3 - Report generation capabilities and UI enforcement

---

## EXECUTIVE SUMMARY

**VERDICT: NON-COMPLIANT — CRITICAL FIXES REQUIRED**

This audit identified **7 critical defects** and **3 violations** across engine classes. Frontend UI does not consistently enforce backend capabilities, and Class B/C engines expose report-related UI elements that must be removed.

---

## ENGINE CLASSIFICATION

### **Class A — Report-Producing Engines (MUST support reports)**

| Engine ID | Display Name | Backend `/report` | `report_sections` | Frontend Generate | Status |
|-----------|--------------|-------------------|-------------------|-------------------|--------|
| `engine_csrd` | CSRD & ESRS Compliance | ✅ YES | ✅ YES (4 sections) | ✅ YES (probed) | **PASS** |
| `engine_financial_forensics` | Financial Forensics & Leakage | ✅ YES | ✅ YES (1 section) | ✅ YES (probed) | **PASS** |
| `engine_construction_cost_intelligence` | Construction & Infrastructure Cost Intelligence | ✅ YES | ✅ YES (multiple) | ✅ YES (probed) | **PASS** |
| `engine_enterprise_capital_debt_readiness` | Capital & Loan Readiness | ✅ YES | ✅ YES (2 sections) | ✅ YES (probed) | **PASS** |
| `engine_enterprise_insurance_claim_forensics` | Insurance Claim Forensics | ✅ YES | ✅ YES (1 section) | ✅ YES (probed) | **PASS** |
| `engine_enterprise_litigation_dispute` | Litigation & Dispute Analysis | ✅ YES | ❌ NO (empty tuple) | ✅ YES (probed) | **⚠️ DEFECT** |
| `engine_distressed_asset_debt_stress` | Distressed Asset & Debt Stress | ❌ NO | ✅ YES (4 sections) | ✅ YES (probed) | **❌ CRITICAL DEFECT** |

**Class A Findings:**
- **6 of 7 engines PASS** — Backend and frontend aligned
- **1 CRITICAL DEFECT:** `engine_distressed_asset_debt_stress` has `report_sections` defined but **NO `/report` endpoint** — Frontend will probe and find no endpoint, but spec suggests reports should exist
- **1 MINOR DEFECT:** `engine_enterprise_litigation_dispute` has `/report` endpoint but **empty `report_sections`** — Inconsistent but functional

---

### **Class B — Enabling/Diagnostic Engines (MUST NOT generate reports)**

| Engine ID | Display Name | Backend `/report` | `report_sections` | Frontend Generate | Status |
|-----------|--------------|-------------------|-------------------|-------------------|--------|
| `engine_audit_readiness` | Audit Readiness & Data Quality | ❌ NO | ✅ YES (multiple) | ⚠️ **SHOWN IF PROBED** | **❌ CRITICAL VIOLATION** |
| `engine_data_migration_readiness` | Data Migration & ERP Readiness | ❌ NO | ✅ NO (empty) | ⚠️ **SHOWN IF PROBED** | **❌ CRITICAL VIOLATION** |
| `engine_regulatory_readiness` | Regulatory Readiness (Non-CSRD) | ❌ NO | ✅ YES (4 sections) | ⚠️ **SHOWN IF PROBED** | **❌ CRITICAL VIOLATION** |

**Class B Findings:**
- **ALL 3 engines VIOLATE Class B requirements**
- **Backend is correct** — No `/report` endpoints exist
- **Frontend VIOLATION:** Frontend probes for `/report` endpoint and shows "blocked" state, but **the Report workflow stage is still visible** in the lifecycle UI
- **`report_sections` inconsistency:** `engine_audit_readiness` and `engine_regulatory_readiness` have `report_sections` defined despite being Class B engines — **This is misleading and should be removed**

---

### **Class C — Governance/Meta Engines (MUST NOT generate reports)**

| Engine ID | Display Name | Backend `/report` | `report_sections` | Frontend Generate | Status |
|-----------|--------------|-------------------|-------------------|-------------------|--------|
| `engine_erp_integration_readiness` | ERP Integration Readiness | ❌ NO | ✅ NO (empty) | ⚠️ **SHOWN IF PROBED** | **❌ CRITICAL VIOLATION** |

**Class C Findings:**
- **Backend is correct** — No `/report` endpoint
- **Frontend VIOLATION:** Report workflow stage is visible (blocked state)

---

## DETAILED FINDINGS

### **CRITICAL DEFECT #1: `engine_distressed_asset_debt_stress` — Missing `/report` Endpoint**

**Location:** `backend/app/engines/enterprise_distressed_asset_debt_stress/engine.py`

**Issue:**
- EngineSpec defines `report_sections=("metadata", "debt_exposure", "stress_tests", "assumptions")`
- **NO `/report` endpoint exists** in the router
- Frontend will probe and find no endpoint, causing confusion

**Required Fix:**
- **Option A (Recommended):** Add `/report` endpoint to match Class A requirements
- **Option B:** Remove `report_sections` from EngineSpec if reports are not intended

**Severity:** CRITICAL — Class A engine must support reports

---

### **CRITICAL VIOLATION #1-3: Class B/C Engines Show Report UI**

**Location:** `frontend/web/src/components/engines/engine-page.tsx` (lines 208-238)

**Issue:**
- All engines show a "Report" lifecycle stage in the UI
- For Class B/C engines, the stage shows as "blocked" with message "No engine report endpoint detected"
- **This violates Class B/C requirements** — Report UI must be **completely removed**, not disabled

**Current Behavior:**
```typescript
{
  id: "report",
  label: "Report",
  status: !reportSupported ? "blocked" : ...,
  blockedReason: !reportSupported ? "No engine report endpoint detected" : ...,
}
```

**Required Fix:**
- **Conditionally exclude** the "report" stage from `lifecycleStages` array for Class B/C engines
- Use engine classification to determine visibility
- **Do not show "blocked" state** — show nothing

**Affected Engines:**
- `engine_audit_readiness` (Class B)
- `engine_data_migration_readiness` (Class B)
- `engine_regulatory_readiness` (Class B)
- `engine_erp_integration_readiness` (Class C)

**Severity:** CRITICAL — Violates engine class requirements

---

### **MINOR DEFECT #1: `engine_enterprise_litigation_dispute` — Empty `report_sections`**

**Location:** `backend/app/engines/enterprise_litigation_dispute/engine.py`

**Issue:**
- Engine has `/report` endpoint (Class A requirement met)
- `report_sections=()` is empty tuple
- **Inconsistent but functional** — endpoint exists, sections can be added later

**Required Fix:**
- Add appropriate `report_sections` to EngineSpec for consistency
- Or document why sections are empty

**Severity:** MINOR — Functional but inconsistent

---

### **BACKEND INCONSISTENCY: Class B Engines with `report_sections`**

**Issue:**
- `engine_audit_readiness` has `report_sections` defined (multiple sections)
- `engine_regulatory_readiness` has `report_sections` defined (4 sections)
- These are Class B engines and should NOT have report sections

**Required Fix:**
- Remove `report_sections` from EngineSpec for:
  - `engine_audit_readiness`
  - `engine_regulatory_readiness`
- Keep empty tuple `()` for Class B engines

**Severity:** MEDIUM — Misleading but non-functional

---

## MANDATORY FRONTEND CHANGES

### **Change #1: Remove Report Stage for Class B/C Engines**

**File:** `frontend/web/src/components/engines/engine-page.tsx`

**Action:**
1. Create engine classification helper:
```typescript
const ENGINE_CLASSES = {
  CLASS_A: [
    "engine_csrd",
    "engine_financial_forensics",
    "engine_construction_cost_intelligence",
    "engine_enterprise_capital_debt_readiness",
    "engine_enterprise_insurance_claim_forensics",
    "engine_enterprise_litigation_dispute",
    "engine_distressed_asset_debt_stress",
  ],
  CLASS_B: [
    "engine_audit_readiness",
    "engine_data_migration_readiness",
    "engine_regulatory_readiness",
  ],
  CLASS_C: [
    "engine_erp_integration_readiness",
  ],
} as const;

function isClassA(engineId: string): boolean {
  return ENGINE_CLASSES.CLASS_A.includes(engineId as any);
}
```

2. Filter lifecycle stages:
```typescript
const lifecycleStages = useMemo(() => {
  const stages = [
    // ... import, normalize, calculate stages ...
    // Conditionally include report stage
    ...(isClassA(engineId) ? [{
      id: "report",
      // ... report stage config ...
    }] : []),
    // ... audit stage ...
  ];
  return stages;
}, [engineId, ...]);
```

**Priority:** CRITICAL

---

### **Change #2: Remove Workflow and Report from Sidebar**

**File:** `frontend/web/src/components/layout/sidebar.tsx`

**Status:** ✅ **COMPLETED** — Links removed

---

## MANDATORY BACKEND CHANGES

### **Change #1: Add `/report` Endpoint to `engine_distressed_asset_debt_stress`**

**File:** `backend/app/engines/enterprise_distressed_asset_debt_stress/engine.py`

**Action:**
- Add `@router.post("/report")` endpoint
- Implement report assembly logic
- Match pattern from other Class A engines

**Priority:** CRITICAL

---

### **Change #2: Remove `report_sections` from Class B Engines**

**Files:**
- `backend/app/engines/audit_readiness/engine.py`
- `backend/app/engines/regulatory_readiness/engine.py`

**Action:**
- Change `report_sections=(...)` to `report_sections=()`
- Remove any report-related documentation

**Priority:** MEDIUM

---

### **Change #3: Add `report_sections` to `engine_enterprise_litigation_dispute`**

**File:** `backend/app/engines/enterprise_litigation_dispute/engine.py`

**Action:**
- Define appropriate report sections in EngineSpec
- Document sections in engine README

**Priority:** LOW

---

## COMPLIANCE MATRIX

| Engine | Class | Backend Report | Frontend Report UI | Compliance |
|--------|-------|----------------|-------------------|------------|
| CSRD | A | ✅ | ✅ | ✅ PASS |
| Financial Forensics | A | ✅ | ✅ | ✅ PASS |
| Construction Cost | A | ✅ | ✅ | ✅ PASS |
| Capital & Loan | A | ✅ | ✅ | ✅ PASS |
| Insurance Claim | A | ✅ | ✅ | ✅ PASS |
| Litigation Dispute | A | ✅ | ✅ | ⚠️ MINOR (empty sections) |
| Distressed Asset | A | ❌ | ✅ | ❌ FAIL |
| Audit Readiness | B | ❌ | ⚠️ (blocked) | ❌ FAIL |
| Data Migration | B | ❌ | ⚠️ (blocked) | ❌ FAIL |
| Regulatory Readiness | B | ❌ | ⚠️ (blocked) | ❌ FAIL |
| ERP Integration | C | ❌ | ⚠️ (blocked) | ❌ FAIL |

**Compliance Rate:** 5/11 engines fully compliant (45%)

---

## FINAL VERDICT

**STATUS: NON-COMPLIANT — FIXES REQUIRED**

**Summary:**
- **5 engines** fully compliant (Class A engines, except Distressed Asset)
- **6 engines** non-compliant:
  - 1 Class A engine missing `/report` endpoint
  - 4 Class B/C engines showing report UI (must be removed)
  - 1 Class A engine with inconsistent `report_sections`

**Required Actions:**
1. ✅ **COMPLETED:** Remove Workflow/Report from sidebar
2. **CRITICAL:** Add `/report` endpoint to `engine_distressed_asset_debt_stress`
3. **CRITICAL:** Remove report stage UI for Class B/C engines
4. **MEDIUM:** Remove `report_sections` from Class B engines
5. **LOW:** Add `report_sections` to `engine_enterprise_litigation_dispute`

**Estimated Fix Time:** 2-4 hours

---

**Audit Complete**

