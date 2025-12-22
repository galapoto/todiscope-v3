from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.evidence.models import EvidenceRecord, FindingEvidenceLink, FindingRecord


def deterministic_evidence_id(*, dataset_version_id: str, engine_id: str, kind: str, stable_key: str) -> str:
    namespace = uuid.UUID("00000000-0000-0000-0000-000000000042")
    return str(uuid.uuid5(namespace, f"{dataset_version_id}|{engine_id}|{kind}|{stable_key}"))


async def create_evidence(
    db: AsyncSession,
    *,
    evidence_id: str,
    dataset_version_id: str,
    engine_id: str,
    kind: str,
    payload: dict,
    created_at: datetime,
) -> EvidenceRecord:
    existing = await db.scalar(select(EvidenceRecord).where(EvidenceRecord.evidence_id == evidence_id))
    if existing is not None:
        return existing

    rec = EvidenceRecord(
        evidence_id=evidence_id,
        dataset_version_id=dataset_version_id,
        engine_id=engine_id,
        kind=kind,
        payload=payload,
        created_at=created_at,
    )
    db.add(rec)
    await db.flush()
    return rec


async def create_finding(
    db: AsyncSession,
    *,
    finding_id: str,
    dataset_version_id: str,
    raw_record_id: str,
    kind: str,
    payload: dict,
    created_at: datetime,
) -> FindingRecord:
    existing = await db.scalar(select(FindingRecord).where(FindingRecord.finding_id == finding_id))
    if existing is not None:
        return existing
    rec = FindingRecord(
        finding_id=finding_id,
        dataset_version_id=dataset_version_id,
        raw_record_id=raw_record_id,
        kind=kind,
        payload=payload,
        created_at=created_at,
    )
    db.add(rec)
    await db.flush()
    return rec


async def link_finding_to_evidence(
    db: AsyncSession, *, link_id: str, finding_id: str, evidence_id: str
) -> FindingEvidenceLink:
    existing = await db.scalar(select(FindingEvidenceLink).where(FindingEvidenceLink.link_id == link_id))
    if existing is not None:
        return existing
    rec = FindingEvidenceLink(link_id=link_id, finding_id=finding_id, evidence_id=evidence_id)
    db.add(rec)
    await db.flush()
    return rec
