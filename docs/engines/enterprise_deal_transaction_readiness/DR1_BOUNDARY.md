# DR-1 Boundary Document — Engine #5: Enterprise Deal & Transaction Readiness

**Status:** Draft (authoritative boundary skeleton)  
**Immutability/Detachability Class:** Detachable engine (modular monolith module)  
**Dataset Anchor:** `dataset_version_id` (immutable, UUIDv7)  

---

## Purpose Statement

Engine #5 produces a deterministic, evidence-backed **Transaction Readiness Package** for a single immutable `DatasetVersion`, suitable for enterprise due diligence and transaction workflows (e.g., data-room preparation, disclosure schedules, control/readiness checklists).

Its role is strictly **advisory and evidentiary**: it reports packaging status, evidence coverage, binding validity, and explicit readiness gaps for the declared runtime scope. It **does not** provide valuation, market predictions, pricing guidance, or any deal success/probability statements.

It translates already-ingested immutable artifacts and already-produced immutable findings/reports into a **shareable, auditable, replayable readiness view** strictly bound to `dataset_version_id`.

---

## Scope

### In Scope (What the Engine Does)

- **Runtime-scoped execution (not part of DatasetVersion)**
  - Transaction scope is a runtime parameter provided at execution and is persisted in the engine’s run table.
- **Readiness packaging**
  - Build an immutable “readiness pack” manifest (the index of what is included, what is missing, and why) bound to `dataset_version_id` and `run_id`.
  - Produce externally shareable views by applying deterministic redaction/omission rules and enforcing evidence-backing requirements.
- **Readiness checks (deterministic, evidence-backed)**
  - Evaluate the presence, binding correctness, and internal consistency of required artifacts and required upstream engine outputs for a declared runtime transaction scope.
  - Emit readiness “gaps” as findings with explicit evidence bundles (missing artifact references, binding mismatches, schema mismatches, or contract violations).
- **Interface normalization**
  - Canonicalize upstream outputs into a stable, engine-owned readiness schema (no enrichment, no inference, no aggregation beyond explicit checklist rollups).
- **Idempotent, append-only persistence**
  - Persist engine-owned outputs as immutable records (create-by-ID, no updates/deletes), and externalize shareable artifacts via core-owned artifact storage.

### Out of Scope (What is Not Claimed Even When In Scope)

- The engine’s outputs assert **readiness state and evidence coverage only** for the provided `DatasetVersion` and runtime transaction scope; they do not assert correctness of business outcomes, and they do not recommend whether to proceed with a transaction.

---

## Exclusions

### Explicit Functional Exclusions (Hard “MUST NOT”)

- **No speculative features**
  - No market prediction, valuation, pricing guidance, or deal success probability.
  - No recommendation/decisioning (“should accept”, “should proceed”, “optimal structure”).
- **No negotiation or external workflow automation**
  - No third-party outreach, document requests to counterparties, or automated diligence Q&A.
  - No email/Slack/CRM integrations as part of engine logic.
- **No external data fetching**
  - No market data, pricing comps, public filings lookups, or third-party enrichment APIs as part of engine execution.
- **No new data creation or enrichment**
  - No generation of new “facts” about the business (e.g., inferred revenue, inferred commitments).
  - No joining across datasets, no “latest dataset”, no historical trend analysis.
- **No policy/compliance adjudication**
  - No legal opinions, regulatory compliance determinations, or accounting policy conclusions.
  - May report evidence presence/absence and binding validity only.

### Architectural/Platform Exclusions (Non-Negotiable)

- No domain logic in core (all deal/readiness domain schemas, rules, and terminology live inside this engine module).
- Modular monolith only: Engine #5 ships as an in-process module; it must not be deployed as a separate service and must not require inter-service RPC to function.
- No direct access to shared storage from engine code (all shared mechanics go through core services).
- No cross-engine imports (Engine #5 must not import code modules from other engines).
- No mutable writes (updates/deletes) to any persisted artifacts, evidence, findings, or outputs.

---

## Ownership Declaration

### What Engine #5 Owns

Engine #5 is the sole owner of its **domain rules and persisted outputs** for transaction readiness, including:

- **Readiness rulebook and checklist definitions** (engine-internal, versioned, deterministic order).
- **Readiness findings** (gap records, completeness statuses, binding mismatch reports) bound to `dataset_version_id` and `run_id`.
- **Readiness pack manifests** (the authoritative index of included artifacts/outputs and the reasons for inclusion/exclusion).
- **Externalization/redaction rules for readiness views** (engine-owned policies for what is safe to share, implemented deterministically).

All engine-owned persisted state must live in engine-owned tables/namespaces and must be removable without impacting core boot.

### What Engine #5 Consumes (But Does Not Own)

Engine #5 consumes the following via core-owned interfaces only:

- **DatasetVersion registry** (read-only) to validate the provided `dataset_version_id` exists.
- **Artifact store** (read-only for loads; write-only via core API for externalized pack artifacts) using content-addressed payloads.
- **Evidence registry** (write evidence bundles; read evidence references) as a core-owned, engine-agnostic system.
- **Upstream engine outputs** only as immutable artifacts/evidence registered in core (never by reading upstream engine tables directly).

### Data Ownership (Who Owns What Data)

- **External systems** own source-of-truth business data; ingestion produces immutable artifacts and binds them to a `DatasetVersion`.
- **Core services** own the mechanics and registries: `DatasetVersion`, artifact storage/addressing, and evidence/review infrastructure.
- **Engine #5** owns only its readiness domain logic and its readiness outputs (manifests, findings, checklist statuses) and is forbidden from mutating upstream data or core registries.

### What Engine #5 Is Forbidden From Touching

- Creating, modifying, or selecting DatasetVersions (no “latest/current/default”; no ingestion responsibilities).
- Modifying core schemas, core evidence semantics, or artifact storage mechanics.
- Reading or writing other engines’ internal tables/state.
- Mutating any shared record (users, orgs, permissions, billing, review workflow), except through explicitly allowed core APIs that are engine-agnostic and mechanics-only.

---

## DatasetVersion Details

### Anchor and Immutability

- `dataset_version_id` is **mandatory** for every Engine #5 entrypoint and must be a **UUIDv7** created by ingestion.
- The engine operates on **exactly one** `dataset_version_id` per run.
- The engine must not infer a dataset (“latest”), must not accept ambiguous identifiers, and must hard-fail on unknown `dataset_version_id`.

### DatasetVersion Represents Data (Not Analysis Parameters)

- `DatasetVersion` represents the immutable **data snapshot** and its immutable ingested artifacts.
- Transaction scope and any analysis parameters are **not** stored in `DatasetVersion`.
- Run parameters (FX rates, assumptions, transaction scope) are provided at runtime and stored in the engine’s run table, not in `DatasetVersion`.

### Binding Rules (Replayability and Validity)

Engine #5 guarantees replayability under the following conditions:

- **Inputs are immutable and fully declared**
  - All consumed artifacts are content-addressed and checksum-verified on load.
  - All upstream engine outputs consumed by Engine #5 are referenced as immutable artifacts bound to the same `dataset_version_id`.
  - All run parameters that can affect outputs are explicit, validated, and persisted with the engine run record (engine-owned run table), not in `DatasetVersion`.
- **Deterministic execution**
  - No system time, randomness, environment-dependent branching, or unordered iteration.
  - Explicit rule ordering; stable sorting for any collection operations.
- **Output identity**
  - All replay-stable persisted outputs use deterministic IDs derived from stable keys (at minimum: `dataset_version_id`, engine version, rule identifiers, canonical input references, and the persisted run parameters).

### Replay Contract

Given the same `dataset_version_id`, the same set of referenced immutable artifacts (by hash/ID), and the same persisted run parameters (including transaction scope), Engine #5 must be able to re-run and reproduce:

- the same readiness findings (set equality and deterministic IDs),
- the same readiness pack manifest bytes (bitwise identical),
- the same externalized artifacts bytes (bitwise identical),
- or else fail with a deterministic contract violation.

If Engine #5 persists a `run_id` (UUIDv7) for operational traceability, that identifier must be treated as metadata and must not be used as an entropy source for any replay-stable IDs or output payload bytes.

### Deterministic ID Requirements (Hard Constraints)

- `dataset_version_id` is UUIDv7 (ingestion-generated) and is the immutable dataset anchor.
- Engine #5 MUST NOT generate replay-stable identifiers using UUIDv4, randomness, or system time.
- Engine #5 MUST NOT embed system-time-derived identifiers into readiness artifacts intended to be bitwise replayable.
- Where a UUID is required for run tracking, Engine #5 uses UUIDv7 (not UUIDv4); replay-stable object IDs remain deterministic and stable across reruns.

---

## Platform Law Alignment (Explicit References)

Engine #5 must comply with `docs/NON_NEGOTIABLE_PLATFORM_LAWS.md`:

1. **Law #1 — Core is mechanics-only:** no readiness domain schemas/rules in core; Engine #5 contains all readiness domain logic.
2. **Law #2 — Engines are detachable:** Engine #5 can be absent/disabled without impacting core boot; disabled = no routes and no writes.
3. **Law #3 — DatasetVersion is mandatory:** every run and every output is bound to explicit `dataset_version_id`; no implicit dataset selection.
4. **Law #4 — Artifacts are content-addressed:** all externalized readiness artifacts are stored via core artifact store and verified by checksum.
5. **Law #5 — Evidence and review are core-owned:** Engine #5 writes evidence bundles to core evidence registry and does not implement engine-specific review mechanics.
6. **Law #6 — No implicit defaults:** every output-affecting parameter (including transaction scope) is explicit, validated, and persisted in the engine run table.

---

## Kill-Switch Definition

### Required Behavior

Engine #5 must be controlled by a single enable/disable kill-switch that enforces:

- **Phase 0 gating:** check kill-switch before routing, before any reads, and before any writes.
- **Disabled state guarantees:**
  - No routes mounted (or all routes return a deterministic “engine disabled” error without performing reads/writes).
  - No background jobs, scheduled runs, or side effects.
  - Zero writes under all circumstances when disabled.
 - **Dual enforcement points (mandatory)**
   - **Mount-time gating:** routers are mounted only when enabled.
   - **Runtime gating:** every entrypoint re-checks enabled state before any side effects.
 - **State change handling**
   - If the engine transitions from enabled → disabled, any in-progress execution must be invalidated/aborted before producing outputs or exports.

**Reference patterns (implementation files):**
- `docs/ENGINE_EXECUTION_TEMPLATE.md` (Phase 0 Gate invariant)
- `docs/engines/audit_readiness/EXTERNALIZATION_AND_HARDENING.md` (Kill-Switch Revalidation Checklist)
- `backend/app/core/engine_registry/mount.py` (mount-time router gating)
- `backend/app/core/engine_registry/kill_switch.py` (kill-switch predicate)

### Detachability Guarantees

- The platform must boot and operate without Engine #5 present or enabled.
- Engine #5 must depend only on core mechanics APIs plus immutable inputs; removing the engine must not break core or other engines.
- Engine #5 outputs (artifacts/evidence) are optional, additive, and discoverable only if the engine is enabled and has executed.

---

## Interfaces with Other Engines (Upstream/Downstream)

### Upstream Interfaces (Consumed Inputs)

Engine #5 may consume only immutable, dataset-bound inputs:

1. **Core (mandatory)**
   - `DatasetVersion` existence/metadata (read-only): validate `dataset_version_id` (UUIDv7) is known.
   - Artifact retrieval (read-only): load artifacts by content hash/ID with checksum verification.
   - Evidence registry (read/write): attach evidence bundles; reference prior evidence by ID.

2. **Engine #2 — Financial Forensics & Leakage (optional, via core-registered artifacts only)**
   - Externalized forensics reports/manifests bound to the same `dataset_version_id`.
   - Findings/evidence references required for diligence packaging (as immutable artifacts/evidence IDs).
   - Engine #5 MUST NOT read Engine #2 internal tables or call Engine #2 code directly.

3. **Engine #4 — Enterprise Audit Readiness & Data Quality (optional, via core-registered artifacts only)**
   - Externalized audit readiness reports and evaluation manifests bound to the same `dataset_version_id`.
   - Evidence completeness/binding-status artifacts used as prerequisites for readiness checks.
   - Engine #5 MUST NOT read Engine #4 internal tables or call Engine #4 code directly.

**Error handling rules (mandatory vs optional):**

- **Mandatory core inputs missing/invalid:** hard-fail deterministically with a typed error; produce no partial outputs.
- **Optional upstream engine inputs missing:** do not guess; emit deterministic “missing prerequisite” findings with evidence describing what was expected and why.
- **Binding mismatch (artifact not bound to `dataset_version_id`):** emit a deterministic binding violation finding and exclude the mismatched artifact from the readiness pack.

### Downstream Interfaces (Produced Outputs)

Engine #5 produces only immutable, dataset-bound outputs:

1. **Core Evidence Registry (mandatory)**
   - Evidence bundles for every readiness finding (presence/absence, binding mismatches, contract violations).

2. **Core Artifact Store (as externalized deliverables)**
   - `transaction_readiness_pack_manifest` (machine-readable index of inclusions/exclusions, bound to `dataset_version_id` and `run_id`).
   - `transaction_readiness_report` (human-readable, externally shareable, with deterministic redaction/omission rules).
   - `data_room_index` (deterministic listing of referenced artifacts and their bindings; no payload rewriting).

3. **Engine-owned persistence (optional, internal)**
   - Append-only records describing run parameters, readiness checks executed, and derived checklist statuses; all bound to `dataset_version_id` and `run_id`.

Downstream consumers (UI/export/review) must treat these outputs as immutable artifacts/evidence tied to `dataset_version_id` and must not assume Engine #5 is present.
