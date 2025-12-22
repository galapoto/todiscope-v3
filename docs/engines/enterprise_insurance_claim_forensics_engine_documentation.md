DatasetVersion: 1.0.0
ReleaseDate: 2025-12-22
Author: Documentation Team (Agent 3)

# Enterprise Insurance Claim Forensics Engine — Findings, Evidence & Traceability

## Overview

This document describes how the **Enterprise Insurance Claim Forensics** engine integrates with the TodiScope core evidence and findings services **after remediation**. It focuses on:

- Creation of platform-level findings via the core `create_finding()` service
- Deterministic creation of evidence records via `create_evidence()` and `deterministic_evidence_id()`
- Linking findings to evidence via `FindingEvidenceLink` with conflict detection
- End‑to‑end traceability from `RawRecord` → `NormalizedRecord` → `FindingRecord` → `EvidenceRecord`

The engine implementation lives under:

- `backend/app/engines/enterprise_insurance_claim_forensics/`
- Core evidence & findings services: `backend/app/core/evidence/service.py`
- Core models: `backend/app/core/evidence/models.py`

This documentation is descriptive only and reflects the current implementation; it does **not** introduce new behavior.

---

## Core Evidence & Findings Services

### EvidenceRecord, FindingRecord, FindingEvidenceLink

The shared evidence models are defined in `backend/app/core/evidence/models.py`:

```python
class EvidenceRecord(Base):
    __tablename__ = "evidence_records"

    evidence_id: Mapped[str] = mapped_column(String, primary_key=True)
    dataset_version_id: Mapped[str] = mapped_column(
        String, ForeignKey("dataset_version.id"), nullable=False, index=True
    )
    engine_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FindingRecord(Base):
    __tablename__ = "finding_record"

    finding_id: Mapped[str] = mapped_column(String, primary_key=True)
    dataset_version_id: Mapped[str] = mapped_column(
        String, ForeignKey("dataset_version.id"), nullable=False, index=True
    )
    raw_record_id: Mapped[str] = mapped_column(
        String, ForeignKey("raw_record.raw_record_id"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FindingEvidenceLink(Base):
    __tablename__ = "finding_evidence_link"

    link_id: Mapped[str] = mapped_column(String, primary_key=True)
    finding_id: Mapped[str] = mapped_column(
        String, ForeignKey("finding_record.finding_id"), nullable=False, index=True
    )
    evidence_id: Mapped[str] = mapped_column(
        String, ForeignKey("evidence_records.evidence_id"), nullable=False, index=True
    )
```

Key points for the engine:

- **All findings** are persisted as `FindingRecord` instances via the core service.
- Each `FindingRecord` carries a **`raw_record_id`** that links it back to the source `RawRecord`.
- `FindingEvidenceLink` provides the platform‑level mapping between findings and evidence.

### Core services: deterministic IDs, evidence & finding creation

In `backend/app/core/evidence/service.py`:

```python
from backend.app.core.evidence.models import EvidenceRecord, FindingEvidenceLink, FindingRecord


def deterministic_evidence_id(*, dataset_version_id: str, engine_id: str, kind: str, stable_key: str) -> str:
    namespace = uuid.UUID("00000000-0000-0000-0000-000000000042")
    return str(uuid.uuid5(namespace, f"{dataset_version_id}|{engine_id}|{kind}|{stable_key}"))


async def create_evidence(
    db: AsyncSession,
    *,
    evidence_id: str,
    dataset_version_id: str,
    engine_id: str,
    kind: str,
    payload: dict,
    created_at: datetime,
) -> EvidenceRecord:
    existing = await db.scalar(select(EvidenceRecord).where(EvidenceRecord.evidence_id == evidence_id))
    if existing is not None:
        return existing

    rec = EvidenceRecord(
        evidence_id=evidence_id,
        dataset_version_id=dataset_version_id,
        engine_id=engine_id,
        kind=kind,
        payload=payload,
        created_at=created_at,
    )
    db.add(rec)
    await db.flush()
    return rec


async def create_finding(
    db: AsyncSession,
    *,
    finding_id: str,
    dataset_version_id: str,
    raw_record_id: str,
    kind: str,
    payload: dict,
    created_at: datetime,
) -> FindingRecord:
    existing = await db.scalar(select(FindingRecord).where(FindingRecord.finding_id == finding_id))
    if existing is not None:
        return existing
    rec = FindingRecord(
        finding_id=finding_id,
        dataset_version_id=dataset_version_id,
        raw_record_id=raw_record_id,
        kind=kind,
        payload=payload,
        created_at=created_at,
    )
    db.add(rec)
    await db.flush()
    return rec


async def link_finding_to_evidence(
    db: AsyncSession, *, link_id: str, finding_id: str, evidence_id: str
) -> FindingEvidenceLink:
    existing = await db.scalar(select(FindingEvidenceLink).where(FindingEvidenceLink.link_id == link_id))
    if existing is not None:
        return existing
    rec = FindingEvidenceLink(link_id=link_id, finding_id=finding_id, evidence_id=evidence_id)
    db.add(rec)
    await db.flush()
    return rec
```

The insurance claim forensics engine **always** goes through these services for creating findings and linking to evidence, adding an engine‑specific strict layer for immutability guarantees.

---

## Raw Record Linkage and Claim Mapping

A core remediation goal was to ensure that every finding can be traced back to a **specific raw record**.

### From NormalizedRecord to claim_raw_map

In `run_engine()` (file: `backend/app/engines/enterprise_insurance_claim_forensics/run.py`):

1. The engine loads all normalized records for the requested `DatasetVersion`.
2. It builds `(raw_record_id, payload)` tuples.
3. It delegates parsing to `extract_claims_and_transactions()`, which returns a mapping from `claim_id` to `raw_record_id`.

```python
# run.py
normalized_records = (
    await db.scalars(
        select(NormalizedRecord)
        .where(NormalizedRecord.dataset_version_id == dv_id)
        .order_by(NormalizedRecord.normalized_at.asc())
    )
).all()
if not normalized_records:
    raise NormalizedRecordMissingError("NORMALIZED_RECORD_REQUIRED")

records_with_raw = [(record.raw_record_id, record.payload) for record in normalized_records]
claims, transactions, claim_raw_map = extract_claims_and_transactions(records_with_raw, dv_id)
```

The helper in `analysis.py` threads the `raw_record_id` through to each claim:

```python
# analysis.py

def extract_claims_and_transactions(
    records: Sequence[tuple[str, dict[str, Any]]], dataset_version_id: str
) -> tuple[list[ClaimRecord], list[ClaimTransaction], dict[str, str]]:
    """Build claim records, transactions, and raw record mappings from normalized inputs."""
    claims: list[ClaimRecord] = []
    transactions: list[ClaimTransaction] = []
    claim_raw_map: dict[str, str] = {}
    for raw_record_id, payload in records:
        if not isinstance(payload, dict):
            continue
        try:
            claim = parse_claim_from_payload(payload, dataset_version_id)
        except ValueError:
            continue
        claims.append(claim)
        claim_raw_map[claim.claim_id] = raw_record_id
        transactions.extend(
            extract_transactions_from_claim_payload(payload, dataset_version_id, claim.claim_id, claim.reported_date)
        )
    return claims, transactions, claim_raw_map
```

### Using claim_to_raw_record in finding persistence

The `claim_raw_map` is passed into `_persist_findings()` as `claim_to_raw_record`:

```python
extra_entries = await _persist_findings(
    db,
    run_id=run_id,
    dataset_version_id=dv_id,
    exposures=exposures,
    validations=validation_results,
    evidence_lookup=claim_evidence,
    claim_to_raw_record=claim_raw_map,
    created_at=completed,
)
```

Inside `_persist_findings()`, each exposure must resolve to a `raw_record_id`:

```python
# run.py
async def _persist_findings(
    db,
    *,
    run_id: str,
    dataset_version_id: str,
    exposures: list[dict[str, Any]],
    validations: dict[str, dict[str, Any]],
    evidence_lookup: dict[str, list[str]],
    claim_to_raw_record: dict[str, str],
    created_at: datetime,
) -> list[dict[str, Any]]:
    """Persist findings using core services with raw_record_id linkage and evidence linking."""
    extra_entries: list[dict[str, Any]] = []
    for exposure in exposures:
        claim_id = exposure.get("claim_id")
        if not claim_id:
            continue

        raw_record_id = claim_to_raw_record.get(claim_id)
        if not raw_record_id:
            raise ClaimPayloadMissingError("CLAIM_RAW_RECORD_ID_REQUIRED")
        # ... build finding payload and persist via _strict_create_finding(...)
```

If the mapping is missing, the engine **hard‑fails** with `ClaimPayloadMissingError("CLAIM_RAW_RECORD_ID_REQUIRED")`, guaranteeing that no finding is created without a raw‑record linkage.

---

## Findings Creation via Core Service

### Strict wrapper around create_finding()

To align with platform immutability guarantees, the engine uses a strict helper `_strict_create_finding()` that wraps the core `create_finding()`:

```python
# run.py
async def _strict_create_finding(
    db,
    *,
    finding_id: str,
    dataset_version_id: str,
    raw_record_id: str,
    kind: str,
    payload: dict[str, Any],
    created_at: datetime,
) -> FindingRecord:
    """Create finding with immutability conflict detection."""
    existing = await db.scalar(select(FindingRecord).where(FindingRecord.finding_id == finding_id))
    if existing is not None:
        if (
            existing.dataset_version_id != dataset_version_id
            or existing.raw_record_id != raw_record_id
            or existing.kind != kind
        ):
            logger.warning(
                "INSURANCE_CLAIM_IMMUTABLE_CONFLICT finding_id_collision finding_id=%s dataset_version_id=%s",
                finding_id,
                dataset_version_id,
            )
            raise ImmutableConflictError("FINDING_ID_COLLISION")
        if existing.payload != payload:
            logger.warning(
                "INSURANCE_CLAIM_IMMUTABLE_CONFLICT finding_payload_mismatch finding_id=%s dataset_version_id=%s",
                finding_id,
                dataset_version_id,
            )
            raise ImmutableConflictError("IMMUTABLE_FINDING_MISMATCH")
        return existing
    return await create_finding(
        db,
        finding_id=finding_id,
        dataset_version_id=dataset_version_id,
        raw_record_id=raw_record_id,
        kind=kind,
        payload=payload,
        created_at=created_at,
    )
```

Behavior:

- **Idempotent**: If the same `finding_id` is reused with the same metadata and payload, the existing record is returned.
- **Immutable**: If the same `finding_id` is reused with different `dataset_version_id`, `raw_record_id`, `kind`, or `payload`, the helper raises `ImmutableConflictError`.
- **Platform‑aligned**: All eventual writes go through the shared `create_finding()` service.

### Findings creation flow in _persist_findings()

Within `_persist_findings()`, each loss‑exposure result is converted into a platform finding:

```python
finding_id = deterministic_id(dataset_version_id, run_id, claim_id, "loss_exposure")
finding_payload = {
    "id": finding_id,
    "dataset_version_id": dataset_version_id,
    "claim_id": claim_id,
    "category": "claim_forensics",
    "metric": "loss_exposure",
    "status": status,
    "confidence": confidence,
    "exposure": exposure,
    "validation": validation,
}

await _strict_create_finding(
    db,
    finding_id=finding_id,
    dataset_version_id=dataset_version_id,
    raw_record_id=raw_record_id,
    kind="claim_forensics",
    payload=finding_payload,
    created_at=created_at,
)
```

Notes:

- `finding_id` is **deterministic** via `deterministic_id(dataset_version_id, run_id, claim_id, "loss_exposure")`.
- `raw_record_id` comes from the earlier `claim_to_raw_record` map.
- The `payload` embeds both the exposure metrics and the validation result, providing a self‑contained audit context.

### Engine‑specific finding model

The engine also stores a view‑specific finding record for reporting in `EnterpriseInsuranceClaimForensicsFinding` (`models.py`), keyed by the same `finding_id` used for the core `FindingRecord`:

```python
class EnterpriseInsuranceClaimForensicsFinding(Base):
    __tablename__ = "engine_enterprise_insurance_claim_forensics_findings"

    finding_id: Mapped[str] = mapped_column(String, primary_key=True)
    dataset_version_id: Mapped[str] = mapped_column(
        String, ForeignKey("dataset_version.id"), nullable=False, index=True
    )
    run_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("engine_enterprise_insurance_claim_forensics_runs.run_id"),
        nullable=False,
        index=True,
    )
    category: Mapped[str] = mapped_column(String, nullable=False)
    metric: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[str] = mapped_column(String, nullable=False)
    evidence_ids: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
```

This **does not replace** the core `FindingRecord` and is considered an engine‑local projection for reporting.

---

## Evidence Creation, Deterministic IDs, and Strict Helpers

### Strict evidence creation

Both the audit trail and the finding persistence path use a strict evidence helper to enforce immutability. In `audit_trail.py`:

```python
async def _strict_create_evidence(
    db: AsyncSession,
    *,
    evidence_id: str,
    dataset_version_id: str,
    engine_id: str,
    kind: str,
    payload: dict[str, Any],
    created_at: datetime,
) -> EvidenceRecord:
    """Create evidence with immutability conflict detection."""
    existing = await db.scalar(select(EvidenceRecord).where(EvidenceRecord.evidence_id == evidence_id))
    if existing is not None:
        if existing.dataset_version_id != dataset_version_id or existing.engine_id != engine_id or existing.kind != kind:
            logger.warning(
                "INSURANCE_CLAIM_IMMUTABLE_CONFLICT evidence_id_collision evidence_id=%s dataset_version_id=%s",
                evidence_id,
                dataset_version_id,
            )
            raise ImmutableConflictError("EVIDENCE_ID_COLLISION")
        existing_created_at = existing.created_at
        if existing_created_at.tzinfo is None:
            existing_created_at = existing_created_at.replace(tzinfo=timezone.utc)
        normalized_created_at = created_at if created_at.tzinfo is not None else created_at.replace(tzinfo=timezone.utc)
        if existing_created_at != normalized_created_at:
            logger.warning(
                "INSURANCE_CLAIM_IMMUTABLE_CONFLICT evidence_created_at_mismatch evidence_id=%s dataset_version_id=%s",
                evidence_id,
                dataset_version_id,
            )
            raise ImmutableConflictError("IMMUTABLE_EVIDENCE_CREATED_AT_MISMATCH")
        if existing.payload != payload:
            logger.warning(
                "INSURANCE_CLAIM_IMMUTABLE_CONFLICT evidence_payload_mismatch evidence_id=%s dataset_version_id=%s",
                evidence_id,
                dataset_version_id,
            )
            raise ImmutableConflictError("IMMUTABLE_EVIDENCE_MISMATCH")
        return existing
    return await create_evidence(
        db,
        evidence_id=evidence_id,
        dataset_version_id=dataset_version_id,
        engine_id=engine_id,
        kind=kind,
        payload=payload,
        created_at=created_at,
    )
```

A similar helper is defined in `run.py` and used when creating evidence for findings.

### Deterministic evidence IDs for findings

Within `_persist_findings()`, the engine creates a dedicated evidence record per finding using the core `deterministic_evidence_id()` function:

```python
finding_evidence_id = deterministic_evidence_id(
    dataset_version_id=dataset_version_id,
    engine_id=ENGINE_ID,
    kind="loss_exposure",
    stable_key=f"{run_id}|{claim_id}|{finding_id}",
)
await _strict_create_evidence(
    db,
    evidence_id=finding_evidence_id,
    dataset_version_id=dataset_version_id,
    engine_id=ENGINE_ID,
    kind="loss_exposure",
    payload={
        "source_raw_record_id": raw_record_id,
        "finding": finding_payload,
        "exposure": exposure,
        "validation": validation,
        "audit_trail_evidence_ids": list(evidence_lookup.get(claim_id, [])),
    },
    created_at=created_at,
)
```

Notes:

- IDs are **deterministic** across runs given the same `dataset_version_id`, `run_id`, `claim_id`, and `finding_id`.
- The evidence payload explicitly includes:
  - `source_raw_record_id` (the same raw record tied to the `FindingRecord`)
  - `finding` (full finding payload)
  - `exposure` and `validation` details
  - `audit_trail_evidence_ids` for linking back to per‑event audit evidence

---

## Evidence Linking via FindingEvidenceLink

### Strict link helper

To link findings to evidence, the engine defines `_strict_link()` in `run.py`:

```python
async def _strict_link(
    db,
    *,
    link_id: str,
    finding_id: str,
    evidence_id: str,
) -> FindingEvidenceLink:
    existing = await db.scalar(select(FindingEvidenceLink).where(FindingEvidenceLink.link_id == link_id))
    if existing is not None:
        if existing.finding_id != finding_id or existing.evidence_id != evidence_id:
            logger.warning(
                "INSURANCE_CLAIM_IMMUTABLE_CONFLICT link_mismatch link_id=%s",
                link_id,
            )
            raise ImmutableConflictError("IMMUTABLE_LINK_MISMATCH")
        return existing
    return await link_finding_to_evidence(db, link_id=link_id, finding_id=finding_id, evidence_id=evidence_id)
```

Behavior:

- **Idempotent**: Reusing the same link ID with the same `finding_id` and `evidence_id` returns the existing record.
- **Immutable**: Any attempt to reuse a link ID for a different pairing results in `ImmutableConflictError("IMMUTABLE_LINK_MISMATCH")`.

### Link creation per finding

After creating the finding and its evidence, `_persist_findings()` links them:

```python
link_id = deterministic_id(dataset_version_id, run_id, claim_id, "loss_exposure_link")
await _strict_link(
    db,
    link_id=link_id,
    finding_id=finding_id,
    evidence_id=finding_evidence_id,
)
```

The same link ID pattern is used consistently, ensuring deterministic linkage that is safe under retries.

Engine‑local findings also embed evidence IDs for downstream reporting:

```python
engine_finding = EnterpriseInsuranceClaimForensicsFinding(
    finding_id=finding_id,
    dataset_version_id=dataset_version_id,
    run_id=run_id,
    category="claim_forensics",
    metric="loss_exposure",
    status=status,
    confidence=confidence,
    evidence_ids={
        "audit_trail": list(evidence_lookup.get(claim_id, [])),
        "loss_exposure": [finding_evidence_id],
    },
    payload=finding_payload,
    created_at=created_at,
)
```

---

## End‑to‑End Traceability

After remediation, the traceability chain for each loss‑exposure finding is:

1. **RawRecord**
   - Created during ingestion with `raw_record_id` and `dataset_version_id`.
2. **NormalizedRecord**
   - References the same `raw_record_id` and `dataset_version_id`.
3. **ClaimRecord / ClaimTransaction**
   - Parsed from normalized payloads by `extract_claims_and_transactions()`.
4. **FindingRecord** (core)
   - Created via `_strict_create_finding()` → `create_finding()`.
   - Includes `raw_record_id` (foreign key to `raw_record.raw_record_id`).
5. **EvidenceRecord** (core)
   - Created via `_strict_create_evidence()` → `create_evidence()` with deterministic IDs.
   - Payload embeds `source_raw_record_id` and the full finding payload.
6. **FindingEvidenceLink** (core)
   - Ensures a formal, immutable mapping from `finding_id` to `evidence_id`.
7. **EnterpriseInsuranceClaimForensicsFinding** (engine‑local)
   - References the same `finding_id` and aggregates evidence IDs for reporting.

This satisfies the requirement documented in `ENTERPRISE_INSURANCE_CLAIM_FORENSICS_REMEDIATION_COMPLETE.md`:

> Complete traceability chain: RawRecord → Finding → Evidence → AuditTrail.

---

## API & Integration Notes

### Engine identifier and version

- `ENGINE_ID = "engine_enterprise_insurance_claim_forensics"`
- `ENGINE_VERSION = "v1"`

Registered via `register_engine()` in `backend/app/engines/enterprise_insurance_claim_forensics/engine.py`.

### HTTP endpoint

The engine exposes a single run endpoint:

```http
POST /api/v3/engines/enterprise-insurance-claim-forensics/run
Content-Type: application/json
```

Example request body:

```json
{
  "dataset_version_id": "dv-insurance-forensics",
  "started_at": "2023-09-10T00:00:00Z",
  "parameters": {
    "assumptions": [
      {"name": "priority", "value": "unit"}
    ]
  }
}
```

On success, the response includes:

- `run_id` — deterministic engine run identifier
- `dataset_version_id` — the DatasetVersion used
- `status` — run status (e.g. `"completed"`)
- `loss_exposures` — per‑claim exposure details
- `claim_summary` — portfolio‑level aggregation
- `validation_results` and `validation_summary`
- `assumptions` — model and parameter assumptions
- `audit_trail_summary` — summary of audit trail evidence created

### Error and conflict handling

The FastAPI endpoint maps domain errors to HTTP status codes (see `engine.py`):

- 400 — validation issues (missing/invalid DatasetVersion, parameters, normalized data, claims)
- 404 — DatasetVersion not found
- 409 — `ImmutableConflictError` from strict helpers (evidence, findings, links)
- 500 — unexpected failures

For integrations, a 409 response indicates an attempt to **change immutable data** (e.g., reuse of a deterministic ID with different payload). Callers should treat this as a configuration or data pipeline issue rather than retrying blindly.

---

## Developer Guidelines & Best Practices

When extending or maintaining the Enterprise Insurance Claim Forensics engine:

1. **Always use core services for new findings and evidence**
   - Use `_strict_create_finding()` → `create_finding()` for any new finding categories.
   - Use `_strict_create_evidence()` → `create_evidence()` for any evidence.
   - Use `_strict_link()` → `link_finding_to_evidence()` for all finding‑evidence relationships.

2. **Preserve raw record linkage**
   - Ensure any new findings are backed by a `raw_record_id` obtained from normalized records.
   - Never create a `FindingRecord` without a resolvable `raw_record_id`.

3. **Use deterministic IDs**
   - Derive finding and evidence IDs using `deterministic_id()` and `deterministic_evidence_id()` with stable components.
   - Keep the ID schemas stable to preserve idempotency across reruns.

4. **Respect immutability and conflict detection**
   - Do not bypass the strict helpers when creating findings, evidence, or links.
   - Treat `ImmutableConflictError` as a signal that upstream inputs or ID construction have changed.

5. **Keep engine‑local projections in sync with core records**
   - Engine models like `EnterpriseInsuranceClaimForensicsFinding` should reference the same IDs and payloads as the core `FindingRecord` / `EvidenceRecord` entries to maintain coherent traceability.

This document should be reviewed and updated whenever the engine’s findings creation, evidence linking, or raw record linkage logic changes, keeping it aligned with the actual implementation and audit expectations.
