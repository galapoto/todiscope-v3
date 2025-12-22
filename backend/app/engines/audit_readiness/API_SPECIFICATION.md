# Audit Readiness Engine — API Specification

**Engine ID:** `engine_audit_readiness`  
**Engine Version:** `v1`  
**Last Updated:** 2025-01-XX

---

## Endpoint

**POST** `/api/v3/engines/audit-readiness/run`

Run audit readiness evaluation for regulatory frameworks.

---

## Request

### Headers
- `Content-Type: application/json`

### Body
```json
{
  "dataset_version_id": "string (UUIDv7, required)",
  "started_at": "string (ISO8601 timestamp, required)",
  "regulatory_frameworks": ["string"] (optional, default: []),
  "control_catalog": {
    "frameworks": {
      "framework_id": {
        "metadata": {
          "name": "string",
          "version": "string"
        },
        "controls": [
          {
            "control_id": "string (required)",
            "control_name": "string",
            "critical": "boolean",
            "required_evidence_types": ["string"],
            "remediation_guidance": "string (optional)"
          }
        ],
        "required_evidence_types": {
          "control_id": ["string"]
        }
      }
    }
  } (optional),
  "evaluation_scope": {} (optional, default: {}),
  "parameters": {} (optional, default: {})
}
```

### Required Fields
- `dataset_version_id`: Dataset version identifier (UUIDv7 format)
- `started_at`: ISO8601 timestamp with timezone

### Optional Fields
- `regulatory_frameworks`: List of framework IDs to evaluate
- `control_catalog`: Control catalog structure (from Agent 1)
- `evaluation_scope`: Framework-specific evaluation scope
- `parameters`: Additional runtime parameters

---

## Response

### Success (200 OK)
```json
{
  "dataset_version_id": "string",
  "run_id": "string (deterministic UUIDv5)",
  "started_at": "string (ISO8601)",
  "regulatory_results": [
    {
      "framework_id": "string",
      "framework_name": "string",
      "framework_version": "string",
      "check_status": "ready|not_ready|partial|unknown",
      "risk_level": "critical|high|medium|low|none",
      "risk_score": 0.0,
      "controls_assessed": 0,
      "controls_passing": 0,
      "controls_failing": 0,
      "control_gaps": [
        {
          "control_id": "string",
          "control_name": "string",
          "gap_type": "missing|incomplete|insufficient",
          "severity": "critical|high|medium|low",
          "description": "string",
          "evidence_required": ["string"],
          "remediation_guidance": "string (optional)"
        }
      ],
      "evidence_ids": ["string"]
    }
  ],
  "findings_count": 0,
  "evidence_ids": ["string"],
  "audit_trail_entries": 0
}
```

### Error Responses

#### 400 Bad Request
- Missing `dataset_version_id`: `"DATASET_VERSION_ID_REQUIRED"`
- Invalid `dataset_version_id`: `"DATASET_VERSION_ID_INVALID"`
- Missing `started_at`: `"STARTED_AT_REQUIRED"`
- Invalid `started_at`: `"STARTED_AT_INVALID"`
- Invalid control catalog: `"CONTROL_CATALOG_INVALID"`

#### 404 Not Found
- DatasetVersion not found: `"DATASET_VERSION_NOT_FOUND"`
- Regulatory framework not found: `"REGULATORY_FRAMEWORK_NOT_FOUND"`

#### 409 Conflict
- Raw records missing: `"RAW_RECORDS_REQUIRED"`
- Immutable conflict: `"IMMUTABLE_EVIDENCE_MISMATCH"` or `"IMMUTABLE_FINDING_MISMATCH"`

#### 500 Internal Server Error
- Evidence storage error: `"EVIDENCE_STORAGE_ERROR"`
- General engine failure: `"ENGINE_RUN_FAILED: {error_type}: {error_message}"`

#### 503 Service Unavailable
- Engine disabled: `"ENGINE_DISABLED: Engine engine_audit_readiness is disabled. Enable via TODISCOPE_ENABLED_ENGINES environment variable."`

---

## Examples

### Minimal Request
```json
{
  "dataset_version_id": "01234567-89ab-7def-0123-456789abcdef",
  "started_at": "2025-01-01T00:00:00+00:00"
}
```

### Full Request
```json
{
  "dataset_version_id": "01234567-89ab-7def-0123-456789abcdef",
  "started_at": "2025-01-01T00:00:00+00:00",
  "regulatory_frameworks": ["sox", "gdpr"],
  "control_catalog": {
    "frameworks": {
      "sox": {
        "metadata": {"name": "SOX", "version": "v1"},
        "controls": [
          {
            "control_id": "sox_ctrl_001",
            "control_name": "Access Controls",
            "critical": true,
            "required_evidence_types": ["access_logs", "policy_docs"]
          }
        ],
        "required_evidence_types": {
          "sox_ctrl_001": ["access_logs", "policy_docs"]
        }
      }
    }
  },
  "evaluation_scope": {
    "sox": {"scope": "financial_reporting"}
  },
  "parameters": {"risk_threshold": 0.7}
}
```

---

## Platform Conventions

- Endpoint follows pattern: `/api/v3/engines/{engine-id-with-dashes}/run`
- Engine ID `engine_audit_readiness` maps to endpoint `/api/v3/engines/audit-readiness/run`
- Consistent with other engines (e.g., `engine_csrd` → `/api/v3/engines/csrd/run`)

---

## Notes

- All evidence and findings are bound to `dataset_version_id`
- Run IDs are deterministic (UUIDv5) based on stable inputs
- Evidence IDs are deterministic (UUIDv5) based on DatasetVersion and stable keys
- All operations respect DatasetVersion immutability constraints

