# **Agent 2: Final Audit Report for CSRD Engine**

**Date:** 2025-01-XX  
**Auditor:** Agent 2 — Architecture & Risk Auditor  
**Scope:** Final verification of CSRD Engine compliance with DatasetVersion enforcement and evidence linkage requirements

---

## **Executive Summary**

**Status:** ✅ **AUDIT PASSED — FULLY COMPLIANT**

The CSRD (Corporate Sustainability Reporting Directive) engine implementation has been **fully verified** and complies with all Platform Laws and architectural requirements. This final audit confirms that DatasetVersion enforcement and evidence linkage are properly implemented with enhanced immutability guards.

---

## **Audit Tasks**

### **1. DatasetVersion Enforcement Validation**

#### **Audit Task:**
- **Verify** that **DatasetVersion** is properly enforced throughout the CSRD engine.
  - **Ensure** that `dataset_version_id` is required as a parameter and **validated** before processing.
  - **Confirm** that **DatasetVersion** is bound to all outputs (materiality assessments, emission factors, reports).
- **Check** for immutability enforcement:
  - **Ensure** that no **update/delete operations** are found on records linked to **DatasetVersion**.

#### **Checkpoints:**
- ✅ **DatasetVersion validation** is **mandatory** at the entry point.
- ✅ All outputs (materiality, emission factors, reports) are **linked to DatasetVersion**.
- ✅ No **update/delete operations** are allowed once records are created.

### **2. Evidence Linkage Validation**

#### **Audit Task:**
- **Confirm** that all **findings** and **reports** are linked to **EvidenceRecords**.
- **Verify** that each **FindingRecord** is linked to an **EvidenceRecord** via **FindingEvidenceLink** and that the link is traceable back to **DatasetVersion** and **RawRecord**.

#### **Checkpoints:**
- ✅ **EvidenceRecords** are created for every **report** and **finding**.
- ✅ **Assumptions** are documented and linked to findings.

---

## **Findings**

### **1. DatasetVersion Enforcement Validation: ✅ PASSED**

**Assessment:** DatasetVersion is properly enforced throughout the CSRD engine with enhanced immutability guards.

#### **1.1 DatasetVersion as Mandatory Parameter — ✅ VERIFIED**

**Evidence:**
- ✅ **Entrypoint validation** (`backend/app/engines/csrd/run.py:42-47`):
  ```python
  def _validate_dataset_version_id(value: object) -> str:
      if value is None:
          raise DatasetVersionMissingError("DATASET_VERSION_ID_REQUIRED")
      if not isinstance(value, str) or not value.strip():
          raise DatasetVersionInvalidError("DATASET_VERSION_ID_INVALID")
      return value.strip()
  ```
  - Hard-fail if `dataset_version_id` is None
  - Hard-fail if `dataset_version_id` is not a string or is empty
  - No defaults, no inference

- ✅ **Engine entrypoint** (`backend/app/engines/csrd/run.py:129-131`):
  ```python
  async def run_engine(*, dataset_version_id: object, started_at: object, parameters: dict | None = None) -> dict:
      install_immutability_guards()
      dv_id = _validate_dataset_version_id(dataset_version_id)
  ```
  - `dataset_version_id` is a required parameter (not optional)
  - Validated immediately at function entry
  - Immutability guards installed before processing

- ✅ **API endpoint** (`backend/app/engines/csrd/engine.py:40-41`):
  ```python
  return await run_engine(
      dataset_version_id=payload.get("dataset_version_id"),
      ...
  )
  ```
  - API extracts `dataset_version_id` from payload
  - Errors are properly handled and returned as HTTP 400/404

**Compliance:** ✅ **PASS** — DatasetVersion is mandatory with no defaults or inference.

---

#### **1.2 DatasetVersion Existence Check — ✅ VERIFIED**

**Evidence:**
- ✅ **Existence validation** (`backend/app/engines/csrd/run.py:137-139`):
  ```python
  dv = await db.scalar(select(DatasetVersion).where(DatasetVersion.id == dv_id))
  if dv is None:
      raise DatasetVersionNotFoundError("DATASET_VERSION_NOT_FOUND")
  ```
  - DatasetVersion existence is verified before any processing
  - Hard-fail if DatasetVersion does not exist
  - No fallback or default behavior

**Compliance:** ✅ **PASS** — DatasetVersion existence is verified before processing.

---

#### **1.3 DatasetVersion Binding to All Outputs — ✅ VERIFIED**

**Evidence:**
- ✅ **Materiality findings** (`backend/app/engines/csrd/run.py:172-175`):
  ```python
  material_findings.append({
      "id": deterministic_id(dv_id, "finding", f.stable_key),
      "dataset_version_id": dv_id,
      ...
  })
  ```
  - Every finding includes `dataset_version_id` in its payload
  - Finding ID is deterministic (includes `dataset_version_id`)

- ✅ **Emission calculations** (`backend/app/engines/csrd/run.py:190-191`):
  ```python
  emissions_payload = {
      "dataset_version_id": dv_id,
      "scopes": {...},
      ...
  }
  ```
  - Emission payload includes `dataset_version_id`
  - Emissions evidence is bound to `dataset_version_id` (line 205, 210)

- ✅ **Report generation** (`backend/app/engines/csrd/reporting.py:7, 27, 47`):
  ```python
  def generate_esrs_report(
      *,
      report_id: str,
      dataset_version_id: str,
      ...
  ) -> dict:
      ...
      "data_integrity": {
          "dataset_version_id": dataset_version_id,
          ...
      },
      ...
      "metadata": {
          "dataset_version_id": dataset_version_id,
          ...
      }
  ```
  - Report function requires `dataset_version_id` parameter
  - Report metadata includes `dataset_version_id`
  - Data integrity section includes `dataset_version_id`

- ✅ **Evidence creation** (`backend/app/engines/csrd/run.py:204-215, 229-240`):
  ```python
  emissions_evidence_id = deterministic_evidence_id(
      dataset_version_id=dv_id, engine_id="engine_csrd", kind="emissions", stable_key="scopes_v1"
  )
  await _strict_create_evidence(
      db,
      evidence_id=emissions_evidence_id,
      dataset_version_id=dv_id,
      ...
  )
  ```
  - Emissions evidence is bound to `dataset_version_id`
  - Report evidence is bound to `dataset_version_id`
  - Evidence ID generation includes `dataset_version_id`

- ✅ **Finding creation** (`backend/app/engines/csrd/run.py:244-252`):
  ```python
  await _strict_create_finding(
      db,
      finding_id=finding_id,
      dataset_version_id=dv_id,
      raw_record_id=source_raw_id,
      ...
  )
  ```
  - Every finding is created with `dataset_version_id`
  - FindingRecord model requires `dataset_version_id` (foreign key constraint)

- ✅ **Finding evidence** (`backend/app/engines/csrd/run.py:253-272`):
  ```python
  ev_id = deterministic_evidence_id(
      dataset_version_id=dv_id,
      engine_id="engine_csrd",
      kind="finding",
      stable_key=finding_id,
  )
  await _strict_create_evidence(
      db,
      evidence_id=ev_id,
      dataset_version_id=dv_id,
      ...
  )
  ```
  - Finding evidence is bound to `dataset_version_id`
  - Evidence ID generation includes `dataset_version_id`

- ✅ **Function parameters** (`backend/app/engines/csrd/materiality.py:38, emissions.py:28`):
  ```python
  def assess_double_materiality(
      *,
      dataset_version_id: str,
      ...
  )
  
  def calculate_emissions(*, dataset_version_id: str, esg: dict, parameters: dict) -> EmissionsResult:
  ```
  - Materiality assessment function requires `dataset_version_id`
  - Emission calculation function requires `dataset_version_id`

**Compliance:** ✅ **PASS** — All outputs (findings, emissions, reports, evidence) are bound to DatasetVersion.

---

#### **1.4 Database Model Constraints — ✅ VERIFIED**

**Evidence:**
- ✅ **FindingRecord model** (`backend/app/core/evidence/models.py:28-29`):
  ```python
  dataset_version_id: Mapped[str] = mapped_column(
      String, ForeignKey("dataset_version.id"), nullable=False, index=True
  )
  ```
  - Database constraint enforces DatasetVersion binding
  - Foreign key prevents orphaned findings

- ✅ **EvidenceRecord model** (`backend/app/core/evidence/models.py:15-16`):
  ```python
  dataset_version_id: Mapped[str] = mapped_column(
      String, ForeignKey("dataset_version.id"), nullable=False, index=True
  )
  ```
  - Database constraint enforces DatasetVersion binding
  - Foreign key prevents orphaned evidence

**Compliance:** ✅ **PASS** — Database constraints enforce DatasetVersion binding at the schema level.

---

#### **1.5 Immutability Enforcement — ✅ VERIFIED**

**Evidence:**
- ✅ **Immutability guards installed** (`backend/app/engines/csrd/run.py:130`):
  ```python
  install_immutability_guards()
  ```
  - Immutability guards are installed before any processing
  - Prevents update/delete operations on core records

- ✅ **No mutation operations**: Search for `update|delete|modify|mutate` in `/backend/app/engines/csrd` returned **zero matches** (excluding function names like `_strict_create_evidence`).

- ✅ **Strict creation functions with conflict detection**:
  - `_strict_create_evidence()` (`run.py:58-83`):
    - Checks for existing evidence by ID
    - Validates immutability: raises `ImmutableConflictError` if dataset_version_id, engine_id, kind, or payload mismatch
    - Prevents overwrite of existing evidence
  - `_strict_create_finding()` (`run.py:86-111`):
    - Checks for existing finding by ID
    - Validates immutability: raises `ImmutableConflictError` if dataset_version_id, raw_record_id, kind, or payload mismatch
    - Prevents overwrite of existing findings
  - `_strict_link()` (`run.py:114-126`):
    - Checks for existing link by ID
    - Validates immutability: raises `ImmutableConflictError` if finding_id or evidence_id mismatch
    - Prevents overwrite of existing links

- ✅ **Idempotent creation**: All creation functions check for existing records and return existing if found (with immutability validation)

- ✅ **Append-only pattern**: All database operations use `db.add()` (create), never `db.update()` or `db.delete()`

**Compliance:** ✅ **PASS** — Immutability is enforced: no update/delete operations, idempotent creation with conflict detection, append-only storage, immutability guards installed.

---

### **2. Evidence Linkage Validation: ✅ PASSED**

**Assessment:** Evidence linkage is properly implemented: all findings, emission calculations, and reports are linked to EvidenceRecords with full traceability.

#### **2.1 Evidence Creation for Reports — ✅ VERIFIED**

**Evidence:**
- ✅ **Report evidence creation** (`backend/app/engines/csrd/run.py:229-240`):
  ```python
  report_evidence_id = deterministic_evidence_id(
      dataset_version_id=dv_id, engine_id="engine_csrd", kind="report", stable_key="report"
  )
  await _strict_create_evidence(
      db,
      evidence_id=report_evidence_id,
      dataset_version_id=dv_id,
      engine_id="engine_csrd",
      kind="report",
      payload={"report": report},
      created_at=started,
  )
  ```
  - Report is persisted as evidence
  - Evidence ID is deterministic (includes `dataset_version_id`)
  - Evidence payload contains complete report
  - Evidence is bound to `dataset_version_id`
  - Uses strict creation function with immutability validation

**Compliance:** ✅ **PASS** — Reports are linked to EvidenceRecords.

---

#### **2.2 Evidence Creation for Emissions — ✅ VERIFIED**

**Evidence:**
- ✅ **Emissions evidence creation** (`backend/app/engines/csrd/run.py:204-215`):
  ```python
  emissions_evidence_id = deterministic_evidence_id(
      dataset_version_id=dv_id, engine_id="engine_csrd", kind="emissions", stable_key="scopes_v1"
  )
  await _strict_create_evidence(
      db,
      evidence_id=emissions_evidence_id,
      dataset_version_id=dv_id,
      engine_id="engine_csrd",
      kind="emissions",
      payload={
          "emissions": emissions_payload,
          "assumptions": emissions_res.assumptions,
          "source_raw_record_id": source_raw_id
      },
      created_at=started,
  )
  ```
  - Emissions are persisted as separate evidence
  - Evidence payload includes emissions data, assumptions, and source raw record ID
  - Evidence is bound to `dataset_version_id`
  - Uses strict creation function with immutability validation

**Compliance:** ✅ **PASS** — Emission calculations are linked to EvidenceRecords.

---

#### **2.3 Evidence Creation for Findings — ✅ VERIFIED**

**Evidence:**
- ✅ **Finding evidence creation** (`backend/app/engines/csrd/run.py:253-272`):
  ```python
  ev_id = deterministic_evidence_id(
      dataset_version_id=dv_id,
      engine_id="engine_csrd",
      kind="finding",
      stable_key=finding_id,
  )
  await _strict_create_evidence(
      db,
      evidence_id=ev_id,
      dataset_version_id=dv_id,
      engine_id="engine_csrd",
      kind="finding",
      payload={
          "source_raw_record_id": source_raw_id,
          "finding": f,
          "assumptions": assumptions,
          "emissions_evidence_id": emissions_evidence_id,
      },
      created_at=started,
  )
  ```
  - Every finding has associated evidence
  - Evidence payload includes:
    - `source_raw_record_id`: Link to source RawRecord
    - `finding`: Complete finding data
    - `assumptions`: All assumptions used in calculation
    - `emissions_evidence_id`: Link to emissions evidence
  - Evidence ID is deterministic (includes `dataset_version_id`)
  - Uses strict creation function with immutability validation

**Compliance:** ✅ **PASS** — Findings are linked to EvidenceRecords with source record references and assumption documentation.

---

#### **2.4 Finding-to-Evidence Linking — ✅ VERIFIED**

**Evidence:**
- ✅ **Finding creation** (`backend/app/engines/csrd/run.py:244-252`):
  ```python
  await _strict_create_finding(
      db,
      finding_id=finding_id,
      dataset_version_id=dv_id,
      raw_record_id=source_raw_id,
      kind=f["category"],
      payload=f,
      created_at=started,
  )
  ```
  - Finding is created with `raw_record_id` (link to source RawRecord)
  - Finding is bound to `dataset_version_id`
  - Uses strict creation function with immutability validation

- ✅ **Evidence linking** (`backend/app/engines/csrd/run.py:273-274`):
  ```python
  link_id = deterministic_id(dv_id, "link", finding_id, ev_id)
  await _strict_link(db, link_id=link_id, finding_id=finding_id, evidence_id=ev_id)
  ```
  - Finding is explicitly linked to evidence via `FindingEvidenceLink`
  - Link ID is deterministic
  - Link is idempotent with immutability validation (checks for existing link and validates consistency)

**Compliance:** ✅ **PASS** — Findings are linked to EvidenceRecords via explicit links with immutability validation.

---

#### **2.5 Traceability Chain — ✅ VERIFIED**

**Evidence:**
- ✅ **FindingRecord model** (`backend/app/core/evidence/models.py:24-36`):
  ```python
  class FindingRecord(Base):
      finding_id: Mapped[str] = mapped_column(String, primary_key=True)
      dataset_version_id: Mapped[str] = mapped_column(
          String, ForeignKey("dataset_version.id"), nullable=False, index=True
      )
      raw_record_id: Mapped[str] = mapped_column(
          String, ForeignKey("raw_record.raw_record_id"), nullable=False, index=True
      )
      ...
  ```
  - Finding links to DatasetVersion (via foreign key)
  - Finding links to RawRecord (via foreign key)

- ✅ **FindingEvidenceLink model** (`backend/app/core/evidence/models.py:39-48`):
  ```python
  class FindingEvidenceLink(Base):
      link_id: Mapped[str] = mapped_column(String, primary_key=True)
      finding_id: Mapped[str] = mapped_column(
          String, ForeignKey("finding_record.finding_id"), nullable=False, index=True
      )
      evidence_id: Mapped[str] = mapped_column(
          String, ForeignKey("evidence_records.evidence_id"), nullable=False, index=True
      )
  ```
  - Link connects FindingRecord to EvidenceRecord
  - Both foreign keys enforce referential integrity

- ✅ **Evidence payload includes source** (`backend/app/engines/csrd/run.py:265-270`):
  ```python
  payload={
      "source_raw_record_id": source_raw_id,
      "finding": f,
      "assumptions": assumptions,
      "emissions_evidence_id": emissions_evidence_id,
  }
  ```
  - Evidence payload includes `source_raw_record_id` for traceability
  - Evidence payload includes complete finding data
  - Evidence payload includes all assumptions
  - Evidence payload includes link to emissions evidence

**Traceability Chain:**
```
DatasetVersion (immutable)
  └── RawRecord (source data)
       └── FindingRecord (materiality finding)
            └── FindingEvidenceLink
                 └── EvidenceRecord (evidence with assumptions, source, emissions link)
                      └── EmissionsEvidenceRecord (emissions calculations)
```

**Compliance:** ✅ **PASS** — Full traceability chain: DatasetVersion → RawRecord → FindingRecord → EvidenceRecord → EmissionsEvidenceRecord.

---

#### **2.6 Assumption Transparency — ✅ VERIFIED**

**Evidence:**
- ✅ **Assumptions in evidence payload** (`backend/app/engines/csrd/run.py:158-167`):
  ```python
  assumptions: list[dict] = [
      {
          "id": a.assumption_id,
          "description": a.description,
          "source": a.source,
          "impact": a.impact,
          "sensitivity": a.sensitivity,
      }
      for a in assumptions_dc
  ] + list(emissions_res.assumptions)
  ```
  - Assumptions are collected from materiality assessment
  - Assumptions are collected from emission calculations
  - Assumptions include all required fields: `id`, `description`, `source`, `impact`, `sensitivity`

- ✅ **Assumptions in evidence** (`backend/app/engines/csrd/run.py:265-270`):
  ```python
  payload={
      "source_raw_record_id": source_raw_id,
      "finding": f,
      "assumptions": assumptions,
      "emissions_evidence_id": emissions_evidence_id,
  }
  ```
  - Assumptions are included in finding evidence payload
  - Assumptions are traceable to specific findings

- ✅ **Assumptions in emissions evidence** (`backend/app/engines/csrd/run.py:213`):
  ```python
  payload={
      "emissions": emissions_payload,
      "assumptions": emissions_res.assumptions,
      "source_raw_record_id": source_raw_id
  }
  ```
  - Assumptions are included in emissions evidence payload

- ✅ **Assumption sources documented**:
  - Materiality assumptions (`backend/app/engines/csrd/materiality.py:49-57`):
    - Carbon price assumption with source and sensitivity
  - Emission assumptions (`backend/app/engines/csrd/emissions.py:38-46, 62-70`):
    - Unit convention assumption
    - Default emission factors assumption (with source and sensitivity)

**Compliance:** ✅ **PASS** — All assumptions are explicit, documented, and included in evidence payloads.

---

## **Test Coverage Verification**

**Evidence:**
- ✅ **Integration test** (`backend/tests/engine_csrd/test_csrd_engine.py:112-173`):
  - Tests DatasetVersion binding in response
  - Tests evidence creation and DatasetVersion binding
  - Tests finding creation and RawRecord linking
  - Tests FindingEvidenceLink creation
  - Validates traceability chain

- ✅ **Emission calculation tests** (`backend/tests/engine_csrd/test_csrd_engine.py:175-232`):
  - Tests various emission scenarios
  - Validates DatasetVersion binding in reports

- ✅ **Materiality assessment tests** (`backend/tests/engine_csrd/test_csrd_engine.py:234-289`):
  - Tests materiality assessment logic
  - Validates findings generation

**Compliance:** ✅ **PASS** — Test coverage validates DatasetVersion enforcement and evidence linkage.

---

## **Compliance Summary**

### **Platform Law Compliance**

- ✅ **Platform Law #1**: Core is mechanics-only — **COMPLIANT**
  - CSRD engine logic is in `/backend/app/engines/csrd/`
  - No CSRD logic in core

- ✅ **Platform Law #3**: DatasetVersion is mandatory — **COMPLIANT**
  - `dataset_version_id` is required parameter
  - No defaults, no inference
  - DatasetVersion existence verified
  - All outputs bound to DatasetVersion
  - Immutability guards installed

- ✅ **Platform Law #5**: Evidence is core-owned and engine-agnostic — **COMPLIANT**
  - Uses core evidence service (`backend/app/core/evidence/service.py`)
  - Evidence creation via `create_evidence()` (wrapped in `_strict_create_evidence()`)
  - Finding creation via `create_finding()` (wrapped in `_strict_create_finding()`)
  - Link creation via `link_finding_to_evidence()` (wrapped in `_strict_link()`)

### **Engine Execution Template Compliance**

- ✅ **Phase 1 — Validate**: `dataset_version_id` validated at entry — **COMPLIANT**
- ✅ **Phase 2 — Acquire inputs**: RawRecords loaded via DatasetVersion — **COMPLIANT**
- ✅ **Phase 4 — Produce findings**: Findings generated with deterministic IDs — **COMPLIANT**
- ✅ **Phase 5 — Derive outputs**: Reports generated and bound to DatasetVersion — **COMPLIANT**
- ✅ **Phase 7 — Persist**: Append-only writes to core tables (EvidenceRecord, FindingRecord) with immutability validation — **COMPLIANT**

### **Immutability Requirements**

- ✅ **No update/delete operations**: Zero matches found
- ✅ **Idempotent creation**: All creation functions check for existing records
- ✅ **Immutability conflict detection**: Strict creation functions validate consistency
- ✅ **Immutability guards**: Installed before processing
- ✅ **Append-only pattern**: All operations use `db.add()`

---

## **Conclusion**

### **Overall Status: ✅ AUDIT PASSED — FULLY COMPLIANT**

**Summary:**
1. ✅ **DatasetVersion Enforcement**: **PASSED** — DatasetVersion is mandatory, validated, bound to all outputs, and immutability is enforced with conflict detection
2. ✅ **Evidence Linkage**: **PASSED** — All findings, emission calculations, and reports are linked to EvidenceRecords with full traceability and assumption documentation

**Key Strengths:**
- ✅ Strong validation at entry (DatasetVersion required, validated, existence checked)
- ✅ Enhanced immutability guards with conflict detection
- ✅ Complete traceability chain (DatasetVersion → RawRecord → FindingRecord → EvidenceRecord → EmissionsEvidenceRecord)
- ✅ Immutability enforced (no update/delete operations, idempotent creation with conflict validation, append-only storage)
- ✅ Assumption transparency (all assumptions documented and included in evidence)
- ✅ Database constraints enforce referential integrity
- ✅ Comprehensive test coverage

**No Remediation Required:**
- ✅ All audit checkpoints passed
- ✅ Platform Laws compliance verified
- ✅ Engine Execution Template compliance verified
- ✅ Immutability requirements verified
- ✅ Evidence linkage requirements verified

---

**Audit Status:** ✅ **PASSED — FULLY COMPLIANT**  
**Remediation Required:** ❌ **NONE**  
**Stop Condition:** ✅ **MET** — Audit report complete, confirming DatasetVersion enforcement and evidence linkage are fully validated and compliant.


