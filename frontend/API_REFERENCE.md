# TodiScope v3 API Reference

**Base URL:** `http://localhost:8400` (development)  
**API Version:** `v3`  
**API Prefix:** `/api/v3`

---

## 1. Authentication

### Authentication Method: API Key (Header-based)

**Header:** `X-API-Key: <api_key>`

**Configuration:**
- Set via environment variable: `TODISCOPE_API_KEYS`
- Format: `key1:role1|role2,key2:role3`
- If `TODISCOPE_API_KEYS` is not set, authentication is disabled (dev mode)

**Roles:**
- `INGEST` - Can ingest data
- `READ` - Can read data
- `EXECUTE` - Can execute engines
- `ADMIN` - Full access

**Example:**
```bash
curl -X GET http://localhost:8400/api/v3/engines \
  -H "X-API-Key: your-api-key-here"
```

**Error Responses:**
- `401 UNAUTHORIZED` - `AUTH_REQUIRED` (no API key provided)
- `401 UNAUTHORIZED` - `AUTH_INVALID` (invalid API key)

---

## 2. Dataset Endpoints

### 2.1 List Dataset Versions

**Note:** There is currently **no dedicated GET endpoint** for listing dataset versions. Dataset versions are created via ingestion endpoints and can be queried through audit logs.

**Workaround:** Query audit logs filtered by `dataset_version_id` to discover available dataset versions:

**Endpoint:** `GET /api/v3/audit/logs`

**Query Parameters:**
- `dataset_version_id` (optional) - Filter by dataset version ID
- `limit` (default: 100, max: 1000) - Number of results
- `offset` (default: 0) - Pagination offset
- `start_date` (optional) - Start date filter
- `end_date` (optional) - End date filter

**Response:**
```json
{
  "logs": [
    {
      "audit_log_id": "string",
      "dataset_version_id": "string",
      "calculation_run_id": "string",
      "artifact_id": "string",
      "actor_id": "string",
      "actor_type": "string",
      "action_type": "string",
      "action_label": "string",
      "created_at": "2024-01-01T00:00:00Z",
      "reason": "string",
      "context": {},
      "metadata": {},
      "status": "success|error|warning",
      "error_message": "string"
    }
  ],
  "total": 100,
  "limit": 100,
  "offset": 0
}
```

### 2.2 Create Dataset Version

**Endpoint:** `POST /api/v3/ingest`

**Headers:**
- `Content-Type: application/json`
- `X-API-Key: <api_key>` (if authentication enabled)

**Request Body:**
```json
{
  "records": []
}
```

**Response:**
```json
{
  "dataset_version_id": "01234567-89ab-7def-0123-456789abcdef",
  "import_id": "import-uuid",
  "data_quality": {}
}
```

### 2.3 Ingest Records

**Endpoint:** `POST /api/v3/ingest-records`

**Headers:**
- `Content-Type: application/json`
- `X-API-Key: <api_key>` (if authentication enabled)

**Request Body:**
```json
{
  "records": [
    {
      "field1": "value1",
      "field2": "value2"
    }
  ]
}
```

**Response:**
```json
{
  "dataset_version_id": "01234567-89ab-7def-0123-456789abcdef",
  "import_id": "import-uuid",
  "raw_records_written": 10,
  "data_quality": {}
}
```

### 2.4 Ingest File

**Endpoint:** `POST /api/v3/ingest-file`

**Headers:**
- `Content-Type: multipart/form-data`
- `X-API-Key: <api_key>` (if authentication enabled)

**Form Data:**
- `file` (required) - File to upload (JSON, CSV, or NDJSON)
- `normalize` (optional, default: false) - Whether to normalize
- `expected_checksum` (optional) - SHA256 checksum to verify

**Response:**
```json
{
  "dataset_version_id": "01234567-89ab-7def-0123-456789abcdef",
  "import_id": "import-uuid",
  "raw_records_written": 10,
  "data_quality": {},
  "file_checksum": "sha256-hex-string"
}
```

---

## 3. Engine Registry

### 3.1 List Enabled Engines

**Endpoint:** `GET /api/v3/engine-registry/enabled`

**Response:**
```json
{
  "enabled_engines": [
    "engine_csrd",
    "engine_financial_forensics",
    "engine_construction_cost_intelligence",
    "engine_audit_readiness",
    "engine_enterprise_capital_debt_readiness",
    "engine_data_migration_readiness"
  ]
}
```

---

## 4. Engine Run Endpoints

All engines follow the same pattern: `POST /api/v3/engines/<engine-id>/run`

### 4.1 CSRD Engine

**Endpoint:** `POST /api/v3/engines/csrd/run`

**Request:**
```json
{
  "dataset_version_id": "uuidv7-string",
  "started_at": "2025-01-01T00:00:00Z",
  "parameters": {}
}
```

**Response:**
```json
{
  "dataset_version_id": "uuidv7-string",
  "started_at": "2025-01-01T00:00:00Z",
  "run_id": "uuidv5-string",
  "findings_count": 0,
  "evidence_ids": ["ev_id_1", "ev_id_2"]
}
```

### 4.2 Financial Forensics Engine

**Endpoint:** `POST /api/v3/engines/financial-forensics/run`

**Request:**
```json
{
  "dataset_version_id": "uuidv7-string",
  "fx_artifact_id": "fx-artifact-id (optional)",
  "started_at": "2025-01-01T00:00:00Z",
  "parameters": {}
}
```

**Response:**
```json
{
  "dataset_version_id": "uuidv7-string",
  "started_at": "2025-01-01T00:00:00Z",
  "run_id": "uuidv5-string",
  "findings_count": 0,
  "evidence_ids": ["ev_id_1"]
}
```

### 4.3 Construction Cost Intelligence Engine

**Endpoint:** `POST /api/v3/engines/cost-intelligence/run`

**Request:**
```json
{
  "dataset_version_id": "uuidv7-string",
  "started_at": "2025-01-01T00:00:00Z",
  "boq_raw_record_id": "raw-record-id",
  "actual_raw_record_id": "raw-record-id",
  "normalization_mapping": {},
  "comparison_config": {}
}
```

**Response:**
```json
{
  "engine_id": "engine_construction_cost_intelligence",
  "dataset_version_id": "uuidv7-string",
  "started_at": "2025-01-01T00:00:00Z",
  "assumptions": {},
  "traceability": {
    "assumptions_evidence_id": "ev_id",
    "inputs_evidence_ids": ["ev_id_1"],
    "finding_ids": ["finding_id_1"]
  },
  "comparison": {
    "identity_fields": ["field1", "field2"]
  }
}
```

### 4.4 Audit Readiness Engine

**Endpoint:** `POST /api/v3/engines/audit-readiness/run`

**Request:**
```json
{
  "dataset_version_id": "uuidv7-string",
  "started_at": "2025-01-01T00:00:00Z",
  "regulatory_frameworks": ["framework_id_1"],
  "control_catalog": {
    "frameworks": {
      "framework_id_1": {
        "metadata": {"name": "Framework Name", "version": "v1"},
        "controls": [],
        "required_evidence_types": {}
      }
    }
  },
  "evaluation_scope": {},
  "parameters": {}
}
```

**Response:**
```json
{
  "dataset_version_id": "uuidv7-string",
  "run_id": "uuidv5-string",
  "started_at": "2025-01-01T00:00:00Z",
  "regulatory_results": [
    {
      "framework_id": "framework_id_1",
      "framework_name": "Framework Name",
      "check_status": "ready|not_ready|partial|unknown",
      "risk_level": "critical|high|medium|low|none",
      "risk_score": 0.0,
      "controls_assessed": 10,
      "controls_passing": 8,
      "controls_failing": 2,
      "control_gaps": [],
      "evidence_ids": ["ev_id_1"]
    }
  ],
  "findings_count": 2,
  "evidence_ids": ["ev_id_1", "ev_id_2"],
  "audit_trail_entries": 5
}
```

### 4.5 Enterprise Capital & Debt Readiness Engine

**Endpoint:** `POST /api/v3/engines/enterprise-capital-debt-readiness/run`

**Request:**
```json
{
  "dataset_version_id": "uuidv7-string",
  "started_at": "2025-01-01T00:00:00Z",
  "parameters": {}
}
```

**Response:**
```json
{
  "dataset_version_id": "uuidv7-string",
  "started_at": "2025-01-01T00:00:00Z",
  "run_id": "uuidv5-string",
  "findings_count": 0,
  "evidence_ids": ["ev_id_1"]
}
```

### 4.6 Data Migration & ERP Readiness Engine

**Endpoint:** `POST /api/v3/engines/data-migration-readiness/run`

**Request:**
```json
{
  "dataset_version_id": "uuidv7-string",
  "started_at": "2025-01-01T00:00:00Z",
  "parameters": {}
}
```

**Response:**
```json
{
  "dataset_version_id": "uuidv7-string",
  "started_at": "2025-01-01T00:00:00Z",
  "run_id": "uuidv5-string",
  "findings_count": 0,
  "evidence_ids": ["ev_id_1"]
}
```

---

## 5. Engine Report Endpoints

All engines follow the pattern: `POST /api/v3/engines/<engine-id>/report`

### 5.1 Financial Forensics Report

**Endpoint:** `POST /api/v3/engines/financial-forensics/report`

**Request:**
```json
{
  "dataset_version_id": "uuidv7-string",
  "run_id": "run-id",
  "parameters": {}
}
```

**Response:**
```json
{
  "dataset_version_id": "uuidv7-string",
  "run_id": "run-id",
  "report": {
    "financial_forensics_stub": {
      "summary": {},
      "findings": [],
      "evidence": []
    }
  },
  "metadata": {}
}
```

### 5.2 Construction Cost Intelligence Report

**Endpoint:** `POST /api/v3/engines/cost-intelligence/report`

**Request:**
```json
{
  "dataset_version_id": "uuidv7-string",
  "run_id": "run-id",
  "report_type": "cost_variance|time_phased",
  "parameters": {
    "core_traceability": {}
  },
  "emit_evidence": true
}
```

**Response:**
```json
{
  "dataset_version_id": "uuidv7-string",
  "run_id": "run-id",
  "report_type": "cost_variance",
  "report": {
    "metadata": {},
    "summary": {},
    "variance_analysis": {},
    "findings": [],
    "evidence": []
  }
}
```

### 5.3 Enterprise Capital & Debt Readiness Report

**Endpoint:** `POST /api/v3/engines/enterprise-capital-debt-readiness/report`

**Request:**
```json
{
  "dataset_version_id": "uuidv7-string"
}
```

**Response:**
```json
{
  "dataset_version_id": "uuidv7-string",
  "report": {
    "readiness_scores": {},
    "findings": [],
    "evidence": []
  }
}
```

### 5.4 Enterprise Deal Transaction Readiness Report

**Endpoint:** `POST /api/v3/engines/enterprise-deal-transaction-readiness/report`

**Request:**
```json
{
  "dataset_version_id": "uuidv7-string",
  "run_id": "run-id",
  "view_type": "internal|external",
  "anonymization_salt": "optional-salt"
}
```

**Response:**
```json
{
  "dataset_version_id": "uuidv7-string",
  "run_id": "run-id",
  "view_type": "internal",
  "report": {
    "readiness_assessment": {},
    "findings": [],
    "evidence": []
  }
}
```

### 5.5 Enterprise Litigation Dispute Report

**Endpoint:** `POST /api/v3/engines/enterprise-litigation-dispute/report`

**Request:**
```json
{
  "dataset_version_id": "uuidv7-string"
}
```

**Response:**
```json
{
  "dataset_version_id": "uuidv7-string",
  "report": {
    "dispute_analysis": {},
    "findings": [],
    "evidence": []
  }
}
```

---

## 6. Metrics Endpoints

### 6.1 Prometheus Metrics

**Endpoint:** `GET /metrics`

**Response:** Prometheus metrics format

**Available Metrics:**
- `todiscope_http_requests_total` - Total HTTP requests
- `todiscope_http_request_duration_seconds` - Request duration
- `todiscope_engine_runs_total` - Engine run attempts
- `todiscope_engine_run_duration_seconds` - Engine run duration
- `todiscope_engine_exports_total` - Engine export attempts
- `todiscope_engine_errors_total` - Engine errors by type

**Note:** There are **no engine-specific metrics endpoints** for widget data. Metrics are aggregated at the Prometheus level.

**For Widget Data:**
- Use engine run endpoints to get current state
- Use report endpoints for detailed analysis
- Poll endpoints using React Query for real-time updates

---

## 7. Real-Time Strategy

### 7.1 Current Implementation: Polling Only

**No WebSocket Support:** The backend does not currently implement WebSocket endpoints for real-time updates.

**Recommended Approach:**
- Use **React Query** with `refetchInterval` for polling
- Poll engine run endpoints every 30 seconds
- Poll report endpoints when needed
- Use React Query's caching to minimize API calls

**Example:**
```typescript
const { data, isLoading } = useQuery({
  queryKey: ['engine-run', engineId, datasetVersionId],
  queryFn: () => apiClient.runEngine(engineId, { dataset_version_id: datasetVersionId }),
  refetchInterval: 30000, // 30 seconds
})
```

### 7.2 Future Enhancement: WebSocket Support

**Not Currently Implemented**

If WebSocket support is needed, it would need to be added to the backend. Current architecture supports polling via React Query.

---

## 8. Engine-Specific Widget Data

### 8.1 CSRD Engine Widget Data

**Endpoint:** `POST /api/v3/engines/csrd/run`

**Widget-Relevant Response Fields:**
- `findings_count` - Number of findings
- `evidence_ids` - List of evidence IDs
- Use report endpoint for detailed breakdown

### 8.2 Financial Forensics Widget Data

**Endpoint:** `POST /api/v3/engines/financial-forensics/run`

**Widget-Relevant Response Fields:**
- `findings_count` - Number of findings
- `evidence_ids` - List of evidence IDs
- Use report endpoint for financial analysis details

### 8.3 Construction Cost Intelligence Widget Data

**Endpoint:** `POST /api/v3/engines/cost-intelligence/run`

**Widget-Relevant Response Fields:**
- `comparison.identity_fields` - Fields used for comparison
- `traceability.finding_ids` - Finding IDs
- Use report endpoint for cost variance/time-phased analysis

### 8.4 Audit Readiness Widget Data

**Endpoint:** `POST /api/v3/engines/audit-readiness/run`

**Widget-Relevant Response Fields:**
- `regulatory_results` - Array of framework results
  - `check_status` - ready|not_ready|partial|unknown
  - `risk_level` - critical|high|medium|low|none
  - `risk_score` - Numeric risk score
  - `controls_assessed` - Total controls
  - `controls_passing` - Passing controls
  - `controls_failing` - Failing controls
- `findings_count` - Total findings
- `audit_trail_entries` - Audit log entries

### 8.5 Capital & Debt Readiness Widget Data

**Endpoint:** `POST /api/v3/engines/enterprise-capital-debt-readiness/run`

**Widget-Relevant Response Fields:**
- `findings_count` - Number of findings
- `evidence_ids` - List of evidence IDs
- Use report endpoint for readiness scores

### 8.6 Data Migration & ERP Readiness Widget Data

**Endpoint:** `POST /api/v3/engines/data-migration-readiness/run`

**Widget-Relevant Response Fields:**
- `findings_count` - Number of findings
- `evidence_ids` - List of evidence IDs
- Use report endpoint for migration readiness details

---

## 9. Error Responses

### Common Error Codes

| Status | Error Code | Description |
|--------|------------|-------------|
| 400 | `DATASET_VERSION_ID_REQUIRED` | Missing dataset_version_id |
| 400 | `DATASET_VERSION_ID_INVALID` | Invalid format |
| 400 | `STARTED_AT_REQUIRED` | Missing started_at |
| 400 | `STARTED_AT_INVALID` | Invalid timestamp format |
| 400 | `RUN_ID_REQUIRED` | Missing run_id (for reports) |
| 404 | `DATASET_VERSION_NOT_FOUND` | Dataset version doesn't exist |
| 409 | `RAW_RECORDS_REQUIRED` | No raw records for dataset |
| 500 | `ENGINE_RUN_FAILED` | Engine execution failed |
| 503 | `ENGINE_DISABLED` | Engine is disabled |

---

## 10. Example API Client Implementation

```typescript
// src/lib/api-client.ts
import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8400'
const API_KEY = import.meta.env.VITE_API_KEY

const apiClient = axios.create({
  baseURL: `${API_BASE_URL}/api/v3`,
  headers: {
    'Content-Type': 'application/json',
    ...(API_KEY && { 'X-API-Key': API_KEY }),
  },
})

// Dataset endpoints
export const datasetApi = {
  list: async () => {
    // Workaround: Query audit logs
    const response = await apiClient.get('/audit/logs', {
      params: { limit: 1000, action_type: 'import' }
    })
    // Extract unique dataset_version_ids from logs
    const datasetIds = [...new Set(
      response.data.logs.map((log: any) => log.dataset_version_id).filter(Boolean)
    )]
    return datasetIds.map((id: string) => ({ id, created_at: new Date().toISOString() }))
  },
  
  ingest: async (records: any[]) => {
    const response = await apiClient.post('/ingest-records', { records })
    return response.data
  },
}

// Engine endpoints
export const engineApi = {
  list: async () => {
    const response = await apiClient.get('/engine-registry/enabled')
    return response.data.enabled_engines
  },
  
  run: async (engineId: string, payload: any) => {
    const response = await apiClient.post(`/engines/${engineId}/run`, payload)
    return response.data
  },
  
  report: async (engineId: string, payload: any) => {
    const response = await apiClient.post(`/engines/${engineId}/report`, payload)
    return response.data
  },
}
```

---

## 11. Summary

### API Base URL
- **Development:** `http://localhost:8400`
- **Production:** Configure via environment variable

### Authentication
- **Method:** API Key (Header: `X-API-Key`)
- **Optional:** If `TODISCOPE_API_KEYS` not set, auth is disabled

### Dataset Listing
- **No dedicated endpoint** - Use audit logs workaround
- **Create:** `POST /api/v3/ingest-records` or `/ingest-file`

### Engine Endpoints
- **Run:** `POST /api/v3/engines/<engine-id>/run`
- **Report:** `POST /api/v3/engines/<engine-id>/report`
- **List:** `GET /api/v3/engine-registry/enabled`

### Real-Time Strategy
- **Polling only** - Use React Query with `refetchInterval`
- **No WebSocket** - Not currently implemented
- **Recommended interval:** 30 seconds

### Metrics
- **Prometheus:** `GET /metrics`
- **No engine-specific metrics endpoints** - Use run/report endpoints for widget data

---

**Last Updated:** 2025-01-XX  
**API Version:** v3





