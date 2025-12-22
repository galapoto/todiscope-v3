# Enterprise Distressed Asset & Debt Stress Engine — Monitoring Guidelines

## 1. Monitoring Objectives

- Maintain high availability and predictable latency for stress testing workloads.
- Detect ingestion, modeling, and persistence regressions early.
- Provide auditable traces for evidence/finding workflows.
- Ensure security and compliance observability across all data flows.

## 2. Health Monitoring

### 2.1 Health Checks

Use `backend/benchmarks/distressed_asset_debt_stress/health_check.py` to automate checks for:

- Database connectivity (`DatasetVersion` query).
- Evidence linking health (query `EvidenceRecord`, `FindingRecord`, `FindingEvidenceLink`).
- API availability (`GET /health`).
- Engine availability (`GET /api/v3/engines/distressed-asset-debt-stress/health`).
- Engine run endpoint (`POST /api/v3/engines/distressed-asset-debt-stress/run`) when a dataset version is supplied.

### 2.2 Integration Targets

- Export results to Prometheus via a push gateway or custom exporter.
- Visualize in Grafana dashboards with status indicators per component.

## 3. Performance Metrics

### 3.1 API Metrics

- `todiscope_http_request_duration_seconds{path="/api/v3/engines/distressed-asset-debt-stress/run"}`
- `todiscope_http_requests_total{path="/api/v3/engines/distressed-asset-debt-stress/run"}`
- `todiscope_engine_runs_total{engine_id="engine_distressed_asset_debt_stress"}`

### 3.2 Modeling Metrics

- `todiscope_engine_model_duration_seconds{engine_id="engine_distressed_asset_debt_stress"}`

### 3.3 Persistence Metrics

- `todiscope_engine_persistence_duration_seconds{engine_id="engine_distressed_asset_debt_stress",stage="write"}`
- `todiscope_engine_persistence_duration_seconds{engine_id="engine_distressed_asset_debt_stress",stage="commit"}`

### 3.4 Resource Metrics

- CPU utilization (app + db)
- Memory usage (RSS + heap if available)
- Disk IOPS and latency
- DB connections in use

## 4. Alerting Thresholds (Initial)

Tune thresholds after baseline benchmarks.

| Metric | Warning | Critical | Notes |
| --- | --- | --- | --- |
| API p99 latency | > 1500 ms | > 3000 ms | `POST /run` |
| Error rate | > 1% | > 5% | 5xx responses |
| DB commit latency | > 500 ms | > 1500 ms | Evidence writes |
| Modeling duration | > 2x baseline | > 3x baseline | Per scenario batch |
| CPU | > 80% | > 90% | sustained 5 min |
| Memory | > 80% | > 90% | sustained 5 min |

## 5. Error Monitoring

- Capture and classify 4xx vs 5xx errors.
- Track failures by category:
  - `DATASET_VERSION_ID_INVALID`
  - `NORMALIZED_RECORD_REQUIRED`
  - `IMMUTABLE_*` conflicts
- Alert on spikes in error categories.

## 6. Audit Logging

- Log all engine runs with:
  - `dataset_version_id`
  - `started_at`
  - scenario configuration
- Persist finding/evidence creation events with immutable IDs.
- Retain logs per compliance policy (minimum 1 year or regulatory requirement).
- Store audit logs in append-only storage with access controls.

## 7. Security Monitoring

- Alert on failed auth attempts or RBAC violations.
- Monitor API tokens and anomalous usage patterns.
- Track unexpected spikes in inbound or outbound traffic.

## 8. Availability & Uptime

- Track uptime for:
  - API gateway
  - Engine run endpoint
  - Database connectivity
- Measure mean time to recovery (MTTR) for failover events.

## 9. Compliance Monitoring

- Validate dataset version lineage in every engine run.
- Track evidence and findings counts by dataset version.
- Schedule automated checks for regulatory reporting payloads.

## 10. Status Page Template

Use `docs/engines/enterprise_distressed_asset_debt_stress_status_page.md` to publish status for:

- API availability
- Modeling performance
- Evidence linking health
- Compliance job status

## 11. Production Integration Checklist

- [ ] Prometheus scraping configured for app + DB exporters.
- [ ] Grafana dashboards deployed with engine-specific panels.
- [ ] Alert routes configured (PagerDuty/Slack).
- [ ] Log retention configured in centralized log store.
- [ ] Health check script wired into uptime probes.
- [ ] Failover tests scheduled quarterly.
