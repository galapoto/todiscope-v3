from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.models.base import Base


class EvidenceRecord(Base):
    __tablename__ = "evidence_records"

    evidence_id: Mapped[str] = mapped_column(String, primary_key=True)
    dataset_version_id: Mapped[str] = mapped_column(
        String, ForeignKey("dataset_version.id"), nullable=False, index=True
    )
    engine_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FindingRecord(Base):
    __tablename__ = "finding_record"

    finding_id: Mapped[str] = mapped_column(String, primary_key=True)
    dataset_version_id: Mapped[str] = mapped_column(
        String, ForeignKey("dataset_version.id"), nullable=False, index=True
    )
    raw_record_id: Mapped[str] = mapped_column(
        String, ForeignKey("raw_record.raw_record_id"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FindingEvidenceLink(Base):
    __tablename__ = "finding_evidence_link"

    link_id: Mapped[str] = mapped_column(String, primary_key=True)
    finding_id: Mapped[str] = mapped_column(
        String, ForeignKey("finding_record.finding_id"), nullable=False, index=True
    )
    evidence_id: Mapped[str] = mapped_column(
        String, ForeignKey("evidence_records.evidence_id"), nullable=False, index=True
    )
