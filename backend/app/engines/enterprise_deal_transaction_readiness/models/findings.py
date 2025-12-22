from __future__ import annotations

from sqlalchemy import ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.models.base import Base


class EnterpriseDealTransactionReadinessFinding(Base):
    __tablename__ = "engine_enterprise_deal_transaction_readiness_findings"

    finding_id: Mapped[str] = mapped_column(String, primary_key=True)
    result_set_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    dataset_version_id: Mapped[str] = mapped_column(
        String, ForeignKey("dataset_version.id"), nullable=False, index=True
    )

    kind: Mapped[str] = mapped_column(String, nullable=False)
    severity: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    detail: Mapped[dict] = mapped_column(JSON, nullable=False)

    evidence_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    engine_version: Mapped[str] = mapped_column(String, nullable=False)

