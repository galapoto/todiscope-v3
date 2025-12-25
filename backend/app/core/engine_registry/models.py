from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.models.base import Base


class EngineRegistryEntry(Base):
    __tablename__ = "engine_registry_entry"

    engine_id: Mapped[str] = mapped_column(String, primary_key=True)
    engine_version: Mapped[str | None] = mapped_column(String, nullable=True)
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
