from __future__ import annotations

from datetime import datetime, timezone
import uuid

import pytest
from sqlalchemy import select

from backend.app.core.dataset.raw_models import RawRecord
from backend.app.core.dataset.service import create_dataset_version_via_ingestion
from backend.app.core.db import get_sessionmaker
from backend.app.core.evidence.models import EvidenceRecord, FindingEvidenceLink, FindingRecord
from backend.app.engines.construction_cost_intelligence.run import run_engine


@pytest.mark.anyio
async def test_core_run_persists_assumptions_evidence_and_links(sqlite_db: None) -> None:
    now = datetime.now(timezone.utc)

    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)
        boq_raw_id = str(uuid.uuid4())
        actual_raw_id = str(uuid.uuid4())
        db.add(
            RawRecord(
                raw_record_id=boq_raw_id,
                dataset_version_id=dv.id,
                source_system="test",
                source_record_id="boq",
                payload={
                    "lines": [
                        {"id": "b1", "item": "A", "total": "10", "category": "labor"},
                        {"id": "b2", "item": "B", "total": "", "category": "materials"},  # incomplete cost
                    ]
                },
                ingested_at=now,
            )
        )
        db.add(
            RawRecord(
                raw_record_id=actual_raw_id,
                dataset_version_id=dv.id,
                source_system="test",
                source_record_id="actual",
                payload={
                    "lines": [
                        {"id": "a1", "item": "A", "total": "12", "category": "labor"},
                        {"id": "a3", "item": "C", "total": "5", "category": "materials"},  # unmatched actual
                    ]
                },
                ingested_at=now,
            )
        )
        await db.commit()

    res = await run_engine(
        dataset_version_id=dv.id,
        started_at=now.isoformat(),
        boq_raw_record_id=boq_raw_id,
        actual_raw_record_id=actual_raw_id,
        normalization_mapping={
            "line_id": "id",
            "identity": {"item_code": "item"},
            "total_cost": "total",
            "extras": ["category"],
        },
        comparison_config={
            "identity_fields": ["item_code"],
            "cost_basis": "prefer_total_cost",
            "breakdown_fields": ["category"],
        },
    )

    assert res["dataset_version_id"] == dv.id
    assert res["traceability"]["assumptions_evidence_id"]
    assert len(res["traceability"]["inputs_evidence_ids"]) == 2
    assert len(res["traceability"]["finding_ids"]) >= 2  # incomplete + unmatched_actual
    assert isinstance(res["assumptions"], list) and res["assumptions"]

    assumptions_evidence_id = res["traceability"]["assumptions_evidence_id"]
    finding_ids = res["traceability"]["finding_ids"]

    async with get_sessionmaker()() as db2:
        assumptions_ev = await db2.scalar(select(EvidenceRecord).where(EvidenceRecord.evidence_id == assumptions_evidence_id))
        assert assumptions_ev is not None
        assert assumptions_ev.dataset_version_id == dv.id
        assert assumptions_ev.kind == "assumptions"

        for fid in finding_ids:
            finding = await db2.scalar(select(FindingRecord).where(FindingRecord.finding_id == fid))
            assert finding is not None
            assert finding.dataset_version_id == dv.id
            link_rows = (
                await db2.execute(select(FindingEvidenceLink).where(FindingEvidenceLink.finding_id == fid))
            ).scalars().all()
            assert link_rows, "finding must be linked to evidence"
            linked_evidence_ids = {ln.evidence_id for ln in link_rows}
            assert assumptions_evidence_id in linked_evidence_ids

