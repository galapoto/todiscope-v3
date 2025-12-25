from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.models.base import Base


class RawRecord(Base):
    __tablename__ = "raw_record"

    raw_record_id: Mapped[str] = mapped_column(String, primary_key=True)
    dataset_version_id: Mapped[str] = mapped_column(
        String, ForeignKey("dataset_version.id"), nullable=False, index=True
    )
    source_system: Mapped[str] = mapped_column(String, nullable=False)
    source_record_id: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    file_checksum: Mapped[str | None] = mapped_column(String, nullable=True)
    legacy_no_checksum: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
