from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.models.base import Base


class RegulatoryControl(Base):
    __tablename__ = "regulatory_controls"

    control_record_id: Mapped[str] = mapped_column(String, primary_key=True)
    dataset_version_id: Mapped[str] = mapped_column(
        String, ForeignKey("dataset_version.id"), nullable=False, index=True
    )
    control_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    risk_type: Mapped[str] = mapped_column(String, nullable=False)
    control_status: Mapped[str] = mapped_column(String, nullable=False)
    ownership: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    frameworks: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    evaluation: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RegulatoryGap(Base):
    __tablename__ = "regulatory_gaps"

    gap_id: Mapped[str] = mapped_column(String, primary_key=True)
    dataset_version_id: Mapped[str] = mapped_column(
        String, ForeignKey("dataset_version.id"), nullable=False, index=True
    )
    control_record_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    control_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    framework_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    framework_name: Mapped[str] = mapped_column(String, nullable=False)
    severity: Mapped[str] = mapped_column(String, nullable=False)
    alignment_score: Mapped[float] = mapped_column(Float, nullable=False)
    notes: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RegulatoryRemediationTask(Base):
    __tablename__ = "regulatory_remediation_tasks"

    task_id: Mapped[str] = mapped_column(String, primary_key=True)
    dataset_version_id: Mapped[str] = mapped_column(
        String, ForeignKey("dataset_version.id"), nullable=False, index=True
    )
    gap_id: Mapped[str] = mapped_column(String, ForeignKey("regulatory_gaps.gap_id"), nullable=False, index=True)
    control_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    description: Mapped[str] = mapped_column(String, nullable=False)
    owner: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
