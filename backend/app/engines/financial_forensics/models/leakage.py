from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.models.base import Base


class FinancialForensicsLeakageItem(Base):
    __tablename__ = "engine_financial_forensics_leakage_items"
    __table_args__ = (
        UniqueConstraint("run_id", "finding_id", name="uq_engine_financial_forensics_leakage_run_finding"),
    )

    leakage_item_id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[str] = mapped_column(
        String, ForeignKey("engine_financial_forensics_runs.run_id"), nullable=False, index=True
    )
    finding_id: Mapped[str] = mapped_column(
        String, ForeignKey("engine_financial_forensics_findings.finding_id"), nullable=False, index=True
    )
    dataset_version_id: Mapped[str] = mapped_column(
        String, ForeignKey("dataset_version.id"), nullable=False, index=True
    )
    typology: Mapped[str] = mapped_column(String, nullable=False, index=True)
    exposure_abs: Mapped[Decimal] = mapped_column(Numeric(38, 12), nullable=False)
    exposure_signed: Mapped[Decimal] = mapped_column(Numeric(38, 12), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

