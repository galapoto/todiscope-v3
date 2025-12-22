# Engine Lifecycle Phases
- Phase 0 — Gate: check kill-switch before routing, before any reads, before any writes.
- Phase 1 — Validate: require `dataset_version_id`; validate parameters; reject missing/unknown fields.
- Phase 2 — Acquire inputs: load required immutable artifacts via core services; bind every load to `dataset_version_id`; fail hard if missing; verify checksum on read.
- Phase 3 — Canonicalize: transform raw records into a canonical schema with explicit rules; preserve provenance links; no enrichment; no aggregation; deterministic ordering.
- Phase 4 — Produce findings: apply deterministic rules; assign enum-only confidence; generate deterministic IDs from stable keys; emit one evidence bundle per finding.
- Phase 5 — Derive outputs: map findings into higher-level categories/metrics using an explicit, locked rule order; bind all outputs to `dataset_version_id` and `run_id`.
- Phase 6 — Externalize: produce shareable view by excluding internal sections, redacting/anonymizing identifiers, and enforcing semantics guards; never transform numeric values.
- Phase 7 — Persist: append-only writes to owned tables only; no updates/deletes; idempotent create-by-ID behavior.

# Build vs Audit Discipline
- Parallel build: implement phase-by-phase with hard-fail guards; add tests that fail on contract drift (schema, rule order, forbidden patterns, invariants).
- Parallel audit: run binary structural checks (imports, forbidden APIs, ownership boundaries, dataset binding, immutability paths, deterministic ID derivations).
- Binary outcomes: each phase is `GO` or `REMEDIATION REQUIRED`; no partial acceptance for in-scope requirements.
- Remediation rules: fix the minimal root cause; add/adjust a regression test that would have caught it; re-run the same audit checks; do not advance phases until `GO`.

# Invariants (Non-Negotiable)
- DatasetVersion: every entrypoint requires `dataset_version_id`; no inference; no “latest”; every artifact/evidence/output is bound to `dataset_version_id` (and `run_id` where applicable).
- Immutability: artifacts and evidence are content-addressed or ID-addressed; create is idempotent; overwrite is impossible; checksum verification on every load.
- Determinism: same inputs produce bitwise-identical outputs; no system time; no randomness; no environment-dependent behavior; stable iteration order; no float arithmetic.
- Kill-switch behavior: disabled engine exposes no routes and performs zero writes; kill-switch check happens before any side effects.

# What Future Engines MUST Copy
- Kill-switch gating before routing and before side effects.
- Explicit `dataset_version_id` validation at entry; strict parameter validation; no hidden defaults.
- Core/engine boundary: engines call core services for shared mechanics; engines do not access shared stores directly.
- Deterministic IDs for all persisted objects (run/evidence/finding/output) derived from stable keys.
- Idempotent create-by-ID and immutable storage with checksum verification.
- Evidence schema validation enforced at emission time; evidence payloads are complete, dataset-bound, and append-only.
- Contract locks via tests: forbidden patterns, rule ordering, schema completeness, and scope limits.

# What Future Engines MUST NOT Copy
- Any system time usage (`datetime.now`, `time.time`, `date.today`, equivalents) or time-derived defaults.
- Any direct access to shared storage from engine code; bypassing core services.
- Any cross-engine imports or shared-state coupling.
- Any mutation paths (update/delete) for persisted artifacts, evidence, findings, or outputs.
- Any hidden defaults, implicit inference, or “best effort” fallbacks for required inputs.
- Any nondeterministic iteration (unordered sets/maps without sorting), randomness, or float-based arithmetic.
