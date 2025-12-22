# API Reference: Enterprise Distressed Asset & Debt Stress Engine

**Engine ID:** `engine_distressed_asset_debt_stress`  
**API Version:** v3  
**Documentation Version:** 1.1.0  
**Last Updated:** 2025-01-XX

---

## Endpoint: POST /api/v3/engines/distressed-asset-debt-stress/run

Execute the engine to calculate debt exposure and apply stress scenarios.

### Authentication & Authorization

**Required Headers:**
```
Content-Type: application/json
X-API-Key: <api_key>  # Required if TODISCOPE_API_KEYS is configured
```

**RBAC Requirements:**
- **EXECUTE** role: Required to execute the engine
- **READ** role: Required to access DatasetVersion and normalized records (enforced at platform level)
- **ADMIN** role: Full access to all operations

**Security:**
- All operations are logged for audit purposes
- DatasetVersion access is validated before processing
- Evidence and findings are bound to DatasetVersion for access control

### Request

**URL:** `POST /api/v3/engines/distressed-asset-debt-stress/run`

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

**Request Parameters:**

| Parameter | Type | Required | Description |
|----------|------|----------|-------------|
| `dataset_version_id` | string (UUIDv7) | Yes | DatasetVersion ID to process |
| `started_at` | string (ISO 8601) | Yes | Timestamp of engine execution start |
| `parameters` | object | No | Optional runtime parameters (see below) |

**Parameters Object:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `net_exposure_materiality_threshold_pct` | float | 0.2 | Materiality threshold for debt exposure (20%) |
| `stress_loss_materiality_threshold_pct` | float | 0.05 | Materiality threshold for stress losses (5%) |
| `stress_scenarios` | array | Default scenarios | Custom stress scenarios (overrides defaults) |

---

## Multi-Currency Data Handling

### Overview

The engine operates on **currency-normalized data** that has been processed by the TodiScope v3 normalization pipeline. All monetary values in requests and responses are in the **base currency** (typically EUR or organization's base currency).

### Currency Normalization

**Important:** Currency normalization occurs **during the normalization phase**, not in the engine. The engine receives data that has already been converted to a common base currency.

**Normalization Process:**
1. Raw data includes currency codes (e.g., `USD`, `EUR`, `GBP`)
2. Normalization pipeline applies exchange rates to convert all amounts to base currency
3. Engine receives normalized data with currency-agnostic float values
4. Original currency information is preserved in normalized record metadata

### Example: Multi-Currency Request

**Raw Data (Before Normalization):**
```json
{
  "debt_instruments": [
    {
      "principal": 1000000,
      "currency": "USD",
      "interest_rate_pct": 5.0
    },
    {
      "principal": 500000,
      "currency": "GBP",
      "interest_rate_pct": 4.5
    }
  ],
  "base_currency": "EUR",
  "exchange_rates": {
    "USD": 0.92,
    "GBP": 1.15
  }
}
```

**Normalized Data (Engine Input):**
```json
{
  "financial": {
    "debt": {
      "total_outstanding": 1415000.0,
      "interest_rate_pct": 4.84,
      "instruments": [
        {
          "principal": 920000.0,
          "interest_rate_pct": 5.0
        },
        {
          "principal": 575000.0,
          "interest_rate_pct": 4.5
        }
      ]
    }
  },
  "metadata": {
    "currency_base": "EUR",
    "exchange_rates": {
      "USD": 0.92,
      "GBP": 1.15
    }
  }
}
```

**Engine Request:**
```json
{
  "dataset_version_id": "018f1234-5678-9abc-def0-123456789abc",
  "started_at": "2025-01-15T10:30:00Z"
}
```

**Note:** The engine does not receive currency information in the request. All currency handling occurs during normalization.

### Example: Intercompany Data

**Raw Data (Before Normalization):**
```json
{
  "intercompany_debt": [
    {
      "entity": "Subsidiary A",
      "amount": 500000,
      "currency": "USD"
    },
    {
      "entity": "Subsidiary B",
      "amount": 300000,
      "currency": "GBP"
    }
  ],
  "base_currency": "EUR"
}
```

**Normalized Data (Engine Input):**
```json
{
  "financial": {
    "debt": {
      "total_outstanding": 805000.0
    }
  },
  "metadata": {
    "currency_base": "EUR",
    "intercompany_breakdown": {
      "Subsidiary A": 460000.0,
      "Subsidiary B": 345000.0
    }
  }
}
```

**Engine Processing:**
- Aggregates all intercompany debt to single value in base currency
- Performs stress calculations on aggregated amount
- Preserves intercompany breakdown in metadata (if needed for reporting)

### Currency Metadata in Response

The engine's response includes currency metadata when available:

```json
{
  "report": {
    "metadata": {
      "dataset_version_id": "dv_123",
      "currency_base": "EUR",
      "normalized_at": "2025-01-01T00:00:00Z"
    },
    "debt_exposure": {
      "total_outstanding": 1415000.0,
      "net_exposure_after_recovery": 150000.0
    }
  }
}
```

---

## Response

### Success Response (200 OK)

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

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `dataset_version_id` | string | DatasetVersion ID processed |
| `started_at` | string | ISO 8601 timestamp of execution start |
| `debt_exposure_evidence_id` | string | Evidence ID for debt exposure calculations |
| `stress_test_evidence_ids` | object | Map of scenario IDs to evidence IDs |
| `material_findings` | array | Material findings with risk classifications |
| `report` | object | Complete report with metadata, debt exposure, stress tests, assumptions |

**All monetary values in the response are in the base currency** (as normalized).

---

## Error Responses

### Error Codes

| Status Code | Error Code | Description |
|------------|------------|-------------|
| 400 | `DATASET_VERSION_ID_REQUIRED` | Missing `dataset_version_id` |
| 400 | `DATASET_VERSION_ID_INVALID` | Invalid `dataset_version_id` format |
| 400 | `STARTED_AT_REQUIRED` | Missing `started_at` |
| 400 | `STARTED_AT_INVALID` | Invalid `started_at` format |
| 401 | `AUTH_REQUIRED` | Missing API key (if TODISCOPE_API_KEYS configured) |
| 401 | `AUTH_INVALID` | Invalid API key |
| 403 | `FORBIDDEN` | Insufficient permissions (missing EXECUTE role) |
| 404 | `DATASET_VERSION_NOT_FOUND` | DatasetVersion doesn't exist |
| 409 | `NORMALIZED_RECORD_REQUIRED` | No normalized records for DatasetVersion |
| 409 | `EVIDENCE_ID_COLLISION` | Evidence ID collision (immutability conflict) |
| 409 | `IMMUTABLE_EVIDENCE_MISMATCH` | Evidence payload mismatch (immutability conflict) |
| 500 | `ENGINE_RUN_FAILED` | Internal server error |
| 503 | `ENGINE_DISABLED` | Engine not enabled in `TODISCOPE_ENABLED_ENGINES` |

### Example Error Response

```json
{
  "detail": "DATASET_VERSION_NOT_FOUND"
}
```

---

## Examples

### Example 1: Basic Request

```bash
curl -X POST http://localhost:8000/api/v3/engines/distressed-asset-debt-stress/run \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "dataset_version_id": "018f1234-5678-9abc-def0-123456789abc",
    "started_at": "2025-01-15T10:30:00Z"
  }'
```

### Example 2: Request with Custom Materiality Thresholds

```bash
curl -X POST http://localhost:8000/api/v3/engines/distressed-asset-debt-stress/run \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "dataset_version_id": "018f1234-5678-9abc-def0-123456789abc",
    "started_at": "2025-01-15T10:30:00Z",
    "parameters": {
      "net_exposure_materiality_threshold_pct": 0.15,
      "stress_loss_materiality_threshold_pct": 0.03
    }
  }'
```

### Example 3: Request with Custom Stress Scenarios

```bash
curl -X POST http://localhost:8000/api/v3/engines/distressed-asset-debt-stress/run \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "dataset_version_id": "018f1234-5678-9abc-def0-123456789abc",
    "started_at": "2025-01-15T10:30:00Z",
    "parameters": {
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

---

## Multi-Currency Best Practices

1. **Ensure Normalization**: Verify that data is normalized before engine execution
2. **Check Metadata**: Review currency metadata in reports for accuracy
3. **Handle Warnings**: Monitor for currency-related warnings in normalization logs
4. **Audit Trail**: Use metadata to trace currency conversions in audit scenarios

---

## References

- **Multi-Currency Handling**: `docs/engines/enterprise_distressed_asset_debt_stress/multi_currency_handling.md`
- **Production Deployment**: `backend/app/engines/enterprise_distressed_asset_debt_stress/PRODUCTION_DEPLOYMENT.md`
- **RBAC Documentation**: `docs/engines/enterprise_distressed_asset_debt_stress/rbac_permissions.md`

---

**Document Control**

**Version:** 1.1.0  
**Last Updated:** 2025-01-XX  
**Author:** Backend Engineering Team  
**Status:** Production Ready


