from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.workflows.models import WorkflowSetting


async def get_workflow_setting(db: AsyncSession, *, workflow_id: str) -> WorkflowSetting | None:
    return await db.scalar(select(WorkflowSetting).where(WorkflowSetting.workflow_id == workflow_id))


async def resolve_strict_mode(
    db: AsyncSession,
    *,
    workflow_id: str,
    override: bool | None = None,
    default_strict: bool = True,
) -> bool:
    if override is not None:
        return override
    existing = await get_workflow_setting(db, workflow_id=workflow_id)
    if existing is None:
        return default_strict
    return bool(existing.strict_mode)


async def set_workflow_strict_mode(db: AsyncSession, *, workflow_id: str, strict_mode: bool) -> WorkflowSetting:
    now = datetime.now(timezone.utc)
    existing = await get_workflow_setting(db, workflow_id=workflow_id)
    if existing is None:
        record = WorkflowSetting(workflow_id=workflow_id, strict_mode=strict_mode, updated_at=now)
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return record
    existing.strict_mode = strict_mode
    existing.updated_at = now
    await db.commit()
    await db.refresh(existing)
    return existing
