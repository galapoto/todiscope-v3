from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.models.base import Base


class Import(Base):
    __tablename__ = "import_record"

    import_id: Mapped[str] = mapped_column(String, primary_key=True)
    dataset_version_id: Mapped[str] = mapped_column(
        String, ForeignKey("dataset_version.id"), nullable=False, index=True
    )
    filename: Mapped[str | None] = mapped_column(String, nullable=True)
    content_type: Mapped[str | None] = mapped_column(String, nullable=True)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum_algorithm: Mapped[str] = mapped_column(String, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String, nullable=False)
    record_count: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_content: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    raw_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    quality_report: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
