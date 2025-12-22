"""Database models for the litigation/dispute engine."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import relationship

from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.models.base import Base


class EnterpriseLitigationDisputeRun(Base):
    __tablename__ = "engine_enterprise_litigation_dispute_runs"

    run_id: Mapped[str] = mapped_column(String, primary_key=True)
    dataset_version_id: Mapped[str] = mapped_column(
        String, ForeignKey("dataset_version.id"), nullable=False, index=True
    )
    run_start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    run_end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False)
    damage_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    liability_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    scenario_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    legal_consistency_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    assumptions: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    summary: Mapped[dict] = mapped_column(JSON, nullable=False)
    evidence_map: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False)
    findings: Mapped[list["EnterpriseLitigationDisputeFinding"]] = relationship(
        "EnterpriseLitigationDisputeFinding",
        back_populates="run",
        cascade="all, delete-orphan",
    )


class EnterpriseLitigationDisputeFinding(Base):
    __tablename__ = "engine_enterprise_litigation_dispute_findings"

    finding_id: Mapped[str] = mapped_column(String, primary_key=True)
    dataset_version_id: Mapped[str] = mapped_column(
        String, ForeignKey("dataset_version.id"), nullable=False, index=True
    )
    run_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("engine_enterprise_litigation_dispute_runs.run_id"),
        nullable=False,
        index=True,
    )
    category: Mapped[str] = mapped_column(String, nullable=False)
    metric: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[str] = mapped_column(String, nullable=False)
    evidence_ids: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    run: Mapped["EnterpriseLitigationDisputeRun"] = relationship(
        "EnterpriseLitigationDisputeRun", back_populates="findings"
    )
