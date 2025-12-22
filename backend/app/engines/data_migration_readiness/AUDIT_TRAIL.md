# Audit Trail — Data Migration Readiness

## Risk Metadata Snapshot
- Each `RiskSignal` entry includes:
  - Deterministic `id` built from `DatasetVersion`, category, and severity (`backend/app/engines/data_migration_readiness/checks.py:268-354`).
  - `dataset_version_id` that ties the record directly to the DatasetVersion under review.
  - Sorted `source_systems` tuple appended to the metadata payload when risks are generated (`backend/app/engines/data_migration_readiness/checks.py:280-294`).
  - Immutable metadata (wrapped in `MappingProxyType`) to prevent post-creation mutation.

## Log Trace Example
- Warning emitted when risks exist:

   ```
   DATA_MIGRATION_READINESS_RISKS dataset_version_id=dv-test source_systems=('erp',) risks=['Structural requirements not met; required collections or metadata missing.', 'Duplicate source identifiers detected in the dataset.', 'Field mapping coverage is incomplete for one or more collections.', 'Data integrity violation: duplicate records would cause migration ambiguity.']
   ```

   Source: `backend/app/engines/data_migration_readiness/VALIDATION_REPORT.md:11-18`.

## Approval & Assumption Metadata
- Approval metadata is implicit in the configuration assumptions that the snapshot is immutable, field mappings are stable, and source systems enforce unique IDs (`backend/app/engines/data_migration_readiness/config/defaults.json:1-70`).
- These assumptions serve as the documented justification for the migration run and are returned with every readiness export (`backend/app/engines/data_migration_readiness/run.py:133-142`).

## Test Coverage & Regression Flags
- Unit tests confirm readiness gating, risk metadata enrichment, and log capture (`backend/app/engines/data_migration_readiness/tests/test_readiness.py:128-217`).
- Regression safety: dataclass serialization was hardened to avoid `mappingproxy` issues, preserving immutable risk payloads.

## DatasetVersion & Source-System Mapping Table
| DatasetVersion | Source Systems | Risk Types Logged | Notes |
|---------------|----------------|------------------|-------|
| `dv-test`     | (`erp`,)       | structure, quality, mapping, integrity | All risks emitted when sample raw records lacked the `accounts` collection and had a duplicate `source_record_id`. |

This table captures the trace record that auditors need for compliance reviews.
