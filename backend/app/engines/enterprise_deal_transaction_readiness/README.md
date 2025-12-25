# Engine #5 — Enterprise Deal & Transaction Readiness

## Overview

Engine #5 produces deterministic, evidence-backed **Transaction Readiness Packages** for immutable DatasetVersions, suitable for enterprise due diligence and transaction workflows (e.g., data-room preparation, disclosure schedules, control/readiness checklists).

## Purpose

The engine translates already-ingested, immutable artifacts and already-produced, immutable findings/reports into a **shareable, auditable, replayable readiness view** that is strictly bound to `dataset_version_id`.

**Role:** Strictly **advisory and evidentiary** — reports packaging status, evidence coverage, binding validity, and explicit readiness gaps for the declared runtime scope.

## Explicit Non-Claims

- No assertions of transaction readiness correctness
- No assertions of deal success probability
- No scoring, grading, or ranking of readiness
- No compliance assertions (legal, regulatory, accounting)
- No recommendations or decisioning
- No assertions of business outcome correctness

## Platform Law Compliance

Engine #5 complies with all 6 TodiScope v3 Platform Laws:

1. **Law #1 — Core is mechanics-only:** All readiness domain logic lives in Engine #5
2. **Law #2 — Engines are detachable:** Engine can be disabled without impacting core boot
3. **Law #3 — DatasetVersion is mandatory:** Every run/output bound to explicit `dataset_version_id` (UUIDv7)
4. **Law #4 — Artifacts are content-addressed:** All artifacts stored via core artifact store with checksum verification
5. **Law #5 — Evidence and review are core-owned:** Evidence written to core evidence registry
6. **Law #6 — No implicit defaults:** All output-affecting parameters explicit, validated, and persisted

## Architecture

### Data Separation

- **DatasetVersion:** Immutable data snapshot (created via ingestion only)
- **Run Table:** Analysis parameters (transaction_scope, parameters, FX rates, assumptions)
- **Findings Table:** Readiness findings bound to `dataset_version_id` and deterministic `result_set_id`
- **Checklist Table:** Checklist statuses bound to `dataset_version_id` and `run_id`

### Kill-Switch

- **Dual Enforcement:**
  - Mount-time: Routes only mounted when engine enabled
  - Runtime: Entrypoint checks enabled state before any side effects
- **Disabled State:** No routes, no writes, no side effects

### Replay Contract

- Same `dataset_version_id` + same run parameters → same outputs (bitwise identical)
- All replay-stable IDs are deterministic (derived from stable keys)
- `run_id` is UUIDv7 (metadata only, not used for replay-stable IDs)

## API Endpoints

### POST `/api/v3/engines/enterprise-deal-transaction-readiness/run`

Run Engine #5 to generate readiness assessment.

**Request:**
```json
{
  "dataset_version_id": "uuidv7-string",
  "started_at": "2025-01-01T00:00:00+00:00",
  "transaction_scope": {
    "scope_kind": "full_dataset"
  },
  "parameters": {
    "fx": {
      "rates": {}
    },
    "assumptions": {
      "note": "explicit"
    }
  },
  "optional_inputs": {
    "engine2_report": {
      "artifact_key": "path/in/artifact-store.json",
      "sha256": "64-hex-sha256",
      "content_type": "application/json"
    }
  }
}
```

**Response:**
```json
{
  "engine_id": "engine_enterprise_deal_transaction_readiness",
  "engine_version": "v1",
  "run_id": "uuidv7-string",
  "result_set_id": "uuidv5-string",
  "dataset_version_id": "uuidv7-string",
  "status": "completed"
}
```

### POST `/api/v3/engines/enterprise-deal-transaction-readiness/report`

Generate transaction readiness report.

**Request:**
```json
{
  "dataset_version_id": "uuidv7-string",
  "run_id": "uuidv7-string",
  "view_type": "internal",
  "anonymization_salt": "optional"
}
```

**Response:**
```json
{
  "engine_id": "engine_enterprise_deal_transaction_readiness",
  "engine_version": "v1",
  "dataset_version_id": "uuidv7-string",
  "run_id": "uuidv7-string",
  "sections": [
    {
      "section_id": "executive_overview",
      "section_type": "executive_overview",
      ...
    },
    {
      "section_id": "readiness_findings",
      "section_type": "readiness_findings",
      ...
    },
    ...
  ]
}
```

### POST `/api/v3/engines/enterprise-deal-transaction-readiness/export`

Export report as immutable artifacts in external view (shareable) or internal view (full).

**Request:**
```json
{
  "dataset_version_id": "uuidv7-string",
  "run_id": "uuidv7-string",
  "view_type": "external",
  "formats": ["json", "pdf"],
  "anonymization_salt": "optional-salt",
  "include_report": false
}
```

**Response:**
```json
{
  "view_type": "external",
  "dataset_version_id": "uuidv7-string",
  "run_id": "uuidv7-string",
  "result_set_id": "uuidv5-string",
  "exports": [
    { "format": "json", "uri": "memory://...", "sha256": "...", "size_bytes": 123 },
    { "format": "pdf", "uri": "memory://...", "sha256": "...", "size_bytes": 456 }
  ]
}
```

## Error Handling

### Mandatory Inputs (Hard-Fail)

- `dataset_version_id`: Required, must be UUIDv7, must exist
- `transaction_scope`: Required, must be dict
- `parameters`: Required, must include "fx" and "assumptions"
- `started_at`: Required, must be ISO format with timezone

### Optional Inputs (Findings)

- Upstream engine artifacts (Engine #2, Engine #4): Missing artifacts produce deterministic "missing prerequisite" findings

## Externalization

### External View Policy

**Shareable Sections:**
- Executive overview
- Transaction scope validation
- Execution summary
- Readiness findings
- Checklist status
- Evidence index
- Limitations & uncertainty
- Explicit non-claims

**Internal-Only Sections:**
- Internal notes
- Transaction scope details
- Run parameters
- Dataset version details

**Redacted Fields:**
- `dataset_version_id`, `run_id` (anonymized)
- `transaction_scope` (redacted)
- `run_parameters` (redacted)
- Internal identifiers

**Anonymized Fields:**
- `finding_id` → `REF-xxx`
- `evidence_id` → `REF-xxx`
- `checklist_item_id` → `REF-xxx`

### Export Formats

- **JSON:** Deterministic, policy-filtered (external) or full (internal) report.
- **PDF:** Minimal deterministic PDF rendering of the exported view.
- **Artifact Store:** Exports are stored via core artifact store as immutable, content-addressed artifacts.

## Production Readiness

### Hardening Features

- Kill-switch revalidation on all endpoints
- Comprehensive error handling
- Input validation at function entry
- Deterministic ID generation
- Replay contract compliance
- External view validation

### Scalability

- Deterministic execution (no randomness, no system time)
- Idempotent operations
- Append-only persistence
- Content-addressed artifacts

### Performance

- Efficient database queries with proper indexing
- Deterministic sorting for stable outputs
- Minimal memory footprint

## Testing

See test files in `backend/tests/engine_enterprise_deal_transaction_readiness/` for:
- Transaction scope and parameter persistence
- UUIDv7 validation
- Kill-switch behavior
- Error handling

## References

- **Boundary Document:** `docs/engines/enterprise_deal_transaction_readiness/DR1_BOUNDARY.md`
- **Platform Laws:** `docs/NON_NEGOTIABLE_PLATFORM_LAWS.md`
- **Execution Template:** `docs/ENGINE_EXECUTION_TEMPLATE.md`





