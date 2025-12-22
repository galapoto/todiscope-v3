# Enterprise Distressed Asset & Debt Stress Engine — Performance Benchmarks

## 1. Scope

This report defines the benchmarking plan and capture format for production-grade performance validation. It covers:

- Data ingestion + normalization throughput.
- Stress scenario modeling CPU/memory behavior.
- API response time under concurrency.
- Persistence and transaction latency for evidence and findings.
- Evidence linking scalability.
- Load testing at high concurrency.
- Fault tolerance and failover behavior.

## 2. Test Environment (Fill Before Run)

- **Environment:** dev / staging / production
- **Region / AZ:** TBD
- **Host specs:** CPU / RAM / disk
- **Database:** engine + version + instance class
- **Application version:** git SHA
- **Dataset version(s):** IDs used in tests

## 3. Benchmark Tooling

Scripts (see `backend/benchmarks/distressed_asset_debt_stress/`):

- `bench_ingestion.py`
- `bench_stress_modeling.py`
- `bench_api.py`
- `bench_persistence.py`
- `health_check.py`

## 4. Data Ingestion Performance

### 4.1 Method

- Ingest datasets at sizes: 10^2, 10^3, 10^4, 10^5.
- Toggle normalization on/off.
- Repeat for multiple DatasetVersions to capture versioning overhead.

### 4.2 Results (Populate)

| Dataset Size | Normalize | Version | Duration (ms) | Records Written | Max RSS (KB) |
| --- | --- | --- | --- | --- | --- |
| TBD | TBD | TBD | TBD | TBD | TBD |

### 4.3 Notes

- Identify inflection points where throughput degrades.
- Record any dataset version creation latency outliers.

## 5. Stress Test Modeling Performance

### 5.1 Method

- Run scenario modeling with increasing instrument counts and distressed assets.
- Capture CPU time, wall time, max RSS, and peak allocations.

### 5.2 Results (Populate)

| Instruments | Distressed Assets | Scenarios | Iterations | Duration (ms) | CPU (ms) | Max RSS (KB) |
| --- | --- | --- | --- | --- | --- | --- |
| TBD | TBD | TBD | TBD | TBD | TBD | TBD |

### 5.3 Notes

- Capture any spikes in memory usage for large instrument sets.

## 6. API Response Time

### 6.1 Method

- Target endpoint: `POST /api/v3/engines/distressed-asset-debt-stress/run`
- Payload uses DatasetVersion with normalized records.
- Concurrency levels: 1, 10, 50, 100, 500, 1000.

### 6.2 Results (Populate)

| Concurrency | Requests | P50 (ms) | P90 (ms) | P99 (ms) | Throughput (rps) | Errors |
| --- | --- | --- | --- | --- | --- | --- |
| TBD | TBD | TBD | TBD | TBD | TBD | TBD |

## 7. Persistence Layer Performance

### 7.1 Method

- Measure evidence + finding + link creation.
- Record commit latency and read latency after inserts.

### 7.2 Results (Populate)

| Count | RawRecord (ms) | Evidence (ms) | Finding (ms) | Link (ms) | Commit (ms) | Read (ms) |
| --- | --- | --- | --- | --- | --- | --- |
| TBD | TBD | TBD | TBD | TBD | TBD | TBD |

## 8. Evidence Linking & Traceability Performance

### 8.1 Method

- Create 10^2 to 10^5 findings + evidence links.
- Track linking throughput and read latency for trace queries.

### 8.2 Results (Populate)

| Links | Link Duration (ms) | Links/sec | Read Latency (ms) |
| --- | --- | --- | --- |
| TBD | TBD | TBD | TBD |

## 9. Load Testing (High Concurrency)

### 9.1 Method

- Simulate 1000 concurrent users running stress scenarios.
- Capture throughput and tail latency.
- Track CPU, memory, and DB connections.

### 9.2 Results (Populate)

| Concurrent Users | RPS | P99 (ms) | Error Rate | CPU % | Memory % | DB Connections |
| --- | --- | --- | --- | --- | --- | --- |
| TBD | TBD | TBD | TBD | TBD | TBD | TBD |

## 10. Fault Tolerance & Failover Testing

### 10.1 Method

- Simulate DB outage (read/write failure).
- Simulate network partition to DB.
- Validate retry/rollback behavior and recovery time.

### 10.2 Results (Populate)

| Failure Mode | Recovery Time (s) | Data Loss | Notes |
| --- | --- | --- | --- |
| TBD | TBD | TBD | TBD |

## 11. Scalability Graphs

Attach charts generated from JSON output of the benchmark scripts:

- Throughput vs. concurrency.
- Latency percentiles vs. concurrency.
- Ingestion time vs. dataset size.
- Evidence linking time vs. link volume.

## 12. Recommendations

Populate after results are collected.

- **Ingestion:** TBD (batch size, normalization optimizations, IO parallelism).
- **Modeling:** TBD (vectorized calculations, caching).
- **API:** TBD (async worker tuning, connection pooling).
- **Persistence:** TBD (bulk inserts, index review).
- **Evidence linking:** TBD (batch linking, index coverage).
- **Failover:** TBD (retry policy, circuit breakers).

## 13. DevOps Review Checklist

- [ ] Benchmark outputs stored and versioned.
- [ ] Results reviewed with SLO targets.
- [ ] Load tests validated in staging.
- [ ] Failover tests validated.
- [ ] Findings and remediation actions captured.
