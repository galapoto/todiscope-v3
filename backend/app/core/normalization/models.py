from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.models.base import Base


class NormalizedRecord(Base):
    __tablename__ = "normalized_record"

    normalized_record_id: Mapped[str] = mapped_column(String, primary_key=True)
    dataset_version_id: Mapped[str] = mapped_column(
        String, ForeignKey("dataset_version.id"), nullable=False, index=True
    )
    raw_record_id: Mapped[str] = mapped_column(
        String, ForeignKey("raw_record.raw_record_id"), nullable=False, index=True
    )
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    normalized_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

