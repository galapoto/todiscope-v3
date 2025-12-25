# API Implementation Guide for Frontend Integration

**Date:** 2025-01-XX  
**Purpose:** Complete guide for integrating real backend APIs into frontend widgets

---

## 1. API Base Configuration

### Base URL
```typescript
// Development
const API_BASE_URL = 'http://localhost:8400'

// Production (set via environment variable)
const API_BASE_URL = process.env.VITE_API_BASE_URL || 'http://localhost:8400'
```

### Authentication
```typescript
// Header-based API Key
headers: {
  'X-API-Key': process.env.VITE_API_KEY || '', // Optional if TODISCOPE_API_KEYS not set
  'Content-Type': 'application/json'
}
```

**Note:** If `TODISCOPE_API_KEYS` environment variable is not set on the backend, authentication is disabled (dev mode).

---

## 2. Dataset Endpoints

### 2.1 List Dataset Versions

**Issue:** There is **no dedicated GET endpoint** for listing dataset versions.

**Workaround Solution:**
```typescript
// Query audit logs to discover dataset versions
async function listDatasetVersions() {
  const response = await apiClient.get('/audit/logs', {
    params: {
      action_type: 'import',
      limit: 1000
    }
  })
  
  // Extract unique dataset_version_ids
  const datasetIds = new Set<string>()
  response.data.logs.forEach((log: any) => {
    if (log.dataset_version_id) {
      datasetIds.add(log.dataset_version_id)
    }
  })
  
  // Return as array with metadata
  return Array.from(datasetIds).map(id => ({
    id,
    created_at: response.data.logs.find((l: any) => l.dataset_version_id === id)?.created_at || new Date().toISOString()
  }))
}
```

**Alternative:** Create a custom endpoint in the backend if needed, or use the audit log approach above.

### 2.2 Get Dataset Version Details

**Endpoint:** Query via audit logs or use dataset_version_id directly in engine calls.

---

## 3. Engine Run Endpoints - Response Schemas

### 3.1 CSRD Engine

**Endpoint:** `POST /api/v3/engines/csrd/run`

**Request:**
```json
{
  "dataset_version_id": "uuidv7-string",
  "started_at": "2025-01-01T00:00:00Z",
  "parameters": {}
}
```

**Response Schema:**
```typescript
interface CSRDRunResponse {
  dataset_version_id: string
  started_at: string
  run_id: string
  findings_count: number
  evidence_ids: string[]
}
```

### 3.2 Financial Forensics Engine

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

**Response Schema:**
```typescript
interface FinancialForensicsRunResponse {
  dataset_version_id: string
  started_at: string
  run_id: string
  findings_count: number
  evidence_ids: string[]
}
```

### 3.3 Construction Cost Intelligence Engine

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

**Response Schema:**
```typescript
interface ConstructionCostRunResponse {
  engine_id: string
  dataset_version_id: string
  started_at: string
  assumptions: Record<string, any>
  traceability: {
    assumptions_evidence_id: string
    inputs_evidence_ids: string[]
    finding_ids: string[]
  }
  comparison: {
    identity_fields: string[]
    // ... other comparison fields
  }
}
```

### 3.4 Audit Readiness Engine

**Endpoint:** `POST /api/v3/engines/audit-readiness/run`

**Request:**
```json
{
  "dataset_version_id": "uuidv7-string",
  "started_at": "2025-01-01T00:00:00Z",
  "regulatory_frameworks": ["framework_id_1"],
  "control_catalog": {},
  "evaluation_scope": {},
  "parameters": {}
}
```

**Response Schema:**
```typescript
interface AuditReadinessRunResponse {
  dataset_version_id: string
  run_id: string
  started_at: string
  regulatory_results: Array<{
    framework_id: string
    framework_name: string
    check_status: 'ready' | 'not_ready' | 'partial' | 'unknown'
    risk_level: 'critical' | 'high' | 'medium' | 'low' | 'none'
    risk_score: number
    controls_assessed: number
    controls_passing: number
    controls_failing: number
    control_gaps: Array<{
      control_id: string
      control_name: string
      gap_type: 'missing' | 'incomplete' | 'insufficient'
      severity: 'critical' | 'high' | 'medium' | 'low'
      description: string
      evidence_required: string[]
      remediation_guidance?: string
    }>
    evidence_ids: string[]
  }>
  findings_count: number
  evidence_ids: string[]
  audit_trail_entries: number
}
```

**Widget Data Mapping:**
- **Pending Reviews:** `regulatory_results` with `check_status !== 'ready'`
- **High Priority:** `regulatory_results` with `risk_level === 'critical' || risk_level === 'high'`
- **Overdue:** Filter by `controls_failing > 0` or custom logic

### 3.5 Enterprise Capital & Debt Readiness Engine

**Endpoint:** `POST /api/v3/engines/enterprise-capital-debt-readiness/run`

**Request:**
```json
{
  "dataset_version_id": "uuidv7-string",
  "started_at": "2025-01-01T00:00:00Z",
  "parameters": {}
}
```

**Response Schema:**
```typescript
interface CapitalDebtReadinessRunResponse {
  dataset_version_id: string
  started_at: string
  run_id: string
  findings_count: number
  evidence_ids: string[]
}
```

### 3.6 Data Migration & ERP Readiness Engine

**Endpoint:** `POST /api/v3/engines/data-migration-readiness/run`

**Request:**
```json
{
  "dataset_version_id": "uuidv7-string",
  "started_at": "2025-01-01T00:00:00Z",
  "parameters": {}
}
```

**Response Schema:**
```typescript
interface DataMigrationReadinessRunResponse {
  dataset_version_id: string
  started_at: string
  run_id: string
  findings_count: number
  evidence_ids: string[]
}
```

---

## 4. Engine Report Endpoints - Response Schemas

### 4.1 Financial Forensics Report

**Endpoint:** `POST /api/v3/engines/financial-forensics/report`

**Request:**
```json
{
  "dataset_version_id": "uuidv7-string",
  "run_id": "run-id",
  "parameters": {}
}
```

**Response Schema:**
```typescript
interface FinancialForensicsReportResponse {
  dataset_version_id: string
  run_id: string
  report: {
    financial_forensics_stub: {
      summary: {
        total_exposure: string // Decimal as string
        leakage_breakdown: Array<{
          typology: string
          finding_count: number
          total_exposure_abs: string
        }>
      }
      findings: Array<{
        finding_id: string
        rule_id: string
        rule_version: string
        confidence: number
        finding_type: string
        typology: string
        exposure_abs: string
        exposure_signed: string
        matched_record_ids: string[]
      }>
      evidence: Array<{
        evidence_id: string
        kind: string
        payload: Record<string, any>
      }>
    }
  }
  metadata: Record<string, any>
}
```

**Widget Data Mapping:**
- **Financial Exposure:** `report.financial_forensics_stub.summary.total_exposure`
- **Breakdown:** `report.financial_forensics_stub.summary.leakage_breakdown`
- **Trend:** Calculate from historical runs or use report metadata

### 4.2 Construction Cost Intelligence Report

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

**Response Schema (cost_variance):**
```typescript
interface CostVarianceReportResponse {
  dataset_version_id: string
  run_id: string
  report_type: 'cost_variance'
  report: {
    metadata: Record<string, any>
    executive_summary: {
      total_variance: string
      total_boq_cost: string
      total_actual_cost: string
      severity_breakdown: Record<string, number>
    }
    variance_summary_by_severity: Array<{
      severity: string
      count: number
      total_variance: string
    }>
    variance_summary_by_category: Array<{
      category: string
      count: number
      total_variance: string
    }>
    cost_variances: Array<{
      item_id: string
      severity: string
      direction: 'over_budget' | 'under_budget' | 'on_budget'
      boq_cost: string
      actual_cost: string
      variance: string
      variance_percentage: string
      category?: string
    }>
    evidence: Array<{
      evidence_id: string
      kind: string
      payload: Record<string, any>
    }>
  }
}
```

**Response Schema (time_phased):**
```typescript
interface TimePhasedReportResponse {
  dataset_version_id: string
  run_id: string
  report_type: 'time_phased'
  report: {
    metadata: Record<string, any>
    time_phased_report: {
      period_type: 'daily' | 'weekly' | 'monthly' | 'quarterly' | 'yearly'
      periods: Array<{
        period_identifier: string
        boq_total_cost: string
        actual_total_cost: string
        variance: string
        item_count: number
      }>
      totals: {
        boq_total_cost: string
        actual_total_cost: string
        total_variance: string
      }
    }
    evidence: Array<{
      evidence_id: string
      kind: string
      payload: Record<string, any>
    }>
  }
}
```

**Widget Data Mapping:**
- **Cost Variance:** Use `cost_variance` report type
- **Time Series:** Use `time_phased` report type for charts
- **Historical Data:** Store multiple runs and aggregate

### 4.3 Enterprise Capital & Debt Readiness Report

**Endpoint:** `POST /api/v3/engines/enterprise-capital-debt-readiness/report`

**Request:**
```json
{
  "dataset_version_id": "uuidv7-string"
}
```

**Response Schema:**
```typescript
interface CapitalDebtReadinessReportResponse {
  dataset_version_id: string
  report: {
    readiness_scores: Record<string, number>
    findings: Array<{
      finding_id: string
      severity: string
      description: string
    }>
    evidence: Array<{
      evidence_id: string
      kind: string
      payload: Record<string, any>
    }>
  }
}
```

### 4.4 Enterprise Deal Transaction Readiness Report

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

**Response Schema:**
```typescript
interface TransactionReadinessReportResponse {
  dataset_version_id: string
  run_id: string
  view_type: 'internal' | 'external'
  report: {
    readiness_assessment: {
      overall_readiness: string
      scores: Record<string, number>
    }
    findings: Array<{
      finding_id: string
      severity: string
      description: string
    }>
    evidence: Array<{
      evidence_id: string
      kind: string
      payload: Record<string, any>
    }>
  }
}
```

### 4.5 Enterprise Litigation Dispute Report

**Endpoint:** `POST /api/v3/engines/enterprise-litigation-dispute/report`

**Request:**
```json
{
  "dataset_version_id": "uuidv7-string"
}
```

**Response Schema:**
```typescript
interface LitigationDisputeReportResponse {
  dataset_version_id: string
  report: {
    dispute_analysis: Record<string, any>
    findings: Array<{
      finding_id: string
      severity: string
      description: string
    }>
    evidence: Array<{
      evidence_id: string
      kind: string
      payload: Record<string, any>
    }>
  }
}
```

---

## 5. Real-Time Strategy

### 5.1 Current Implementation: Polling Only

**No WebSocket Support**

The backend does **not** currently implement WebSocket endpoints. Use React Query polling:

```typescript
// Example: Polling engine run status
const { data, isLoading } = useQuery({
  queryKey: ['engine-run', engineId, datasetVersionId],
  queryFn: async () => {
    const response = await apiClient.post(`/engines/${engineId}/run`, {
      dataset_version_id: datasetVersionId,
      started_at: new Date().toISOString(),
      parameters: {}
    })
    return response.data
  },
  refetchInterval: 30000, // 30 seconds
  enabled: !!datasetVersionId
})
```

### 5.2 Recommended Polling Intervals

- **Widget Metrics:** 30 seconds
- **Report Data:** 60 seconds (or on-demand)
- **Dataset List:** 5 minutes (or on-demand)

---

## 6. Widget Data Mapping

### 6.1 Financial Exposure Widget

**Data Source:** Financial Forensics Report

```typescript
// Fetch report
const { data: report } = useQuery({
  queryKey: ['financial-forensics-report', datasetVersionId, runId],
  queryFn: () => apiClient.post('/engines/financial-forensics/report', {
    dataset_version_id: datasetVersionId,
    run_id: runId,
    parameters: {}
  }),
  refetchInterval: 30000
})

// Map to widget data
const widgetData = {
  totalExposure: parseFloat(report?.report.financial_forensics_stub.summary.total_exposure || '0'),
  currency: 'EUR', // Default or from metadata
  trend: calculateTrend(previousReport, currentReport),
  trendPercentage: calculateTrendPercentage(previousReport, currentReport),
  breakdown: report?.report.financial_forensics_stub.summary.leakage_breakdown.map(item => ({
    category: item.typology,
    amount: parseFloat(item.total_exposure_abs),
    percentage: (parseFloat(item.total_exposure_abs) / totalExposure) * 100
  }))
}
```

### 6.2 Pending Reviews Widget

**Data Source:** Audit Readiness Engine Run

```typescript
// Fetch run results
const { data: runData } = useQuery({
  queryKey: ['audit-readiness-run', datasetVersionId],
  queryFn: () => apiClient.post('/engines/audit-readiness/run', {
    dataset_version_id: datasetVersionId,
    started_at: new Date().toISOString(),
    regulatory_frameworks: [],
    parameters: {}
  }),
  refetchInterval: 30000
})

// Map to widget data
const widgetData = {
  total: runData?.regulatory_results.length || 0,
  highPriority: runData?.regulatory_results.filter(
    (r: any) => r.risk_level === 'critical' || r.risk_level === 'high'
  ).length || 0,
  overdue: runData?.regulatory_results.filter(
    (r: any) => r.controls_failing > 0
  ).length || 0,
  reviews: runData?.regulatory_results.map((result: any) => ({
    id: result.framework_id,
    title: result.framework_name,
    priority: result.risk_level === 'critical' ? 'high' : 
              result.risk_level === 'high' ? 'high' : 'medium',
    dueDate: calculateDueDate(result), // Custom logic
    assignee: 'System', // Default or from metadata
    status: result.check_status === 'ready' ? 'pending' : 
            result.check_status === 'not_ready' ? 'overdue' : 'in-progress'
  }))
}
```

### 6.3 CO2 Emissions Widget

**Data Source:** CSRD Engine Report (or custom endpoint if available)

```typescript
// Note: CO2 emissions may need a custom engine or data source
// For now, use CSRD engine findings or create mock data structure

// If CSRD engine provides emissions data:
const { data: csrdData } = useQuery({
  queryKey: ['csrd-run', datasetVersionId],
  queryFn: () => apiClient.post('/engines/csrd/run', {
    dataset_version_id: datasetVersionId,
    started_at: new Date().toISOString(),
    parameters: {}
  }),
  refetchInterval: 30000
})

// Map to widget data (adjust based on actual CSRD response structure)
const widgetData = {
  total: extractCO2Total(csrdData), // Custom extraction logic
  unit: 'tCO2e',
  trend: calculateTrend(previousData, currentData),
  trendPercentage: calculateTrendPercentage(previousData, currentData),
  byScope: extractScopeBreakdown(csrdData), // Custom extraction
  historical: getHistoricalData(datasetVersionId) // Store historical runs
}
```

---

## 7. Typed API Client Implementation

### 7.1 Complete API Client

```typescript
// src/lib/api-client.ts
import axios, { AxiosInstance } from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8400'
const API_KEY = import.meta.env.VITE_API_KEY

export const apiClient: AxiosInstance = axios.create({
  baseURL: `${API_BASE_URL}/api/v3`,
  headers: {
    'Content-Type': 'application/json',
    ...(API_KEY && { 'X-API-Key': API_KEY }),
  },
})

// Types
export interface DatasetVersion {
  id: string
  created_at: string
}

export interface Engine {
  id: string
  name: string
  enabled: boolean
}

export interface EngineRunRequest {
  dataset_version_id: string
  started_at: string
  parameters?: Record<string, any>
  [key: string]: any // Engine-specific fields
}

export interface EngineReportRequest {
  dataset_version_id: string
  run_id?: string
  report_type?: string
  view_type?: 'internal' | 'external'
  parameters?: Record<string, any>
}

// API Functions
export const api = {
  // Engine Registry
  async getEngines(): Promise<string[]> {
    const response = await apiClient.get('/engine-registry/enabled')
    return response.data.enabled_engines
  },

  // Dataset Versions (workaround via audit logs)
  async getDatasetVersions(): Promise<DatasetVersion[]> {
    const response = await apiClient.get('/audit/logs', {
      params: {
        action_type: 'import',
        limit: 1000
      }
    })
    
    const datasetIds = new Set<string>()
    const datasetMap = new Map<string, string>()
    
    response.data.logs.forEach((log: any) => {
      if (log.dataset_version_id) {
        datasetIds.add(log.dataset_version_id)
        if (!datasetMap.has(log.dataset_version_id)) {
          datasetMap.set(log.dataset_version_id, log.created_at)
        }
      }
    })
    
    return Array.from(datasetIds).map(id => ({
      id,
      created_at: datasetMap.get(id) || new Date().toISOString()
    }))
  },

  // Engine Run
  async runEngine(engineId: string, request: EngineRunRequest): Promise<any> {
    const response = await apiClient.post(`/engines/${engineId}/run`, request)
    return response.data
  },

  // Engine Report
  async generateReport(engineId: string, request: EngineReportRequest): Promise<any> {
    const response = await apiClient.post(`/engines/${engineId}/report`, request)
    return response.data
  },

  // Audit Logs
  async getAuditLogs(params?: {
    dataset_version_id?: string
    limit?: number
    offset?: number
  }): Promise<any> {
    const response = await apiClient.get('/audit/logs', { params })
    return response.data
  },
}
```

### 7.2 React Query Hooks

```typescript
// src/hooks/useEngines.ts
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api-client'

export function useEngines() {
  return useQuery({
    queryKey: ['engines'],
    queryFn: () => api.getEngines(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

// src/hooks/useDatasetVersions.ts
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api-client'

export function useDatasetVersions() {
  return useQuery({
    queryKey: ['dataset-versions'],
    queryFn: () => api.getDatasetVersions(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

// src/hooks/useEngineRun.ts
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api-client'
import type { EngineRunRequest } from '../lib/api-client'

export function useEngineRun(
  engineId: string,
  request: EngineRunRequest,
  options?: { enabled?: boolean; refetchInterval?: number }
) {
  return useQuery({
    queryKey: ['engine-run', engineId, request.dataset_version_id],
    queryFn: () => api.runEngine(engineId, request),
    enabled: options?.enabled !== false && !!request.dataset_version_id,
    refetchInterval: options?.refetchInterval || 30000, // 30 seconds default
  })
}

// src/hooks/useEngineReport.ts
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api-client'
import type { EngineReportRequest } from '../lib/api-client'

export function useEngineReport(
  engineId: string,
  request: EngineReportRequest,
  options?: { enabled?: boolean }
) {
  return useQuery({
    queryKey: ['engine-report', engineId, request.dataset_version_id, request.run_id],
    queryFn: () => api.generateReport(engineId, request),
    enabled: options?.enabled !== false && !!request.dataset_version_id,
    staleTime: 60 * 1000, // 1 minute
  })
}
```

---

## 8. Widget Implementation Examples

### 8.1 Financial Exposure Widget (Real API)

```typescript
// src/components/widgets/FinancialExposureWidget.tsx
import { useQuery } from '@tanstack/react-query'
import { useEngineReport } from '../../hooks/useEngineReport'
import { useState } from 'react'

export const FinancialExposureWidget: React.FC<{
  datasetVersionId: string
  runId?: string
}> = ({ datasetVersionId, runId }) => {
  const [isModalOpen, setIsModalOpen] = useState(false)

  const { data: report, isLoading, error, refetch } = useEngineReport(
    'financial-forensics',
    {
      dataset_version_id: datasetVersionId,
      run_id: runId || '',
      parameters: {}
    },
    { enabled: !!runId }
  )

  if (isLoading) return <LoadingSpinner />
  if (error) return <ErrorAlert onRetry={() => refetch()} />

  const summary = report?.report?.financial_forensics_stub?.summary
  const breakdown = summary?.leakage_breakdown || []
  const totalExposure = parseFloat(summary?.total_exposure || '0')

  return (
    <>
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <DollarSign className="h-6 w-6 text-primary-600" />
          <div>
            <p className="text-sm text-neutral-600">Total Exposure</p>
            <p className="text-2xl font-bold">
              {new Intl.NumberFormat('en-US', {
                style: 'currency',
                currency: 'EUR'
              }).format(totalExposure)}
            </p>
          </div>
        </div>

        <div className="space-y-2">
          {breakdown.map((item, index) => (
            <div key={index} className="space-y-1">
              <div className="flex justify-between text-sm">
                <span>{item.typology}</span>
                <span>{parseFloat(item.total_exposure_abs).toLocaleString()} EUR</span>
              </div>
              <div className="w-full bg-neutral-200 rounded-full h-2">
                <div
                  className="bg-primary-600 h-2 rounded-full"
                  style={{ width: `${(parseFloat(item.total_exposure_abs) / totalExposure) * 100}%` }}
                />
              </div>
            </div>
          ))}
        </div>

        <Button onClick={() => setIsModalOpen(true)}>
          View Details
        </Button>
      </div>

      <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)}>
        {/* Detailed breakdown */}
      </Modal>
    </>
  )
}
```

### 8.2 Pending Reviews Widget (Real API)

```typescript
// src/components/widgets/PendingReviewsWidget.tsx
import { useEngineRun } from '../../hooks/useEngineRun'

export const PendingReviewsWidget: React.FC<{
  datasetVersionId: string
}> = ({ datasetVersionId }) => {
  const { data: runData, isLoading, error } = useEngineRun(
    'audit-readiness',
    {
      dataset_version_id: datasetVersionId,
      started_at: new Date().toISOString(),
      regulatory_frameworks: [],
      parameters: {}
    },
    { refetchInterval: 30000 }
  )

  if (isLoading) return <LoadingSpinner />
  if (error) return <ErrorAlert />

  const regulatoryResults = runData?.regulatory_results || []
  const highPriority = regulatoryResults.filter(
    (r: any) => r.risk_level === 'critical' || r.risk_level === 'high'
  ).length
  const overdue = regulatoryResults.filter(
    (r: any) => r.controls_failing > 0
  ).length

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <FileCheck className="h-6 w-6 text-warning-600" />
        <div>
          <p className="text-sm text-neutral-600">Pending Reviews</p>
          <p className="text-2xl font-bold">{regulatoryResults.length}</p>
        </div>
      </div>

      <div className="space-y-2">
        <div className="flex justify-between text-sm">
          <span>High Priority</span>
          <span className="font-semibold text-error-600">{highPriority}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span>Overdue</span>
          <span className="font-semibold text-error-600">{overdue}</span>
        </div>
      </div>
    </div>
  )
}
```

---

## 9. Dataset Table with Sorting/Filtering/Pagination

```typescript
// src/components/data/DatasetTable.tsx
import { useQuery } from '@tanstack/react-query'
import { api } from '../../lib/api-client'
import { useState } from 'react'

export const DatasetTable: React.FC = () => {
  const [page, setPage] = useState(1)
  const [limit, setLimit] = useState(20)
  const [sortBy, setSortBy] = useState<'created_at' | 'id'>('created_at')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')

  const { data, isLoading } = useQuery({
    queryKey: ['dataset-versions', page, limit, sortBy, sortOrder],
    queryFn: async () => {
      const datasets = await api.getDatasetVersions()
      // Client-side sorting and pagination (or implement server-side)
      const sorted = [...datasets].sort((a, b) => {
        const aVal = a[sortBy]
        const bVal = b[sortBy]
        return sortOrder === 'asc' 
          ? aVal.localeCompare(bVal)
          : bVal.localeCompare(aVal)
      })
      const start = (page - 1) * limit
      return {
        items: sorted.slice(start, start + limit),
        total: sorted.length,
        page,
        limit
      }
    }
  })

  const handleExport = () => {
    // Export to Excel using xlsx library
    const XLSX = require('xlsx')
    const ws = XLSX.utils.json_to_sheet(data?.items || [])
    const wb = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(wb, ws, 'Datasets')
    XLSX.writeFile(wb, 'datasets.xlsx')
  }

  return (
    <div>
      <div className="flex justify-between mb-4">
        <h2>Dataset Versions</h2>
        <Button onClick={handleExport}>Export to Excel</Button>
      </div>
      
      <table>
        {/* Table implementation */}
      </table>
      
      {/* Pagination */}
    </div>
  )
}
```

---

## 10. Report Generation with AI Insights

```typescript
// src/pages/ReportGeneration.tsx (Updated)
import { useEngineReport } from '../hooks/useEngineReport'

export const ReportGeneration: React.FC = () => {
  const [selectedEngine, setSelectedEngine] = useState('')
  const [selectedDataset, setSelectedDataset] = useState('')
  const [runId, setRunId] = useState('')
  const [reportType, setReportType] = useState('')

  const { data: report, isLoading, error } = useEngineReport(
    selectedEngine,
    {
      dataset_version_id: selectedDataset,
      run_id: runId,
      report_type: reportType,
      view_type: 'internal',
      parameters: {}
    },
    { enabled: !!selectedEngine && !!selectedDataset && !!runId }
  )

  const handleExportPDF = () => {
    // Use jsPDF to generate PDF from report data
    const { jsPDF } = require('jspdf')
    const doc = new jsPDF()
    // Add report content
    doc.save('report.pdf')
  }

  const handleExportExcel = () => {
    // Use xlsx to generate Excel from report data
    const XLSX = require('xlsx')
    const ws = XLSX.utils.json_to_sheet(flattenReport(report))
    const wb = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(wb, ws, 'Report')
    XLSX.writeFile(wb, 'report.xlsx')
  }

  return (
    <div>
      {/* Form for selecting engine, dataset, run_id, report_type */}
      
      {report && (
        <div>
          <ReportViewer report={report} />
          <div className="flex gap-2">
            <Button onClick={handleExportPDF}>Export PDF</Button>
            <Button onClick={handleExportExcel}>Export Excel</Button>
          </div>
        </div>
      )}
    </div>
  )
}
```

---

## 11. Summary

### API Base URL
- **Development:** `http://localhost:8400`
- **Production:** Set via `VITE_API_BASE_URL`

### Authentication
- **Method:** `X-API-Key` header
- **Optional:** If backend `TODISCOPE_API_KEYS` not set

### Dataset Listing
- **Workaround:** Query `/api/v3/audit/logs` with `action_type=import`
- **No dedicated endpoint** currently exists

### Engine Endpoints
- **Run:** `POST /api/v3/engines/<engine-id>/run`
- **Report:** `POST /api/v3/engines/<engine-id>/report`
- **List:** `GET /api/v3/engine-registry/enabled`

### Real-Time Strategy
- **Polling only** - React Query with `refetchInterval: 30000`
- **No WebSocket** - Not implemented

### Next Steps
1. Implement typed API client
2. Replace mock data in widgets
3. Add dataset table with Excel export
4. Integrate report generation with PDF/Excel export
5. Add interactive drilldowns in modals

---

**Last Updated:** 2025-01-XX





