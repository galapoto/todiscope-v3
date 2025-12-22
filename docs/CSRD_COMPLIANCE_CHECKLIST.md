# CSRD Engine Compliance Checklist (v3)

This checklist is aligned to the current `engine_csrd` implementation and its output schema.

## Checklist
- **Materiality Assessment Completed**: Yes
  - Implemented in `backend/app/engines/csrd/materiality.py` and executed in `backend/app/engines/csrd/run.py`.
- **Emission Factors Calculated**: Yes
  - Scope totals and per-scope factors returned in `report.emission_calculations.scopes` with `unit/source/methodology`.
- **Evidence Linked to DatasetVersion**: Yes
  - Emissions/report/finding evidence are persisted as `EvidenceRecord` with `dataset_version_id`.
  - Findings are linked via `FindingEvidenceLink` and include `FindingRecord.dataset_version_id`.
- **Report Sections Generated**: Yes
  - Required sections: `executive_summary`, `materiality_assessment`, `data_integrity`, `compliance_summary`, plus `emission_calculations`.
- **Assumptions Documented**: Yes
  - Engine emits `report.assumptions` and also stores assumptions in evidence payloads (`kind="emissions"` and `kind="finding"`).

## Production Expectations
- **DatasetVersion binding** is mandatory: `POST /api/v3/engines/csrd/run` requires `dataset_version_id` and validates it exists before processing.
- **Append-only immutability** is enforced:
  - Core blocks update/delete of immutable tables.
  - CSRD run fails with HTTP `409` if deterministic evidence/finding IDs would be re-used with different payloads.
- **Traceability chain** is present:
  - `DatasetVersion → RawRecord → FindingRecord → EvidenceRecord` (linked via `FindingEvidenceLink`).
- **Data integrity warnings**:
  - `report.data_integrity.warnings` is populated when required inputs are missing (e.g., missing emissions block).

