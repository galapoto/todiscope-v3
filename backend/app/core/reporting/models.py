from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.models.base import Base


class ReportArtifact(Base):
    __tablename__ = "report_artifact"

    report_id: Mapped[str] = mapped_column(String, primary_key=True)
    dataset_version_id: Mapped[str] = mapped_column(
        String, ForeignKey("dataset_version.id"), nullable=False, index=True
    )
    calculation_run_id: Mapped[str] = mapped_column(
        String, ForeignKey("calculation_run.run_id"), nullable=False, index=True
    )
    engine_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    report_kind: Mapped[str] = mapped_column(String, nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
