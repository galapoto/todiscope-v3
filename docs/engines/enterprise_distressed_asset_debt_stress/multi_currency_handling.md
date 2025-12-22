# Multi-Currency Handling: Enterprise Distressed Asset & Debt Stress Engine

**Engine ID:** `engine_distressed_asset_debt_stress`  
**Documentation Version:** 1.0  
**Last Updated:** 2025-01-XX

---

## Overview

The Enterprise Distressed Asset & Debt Stress Engine operates on **currency-normalized data** that has been processed by the TodiScope v3 normalization pipeline. The engine itself is **currency-agnostic** and performs all calculations using normalized float values, assuming all monetary amounts have been converted to a common base currency during the normalization phase.

---

## Currency Normalization Architecture

### Normalization Layer Responsibility

**Currency normalization occurs at the TodiScope v3 normalization layer**, not within the engine. This design ensures:

1. **Separation of Concerns**: Currency conversion logic is centralized in the normalization pipeline
2. **Consistency**: All engines receive data in the same normalized format
3. **Determinism**: Exchange rates are applied consistently across all data processing
4. **Traceability**: Currency conversion metadata is preserved in normalization records

### Normalization Process

The normalization pipeline is responsible for:

1. **Currency Identification**: Extracting currency codes from raw data (e.g., `USD`, `EUR`, `GBP`)
2. **Exchange Rate Application**: Applying exchange rates to convert all amounts to base currency
3. **Data Normalization**: Producing normalized records with currency-agnostic float values
4. **Metadata Preservation**: Storing original currency information in normalized record metadata

---

## Expected Data Format

### Normalized Record Structure

The engine expects normalized records with the following structure:

```json
{
  "financial": {
    "debt": {
      "total_outstanding": 1000000.0,
      "interest_rate_pct": 5.0,
      "collateral_value": 750000.0,
      "instruments": [
        {
          "principal": 500000.0,
          "interest_rate_pct": 4.5,
          "collateral_value": 400000.0
        }
      ]
    },
    "assets": {
      "total": 2000000.0
    },
    "distressed_assets": [
      {
        "name": "Asset A",
        "value": 350000.0,
        "recovery_rate_pct": 41.4
      }
    ]
  },
  "metadata": {
    "currency_base": "EUR",
    "normalized_at": "2025-01-01T00:00:00Z",
    "exchange_rates": {
      "USD": 0.92,
      "GBP": 1.15
    }
  }
}
```

### Key Points

- **All monetary values are floats** in the base currency
- **Currency information** is preserved in metadata (if needed for reporting)
- **No currency conversion logic** exists in the engine
- **All calculations** assume a single base currency

---

## Exchange Rate Handling

### Exchange Rate Source

Exchange rates are **not managed by the engine**. They are:

1. **Applied during normalization** by the normalization pipeline
2. **Sourced from** external exchange rate providers or internal rate tables
3. **Timestamped** to ensure consistency (rates applied at normalization time)
4. **Stored in metadata** for audit and traceability purposes

### Exchange Rate Application

The normalization layer should:

1. **Identify base currency**: Typically configured at the DatasetVersion or organization level
2. **Apply rates**: Convert all amounts to base currency using rates valid at normalization time
3. **Handle missing rates**: Either reject records with missing rates or apply default rates (with warnings)
4. **Preserve originals**: Store original currency and amount in metadata for audit purposes

---

## Multi-Currency Data Scenarios

### Scenario 1: Single Currency

**Input (Raw):**
```json
{
  "debt_outstanding": 1000000,
  "currency": "EUR"
}
```

**Normalized:**
```json
{
  "financial": {
    "debt": {
      "total_outstanding": 1000000.0
    }
  },
  "metadata": {
    "currency_base": "EUR"
  }
}
```

**Engine Processing:**
- Engine receives `1000000.0` (already in base currency)
- No conversion needed
- Calculations proceed normally

### Scenario 2: Multiple Currencies

**Input (Raw):**
```json
{
  "debt_instruments": [
    {
      "principal": 500000,
      "currency": "USD"
    },
    {
      "principal": 400000,
      "currency": "GBP"
    }
  ],
  "base_currency": "EUR",
  "exchange_rates": {
    "USD": 0.92,
    "GBP": 1.15
  }
}
```

**Normalized:**
```json
{
  "financial": {
    "debt": {
      "instruments": [
        {
          "principal": 460000.0,
          "interest_rate_pct": 5.0
        },
        {
          "principal": 460000.0,
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
    },
    "original_currencies": ["USD", "GBP"]
  }
}
```

**Engine Processing:**
- Engine receives aggregated `total_outstanding: 920000.0` (EUR)
- All calculations use normalized EUR values
- Original currency information preserved in metadata

### Scenario 3: Intercompany Transactions

**Input (Raw):**
```json
{
  "intercompany_debt": [
    {
      "entity": "Subsidiary A",
      "amount": 200000,
      "currency": "USD"
    },
    {
      "entity": "Subsidiary B",
      "amount": 150000,
      "currency": "GBP"
    }
  ]
}
```

**Normalized:**
```json
{
  "financial": {
    "debt": {
      "total_outstanding": 353000.0,
      "intercompany_breakdown": {
        "Subsidiary A": 184000.0,
        "Subsidiary B": 172500.0
      }
    }
  },
  "metadata": {
    "currency_base": "EUR",
    "intercompany_entities": ["Subsidiary A", "Subsidiary B"]
  }
}
```

**Engine Processing:**
- Engine receives aggregated debt in base currency
- Intercompany breakdown preserved in metadata (if needed)
- All stress calculations use normalized values

---

## Missing or Incorrect Currency Data

### Missing Currency Information

**Expected Behavior:**

1. **During Normalization:**
   - If currency code is missing, normalization should either:
     - **Reject the record** (preferred for data quality)
     - **Apply default currency** (with warning logged)
     - **Infer from context** (e.g., entity location, with warning)

2. **During Engine Processing:**
   - Engine assumes all values are in base currency
   - No currency validation performed (already normalized)
   - Missing currency metadata does not affect calculations

### Invalid Currency Codes

**Expected Behavior:**

1. **During Normalization:**
   - Invalid ISO 4217 codes should be rejected
   - Normalization should raise `CanonicalCurrencyInvalidError`
   - Record should not be normalized until currency is corrected

2. **During Engine Processing:**
   - Engine does not validate currency codes
   - Assumes normalization layer has handled validation

### Missing Exchange Rates

**Expected Behavior:**

1. **During Normalization:**
   - If exchange rate is missing for a currency:
     - **Option A**: Reject record (preferred for accuracy)
     - **Option B**: Apply default rate (e.g., 1.0) with warning
     - **Option C**: Use most recent available rate with warning

2. **During Engine Processing:**
   - Engine does not handle missing rates
   - All data should be pre-normalized with valid rates

---

## Currency Metadata in Reports

### Report Structure

The engine's reports include currency metadata when available:

```json
{
  "report": {
    "metadata": {
      "dataset_version_id": "dv_123",
      "currency_base": "EUR",
      "normalized_at": "2025-01-01T00:00:00Z"
    },
    "debt_exposure": {
      "total_outstanding": 1000000.0,
      "net_exposure_after_recovery": 105000.0
    }
  }
}
```

### Currency Information Sources

Currency metadata comes from:

1. **NormalizedRecord metadata**: Base currency and exchange rates
2. **DatasetVersion metadata**: Organization-level currency settings
3. **RawRecord metadata**: Original currency codes (preserved for audit)

---

## Best Practices

### For Data Providers

1. **Include Currency Codes**: Always provide ISO 4217 currency codes in raw data
2. **Provide Exchange Rates**: Include exchange rates or ensure they're available in normalization layer
3. **Timestamp Data**: Include timestamps to ensure rate consistency
4. **Validate Before Normalization**: Ensure currency codes are valid ISO 4217 format

### For Normalization Layer

1. **Validate Currency Codes**: Reject invalid ISO 4217 codes
2. **Apply Rates Consistently**: Use same rate source and timestamp for all records in a DatasetVersion
3. **Preserve Originals**: Store original currency and amount in metadata
4. **Log Conversions**: Log all currency conversions for audit purposes

### For Engine Usage

1. **Verify Normalization**: Ensure data is normalized before engine execution
2. **Check Metadata**: Review currency metadata in reports for accuracy
3. **Handle Warnings**: Monitor for currency-related warnings in normalization logs
4. **Audit Trail**: Use metadata to trace currency conversions in audit scenarios

---

## Error Handling

### Currency-Related Errors

The engine does **not** raise currency-specific errors. All currency issues should be resolved during normalization:

- **Invalid Currency**: Handled by normalization layer (`CanonicalCurrencyInvalidError`)
- **Missing Rate**: Handled by normalization layer (reject or apply default)
- **Conversion Failure**: Handled by normalization layer (reject record)

### Engine Errors

The engine may raise errors if:

- **NormalizedRecord Missing**: No normalized data available
- **Invalid Data Format**: Normalized data structure is incorrect
- **Calculation Errors**: Mathematical errors (unrelated to currency)

---

## Examples

### Example 1: Multi-Currency Debt Aggregation

**Raw Data:**
```json
{
  "debt_instruments": [
    {"principal": 1000000, "currency": "USD", "interest_rate_pct": 5.0},
    {"principal": 500000, "currency": "GBP", "interest_rate_pct": 4.5}
  ],
  "base_currency": "EUR",
  "exchange_rates": {"USD": 0.92, "GBP": 1.15}
}
```

**Normalized Data:**
```json
{
  "financial": {
    "debt": {
      "total_outstanding": 1415000.0,
      "interest_rate_pct": 4.84,
      "instruments": [
        {"principal": 920000.0, "interest_rate_pct": 5.0},
        {"principal": 575000.0, "interest_rate_pct": 4.5}
      ]
    }
  }
}
```

**Engine Output:**
```json
{
  "debt_exposure": {
    "total_outstanding": 1415000.0,
    "interest_payment": 68526.0,
    "net_exposure_after_recovery": 150000.0
  }
}
```

All values are in EUR (base currency).

### Example 2: Intercompany Debt with Currency Conversion

**Raw Data:**
```json
{
  "intercompany_debt": {
    "Subsidiary_US": {"amount": 500000, "currency": "USD"},
    "Subsidiary_UK": {"amount": 300000, "currency": "GBP"}
  },
  "base_currency": "EUR"
}
```

**Normalized Data:**
```json
{
  "financial": {
    "debt": {
      "total_outstanding": 805000.0
    }
  },
  "metadata": {
    "intercompany_breakdown": {
      "Subsidiary_US": 460000.0,
      "Subsidiary_UK": 345000.0
    }
  }
}
```

**Engine Processing:**
- Aggregates all intercompany debt to single value
- Performs stress calculations on aggregated amount
- Preserves intercompany breakdown in metadata (if needed for reporting)

---

## Summary

1. **Currency normalization occurs at the normalization layer**, not in the engine
2. **Engine operates on currency-agnostic float values** in base currency
3. **Exchange rates are applied during normalization**, not by the engine
4. **Currency metadata is preserved** for audit and reporting purposes
5. **All calculations assume single base currency** throughout processing
6. **Missing or invalid currency data** should be handled during normalization

---

## References

- **TodiScope v3 Architecture**: `ARCHITECTURE.md`
- **Normalization Pipeline**: `backend/app/core/normalization/`
- **Financial Forensics Normalization**: `backend/app/engines/financial_forensics/normalization.py` (currency normalization example)
- **Engine API Documentation**: `PRODUCTION_DEPLOYMENT.md`

---

**Document Control**

**Version:** 1.0  
**Last Updated:** 2025-01-XX  
**Author:** Backend Engineering Team  
**Status:** Production Ready


