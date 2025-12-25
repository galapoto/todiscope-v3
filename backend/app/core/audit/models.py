"""
Core audit logging models.

Provides immutable audit logs for all platform actions (import, mapping, normalization,
calculation, reporting, workflow transitions).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.models.base import Base


class AuditLog(Base):
    """
    Immutable audit log for platform actions.
    
    Tracks who, what, when, and why for all platform actions.
    """

    __tablename__ = "audit_log"

    audit_log_id: Mapped[str] = mapped_column(String, primary_key=True)
    dataset_version_id: Mapped[str] = mapped_column(
        String, ForeignKey("dataset_version.id"), nullable=True, index=True
    )
    calculation_run_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    artifact_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    
    # Who performed the action
    actor_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    actor_type: Mapped[str] = mapped_column(String, nullable=False)  # "user", "system", "engine"
    
    # What action was performed
    action_type: Mapped[str] = mapped_column(String, nullable=False, index=True)  # "import", "normalization", "calculation", "reporting", "workflow"
    action_label: Mapped[str | None] = mapped_column(String, nullable=True)
    
    # When the action occurred
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    
    # Why the action was taken (contextual reasoning)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    context: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    
    # Additional metadata
    event_metadata: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict, name="metadata"
    )
    
    # Status and outcome
    status: Mapped[str] = mapped_column(String, nullable=False)  # "success", "failure", "warning"
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)




