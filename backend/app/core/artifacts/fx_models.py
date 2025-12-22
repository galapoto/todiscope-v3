from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.models.base import Base


class FxArtifact(Base):
    __tablename__ = "fx_artifacts"
    __table_args__ = (UniqueConstraint("dataset_version_id", "checksum", name="uq_fx_dataset_checksum"),)

    fx_artifact_id: Mapped[str] = mapped_column(String, primary_key=True)
    dataset_version_id: Mapped[str] = mapped_column(
        String, ForeignKey("dataset_version.id"), nullable=False, index=True
    )
    base_currency: Mapped[str] = mapped_column(String, nullable=False)
    effective_date: Mapped[str] = mapped_column(String, nullable=False)
    checksum: Mapped[str] = mapped_column(String, nullable=False, index=True)
    artifact_uri: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

