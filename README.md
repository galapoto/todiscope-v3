# TodiScope v3 (Bootstrap)

This repository is a clean v3 monorepo scaffold that enforces platform laws structurally:
- modular monolith
- core is mechanics-only
- engines are detachable (registry + kill-switch)
- DatasetVersion is mandatory and created via ingestion only (UUIDv7)
- artifacts are stored via core-owned `artifact_store` (S3-compatible; MinIO in dev)
- no implicit defaults
- test-first guardrails

## Local bootstrap

### Infra (Postgres + MinIO)
```bash
docker compose -f infra/docker-compose.yml up -d
```

### Backend
```bash
python -m venv .venv && source .venv/bin/activate
pip install -e backend
uvicorn backend.app.main:app --reload
```

### Tests
```bash
pytest backend/tests
```

## Engines

- **Enterprise Regulatory Readiness Engine** (`engine_regulatory_readiness`)
  - Endpoint: `POST /api/v3/engines/regulatory-readiness/run`
  - Focus: Framework-agnostic control catalog ingestion, readiness scoring, and regulatory gap remediation for non-CSRD programs.
  - Data model: Every run ties back to a `DatasetVersion`, captures per-control evaluations, persists gaps/remediation tasks, and emits deterministic evidence for audit defensibility.
  - Traceability: Findings link to evidence records via `FindingEvidenceLink`, and all artifacts respect immutability guards.
