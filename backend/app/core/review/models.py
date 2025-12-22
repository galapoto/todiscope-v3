from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.models.base import Base


class ReviewItem(Base):
    __tablename__ = "review_items"

    review_item_id: Mapped[str] = mapped_column(String, primary_key=True)
    dataset_version_id: Mapped[str] = mapped_column(
        String, ForeignKey("dataset_version.id"), nullable=False, index=True
    )
    engine_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    subject_type: Mapped[str] = mapped_column(String, nullable=False)
    subject_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    state: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ReviewEvent(Base):
    __tablename__ = "review_events"

    review_event_id: Mapped[str] = mapped_column(String, primary_key=True)
    review_item_id: Mapped[str] = mapped_column(String, ForeignKey("review_items.review_item_id"), nullable=False)
    dataset_version_id: Mapped[str] = mapped_column(
        String, ForeignKey("dataset_version.id"), nullable=False, index=True
    )
    engine_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    from_state: Mapped[str] = mapped_column(String, nullable=False)
    to_state: Mapped[str] = mapped_column(String, nullable=False)
    evidence_id: Mapped[str] = mapped_column(String, ForeignKey("evidence_records.evidence_id"), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

