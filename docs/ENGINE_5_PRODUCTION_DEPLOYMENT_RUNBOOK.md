# Engine #5 Production Deployment Runbook

This repo cannot deploy to your production environment automatically. This runbook provides the concrete steps and configuration needed to deploy Engine #5 safely, enable exports, and bring up monitoring.

## Preconditions

- A Postgres database is provisioned and reachable from the backend.
- An S3-compatible bucket is provisioned and reachable from the backend (AWS S3, MinIO, etc.).
- You decide which engines to enable via `TODISCOPE_ENABLED_ENGINES`.

## Required Environment Variables

- `TODISCOPE_DATABASE_URL` (e.g. `postgresql+asyncpg://user:pass@host:5432/db`)
- `TODISCOPE_ARTIFACT_STORE_KIND` = `s3` (recommended for production)
- `TODISCOPE_S3_ENDPOINT_URL`
- `TODISCOPE_S3_ACCESS_KEY_ID`
- `TODISCOPE_S3_SECRET_ACCESS_KEY`
- `TODISCOPE_S3_BUCKET`
- `TODISCOPE_ENABLED_ENGINES` includes `engine_enterprise_deal_transaction_readiness`

## Deploy (Container)

1. Build the backend image:
   - `docker build -t todiscope-backend:prod -f backend/Dockerfile .`
2. Run with production env vars set (Kubernetes, ECS, systemd, etc.).
3. Confirm health and metrics:
   - `GET /api/v3/health`
   - `GET /metrics`

## Enable Monitoring (Prometheus + Grafana)

For a reference stack, use `infra/docker-compose.yml` (Prometheus scrapes `/metrics` and Grafana provisions a dashboard):

- Start:
  - `docker compose -f infra/docker-compose.yml up --build`
- Grafana:
  - URL: `http://localhost:3000` (admin/admin by default in the compose file)
  - Dashboard: “Engine #5 — Exports & Health”

## Post-Deployment Validation

- Run the full test suite in CI prior to deploy:
  - `python3 -m pytest -q`
- Validate Engine #5 externally:
  1. Create a DatasetVersion:
     - `POST /api/v3/ingest`
  2. Run Engine #5 with explicit parameters:
     - `POST /api/v3/engines/enterprise-deal-transaction-readiness/run`
  3. Export external artifacts:
     - `POST /api/v3/engines/enterprise-deal-transaction-readiness/export` with `formats: ["json","pdf"]`

