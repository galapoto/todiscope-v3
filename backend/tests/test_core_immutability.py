from __future__ import annotations

from datetime import datetime, timezone
import uuid

import pytest
from sqlalchemy import select

from backend.app.core.dataset.immutability import ImmutableViolation, install_immutability_guards
from backend.app.core.dataset.raw_models import RawRecord
from backend.app.core.dataset.service import create_dataset_version_via_ingestion
from backend.app.core.db import get_sessionmaker
from backend.app.core.evidence.service import create_evidence, create_finding, link_finding_to_evidence
from backend.app.core.evidence.models import FindingEvidenceLink


@pytest.mark.anyio
async def test_core_records_are_immutable(sqlite_db: None) -> None:
    install_immutability_guards()
    now = datetime.now(timezone.utc)

    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)
        raw_id = str(uuid.uuid4())
        db.add(
            RawRecord(
                raw_record_id=raw_id,
                dataset_version_id=dv.id,
                source_system="sys",
                source_record_id="r1",
                payload={"source_system": "sys", "source_record_id": "r1"},
                ingested_at=now,
            )
        )
        await db.commit()

    async with get_sessionmaker()() as db2:
        rec = await db2.scalar(select(RawRecord).where(RawRecord.raw_record_id == raw_id))
        assert rec is not None
        rec.source_system = "sys2"
        with pytest.raises(ImmutableViolation):
            await db2.commit()


@pytest.mark.anyio
async def test_finding_links_to_source_and_evidence(sqlite_db: None) -> None:
    install_immutability_guards()
    now = datetime.now(timezone.utc)

    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)
        raw_id = str(uuid.uuid4())
        db.add(
            RawRecord(
                raw_record_id=raw_id,
                dataset_version_id=dv.id,
                source_system="sys",
                source_record_id="r1",
                payload={"source_system": "sys", "source_record_id": "r1"},
                ingested_at=now,
            )
        )
        await db.commit()

        ev = await create_evidence(
            db,
            evidence_id=str(uuid.uuid4()),
            dataset_version_id=dv.id,
            engine_id="core",
            kind="source",
            payload={"raw_record_id": raw_id},
            created_at=now,
        )
        finding = await create_finding(
            db,
            finding_id=str(uuid.uuid4()),
            dataset_version_id=dv.id,
            raw_record_id=raw_id,
            kind="generic",
            payload={"note": "x"},
            created_at=now,
        )
        link_id = str(uuid.uuid4())
        await link_finding_to_evidence(db, link_id=link_id, finding_id=finding.finding_id, evidence_id=ev.evidence_id)
        await db.commit()

    async with get_sessionmaker()() as db2:
        link = await db2.scalar(select(FindingEvidenceLink).where(FindingEvidenceLink.link_id == link_id))
        assert link is not None
        assert link.finding_id == finding.finding_id
        assert link.evidence_id == ev.evidence_id

