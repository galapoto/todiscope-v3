from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.models.base import Base


class AiEventLog(Base):
    __tablename__ = "ai_event_log"

    event_id: Mapped[str] = mapped_column(String, primary_key=True)
    dataset_version_id: Mapped[str] = mapped_column(
        String, ForeignKey("dataset_version.id"), nullable=False, index=True
    )
    engine_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    model_identifier: Mapped[str] = mapped_column(String, nullable=False)
    model_version: Mapped[str] = mapped_column(String, nullable=True)
    context_id: Mapped[str] = mapped_column(String, nullable=True)
    event_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    event_label: Mapped[str] = mapped_column(String, nullable=True)
    inputs: Mapped[dict] = mapped_column(JSON, nullable=False)
    outputs: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    tool_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    rag_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    governance_metadata: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
