"""
Run model for Audit Readiness Engine
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.models.base import Base


class AuditReadinessRun(Base):
    """
    Engine-owned run table for audit readiness evaluations.
    
    Stores runtime parameters and evaluation scope for regulatory readiness checks.
    """
    __tablename__ = "audit_readiness_runs"

    run_id: Mapped[str] = mapped_column(String, primary_key=True)
    dataset_version_id: Mapped[str] = mapped_column(
        String, ForeignKey("dataset_version.id"), nullable=False, index=True
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    
    # Runtime parameters
    regulatory_frameworks: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    evaluation_scope: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    parameters: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    
    engine_version: Mapped[str] = mapped_column(String, nullable=False)

