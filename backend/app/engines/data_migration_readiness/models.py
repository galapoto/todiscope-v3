from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.models.base import Base


class DataMigrationReadinessRun(Base):
    __tablename__ = "engine_data_migration_readiness_runs"

    run_id: Mapped[str] = mapped_column(String, primary_key=True)
    dataset_version_id: Mapped[str] = mapped_column(
        String, ForeignKey("dataset_version.id"), nullable=False, index=True
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, index=True)
    readiness_score: Mapped[float] = mapped_column(Float, nullable=False)
    readiness_level: Mapped[str] = mapped_column(String, nullable=False)
    component_scores: Mapped[dict] = mapped_column(JSON, nullable=False)
    remediation_tasks: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    source_systems: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    risk_count: Mapped[int] = mapped_column(Integer, nullable=False)
    engine_version: Mapped[str] = mapped_column(String, nullable=False)


class DataMigrationReadinessFinding(Base):
    __tablename__ = "engine_data_migration_readiness_findings"

    finding_id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[str] = mapped_column(
        String, ForeignKey("engine_data_migration_readiness_runs.run_id"), nullable=False, index=True
    )
    dataset_version_id: Mapped[str] = mapped_column(
        String, ForeignKey("dataset_version.id"), nullable=False, index=True
    )
    category: Mapped[str] = mapped_column(String, nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String, nullable=False, index=True)
    description: Mapped[str] = mapped_column(String, nullable=False)
    details: Mapped[dict] = mapped_column(JSON, nullable=False, name="metadata")
    evidence_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    engine_version: Mapped[str] = mapped_column(String, nullable=False)
