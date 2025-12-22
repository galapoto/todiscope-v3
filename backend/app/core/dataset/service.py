from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.dataset.models import DatasetVersion
from backend.app.core.dataset.uuidv7 import uuid7


async def create_dataset_version_via_ingestion(db: AsyncSession) -> DatasetVersion:
    dv = DatasetVersion(id=str(uuid7()))
    db.add(dv)
    await db.commit()
    await db.refresh(dv)
    return dv

