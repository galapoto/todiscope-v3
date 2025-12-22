from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.review import DEFAULT_REVIEW_STATE, ensure_review_item
from backend.app.engines.financial_forensics.engine import ENGINE_ID


async def ensure_default_review_state(
    db: AsyncSession,
    *,
    dataset_version_id: str,
    finding_id: str,
    created_at: datetime,
) -> str:
    item = await ensure_review_item(
        db,
        dataset_version_id=dataset_version_id,
        engine_id=ENGINE_ID,
        subject_type="finding",
        subject_id=finding_id,
        created_at=created_at,
    )
    return item.state


__all__ = ["DEFAULT_REVIEW_STATE", "ensure_default_review_state"]

