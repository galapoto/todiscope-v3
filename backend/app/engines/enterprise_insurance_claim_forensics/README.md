# Enterprise Insurance Claim Forensics Engine

## Overview

The Enterprise Insurance Claim Forensics Engine provides a control framework for managing and analyzing insurance claims with comprehensive validation rules and complete audit trail functionality.

## Features

### 1. Claims Management Structure

- **ClaimRecord**: Immutable claim record structure with validation
- **ClaimTransaction**: Immutable transaction record structure
- **parse_claim_from_payload**: Utility to parse claims from normalized payloads

### 2. Validation Rules

The engine implements multiple validation rules for claims consistency:

- **ClaimAmountConsistencyRule**: Validates that claim amount matches transaction totals (1% tolerance)
- **ClaimDateConsistencyRule**: Validates that incident date is before or equal to reported date
- **TransactionDateConsistencyRule**: Validates that transaction dates are within reasonable range
- **CurrencyConsistencyRule**: Validates that all transactions use the same currency as the claim
- **ClaimStatusConsistencyRule**: Validates that claim status is consistent with transaction patterns

### 3. Audit Trail

Complete audit trail functionality for all claim interactions:

- **Claim Creation**: Logs every claim creation event
- **Claim Updates**: Logs claim update events
- **Transactions**: Logs all transaction events
- **Validation Results**: Logs validation results
- **Forensic Analysis**: Logs forensic analysis events

All audit trail entries are stored as evidence records with deterministic IDs, ensuring complete traceability.

### 4. DatasetVersion Compliance

- All operations require explicit `dataset_version_id`
- All evidence and findings are bound to DatasetVersion
- Immutability guards ensure no modifications to core entities
- Deterministic ID generation for all evidence and findings

## API Endpoints

### POST `/api/v3/engines/insurance-claim-forensics/run`

Run the engine for a given dataset version.

**Request:**
```json
{
  "dataset_version_id": "uuid-v7",
  "started_at": "2024-01-01T00:00:00Z",
  "parameters": {
    "assumptions": {}
  }
}
```

**Response:**
```json
{
  "dataset_version_id": "uuid-v7",
  "started_at": "2024-01-01T00:00:00Z",
  "claim_id": "claim-123",
  "policy_number": "POL-001",
  "claim_number": "CLM-001",
  "claim_type": "property",
  "claim_status": "open",
  "claim_amount": 10000.0,
  "currency": "USD",
  "validation_result": {
    "is_valid": true,
    "errors": [],
    "warnings": [],
    "rule_results": {},
    "summary": {}
  },
  "audit_trail_summary": {
    "total_entries": 5,
    "action_counts": {}
  },
  "transaction_count": 1,
  "findings": [],
  "evidence": {
    "claim": "evidence-id",
    "validation": "evidence-id",
    "audit_summary": "evidence-id",
    "summary": "evidence-id"
  },
  "summary": {}
}
```

### POST `/api/v3/engines/insurance-claim-forensics/report`

Generate a report for a previous engine run.

**Request:**
```json
{
  "dataset_version_id": "uuid-v7",
  "run_id": "run-id"
}
```

## Data Model

### Input Payload Format

The engine expects normalized records with the following structure:

```json
{
  "insurance_claim": {
    "claim_id": "claim-123",
    "policy_number": "POL-001",
    "claim_number": "CLM-001",
    "claim_type": "property",
    "claim_status": "open",
    "reported_date": "2024-01-01T00:00:00Z",
    "incident_date": "2023-12-15T00:00:00Z",
    "claim_amount": 10000.0,
    "currency": "USD",
    "claimant_name": "John Doe",
    "claimant_type": "individual",
    "description": "Property damage claim",
    "transactions": [
      {
        "transaction_id": "tx-1",
        "transaction_type": "payment",
        "transaction_date": "2024-01-15T00:00:00Z",
        "amount": 10000.0,
        "currency": "USD",
        "description": "Full payment"
      }
    ]
  }
}
```

## Database Models

### EnterpriseInsuranceClaimForensicsRun

Stores run records with:
- `run_id`: Unique run identifier
- `dataset_version_id`: Dataset version reference
- `claim_summary`: Summary of the claim
- `validation_results`: Complete validation results
- `audit_trail_summary`: Summary of audit trail entries
- `evidence_map`: Map of evidence IDs

### EnterpriseInsuranceClaimForensicsFinding

Stores findings with:
- `finding_id`: Unique finding identifier
- `dataset_version_id`: Dataset version reference
- `category`: Finding category (e.g., "validation")
- `metric`: Metric name
- `status`: Status (e.g., "error", "warning")
- `confidence`: Confidence level
- `evidence_ids`: Map of related evidence IDs
- `payload`: Complete finding payload

## Testing

Comprehensive unit tests are provided in `backend/tests/engine_enterprise_insurance_claim_forensics/`:

- `test_claims_management.py`: Tests for claims management structure
- `test_validation.py`: Tests for validation rules
- `test_engine.py`: Integration tests for the engine

## Integration with TodiScope

The engine is fully integrated with the TodiScope platform:

- **Engine Registry**: Registered in `backend/app/engines/__init__.py`
- **Kill Switch**: Respects `TODISCOPE_ENABLED_ENGINES` environment variable
- **Evidence System**: Uses core evidence service for immutable evidence storage
- **Findings System**: Uses core findings service for finding persistence
- **DatasetVersion**: All operations require and bind to DatasetVersion
- **Immutability**: All core entities are protected by immutability guards

## Constraints

- The engine does not override or replicate core TodiScope ingestion or normalization services
- All components are compliant with DatasetVersion system
- Complete audit trail for every claim interaction
- No domain-specific logic in core services
- All evidence and findings are immutable once created






