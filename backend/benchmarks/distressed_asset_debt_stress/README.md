# Distressed Asset & Debt Stress Engine Benchmarks

This folder contains repeatable benchmark scripts for data ingestion, stress modeling, API latency, and persistence.

## Quick Start

1. Ensure the backend is configured with `TODISCOPE_DATABASE_URL`.
2. Run ingestion to generate dataset versions with normalized records.
3. Use the dataset version id(s) for API and stress testing benchmarks.

## Scripts

- `bench_ingestion.py` - Measures ingest + normalization latency across dataset sizes and versions.
- `bench_stress_modeling.py` - Measures CPU and memory for stress scenario calculations.
- `bench_api.py` - Measures API latency and throughput under concurrent load.
- `bench_persistence.py` - Measures ORM persistence and evidence linking latency.
- `health_check.py` - Automated health checks for API + DB + evidence linking.

## Example Runs

```bash
python backend/benchmarks/distressed_asset_debt_stress/bench_ingestion.py --sizes 100,1000 --versions 2 --output /tmp/ingestion.json
python backend/benchmarks/distressed_asset_debt_stress/bench_stress_modeling.py --instruments 5000 --distressed-assets 1000 --scenarios 9 --iterations 20
python backend/benchmarks/distressed_asset_debt_stress/bench_persistence.py --count 2000 --output /tmp/persistence.json
python backend/benchmarks/distressed_asset_debt_stress/bench_api.py --dataset-version-id <dv_id> --requests 500 --concurrency 50 --output /tmp/api.json
python backend/benchmarks/distressed_asset_debt_stress/health_check.py --dataset-version-id <dv_id>
```

## Output

All scripts emit JSON to stdout (or `--output`). Use this output to build latency/throughput graphs and to populate
the performance report.
