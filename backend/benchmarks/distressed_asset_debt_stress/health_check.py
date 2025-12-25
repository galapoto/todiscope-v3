from __future__ import annotations

import argparse
import asyncio
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import time

import httpx
from sqlalchemy import select

from backend.app.core.db import get_sessionmaker
from backend.app.core.dataset.models import DatasetVersion
from backend.app.core.evidence.models import EvidenceRecord, FindingEvidenceLink, FindingRecord


@dataclass(frozen=True)
class HealthCheckResult:
    label: str
    ok: bool
    latency_ms: float
    detail: str | None


async def _check_db() -> list[HealthCheckResult]:
    sessionmaker = get_sessionmaker()
    results: list[HealthCheckResult] = []
    async with sessionmaker() as db:
        start = time.perf_counter()
        try:
            await db.scalar(select(DatasetVersion.id).limit(1))
            latency_ms = (time.perf_counter() - start) * 1000
            results.append(HealthCheckResult(label="db_connectivity", ok=True, latency_ms=latency_ms, detail=None))
        except Exception as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            results.append(
                HealthCheckResult(label="db_connectivity", ok=False, latency_ms=latency_ms, detail=str(exc))
            )

        start = time.perf_counter()
        try:
            await db.scalar(select(EvidenceRecord.evidence_id).limit(1))
            await db.scalar(select(FindingRecord.finding_id).limit(1))
            await db.scalar(select(FindingEvidenceLink.link_id).limit(1))
            latency_ms = (time.perf_counter() - start) * 1000
            results.append(HealthCheckResult(label="evidence_linking", ok=True, latency_ms=latency_ms, detail=None))
        except Exception as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            results.append(HealthCheckResult(label="evidence_linking", ok=False, latency_ms=latency_ms, detail=str(exc)))
    return results


async def _check_http(client: httpx.AsyncClient, label: str, method: str, url: str, payload: dict | None) -> HealthCheckResult:
    start = time.perf_counter()
    try:
        if method == "POST":
            response = await client.post(url, json=payload)
        else:
            response = await client.get(url)
        latency_ms = (time.perf_counter() - start) * 1000
        ok = response.status_code < 400
        return HealthCheckResult(
            label=label,
            ok=ok,
            latency_ms=latency_ms,
            detail=None if ok else f"HTTP {response.status_code}",
        )
    except Exception as exc:  # pragma: no cover - bench-only path
        latency_ms = (time.perf_counter() - start) * 1000
        return HealthCheckResult(label=label, ok=False, latency_ms=latency_ms, detail=str(exc))


async def main() -> int:
    parser = argparse.ArgumentParser(description="Run health checks for distressed asset engine.")
    parser.add_argument("--base-url", default="http://localhost:8400")
    parser.add_argument("--dataset-version-id", default="", help="Optional dataset version for run check.")
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--output", default="", help="Optional path to write JSON output.")
    args = parser.parse_args()

    checks: list[HealthCheckResult] = []
    checks.extend(await _check_db())

    base = args.base_url.rstrip("/")
    async with httpx.AsyncClient(timeout=args.timeout) as client:
        checks.append(await _check_http(client, "api_health", "GET", f"{base}/health", None))
        checks.append(
            await _check_http(
                client,
                "engine_health",
                "GET",
                f"{base}/api/v3/engines/distressed-asset-debt-stress/health",
                None,
            )
        )
        if args.dataset_version_id:
            payload = {
                "dataset_version_id": args.dataset_version_id,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "parameters": {},
            }
            checks.append(
                await _check_http(
                    client,
                    "api_run",
                    "POST",
                    f"{base}/api/v3/engines/distressed-asset-debt-stress/run",
                    payload,
                )
            )

    output = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": [asdict(check) for check in checks],
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
