from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.evidence import create_evidence, deterministic_evidence_id
from backend.app.core.review.models import ReviewEvent, ReviewItem


DEFAULT_REVIEW_STATE = "unreviewed"


def deterministic_review_item_id(*, dataset_version_id: str, engine_id: str, subject_type: str, subject_id: str) -> str:
    namespace = uuid.UUID("00000000-0000-0000-0000-000000000043")
    return str(uuid.uuid5(namespace, f"{dataset_version_id}|{engine_id}|{subject_type}|{subject_id}"))


def deterministic_review_event_id(*, review_item_id: str, stable_key: str) -> str:
    namespace = uuid.UUID("00000000-0000-0000-0000-000000000044")
    return str(uuid.uuid5(namespace, f"{review_item_id}|{stable_key}"))


async def ensure_review_item(
    db: AsyncSession,
    *,
    dataset_version_id: str,
    engine_id: str,
    subject_type: str,
    subject_id: str,
    created_at: datetime,
) -> ReviewItem:
    review_item_id = deterministic_review_item_id(
        dataset_version_id=dataset_version_id,
        engine_id=engine_id,
        subject_type=subject_type,
        subject_id=subject_id,
    )
    existing = await db.scalar(select(ReviewItem).where(ReviewItem.review_item_id == review_item_id))
    if existing is not None:
        return existing
    item = ReviewItem(
        review_item_id=review_item_id,
        dataset_version_id=dataset_version_id,
        engine_id=engine_id,
        subject_type=subject_type,
        subject_id=subject_id,
        state=DEFAULT_REVIEW_STATE,
        created_at=created_at,
    )
    db.add(item)
    await db.flush()
    return item


async def record_review_event(
    db: AsyncSession,
    *,
    dataset_version_id: str,
    engine_id: str,
    review_item_id: str,
    from_state: str,
    to_state: str,
    payload: dict,
    created_at: datetime,
    stable_key: str,
) -> ReviewEvent:
    evidence_id = deterministic_evidence_id(
        dataset_version_id=dataset_version_id,
        engine_id=engine_id,
        kind="review_event",
        stable_key=f"{review_item_id}|{stable_key}",
    )
    await create_evidence(
        db,
        evidence_id=evidence_id,
        dataset_version_id=dataset_version_id,
        engine_id=engine_id,
        kind="review_event",
        payload=payload,
        created_at=created_at,
    )

    review_event_id = deterministic_review_event_id(review_item_id=review_item_id, stable_key=stable_key)
    existing = await db.scalar(select(ReviewEvent).where(ReviewEvent.review_event_id == review_event_id))
    if existing is not None:
        return existing
    event = ReviewEvent(
        review_event_id=review_event_id,
        review_item_id=review_item_id,
        dataset_version_id=dataset_version_id,
        engine_id=engine_id,
        from_state=from_state,
        to_state=to_state,
        evidence_id=evidence_id,
        payload=payload,
        created_at=created_at,
    )
    db.add(event)
    await db.flush()
    return event

