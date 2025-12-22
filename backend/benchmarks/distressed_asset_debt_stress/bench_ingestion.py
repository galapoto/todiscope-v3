from __future__ import annotations

import argparse
import asyncio
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import resource
import time
from typing import Iterable

from backend.app.core.ingestion.service import ingest_records
from backend.app.core.db import get_sessionmaker


@dataclass(frozen=True)
class IngestionResult:
    size: int
    normalize: bool
    version_index: int
    duration_ms: float
    records_written: int
    dataset_version_id: str
    max_rss_kb: int


def _parse_sizes(value: str) -> list[int]:
    sizes: list[int] = []
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        sizes.append(int(item))
    if not sizes:
        raise ValueError("At least one size is required.")
    return sizes


def _build_record(index: int, currencies: Iterable[str]) -> dict:
    currency_list = list(currencies)
    currency = currency_list[index % len(currency_list)] if currency_list else "USD"
    base = 100000 + (index % 1000) * 125
    return {
        "source_system": "benchmark",
        "source_record_id": f"distressed-bench-{index}",
        "financial": {
            "debt": {
                "total_outstanding": base * 1.25,
                "interest_rate_pct": 4.2 + (index % 7) * 0.15,
                "collateral_value": base * 0.7,
                "instruments": [
                    {
                        "principal": base,
                        "interest_rate_pct": 4.1 + (index % 5) * 0.2,
                        "collateral_value": base * 0.6,
                        "currency": currency,
                    },
                    {
                        "principal": base * 0.25,
                        "interest_rate_pct": 4.8 + (index % 3) * 0.1,
                        "collateral_value": base * 0.1,
                        "currency": currency,
                    },
                ],
            },
            "assets": {"total": base * 4.5},
        },
        "distressed_assets": [
            {"name": "asset-a", "value": base * 0.4, "recovery_rate_pct": 45},
            {"name": "asset-b", "value": base * 0.2, "recovery_rate_pct": 35},
        ],
        "intercompany": {
            "balances": [
                {"counterparty": "holdco", "amount": base * 0.15, "currency": currency},
                {"counterparty": "subco", "amount": base * 0.08, "currency": currency},
            ]
        },
        "currency": currency,
        "as_of": datetime.now(timezone.utc).isoformat(),
    }


async def _run_ingestion(
    *,
    size: int,
    normalize: bool,
    version_index: int,
    currencies: Iterable[str],
) -> IngestionResult:
    sessionmaker = get_sessionmaker()
    records = [_build_record(i, currencies) for i in range(size)]
    start = time.perf_counter()
    async with sessionmaker() as db:
        dataset_version_id, written = await ingest_records(db, records=records, normalize=normalize)
    duration_ms = (time.perf_counter() - start) * 1000
    max_rss_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return IngestionResult(
        size=size,
        normalize=normalize,
        version_index=version_index,
        duration_ms=duration_ms,
        records_written=written,
        dataset_version_id=dataset_version_id,
        max_rss_kb=max_rss_kb,
    )


async def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark data ingestion for distressed asset engine.")
    parser.add_argument("--sizes", default="100,1000,10000", help="Comma-delimited record sizes.")
    parser.add_argument("--versions", type=int, default=3, help="Number of dataset versions to ingest.")
    parser.add_argument("--normalize", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--currencies", default="USD,EUR,GBP,JPY", help="Comma-delimited currencies.")
    parser.add_argument("--output", default="", help="Optional path to write JSON output.")
    args = parser.parse_args()

    sizes = _parse_sizes(args.sizes)
    currencies = [item.strip() for item in args.currencies.split(",") if item.strip()]
    results: list[IngestionResult] = []
    for version_index in range(1, args.versions + 1):
        for size in sizes:
            result = await _run_ingestion(
                size=size,
                normalize=args.normalize,
                version_index=version_index,
                currencies=currencies,
            )
            results.append(result)

    payload = [asdict(result) for result in results]
    serialized = json.dumps(payload, indent=2, sort_keys=True)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(serialized)
    else:
        print(serialized)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
