# Non-Negotiable Platform Laws (v3)

If a change violates any law below, it does not ship in v3.

## 1) Core is mechanics-only
- Core contains only platform mechanics reusable across engines.
- No domain meaning, no domain schemas, no domain rules in core.

## 2) Engines are detachable
- Platform boots with zero engines enabled.
- Enabling/disabling engines must not affect core boot or baseline operations.
- Disabled engines mount no routes and cannot write.

## 3) DatasetVersion is mandatory
- Every dataset-scoped record must be bound to `dataset_version_id`.
- There is no implicit dataset selection (“latest”, “current”, “default”).
- DatasetVersion is created via ingestion only.

## 4) Artifacts are content-addressed
- Payload bytes are stored via the core-owned `artifact_store`.
- DB stores metadata + lineage + sha256 hashes.
- Changing payloads requires new hashes; no overwrite semantics.

## 5) Evidence and review are core-owned
- Evidence registry is core-owned and engine-agnostic.
- Review workflow is core-owned and engine-agnostic.

## 6) No implicit defaults
- Any parameter that can affect outputs must be explicit and persisted.
- Missing required inputs fail hard with deterministic errors.

