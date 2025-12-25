from __future__ import annotations

import argparse
import asyncio
from dataclasses import asdict, dataclass
import json
import statistics
import time

import httpx


@dataclass(frozen=True)
class RequestResult:
    latency_ms: float
    status_code: int | None
    error: str | None


@dataclass(frozen=True)
class Summary:
    total_requests: int
    success_requests: int
    error_requests: int
    duration_ms: float
    throughput_rps: float
    p50_ms: float
    p90_ms: float
    p99_ms: float


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    if pct <= 0:
        return values[0]
    if pct >= 100:
        return values[-1]
    k = (len(values) - 1) * (pct / 100.0)
    lower = int(k)
    upper = min(lower + 1, len(values) - 1)
    if lower == upper:
        return values[lower]
    weight = k - lower
    return values[lower] * (1 - weight) + values[upper] * weight


async def _send_request(
    client: httpx.AsyncClient,
    sem: asyncio.Semaphore,
    url: str,
    payload: dict,
) -> RequestResult:
    async with sem:
        start = time.perf_counter()
        try:
            response = await client.post(url, json=payload)
            latency_ms = (time.perf_counter() - start) * 1000
            return RequestResult(latency_ms=latency_ms, status_code=response.status_code, error=None)
        except Exception as exc:  # pragma: no cover - bench-only path
            latency_ms = (time.perf_counter() - start) * 1000
            return RequestResult(latency_ms=latency_ms, status_code=None, error=str(exc))


async def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark API response times for distressed asset engine.")
    parser.add_argument("--base-url", default="http://localhost:8400")
    parser.add_argument("--endpoint", default="/api/v3/engines/distressed-asset-debt-stress/run")
    parser.add_argument("--dataset-version-id", required=True)
    parser.add_argument("--started-at", default="", help="ISO timestamp; defaults to now.")
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--parameters", default="", help="Optional JSON file for parameters payload.")
    parser.add_argument("--output", default="", help="Optional path to write JSON output.")
    args = parser.parse_args()

    parameters: dict = {}
    if args.parameters:
        with open(args.parameters, "r", encoding="utf-8") as handle:
            parameters = json.load(handle)

    started_at = args.started_at or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    payload = {
        "dataset_version_id": args.dataset_version_id,
        "started_at": started_at,
        "parameters": parameters,
    }

    url = args.base_url.rstrip("/") + args.endpoint
    sem = asyncio.Semaphore(args.concurrency)

    async with httpx.AsyncClient(timeout=60.0) as client:
        for _ in range(args.warmup):
            await client.post(url, json=payload)

        start = time.perf_counter()
        tasks = [
            asyncio.create_task(_send_request(client, sem, url, payload)) for _ in range(args.requests)
        ]
        results = await asyncio.gather(*tasks)
        duration_ms = (time.perf_counter() - start) * 1000

    latencies = sorted(result.latency_ms for result in results)
    success = sum(1 for result in results if result.status_code and result.status_code < 400)
    errors = len(results) - success
    summary = Summary(
        total_requests=len(results),
        success_requests=success,
        error_requests=errors,
        duration_ms=duration_ms,
        throughput_rps=(len(results) / duration_ms) * 1000 if duration_ms else 0.0,
        p50_ms=_percentile(latencies, 50),
        p90_ms=_percentile(latencies, 90),
        p99_ms=_percentile(latencies, 99),
    )

    output = {
        "summary": asdict(summary),
        "requests": [asdict(result) for result in results],
    }
    serialized = json.dumps(output, indent=2, sort_keys=True)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(serialized)
    else:
        print(serialized)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
