# AI Governance Event Logging

The governance core now owns a deterministic audit trail for every internal AI behavior by writing structured records into the `ai_event_log` table. The schema is intentionally narrow so it can capture:

- **Event metadata** (`event_id`, `engine_id`, `model_identifier`, `model_version`, `context_id`, `event_type`, `event_label`) while indexing on dataset version and event type for fast traceability queries.
- **Dataset linkage** (`dataset_version_id`) enforced via a foreign key to `dataset_version.id`; the logging service refuses to persist events without a verified version.
- **Payloads** (`inputs`, `outputs`) stored as JSON, enabling model inputs/outputs to be replayed deterministically; tool-related and RAG-related metadata live in the `tool_metadata` and `rag_metadata` JSON columns.
- **Governance metadata** (`governance_metadata`) tracks confidence scores, decision boundaries, warnings, or other control dimensions and is strictly required (events raise an error if this dict is absent or empty).
- **Timestamps** (`created_at`) are recorded in UTC to show when explicit actions were logged.

The `backend.app.core.governance.service` helpers (`log_model_call`, `log_tool_call`, `log_rag_event`) normalize inputs, ensure a dataset version exists, and attach metadata such as tool names, RAG sources, and governance assertions while still using a simple synchronous-style API that fits within the monolith. Because `governance_metadata` is today required & validated as non-empty, every event contains explicit confidence/decision-boundary context for governance audits.

Example: `backend/app/engines/csrd/run.py` now publishes:

1. A **RAG retrieval** event when `RawRecord` data is fetched, listing each record as a source.
2. A **model call** event when the emissions model runs, emitting the ES G inputs, computed totals, and indexed metadata.
3. A **tool/API call** event when `generate_esrs_report` builds the report payload.

Because every row is tied to `dataset_version_id` and created via the shared service, the log is deterministic (only explicitly executed events end up on disk) and extensible without changing the core table structure.
