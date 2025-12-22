# Enterprise Regulatory Readiness (Non-CSRD) Engine

## Purpose & Scope
This engine establishes a framework-agnostic compliance readiness layer that evaluates controls, maps them to regulatory expectations, and preserves all traceability through immutable DatasetVersions. Its focus is on preparation for enterprise-level regulatory scrutiny (ISO, internal controls, emerging rules) while avoiding hard-coded dependence on any single regime.

## 1. Regulatory Framework Setup

- **Control taxonomy**: `ControlCategory`, `RiskType`, and `ControlStatus` enums (`controls.py:8-42`) define the permitted dimensions for each control, ensuring every catalog entry carries a governance, risk, and implementation posture.
- **Regulatory frameworks**: `RegulatoryFramework` objects (`frameworks.py:9-25`) declare framework IDs, descriptive metadata, and matching heuristics (framework ID membership, explicit control inclusion, domain tags). The default catalog includes ISO 27001, an internal control set, and a “future regulations” placeholder (`frameworks.py:42-64`).
- **Control evaluation modules**: `evaluate_controls` (`checks.py:27-50`) consumes catalog entries plus optional evidence hints to assign statuses, confidence, and rationale. Evaluations remain data-driven and do not bake in framework-specific rules, which keeps the engine reusable.
- **Framework-agnostic mapping**: `map_controls_to_frameworks` (`mapping.py:40-67`) iterates over every registered framework, applies `matches_control`, and computes an alignment score solely based on control status. This ensures the same catalog content can be associated with ISO, internal, or future frameworks without bespoke logic per regime.

## 2. Control Catalog & Assumptions

- Controls are ingested through `ControlCatalog.load_from_payloads` (`catalog.py:18-29`), which validates payloads, normalizes fields via `ControlDefinition.from_payload`, and enforces ownership/framework/tags. The catalog maintains a status distribution for reporting (`catalog.py:36-40`).
- If no explicit catalog is provided, `_ensure_catalog_has_controls` (`run.py:106-125`) injects `default:<framework>` placeholders so every framework remains represented in downstream mappings.
- Assumptions:
  1. Payloads contain `control_id`, `ownership`, `status`, and `frameworks` when present; defaults are safe when fields are missing.
  2. Evidence hints can override statuses per control, enabling evidence-based flexibility without manual code changes (`checks.py:34-48`).

## 3. System Setup & Data Flow

- **DatasetVersion enforcement**: `run_engine` (`run.py:242-399`) validates the incoming `dataset_version_id`, ensures it exists in `dataset_version` (`run.py:248-255`), and loads `RawRecord` entries tied to that version (`run.py:254-257`). `install_immutability_guards` is invoked (`run.py:242`) so core artifacts cannot be mutated.
- **Evidence & findings integration**: `_strict_create_evidence`, `_strict_create_finding`, and `_strict_link` guard immutability when writing to the evidence/finding tables (`run.py:128-233`). Findings and evidence IDs are deterministic and tied to the DatasetVersion via `deterministic_evidence_id`/`deterministic_id` helpers, preserving traceability.
- **Data flow**: The engine extracts the `regulatory`/`regulatory_readiness` payload from the raw record (`run.py:258-288`) and optionally records warnings when data is missing. Control hints from parameters (`params["control_status_hints"]`) or payload-level maps add context for evaluation (`run.py:275-287`).
- **Core integration**: Evidence storage is handled through `backend.app.core.evidence.service.create_evidence` and `create_finding`, ensuring all artifacts conform with platform immutability rules. `ControlDefinition` metadata becomes part of both findings and evidence payloads, facilitating downstream audits.

## 4. Compliance Mapping Logic

- The engine collects control evaluations and maps them to frameworks (`run.py:280-387`). Each evaluation retains the control status, confidence, and rationale, while mapping results include an alignment score computed from `ControlStatus` (`mapping.py:30-37`).
- Framework matches use control metadata (framework IDs, tags, and explicit control ids) so no framework-specific code is required (`frameworks.py:18-25`).
- Findings (`run.py:292-350`) are only created for controls deemed partial or not implemented, keeping attention on remediation areas. These findings bundle the control, evaluation, and framework mappings for transparency.
- A compliance snapshot evidence record (`run.py:357-385`) summarizes the catalog, evaluations, mappings, findings, and warnings, ensuring auditors can recreate the full decision trail tied to the given DatasetVersion.

## 5. Notes for Stakeholders

- The engine is intentionally agnostic to regulatory regimes; introducing additional frameworks only requires adding `RegulatoryFramework` entries (no code changes beyond configuration).
- DatasetVersion is the immutable anchor for every artifact. This satisfies audit requirements related to traceability across raw data, controls, evaluations, findings, and evidence.
- Default placeholder controls ensure that even without an explicit catalog, every framework still appears in the compliance snapshot, so the engine never leaves frameworks unrepresented.

For implementation details, refer to the source files listed above. Adjust control payloads, frameworks, or evidence hints as needed to keep the documentation aligned with evolving regulatory expectations. 
