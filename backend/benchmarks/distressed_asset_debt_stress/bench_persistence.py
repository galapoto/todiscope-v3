from __future__ import annotations

import argparse
import asyncio
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import time
import uuid

from sqlalchemy import func, select

from backend.app.core.dataset.raw_models import RawRecord
from backend.app.core.dataset.service import create_dataset_version_via_ingestion
from backend.app.core.db import get_sessionmaker
from backend.app.core.evidence.models import EvidenceRecord, FindingEvidenceLink, FindingRecord
from backend.app.core.evidence.service import create_evidence, create_finding, deterministic_evidence_id, link_finding_to_evidence
from backend.app.engines.enterprise_distressed_asset_debt_stress.constants import ENGINE_ID
from backend.app.engines.enterprise_distressed_asset_debt_stress.ids import deterministic_id


@dataclass(frozen=True)
class PersistenceResult:
    count: int
    raw_record_ms: float
    evidence_ms: float
    finding_ms: float
    link_ms: float
    commit_ms: float
    read_latency_ms: float


async def _create_dataset_version_id() -> str:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        dv = await create_dataset_version_via_ingestion(db)
        return dv.id


async def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark persistence and evidence linking.")
    parser.add_argument("--count", type=int, default=1000, help="Number of findings/evidence to create.")
    parser.add_argument("--output", default="", help="Optional path to write JSON output.")
    args = parser.parse_args()

    dataset_version_id = await _create_dataset_version_id()
    sessionmaker = get_sessionmaker()
    now = datetime.now(timezone.utc)

    raw_record_ids: list[str] = []
    async with sessionmaker() as db:
        start = time.perf_counter()
        for idx in range(args.count):
            raw_id = str(uuid.uuid4())
            raw_record_ids.append(raw_id)
            db.add(
                RawRecord(
                    raw_record_id=raw_id,
                    dataset_version_id=dataset_version_id,
                    source_system="benchmark",
                    source_record_id=f"bench-{idx}",
                    payload={"index": idx},
                    ingested_at=now,
                )
            )
        await db.commit()
        raw_record_ms = (time.perf_counter() - start) * 1000

    async with sessionmaker() as db:
        evidence_ids: list[str] = []
        start = time.perf_counter()
        for idx in range(args.count):
            evidence_id = deterministic_evidence_id(
                dataset_version_id=dataset_version_id,
                engine_id=ENGINE_ID,
                kind="benchmark",
                stable_key=str(idx),
            )
            evidence_ids.append(evidence_id)
            await create_evidence(
                db=db,
                evidence_id=evidence_id,
                dataset_version_id=dataset_version_id,
                engine_id=ENGINE_ID,
                kind="benchmark",
                payload={"index": idx},
                created_at=now,
            )
        evidence_ms = (time.perf_counter() - start) * 1000

        start = time.perf_counter()
        finding_ids: list[str] = []
        for idx, raw_id in enumerate(raw_record_ids):
            finding_id = deterministic_id(dataset_version_id, "finding", f"bench:{idx}")
            finding_ids.append(finding_id)
            await create_finding(
                db=db,
                finding_id=finding_id,
                dataset_version_id=dataset_version_id,
                raw_record_id=raw_id,
                kind="benchmark",
                payload={"index": idx},
                created_at=now,
            )
        finding_ms = (time.perf_counter() - start) * 1000

        start = time.perf_counter()
        for idx, finding_id in enumerate(finding_ids):
            evidence_id = evidence_ids[idx]
            link_id = deterministic_id(dataset_version_id, "link", finding_id, evidence_id)
            await link_finding_to_evidence(db, link_id=link_id, finding_id=finding_id, evidence_id=evidence_id)
        link_ms = (time.perf_counter() - start) * 1000

        start_commit = time.perf_counter()
        await db.commit()
        commit_ms = (time.perf_counter() - start_commit) * 1000

        start_read = time.perf_counter()
        await db.scalar(select(func.count(EvidenceRecord.evidence_id)))
        await db.scalar(select(func.count(FindingRecord.finding_id)))
        await db.scalar(select(func.count(FindingEvidenceLink.link_id)))
        read_latency_ms = (time.perf_counter() - start_read) * 1000

    result = PersistenceResult(
        count=args.count,
        raw_record_ms=raw_record_ms,
        evidence_ms=evidence_ms,
        finding_ms=finding_ms,
        link_ms=link_ms,
        commit_ms=commit_ms,
        read_latency_ms=read_latency_ms,
    )
    serialized = json.dumps(asdict(result), indent=2, sort_keys=True)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(serialized)
    else:
        print(serialized)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
