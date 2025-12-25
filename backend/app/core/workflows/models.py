from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.models.base import Base


class WorkflowSetting(Base):
    __tablename__ = "workflow_setting"

    workflow_id: Mapped[str] = mapped_column(String, primary_key=True)
    strict_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class WorkflowState(Base):
    """
    Workflow state for subjects (findings, reports, calculations).
    
    Tracks state transitions: draft → review → approved → locked
    """

    __tablename__ = "workflow_state"

    workflow_state_id: Mapped[str] = mapped_column(String, primary_key=True)
    dataset_version_id: Mapped[str] = mapped_column(
        String, ForeignKey("dataset_version.id"), nullable=False, index=True
    )
    subject_type: Mapped[str] = mapped_column(String, nullable=False, index=True)  # "finding", "report", "calculation"
    subject_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    current_state: Mapped[str] = mapped_column(String, nullable=False)  # "draft", "review", "approved", "locked"
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[str | None] = mapped_column(String, nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String, nullable=True)


class WorkflowTransition(Base):
    __tablename__ = "workflow_transition"

    transition_id: Mapped[str] = mapped_column(String, primary_key=True)
    workflow_state_id: Mapped[str] = mapped_column(
        String, ForeignKey("workflow_state.workflow_state_id"), nullable=False, index=True
    )
    dataset_version_id: Mapped[str] = mapped_column(
        String, ForeignKey("dataset_version.id"), nullable=False, index=True
    )
    subject_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    subject_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    from_state: Mapped[str] = mapped_column(String, nullable=False)
    to_state: Mapped[str] = mapped_column(String, nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String, nullable=True)
    reason: Mapped[str | None] = mapped_column(String, nullable=True)
    transition_metadata: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict, name="metadata"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
