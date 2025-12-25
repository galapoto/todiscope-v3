# Production Deployment Guide: Enterprise Distressed Asset & Debt Stress Engine

**Engine ID:** `engine_distressed_asset_debt_stress`  
**Engine Version:** `v1`  
**Documentation Version:** 1.0  
**Last Updated:** 2025-01-XX

---

## Table of Contents

1. [Overview](#1-overview)
2. [Prerequisites](#2-prerequisites)
3. [Installation Guide](#3-installation-guide)
4. [Configuration](#4-configuration)
5. [Deployment Procedures](#5-deployment-procedures)
6. [API Endpoints](#6-api-endpoints)
7. [Security Considerations](#7-security-considerations)
8. [Post-Deployment Checklist](#8-post-deployment-checklist)
9. [Troubleshooting](#9-troubleshooting)
10. [Maintenance](#10-maintenance)
11. [References](#11-references)

---

## 1. Overview

### 1.1 Purpose

The Enterprise Distressed Asset & Debt Stress Engine provides comprehensive financial stress testing capabilities for organizations managing distressed assets and debt exposure. The engine enables:

- **Debt Exposure Modeling**: Calculate comprehensive debt exposure metrics including total outstanding, interest rates, collateral coverage, leverage ratios, and net exposure after recovery
- **Stress Scenario Testing**: Apply deterministic stress scenarios to assess impact of adverse financial conditions (interest rate hikes, market crashes, default waves)
- **Risk Quantification**: Generate loss estimates, impact scores, and materiality-based risk classifications
- **Evidence-Based Reporting**: Produce auditable reports with full traceability to source data

### 1.2 Business Use Case

**Primary Use Cases:**
- **Risk Management**: Assess financial exposure under adverse scenarios
- **Regulatory Compliance**: Generate stress test reports for regulatory submissions
- **Portfolio Analysis**: Evaluate distressed asset recovery potential
- **Debt Restructuring**: Model impact of various restructuring scenarios
- **Due Diligence**: Assess debt exposure and recovery potential in M&A transactions

**Target Users:**
- Risk management teams
- Financial analysts
- Regulatory compliance officers
- Portfolio managers
- Due diligence teams

### 1.3 Scope

**In Scope:**
- ✅ Debt exposure calculations (single and multiple instruments)
- ✅ Distressed asset recovery modeling
- ✅ Deterministic stress scenario application
- ✅ Materiality-based risk classification
- ✅ Evidence-based reporting with full traceability

**Out of Scope:**
- ❌ Market predictions or forecasting
- ❌ Trading logic or recommendations
- ❌ Speculative financial activities
- ❌ Real-time market data integration
- ❌ Portfolio optimization

---

## 2. Prerequisites

### 2.1 System Dependencies

**Required Infrastructure:**
- **PostgreSQL**: Version 14.0 or higher
  - Used for: Core database (DatasetVersion, Evidence, Findings, NormalizedRecord)
  - Connection: Via SQLAlchemy async driver
- **Python**: Version 3.10 or higher
  - Required for: Engine execution
- **FastAPI**: Version 0.100.0 or higher
  - Required for: HTTP API endpoints
- **TodiScope v3 Platform**: Core services must be deployed
  - Evidence registry
  - DatasetVersion management
  - Normalization pipeline
  - Engine registry

**Optional Infrastructure:**
- **Docker**: For containerized deployment
- **MinIO/S3**: For artifact storage (if used by platform)
- **Redis**: For caching (if used by platform)

### 2.2 Platform Dependencies

The engine requires the following TodiScope v3 core services:

1. **Core Database Tables:**
   - `dataset_version` - DatasetVersion management
   - `raw_record` - Raw ingested records
   - `normalized_record` - Normalized records
   - `evidence_records` - Core evidence registry
   - `finding_record` - Core findings registry
   - `finding_evidence_link` - Evidence-finding links

2. **Core Services:**
   - Evidence service (`create_evidence`, `create_finding`, `link_finding_to_evidence`)
   - DatasetVersion service
   - Normalization service
   - Engine registry

### 2.3 Configuration Parameters

**Required Environment Variables:**
- `TODISCOPE_DATABASE_URL` - PostgreSQL connection string
- `TODISCOPE_ENABLED_ENGINES` - Comma-separated list of enabled engines (must include `engine_distressed_asset_debt_stress`)

**Optional Environment Variables:**
- `TODISCOPE_LOG_LEVEL` - Logging level (default: `INFO`)
- `TODISCOPE_ARTIFACT_STORE_URL` - Artifact store URL (if used)

---

## 3. Installation Guide

### 3.1 Step-by-Step Installation

#### Step 1: Verify Prerequisites

```bash
# Check Python version
python3 --version  # Should be 3.10+

# Check PostgreSQL
psql --version  # Should be 14.0+

# Verify TodiScope platform is running
curl http://localhost:8000/health  # Adjust URL as needed
```

#### Step 2: Database Setup

The engine uses core TodiScope tables. No engine-specific migrations are required.

**Verify Core Tables Exist:**
```sql
-- Connect to PostgreSQL
psql -U postgres -d todiscope

-- Verify core tables exist
\dt dataset_version
\dt evidence_records
\dt finding_record
\dt normalized_record
```

**Note:** If core tables don't exist, run TodiScope platform migrations first.

#### Step 3: Install Engine Code

**Option A: From Source (Development)**
```bash
# Clone repository
git clone <repository-url>
cd todiscope-v3

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install backend
cd backend
pip install -e .
```

**Option B: Docker (Production)**
```bash
# Build Docker image
docker build -t todiscope-backend:latest -f backend/Dockerfile .

# Or use docker-compose
docker compose -f infra/docker-compose.yml up -d
```

#### Step 4: Configure Environment Variables

Create `.env` file or set environment variables:

```bash
# Required
export TODISCOPE_DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/todiscope"
export TODISCOPE_ENABLED_ENGINES="engine_distressed_asset_debt_stress"

# Optional
export TODISCOPE_LOG_LEVEL="INFO"
```

#### Step 5: Verify Engine Registration

```bash
# Start platform (if not already running)
uvicorn backend.app.main:app --host 0.0.0.0 --port 8400

# Check engine registry
curl http://localhost:8400/api/v3/engine-registry/enabled

# Should return:
# {"enabled_engines": ["engine_distressed_asset_debt_stress", ...]}
```

#### Step 6: Run Tests

```bash
# Run engine-specific tests
pytest backend/tests/engine_distressed_asset_debt_stress/ -v

# Expected: 36 tests passing
```

### 3.2 Docker Deployment

**Docker Compose Setup:**

```yaml
# docker-compose.yml excerpt
services:
  backend:
    build:
      context: .
      dockerfile: backend/Dockerfile
    environment:
      - TODISCOPE_DATABASE_URL=postgresql+asyncpg://postgres:password@postgres:5432/todiscope
      - TODISCOPE_ENABLED_ENGINES=engine_distressed_asset_debt_stress
    ports:
      - "8000:8000"
    depends_on:
      - postgres
```

**Deploy:**
```bash
docker compose up -d
```

---

## 4. Configuration

### 4.1 Database Connection

**Connection String Format:**
```
postgresql+asyncpg://[user]:[password]@[host]:[port]/[database]
```

**Example:**
```bash
export TODISCOPE_DATABASE_URL="postgresql+asyncpg://todiscope_user:secure_password@db.example.com:5432/todiscope_prod"
```

**Connection Pool Settings:**
- Managed by SQLAlchemy async sessionmaker
- Default pool size: 5 connections
- Connection timeout: 30 seconds

### 4.2 API Settings

**Engine Endpoint:**
- Base URL: `/api/v3/engines/distressed-asset-debt-stress`
- Full endpoint: `POST /api/v3/engines/distressed-asset-debt-stress/run`

**Kill Switch:**
- Engine can be disabled via `TODISCOPE_ENABLED_ENGINES`
- If disabled, endpoint returns `503 Service Unavailable`
- No restart required to enable/disable

### 4.3 Multi-Currency Handling

**Current Implementation:**
- Engine operates on normalized data (currency normalization expected at ingestion)
- All calculations use float values (currency-agnostic)
- Currency conversion should be handled at normalization layer

**Configuration:**
- No engine-specific currency configuration required
- Ensure normalization pipeline handles currency conversion
- All monetary values in reports are in base currency (as normalized)

### 4.4 Evidence Linking Settings

**Automatic Configuration:**
- Evidence linking is automatic and requires no configuration
- Evidence stored in core `evidence_records` table
- Findings stored in core `finding_record` table
- Links stored in core `finding_evidence_link` table

**Evidence Kinds:**
- `debt_exposure` - Base debt exposure calculations
- `stress_test` - Stress scenario results (one per scenario)

**Finding Categories:**
- `debt_exposure` - Debt exposure findings
- `stress_test` - Stress test findings

### 4.5 Materiality Thresholds

**Configurable Parameters:**
- `net_exposure_materiality_threshold_pct` (default: 0.2 = 20%)
  - Threshold for debt exposure materiality
  - Applied to: `net_exposure_after_recovery`
  
- `stress_loss_materiality_threshold_pct` (default: 0.05 = 5%)
  - Threshold for stress test loss materiality
  - Applied to: `loss_estimate` from stress scenarios

**Example Configuration:**
```json
{
  "dataset_version_id": "dv_123",
  "started_at": "2025-01-01T00:00:00Z",
  "parameters": {
    "net_exposure_materiality_threshold_pct": 0.15,
    "stress_loss_materiality_threshold_pct": 0.03
  }
}
```

---

## 5. Deployment Procedures

### 5.1 Initial Deployment

**Pre-Deployment Checklist:**
- [ ] Database connection verified
- [ ] Core TodiScope tables exist
- [ ] Environment variables configured
- [ ] Engine enabled in `TODISCOPE_ENABLED_ENGINES`
- [ ] Tests passing (36 tests)

**Deployment Steps:**

1. **Deploy Code:**
   ```bash
   # Option A: Direct deployment
   git pull origin main
   pip install -e backend/
   
   # Option B: Docker
   docker compose pull
   docker compose up -d
   ```

2. **Verify Engine Registration:**
   ```bash
   curl http://localhost:8000/api/v3/engine-registry/enabled | jq
   # Should include "engine_distressed_asset_debt_stress"
   ```

3. **Test Endpoint:**
   ```bash
   curl -X POST http://localhost:8000/api/v3/engines/distressed-asset-debt-stress/run \
     -H "Content-Type: application/json" \
     -d '{
       "dataset_version_id": "test-dv-id",
       "started_at": "2025-01-01T00:00:00Z"
     }'
   ```

4. **Monitor Logs:**
   ```bash
   # Check application logs
   tail -f /var/log/todiscope/app.log
   
   # Or Docker logs
   docker compose logs -f backend
   ```

### 5.2 CI/CD Pipeline Deployment

**Recommended Pipeline Steps:**

1. **Build:**
   ```yaml
   - name: Build Docker Image
     run: docker build -t todiscope-backend:${{ github.sha }} -f backend/Dockerfile .
   ```

2. **Test:**
   ```yaml
   - name: Run Tests
     run: |
       pytest backend/tests/engine_distressed_asset_debt_stress/ -v
   ```

3. **Deploy:**
   ```yaml
   - name: Deploy to Production
     run: |
       docker tag todiscope-backend:${{ github.sha }} registry.example.com/todiscope-backend:latest
       docker push registry.example.com/todiscope-backend:latest
       kubectl rollout restart deployment/todiscope-backend
   ```

### 5.3 Restart Procedures

**Restart Engine (No Downtime):**

1. **Graceful Restart:**
   ```bash
   # Docker Compose
   docker compose restart backend
   
   # Kubernetes
   kubectl rollout restart deployment/todiscope-backend
   ```

2. **Verify After Restart:**
   ```bash
   # Check health
   curl http://localhost:8000/health
   
   # Check engine enabled
   curl http://localhost:8000/api/v3/engine-registry/enabled
   
   # Test endpoint
   curl -X POST http://localhost:8000/api/v3/engines/distressed-asset-debt-stress/run \
     -H "Content-Type: application/json" \
     -d '{"dataset_version_id": "test", "started_at": "2025-01-01T00:00:00Z"}'
   ```

**Emergency Restart:**
```bash
# Force restart
docker compose down
docker compose up -d

# Or Kubernetes
kubectl delete pod -l app=todiscope-backend
```

### 5.4 Rolling Updates

**Zero-Downtime Update:**

1. **Deploy New Version:**
   ```bash
   # Build new image
   docker build -t todiscope-backend:v1.1 -f backend/Dockerfile .
   
   # Update deployment
   kubectl set image deployment/todiscope-backend \
     backend=registry.example.com/todiscope-backend:v1.1
   ```

2. **Monitor Rollout:**
   ```bash
   kubectl rollout status deployment/todiscope-backend
   ```

3. **Rollback (if needed):**
   ```bash
   kubectl rollout undo deployment/todiscope-backend
   ```

---

## 6. API Endpoints

### 6.1 Run Engine Endpoint

**Endpoint:** `POST /api/v3/engines/distressed-asset-debt-stress/run`

**Description:** Execute the engine to calculate debt exposure and apply stress scenarios.

**Authentication:** Required (handled by platform middleware)

**Request Headers:**
```
Content-Type: application/json
Authorization: Bearer <token>  # Platform-level authentication
```

**Request Body:**
```json
{
  "dataset_version_id": "uuidv7-string",
  "started_at": "2025-01-01T00:00:00Z",
  "parameters": {
    "net_exposure_materiality_threshold_pct": 0.2,
    "stress_loss_materiality_threshold_pct": 0.05,
    "stress_scenarios": [
      {
        "scenario_id": "custom_severe",
        "description": "Custom severe stress scenario",
        "interest_rate_delta_pct": 5.0,
        "collateral_market_impact_pct": -0.3,
        "recovery_degradation_pct": -0.2,
        "default_risk_increment_pct": 0.1
      }
    ]
  }
}
```

**Multi-Currency Data Handling:**
- All monetary values in the request should be in the **base currency** (normalized at ingestion layer)
- Currency normalization occurs during the normalization phase, not in the engine
- The engine operates on currency-agnostic float values
- Original currency information is preserved in normalized record metadata
- See `docs/engines/enterprise_distressed_asset_debt_stress/multi_currency_handling.md` for detailed currency handling documentation

**Intercompany Data Handling:**
- Intercompany debt and assets are aggregated during normalization
- The engine receives aggregated values in base currency
- Intercompany breakdown is preserved in metadata (if needed for reporting)
- All calculations use normalized, aggregated values

**Request Parameters:**
- `dataset_version_id` (required, string): UUIDv7 DatasetVersion ID
- `started_at` (required, string): ISO 8601 timestamp
- `parameters` (optional, object):
  - `net_exposure_materiality_threshold_pct` (float, default: 0.2): Materiality threshold for debt exposure
  - `stress_loss_materiality_threshold_pct` (float, default: 0.05): Materiality threshold for stress losses
  - `stress_scenarios` (array, optional): Custom stress scenarios (overrides defaults)

**Response (Success - 200):**
```json
{
  "dataset_version_id": "uuidv7-string",
  "started_at": "2025-01-01T00:00:00Z",
  "debt_exposure_evidence_id": "uuidv5-string",
  "stress_test_evidence_ids": {
    "interest_rate_spike": "uuidv5-string",
    "market_crash": "uuidv5-string",
    "default_wave": "uuidv5-string"
  },
  "material_findings": [
    {
      "id": "uuidv5-string",
      "dataset_version_id": "uuidv7-string",
      "title": "debt_exposure: net",
      "category": "debt_exposure",
      "metric": "net_exposure_after_recovery",
      "value": 105000.0,
      "threshold": 200000.0,
      "is_material": false,
      "materiality": "not_material",
      "financial_impact_eur": 105000.0,
      "impact_score": 0.105,
      "confidence": "medium"
    }
  ],
  "report": {
    "metadata": {
      "dataset_version_id": "uuidv7-string",
      "generated_at": "2025-01-01T00:00:00Z",
      "normalized_record_id": "uuidv5-string",
      "raw_record_id": "uuidv5-string",
      "warnings": [],
      "parameters": {}
    },
    "debt_exposure": {
      "total_outstanding": 1000000.0,
      "interest_rate_pct": 5.0,
      "interest_payment": 50000.0,
      "collateral_value": 750000.0,
      "collateral_shortfall": 250000.0,
      "collateral_coverage_ratio": 0.75,
      "assets_value": 2000000.0,
      "leverage_ratio": 0.5,
      "distressed_asset_value": 350000.0,
      "distressed_asset_recovery": 145000.0,
      "distressed_asset_recovery_ratio": 0.414,
      "distressed_asset_count": 2,
      "net_exposure_after_recovery": 105000.0
    },
    "stress_tests": [
      {
        "scenario_id": "interest_rate_spike",
        "description": "Interest rate hike with modest refinancing pressure.",
        "interest_rate_pct": 7.5,
        "interest_payment": 75000.0,
        "collateral_value": 712500.0,
        "collateral_loss": 37500.0,
        "distressed_asset_value": 332500.0,
        "distressed_asset_loss": 17500.0,
        "distressed_asset_recovery": 137750.0,
        "default_risk_buffer": 20000.0,
        "net_exposure_after_recovery": 169750.0,
        "loss_estimate": 64750.0,
        "impact_score": 0.06475
      }
    ],
    "assumptions": [
      {
        "id": "assumption_interest_units",
        "description": "Interest rates are annual and expressed as percentage points before additional shocks.",
        "source": "Engine design",
        "impact": "Interest payment exposure scales linearly with the rate.",
        "sensitivity": "Medium"
      }
    ]
  },
  "assumptions": [...]
}
```

**Error Responses:**

| Status Code | Error | Description |
|------------|-------|-------------|
| 400 | `DATASET_VERSION_ID_REQUIRED` | Missing `dataset_version_id` |
| 400 | `DATASET_VERSION_ID_INVALID` | Invalid `dataset_version_id` format |
| 400 | `STARTED_AT_REQUIRED` | Missing `started_at` |
| 400 | `STARTED_AT_INVALID` | Invalid `started_at` format |
| 404 | `DATASET_VERSION_NOT_FOUND` | DatasetVersion doesn't exist |
| 409 | `NORMALIZED_RECORD_REQUIRED` | No normalized records for DatasetVersion |
| 409 | `EVIDENCE_ID_COLLISION` | Evidence ID collision (immutability conflict) |
| 409 | `IMMUTABLE_EVIDENCE_MISMATCH` | Evidence payload mismatch (immutability conflict) |
| 500 | `ENGINE_RUN_FAILED` | Internal server error |
| 503 | `ENGINE_DISABLED` | Engine not enabled in `TODISCOPE_ENABLED_ENGINES` |

**Example Error Response:**
```json
{
  "detail": "DATASET_VERSION_NOT_FOUND"
}
```

### 6.2 Security/Authentication

**Platform-Level Security:**
- Authentication handled by FastAPI middleware
- RBAC enforced at platform level and engine level
- Engine-specific RBAC checks implemented

**Access Control:**
- **Engine Endpoint**: Requires `EXECUTE` role (enforced via `require_principal(Role.EXECUTE)`)
- **Data Access**: Requires `READ` role for accessing DatasetVersion and normalized records (enforced at platform level)
- **Admin Access**: `ADMIN` role has full access to all operations
- Engine endpoints enforce explicit RBAC checks
- Audit logging via platform logging infrastructure

**RBAC Roles:**
- `EXECUTE`: Required to run the engine and generate stress test reports
- `READ`: Required to access DatasetVersion and normalized records
- `ADMIN`: Full access to all operations

---

## 7. Security Considerations

### 7.1 Security Measures

**Platform-Level Security:**
- ✅ Authentication: Handled by FastAPI middleware (JWT, OAuth, etc.)
- ✅ Authorization: RBAC enforced at platform level
- ✅ API Security: HTTPS/TLS required in production
- ✅ Input Validation: All inputs validated (DatasetVersion, timestamps, parameters)

**Engine-Level Security:**
- ✅ SQL Injection Protection: SQLAlchemy parameterized queries
- ✅ Immutability Guards: Prevents unauthorized data modification
- ✅ DatasetVersion Isolation: Strict DatasetVersion enforcement prevents cross-version access
- ✅ Error Handling: No sensitive information leaked in error messages

### 7.2 Audit Logging

**Logging Configuration:**
- Logger: `backend.app.engines.enterprise_distressed_asset_debt_stress.run`
- Log Level: Controlled by `TODISCOPE_LOG_LEVEL` (default: `INFO`)

**Logged Events:**
- Immutability conflicts: `DISTRESSED_DEBT_IMMUTABLE_CONFLICT` warnings
- Evidence ID collisions
- Evidence payload mismatches
- Finding ID collisions

**Log Format:**
```
DISTRESSED_DEBT_IMMUTABLE_CONFLICT evidence_id_collision evidence_id=<id> dataset_version_id=<dv_id>
```

**Audit Trail:**
- All evidence records include timestamps and DatasetVersion
- All findings include timestamps and DatasetVersion
- Complete traceability chain: RawRecord → NormalizedRecord → EvidenceRecord → FindingRecord

**Monitoring:**
- Monitor for `IMMUTABLE_CONFLICT` warnings (indicates potential data integrity issues)
- Monitor for `ENGINE_RUN_FAILED` errors (indicates system issues)
- Track evidence creation rates and finding counts

### 7.3 Data Privacy

**Sensitive Data Handling:**
- Engine processes financial data (debt, assets, distressed assets)
- All data stored in database with DatasetVersion binding
- No data transmitted outside platform
- Evidence and findings stored immutably (no deletion)

**Compliance:**
- GDPR: Data bound to DatasetVersion enables data deletion at DatasetVersion level
- Audit Trail: Complete audit trail via evidence records
- Immutability: Prevents unauthorized data modification

---

## 8. Post-Deployment Checklist

### 8.1 Verification Tests

**1. Engine Registration:**
```bash
curl http://localhost:8000/api/v3/engine-registry/enabled | jq '.enabled_engines[] | select(. == "engine_distressed_asset_debt_stress")'
# Should return: "engine_distressed_asset_debt_stress"
```

**2. Endpoint Accessibility:**
```bash
curl -X POST http://localhost:8000/api/v3/engines/distressed-asset-debt-stress/run \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "dataset_version_id": "<valid-dv-id>",
    "started_at": "2025-01-01T00:00:00Z"
  }'
# Should return: 200 OK with engine results
```

**3. Kill Switch:**
```bash
# Disable engine
export TODISCOPE_ENABLED_ENGINES="other_engine"

# Restart platform
# Test endpoint - should return 503
curl -X POST http://localhost:8000/api/v3/engines/distressed-asset-debt-stress/run \
  -H "Content-Type: application/json" \
  -d '{"dataset_version_id": "test", "started_at": "2025-01-01T00:00:00Z"}'
# Expected: 503 ENGINE_DISABLED
```

**4. Database Integration:**
```sql
-- Verify evidence creation
SELECT COUNT(*) FROM evidence_records 
WHERE engine_id = 'engine_distressed_asset_debt_stress';

-- Verify findings creation
SELECT COUNT(*) FROM finding_record fr
JOIN finding_evidence_link fel ON fr.finding_id = fel.finding_id
JOIN evidence_records er ON fel.evidence_id = er.evidence_id
WHERE er.engine_id = 'engine_distressed_asset_debt_stress';
```

**5. Integration Tests:**
```bash
# Run full test suite
pytest backend/tests/engine_distressed_asset_debt_stress/ -v

# Expected: 36 tests passing
```

### 8.2 Monitoring Integration

**Metrics to Monitor:**
- Request rate: Requests per minute to `/run` endpoint
- Error rate: 4xx/5xx responses
- Response time: P50, P95, P99 latencies
- Evidence creation rate: Evidence records created per hour
- Finding creation rate: Findings created per hour

**Log Monitoring:**
- Monitor for `IMMUTABLE_CONFLICT` warnings
- Monitor for `ENGINE_RUN_FAILED` errors
- Track DatasetVersion usage patterns

**Health Checks:**
```bash
# Platform health
curl http://localhost:8000/health

# Engine registry health
curl http://localhost:8000/api/v3/engine-registry/enabled
```

### 8.3 Performance Verification

**Load Testing:**
```bash
# Example: 100 requests, 10 concurrent
ab -n 100 -c 10 -p request.json -T application/json \
  -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v3/engines/distressed-asset-debt-stress/run
```

**Expected Performance:**
- Response time: < 2 seconds for typical requests
- Throughput: 50+ requests per second
- Database connections: < 10 concurrent connections

---

## 9. Troubleshooting

### 9.1 Common Deployment Issues

#### Issue: Engine Not Accessible (503 Service Unavailable)

**Symptoms:**
- Endpoint returns `503 ENGINE_DISABLED`
- Engine not in enabled list

**Resolution:**
```bash
# Check environment variable
echo $TODISCOPE_ENABLED_ENGINES

# Enable engine
export TODISCOPE_ENABLED_ENGINES="engine_distressed_asset_debt_stress"

# Restart platform
# Docker
docker compose restart backend

# Or Kubernetes
kubectl rollout restart deployment/todiscope-backend
```

#### Issue: Database Connection Errors

**Symptoms:**
- `ENGINE_RUN_FAILED: OperationalError`
- Connection timeout errors

**Resolution:**
```bash
# Verify database URL
echo $TODISCOPE_DATABASE_URL

# Test connection
psql $TODISCOPE_DATABASE_URL -c "SELECT 1"

# Check database is running
docker compose ps postgres  # If using Docker

# Verify network connectivity
telnet <db-host> <db-port>
```

#### Issue: DatasetVersion Not Found (404)

**Symptoms:**
- `DATASET_VERSION_NOT_FOUND` error

**Resolution:**
```sql
-- Verify DatasetVersion exists
SELECT id, created_at FROM dataset_version WHERE id = '<dv-id>';

-- Check if DatasetVersion is accessible
SELECT COUNT(*) FROM normalized_record WHERE dataset_version_id = '<dv-id>';
```

#### Issue: NormalizedRecord Missing (409)

**Symptoms:**
- `NORMALIZED_RECORD_REQUIRED` error

**Resolution:**
```sql
-- Check for normalized records
SELECT COUNT(*) FROM normalized_record WHERE dataset_version_id = '<dv-id>';

-- If missing, run normalization pipeline first
```

#### Issue: Immutability Conflicts (409)

**Symptoms:**
- `EVIDENCE_ID_COLLISION` or `IMMUTABLE_EVIDENCE_MISMATCH` errors
- Log warnings: `DISTRESSED_DEBT_IMMUTABLE_CONFLICT`

**Resolution:**
- **Expected Behavior**: Engine is idempotent. If same inputs produce different results, this indicates a bug.
- **Investigation**: Check logs for conflict details
- **Action**: Review evidence payloads and verify deterministic ID generation

### 9.2 Error Codes Reference

| Error Code | HTTP Status | Description | Resolution |
|-----------|-------------|-------------|------------|
| `DATASET_VERSION_ID_REQUIRED` | 400 | Missing `dataset_version_id` | Provide `dataset_version_id` in request |
| `DATASET_VERSION_ID_INVALID` | 400 | Invalid `dataset_version_id` format | Use valid UUIDv7 format |
| `STARTED_AT_REQUIRED` | 400 | Missing `started_at` | Provide `started_at` in ISO 8601 format |
| `STARTED_AT_INVALID` | 400 | Invalid `started_at` format | Use ISO 8601 format (e.g., `2025-01-01T00:00:00Z`) |
| `DATASET_VERSION_NOT_FOUND` | 404 | DatasetVersion doesn't exist | Verify DatasetVersion exists in database |
| `NORMALIZED_RECORD_REQUIRED` | 409 | No normalized records for DatasetVersion | Run normalization pipeline first |
| `EVIDENCE_ID_COLLISION` | 409 | Evidence ID collision | Check for duplicate evidence creation (bug) |
| `IMMUTABLE_EVIDENCE_MISMATCH` | 409 | Evidence payload mismatch | Verify deterministic ID generation |
| `IMMUTABLE_FINDING_MISMATCH` | 409 | Finding payload mismatch | Verify deterministic ID generation |
| `ENGINE_DISABLED` | 503 | Engine not enabled | Add to `TODISCOPE_ENABLED_ENGINES` |
| `ENGINE_RUN_FAILED` | 500 | Internal server error | Check logs for details |

### 9.3 Recovery Procedures

**Database Connection Loss:**
1. Verify database is running
2. Check network connectivity
3. Verify connection string
4. Restart engine if needed

**Evidence Creation Failures:**
1. Check database constraints
2. Verify DatasetVersion exists
3. Check for immutability conflicts
4. Review logs for specific error

**Performance Degradation:**
1. Check database connection pool
2. Monitor query performance
3. Check for database locks
4. Scale database if needed

---

## 10. Maintenance

### 10.1 Updating the Engine

**Version Update Process:**

1. **Backup:**
   ```bash
   # Backup database
   pg_dump -U postgres todiscope > backup_$(date +%Y%m%d).sql
   ```

2. **Deploy New Version:**
   ```bash
   # Pull new code
   git pull origin main
   
   # Install dependencies
   pip install -e backend/
   
   # Or Docker
   docker compose pull
   docker compose up -d
   ```

3. **Verify:**
   ```bash
   # Run tests
   pytest backend/tests/engine_distressed_asset_debt_stress/ -v
   
   # Test endpoint
   curl -X POST http://localhost:8000/api/v3/engines/distressed-asset-debt-stress/run ...
   ```

4. **Monitor:**
   - Check logs for errors
   - Monitor evidence creation
   - Verify findings are created correctly

### 10.2 Database Migrations

**Current Status:**
- ✅ No engine-specific tables (uses core evidence registry)
- ✅ No migrations required for engine deployment
- ✅ Core tables managed by platform migrations

**Future Migrations:**
- If engine-specific tables are added in future versions:
  1. Create migration files in platform migrations directory
  2. Run migrations: `alembic upgrade head`
  3. Verify tables created: `\dt engine_distressed_asset_*`

### 10.3 Configuration Updates

**Updating Materiality Thresholds:**
- No restart required
- Pass new thresholds in `parameters` field
- Changes apply to new requests only

**Updating Environment Variables:**
```bash
# Update .env file or environment
export TODISCOPE_ENABLED_ENGINES="engine_distressed_asset_debt_stress,other_engine"

# Restart platform
docker compose restart backend
```

### 10.4 Monitoring and Alerts

**Recommended Alerts:**
- High error rate (> 5% 4xx/5xx responses)
- Immutability conflicts (any `IMMUTABLE_CONFLICT` warnings)
- Database connection failures
- Response time degradation (> 5 seconds P95)

**Monitoring Queries:**
```sql
-- Evidence creation rate (last hour)
SELECT COUNT(*) FROM evidence_records 
WHERE engine_id = 'engine_distressed_asset_debt_stress'
  AND created_at > NOW() - INTERVAL '1 hour';

-- Error rate (check logs)
-- Monitor for ENGINE_RUN_FAILED errors
```

---

## 11. References

### 11.1 Internal Documentation

- **Engine README**: `backend/app/engines/enterprise_distressed_asset_debt_stress/README.md`
- **Implementation Summary**: `backend/app/engines/enterprise_distressed_asset_debt_stress/IMPLEMENTATION_SUMMARY.md`
- **Audit Report**: `backend/app/engines/enterprise_distressed_asset_debt_stress/AUDIT_REPORT.md`
- **Integration Test Report**: `backend/app/engines/enterprise_distressed_asset_debt_stress/INTEGRATION_TEST_REPORT.md`
- **Systems Audit Report**: `backend/app/engines/enterprise_distressed_asset_debt_stress/SYSTEMS_AUDIT_REPORT.md`

### 11.2 Platform Documentation

- **TodiScope Architecture**: `ARCHITECTURE.md`
- **Platform README**: `README.md`
- **Engine Registry**: `backend/app/core/engine_registry/`

### 11.3 API Documentation

- **OpenAPI/Swagger**: Available at `/docs` when platform is running
- **Engine Endpoint**: `POST /api/v3/engines/distressed-asset-debt-stress/run`

### 11.4 Support Contacts

- **Engineering Team**: [Contact Information]
- **DevOps Team**: [Contact Information]
- **Platform Support**: [Contact Information]

### 11.5 Related Resources

- **Test Suite**: `backend/tests/engine_distressed_asset_debt_stress/`
- **Source Code**: `backend/app/engines/enterprise_distressed_asset_debt_stress/`
- **Error Definitions**: `backend/app/engines/enterprise_distressed_asset_debt_stress/errors.py`

---

## Appendix A: Example Request/Response

### Complete Example Request

```bash
curl -X POST http://localhost:8000/api/v3/engines/distressed-asset-debt-stress/run \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "dataset_version_id": "018f1234-5678-9abc-def0-123456789abc",
    "started_at": "2025-01-15T10:30:00Z",
    "parameters": {
      "net_exposure_materiality_threshold_pct": 0.2,
      "stress_loss_materiality_threshold_pct": 0.05,
      "stress_scenarios": [
        {
          "scenario_id": "custom_severe",
          "description": "Custom severe stress scenario",
          "interest_rate_delta_pct": 5.0,
          "collateral_market_impact_pct": -0.3,
          "recovery_degradation_pct": -0.2,
          "default_risk_increment_pct": 0.1
        }
      ]
    }
  }'
```

### Complete Example Response

See Section 6.1 for full response structure.

---

## Appendix B: Default Stress Scenarios

The engine includes three default stress scenarios:

1. **Interest Rate Spike** (`interest_rate_spike`):
   - Interest rate delta: +2.5%
   - Collateral impact: -5%
   - Recovery degradation: -5%
   - Default risk increment: +2%

2. **Market Crash** (`market_crash`):
   - Interest rate delta: +0.5%
   - Collateral impact: -25%
   - Recovery degradation: -15%
   - Default risk increment: +5%

3. **Default Wave** (`default_wave`):
   - Interest rate delta: +1.0%
   - Collateral impact: -10%
   - Recovery degradation: -35%
   - Default risk increment: +8%

These scenarios are automatically applied unless overridden in `parameters.stress_scenarios`.

---

## Document Control

**Version:** 1.0  
**Last Updated:** 2025-01-XX  
**Author:** Technical Writer  
**Review Status:** Ready for Production Deployment  
**Approved By:** [To be filled]

---

**END OF DOCUMENTATION**

