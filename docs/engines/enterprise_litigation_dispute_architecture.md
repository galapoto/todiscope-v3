# Enterprise Litigation & Dispute Analysis Architecture

## Overview
- **Purpose**: Provide a deterministic, DatasetVersion-bound engine that quantifies legal exposure, characterizes liability, compares litigated scenarios, and checks legal consistency without mutating the immutable core dataset. The engine only consumes normalized `legal_dispute` payloads supplied by the ingestion/normalization pipeline (`backend/app/engines/enterprise_litigation_dispute/run.py:74-131`).
- **Compliance anchors**: Every run validates the provided `dataset_version_id` (`run.py:62-71`), ensures `started_at` is RFC3339/Zoned (`run.py:49-60`), and enforces immutability when persisting evidence/finding records (`run.py:93-199`).

## Core Legal & Financial Dispute Logic
- **Damage Quantification** (`analysis.py:72-137`): Aggregates `claims` and gross compensatory/punitive figures, applies mitigation with a configurable recovery rate, and maps the net damage into severity tiers (`high`, `medium`, `low`) along with a normalized severity score. Output payloads are accompanied by two explicit assumptions: recovery rate scaling and severity thresholds.
- **Liability Assessment** (`analysis.py:129-187`): Identifies the dominant responsible party by highest `percent`, thresholds the supporting evidence strength into `weak`, `moderate`, or `strong` classifications, and collects indicators such as admissions or regulatory references. The threshold configuration is exposed as an explicit assumption.
- **Scenario Comparison** (`analysis.py:190-254`): Iterates provided scenarios, clamps probabilities, calculates expected damages and liability exposures, and identifies queueing best/worst cases. Probability weighting and liability multipliers are recorded as named assumptions to help reviewers trace risk rank adjustments.
- **Legal Consistency Check** (`analysis.py:256-310`): Inspects conflict declarations and missing support lists, flags issues, and emits a boolean `consistent` flag with a low/high confidence indicator. The completeness requirements assumption ties directly to how statutes/evidence expectations are interpreted.

## Evidence Aggregation & Reporting
- **Evidence creation workflow**: For each result slice (`damage`, `liability`, `scenario`, `legal_consistency`, plus a consolidated `summary`), the engine writes deterministic evidence records using `deterministic_evidence_id` (`run.py:204-240`). Each entry includes:
  - The dataset version linkage and engine identifier (`ENGINE_ID` constant).
  - The raw normalized payload reference (`source_raw_record_id`).
  - The section-specific payload with its embedded assumptions (e.g., `damage_info["assumptions"]`).
- **Findings**: Four persistent findings are emitted with deterministic IDs (`run.py:258-325`). Each finding references the same `source_raw_record_id` and links back to its evidence record via `FindingEvidenceLink`, ensuring legal/audit traceability (`run.py:310-340`).
- **Summary & Aggregated Output**: The final `summary` contains the dataset, raw record, each assessment payload, the aggregated assumptions list, and evidence IDs. The returned payload includes `findings`, `evidence`, and the `summary` object ready for report-generation tools (`run.py:199-241`, `run.py:336-346`).

## Assumptions (Tied to Logic)
| Identifier | Description | Source | Impacted Logic |
|------------|-------------|--------|----------------|
| `assumption_damage_recovery_rate` | Mitigation offsets are scaled by an assumed recovery rate. | `parameters.assumptions.damage.recovery_rate` (default 1.0) | Net damage after mitigation |
| `assumption_damage_severity_thresholds` | Severity bands categorize urgency for litigation exposure. | `parameters.assumptions.damage.severity_thresholds` | Severity label assignment |
| `assumption_liability_strength_threshold` | Evidence strength thresholds determine liability classification. | `parameters.assumptions.liability.evidence_strength_thresholds` | Liability strength label |
| `assumption_scenario_probabilities` | Scenario probabilities treated as independent likelihood estimates. | `parameters.assumptions.scenario.probabilities` | Scenario ranking, expected loss |
| `assumption_liability_multipliers` | Scenario-specific liability multipliers scale exposures. | `parameters.assumptions.scenario.liability_multiplier` (default 1.0) | Liability exposure calculation |
| `assumption_legal_framework_completeness` | Assumes provided statutes/policies capture relevant obligations/evidence. | `parameters.assumptions.legal_consistency.completeness_requirements` | Conflict/missing support detection |

_*Every assumption is surfaced in the payload returned to callers and persisted within the evidence records so reviewers can trace each conclusion back to its premise (`run.py:204-241`).*_

## Traceability & Outputs
- **DatasetVersion enforcement**: Inputs are always resolved via `DatasetVersion` and normalized record queries. No new DatasetVersion is created or modified (`run.py:99-142`).
- **Normalized inputs**: The first normalized record is used to drive the analysis; if absent, the engine aborts with `NormalizedRecordMissingError` (`run.py:131-145`). This enforces that only normalized data from the canonical pipeline feeds the logic.
- **Evidence linking**: Findings link back to both normalized sources and their supporting evidence using deterministic IDs (`run.py:258-340`), satisfying audit traceability requirements.
- **Results format**: The engine response includes:
  - `damage_assessment`, `liability_assessment`, `scenario_comparison`, `legal_consistency`: Each contains the calculated metrics plus assumptions.
  - `assumptions`: The aggregated list across sections for easier review.
  - `findings`: Four deterministic findings for downstream tooling.
  - `evidence`: Map of deterministic evidence IDs per section and summary.
  - `summary`: Collates everything for report generators, including the `raw_record_id`.

## Operational & Reporting Notes
- **Evidence-ready outputs**: The response payload (`run.py:336-346`) and persisted summary evidence allow Agent 4 and subsequent tooling to stitch report sections together without re-running calculations.
- **Immutability**: Evidence/finding creation helpers enforce immutability by comparing payloads/timestamps and reusing existing IDs when consistent (`run.py:93-199`).
- **Assumption transparency**: All assumptions are communicated in the payload and recorded in evidence, ensuring legal reviewers can validate the basis for high-level findings.

With this documentation, Agent 4 can confidently build downstream reporting/evidence aggregation tools knowing what each section represents, how assumptions impact outcomes, and where to pull the deterministic identifiers for integration.
