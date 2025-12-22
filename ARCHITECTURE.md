# TodiScope v3 Architecture (Core Skeleton)

## Scope
This document describes the platform-neutral **core** building blocks for TodiScope v3:

- Authentication + RBAC (gate access to core APIs)
- Ingestion (accept raw data in multiple formats)
- Normalization (produce canonical, deterministic payloads)
- DatasetVersion (every stored record is tied to a version; write-once semantics)
- Evidence + findings linkage (traceability back to a version and source record)

Engines are intentionally out of scope for core and must remain domain-neutral.

## Core Data Model
- `DatasetVersion`: immutable identifier for a single ingestion run.
- `RawRecord`: append-only raw payloads tied to a `DatasetVersion`.
- `NormalizedRecord`: optional canonical representation derived from a `RawRecord`.
- `EvidenceRecord`: append-only evidence objects tied to a `DatasetVersion`.
- `FindingRecord`: a generic “finding” tied to a `DatasetVersion` and a source `RawRecord`.
- `FindingEvidenceLink`: links `FindingRecord` ↔ `EvidenceRecord`.

## API Surface (Backend)
- `POST /api/v3/ingest`: creates a `DatasetVersion`.
- `POST /api/v3/ingest-records`: ingests JSON records.
- `POST /api/v3/ingest-file`: ingests `.json`, `.csv`, or `.ndjson`.

When `TODISCOPE_API_KEYS` is set, the ingestion endpoints require `X-API-Key` with an `ingest` role.

## Determinism + Immutability
- Core records are protected from updates and deletes via ORM flush guards.
- Normalization produces stable keys and JSON-safe values.

