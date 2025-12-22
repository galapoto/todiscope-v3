# **Agent 2: Audit Report for CSRD Engine Implementation**

**Date:** 2025-01-XX  
**Auditor:** Agent 2 — Architecture & Risk Auditor  
**Scope:** CSRD Engine implementation compliance with Platform Laws and architectural requirements

---

## **Executive Summary**

**Status:** ⚠️ **ENGINE NOT IMPLEMENTED**

The CSRD (Corporate Sustainability Reporting Directive) engine is **not implemented** in the codebase. Only test files, documentation, and placeholder code exist. This audit report documents the current state and provides findings based on what exists and what should exist.

---

## **Audit Tasks**

### **1. Domain Logic Validation**

#### **Audit Task:**
- Ensure that **no CSRD-specific logic** has leaked into the core.
- Confirm that the **CSRD engine** handles only materiality assessments, emission factors, and report generation logic.

### **2. DatasetVersion and Immutability Enforcement**

#### **Audit Task:**
- Validate that the CSRD engine properly **creates DatasetVersion** and enforces **immutability**.
- Ensure that all findings, emission calculations, and reports are **linked** to **DatasetVersion**.

### **3. Evidence Linkage and Assumption Transparency**

#### **Audit Task:**
- Confirm that **evidence** is linked to both **DatasetVersion** and **source records**.
- Ensure that assumptions used in materiality and emission calculations are **explicit** and **traceable**.

---

## **Findings**

### **1. Domain Logic Validation: ✅ PASSED (Core Separation Verified)**

**Assessment:** No CSRD-specific logic has leaked into the core structure.

**Evidence:**
- ✅ **Core audit verification**: Previous core skeleton audit confirmed zero CSRD/ESRS references in `/backend/app/core`
- ✅ **No CSRD imports in core**: Search for CSRD-related terms in core modules returned zero matches
- ✅ **Core remains mechanics-only**: All core modules (dataset, evidence, artifacts, review, engine_registry) contain no domain logic

**CSRD Engine Implementation Status:**
- ❌ **Engine not implemented**: No CSRD engine directory exists in `/backend/app/engines/`
- ❌ **Engine not registered**: CSRD engine is not registered in `backend/app/engines/__init__.py`
- ⚠️ **Test files exist**: Test file `backend/tests/engine_csrd/test_csrd_engine.py` exists but tests placeholder logic
- ⚠️ **Documentation exists**: 
  - `backend/app/engines/csrd_compliance_checklist.md` (compliance checklist)
  - `backend/app/engines/example_esrs_report_template.md` (example template)

**Test File Analysis:**
- The test file (`backend/tests/engine_csrd/test_csrd_engine.py`) contains:
  - Test fixtures for engine specification with expected tables:
    - `csrd_runs`
    - `csrd_materiality_assessments`
    - `csrd_emission_factors`
    - `csrd_reports`
  - Test cases for:
    - Materiality assessment (emissions, board diversity)
    - Emission factor calculation (scope1, scope2, scope3)
    - Report generation (all required sections)
    - Evidence traceability (findings linked to source data)
    - Assumption transparency (explicit assumptions with sources)
  - **Note**: Tests contain placeholder logic, not actual engine implementation

**Compliance:** ✅ **PASS** — Core separation is maintained. No CSRD logic exists in core.

**Recommendation:** ⚠️ **CSRD Engine Implementation Required** — The engine must be implemented following the patterns established by existing engines (Financial Forensics, Enterprise Deal Transaction Readiness).

---

### **2. DatasetVersion and Immutability Enforcement: ❌ CANNOT VERIFY (Engine Not Implemented)**

**Assessment:** Cannot verify DatasetVersion enforcement because the CSRD engine is not implemented.

**Expected Requirements (Based on Platform Laws and Test File):**
- ✅ **DatasetVersion should be mandatory**: Every engine entrypoint must require `dataset_version_id`
- ✅ **DatasetVersion should be immutable**: No update/delete operations on DatasetVersion
- ✅ **All outputs should be bound to DatasetVersion**: Findings, emission calculations, and reports must reference `dataset_version_id`

**Test File Expectations:**
- Test file shows expected structure with `dataset_version_id` in:
  - Report metadata (line 173 in test file)
  - Findings (line 237 in test file)
  - Evidence traceability (line 231 in test file)

**Comparison with Existing Engines:**
- ✅ **Financial Forensics Engine** (`backend/app/engines/financial_forensics/run.py`):
  - Requires `dataset_version_id: str | None` parameter (line 243)
  - Validates `dataset_version_id` at entry (line 262)
  - Checks DatasetVersion existence (lines 272-277)
  - All models bind to `dataset_version_id` via foreign keys
- ✅ **Enterprise Deal Transaction Readiness Engine** (`backend/app/engines/enterprise_deal_transaction_readiness/run.py`):
  - Requires `dataset_version_id` parameter
  - Validates DatasetVersion at entry
  - All findings and evidence bound to `dataset_version_id`

**Compliance:** ❌ **CANNOT VERIFY** — Engine not implemented.

**Recommendation:** ⚠️ **CRITICAL** — When implementing the CSRD engine, it MUST:
1. Require `dataset_version_id` as a mandatory parameter (no defaults, no inference)
2. Validate DatasetVersion existence before processing
3. Bind all outputs (materiality assessments, emission factors, reports) to `dataset_version_id`
4. Use foreign key constraints to enforce DatasetVersion binding in database models
5. Follow the same pattern as Financial Forensics and Enterprise Deal Transaction Readiness engines

---

### **3. Evidence Linkage and Assumption Transparency: ❌ CANNOT VERIFY (Engine Not Implemented)**

**Assessment:** Cannot verify evidence linkage and assumption transparency because the CSRD engine is not implemented.

**Expected Requirements (Based on Platform Laws and Test File):**
- ✅ **Evidence must be linked to DatasetVersion**: Every evidence record requires `dataset_version_id`
- ✅ **Evidence must be linked to source records**: Findings should reference source data records
- ✅ **Assumptions must be explicit**: All assumptions used in calculations must be documented with:
  - Assumption ID
  - Description
  - Source
  - Impact assessment
  - Sensitivity analysis

**Test File Expectations:**
- Test file shows expected evidence structure:
  - Findings with `dataset_version_id` (line 237)
  - Findings with `source_data` array (lines 241-254)
  - Findings with `assumptions` array (lines 255-261)
  - Assumptions with required fields: `id`, `description`, `source`, `impact`, `sensitivity` (lines 301-316)

**Comparison with Existing Engines:**
- ✅ **Financial Forensics Engine** (`backend/app/engines/financial_forensics/evidence.py`):
  - Evidence creation requires `dataset_version_id` (line 30)
  - Evidence ID includes `dataset_version_id` in deterministic generation
  - Evidence schema includes rule identity, tolerance, amount comparison, and source record references
- ✅ **Financial Forensics Leakage** (`backend/app/engines/financial_forensics/leakage/evidence_emitter.py`):
  - Evidence creation requires `dataset_version_id` (line 23)
  - Evidence schema includes typology assignment, exposure derivation, finding references, and primary records

**Compliance:** ❌ **CANNOT VERIFY** — Engine not implemented.

**Recommendation:** ⚠️ **CRITICAL** — When implementing the CSRD engine, it MUST:
1. Use core evidence service (`backend/app/core/evidence/service.py`) for evidence creation
2. Require `dataset_version_id` for all evidence creation
3. Link evidence to source records (emission data, financial data, etc.)
4. Document all assumptions explicitly in evidence payloads:
   - Emission factor sources (IEA, GHG Protocol, etc.)
   - Materiality thresholds
   - Calculation methodologies
   - Sensitivity ranges
5. Follow the evidence schema pattern established by Financial Forensics engine

---

## **Detailed Analysis**

### **Current State**

#### **What Exists:**
1. **Test File** (`backend/tests/engine_csrd/test_csrd_engine.py`):
   - Test fixtures for engine specification
   - Test cases for materiality assessment, emission factors, report generation
   - Test cases for evidence traceability and assumption transparency
   - **Status**: Placeholder tests, not testing actual implementation

2. **Documentation**:
   - `backend/app/engines/csrd_compliance_checklist.md`: Compliance checklist
   - `backend/app/engines/example_esrs_report_template.md`: Example ESRS report template

#### **What's Missing:**
1. **Engine Implementation**:
   - No engine directory: `/backend/app/engines/csrd/` does not exist
   - No engine registration in `backend/app/engines/__init__.py`
   - No engine models (runs, materiality assessments, emission factors, reports)
   - No engine service logic (materiality assessment, emission calculations, report generation)
   - No engine API endpoints (routers)
   - No engine registration function

2. **Database Models**:
   - No `CsrdRun` model
   - No `CsrdMaterialityAssessment` model
   - No `CsrdEmissionFactor` model
   - No `CsrdReport` model

3. **Evidence Integration**:
   - No evidence emission functions
   - No evidence schema definitions
   - No assumption documentation structure

---

## **Implementation Requirements**

Based on Platform Laws and existing engine patterns, the CSRD engine MUST implement:

### **1. Engine Structure**
```
backend/app/engines/csrd/
├── __init__.py
├── engine.py              # Engine registration and API endpoints
├── run.py                 # Main engine execution logic
├── models/
│   ├── __init__.py
│   ├── runs.py            # CsrdRun model
│   ├── materiality.py     # CsrdMaterialityAssessment model
│   ├── emissions.py       # CsrdEmissionFactor model
│   └── reports.py         # CsrdReport model
├── materiality/
│   ├── __init__.py
│   ├── assessor.py        # Materiality assessment logic
│   └── thresholds.py      # Materiality thresholds
├── emissions/
│   ├── __init__.py
│   ├── calculator.py      # Emission calculation logic
│   └── factors.py         # Emission factor management
├── evidence/
│   ├── __init__.py
│   ├── schema_v1.py       # Evidence schema definition
│   └── emitter.py         # Evidence emission functions
└── report/
    ├── __init__.py
    ├── assembler.py       # Report assembly logic
    └── sections.py       # Report section generators
```

### **2. DatasetVersion Requirements**
- ✅ All entrypoints require `dataset_version_id: str` (not optional)
- ✅ DatasetVersion validation at entry (existence check)
- ✅ All models have `dataset_version_id: Mapped[str]` with `ForeignKey("dataset_version.id"), nullable=False`
- ✅ No DatasetVersion inference or defaults

### **3. Evidence Requirements**
- ✅ Use `backend/app/core/evidence/service.py` for evidence creation
- ✅ Evidence ID generation includes `dataset_version_id`
- ✅ Evidence payload includes:
  - Source data references
  - Assumption documentation (id, description, source, impact, sensitivity)
  - Calculation methodologies
  - Materiality assessment rationale

### **4. Immutability Requirements**
- ✅ No update/delete operations on persisted records
- ✅ Idempotent creation (check for existing records by ID)
- ✅ Append-only evidence storage

### **5. Kill-Switch Requirements**
- ✅ Check `is_engine_enabled()` before any processing
- ✅ Engine registration with `enabled_by_default=False`
- ✅ No routes mounted when engine is disabled

---

## **Conclusion**

### **Overall Status: ⚠️ ENGINE NOT IMPLEMENTED**

**Summary:**
1. ✅ **Domain Logic Validation**: **PASSED** — No CSRD logic exists in core (core separation maintained)
2. ❌ **DatasetVersion Enforcement**: **CANNOT VERIFY** — Engine not implemented
3. ❌ **Evidence Linkage**: **CANNOT VERIFY** — Engine not implemented

**Critical Findings:**
- The CSRD engine does not exist as an implementation
- Only test files and documentation exist
- Engine must be implemented following Platform Laws and existing engine patterns

**Remediation Required:**
- ⚠️ **CRITICAL**: Implement the CSRD engine following the requirements outlined in this report
- The engine must comply with:
  - Platform Law #1: Core is mechanics-only (✅ already compliant)
  - Platform Law #3: DatasetVersion is mandatory
  - Platform Law #5: Evidence is core-owned and engine-agnostic
  - Engine Execution Template: All phases must be implemented
  - Evidence Safety Rules: All evidence must be bound to DatasetVersion

**Next Steps:**
1. Create engine directory structure
2. Implement database models with DatasetVersion foreign keys
3. Implement engine execution logic with DatasetVersion validation
4. Implement evidence emission with assumption documentation
5. Implement materiality assessment and emission calculation logic
6. Implement report generation
7. Register engine in `backend/app/engines/__init__.py`
8. Update tests to test actual implementation

---

**Audit Status:** ⚠️ **ENGINE NOT IMPLEMENTED**  
**Remediation Required:** ✅ **YES — CRITICAL**


