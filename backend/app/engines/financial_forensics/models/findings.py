"""
Finding Model (Engine-Owned) for Engine #2

FF-3: Engine-owned findings table with all mandatory fields.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.models.base import Base


class FinancialForensicsFinding(Base):
    """
    Engine-owned findings table.
    
    All fields are mandatory:
    - finding_id: Primary key
    - dataset_version_id: Dataset binding (required)
    - rule_id: Rule identifier (required)
    - rule_version: Rule version (required)
    - framework_version: Framework version (required, locked to "financial_forensics_v1")
    - finding_type: Finding type (required, constrained enum)
    - confidence: Confidence enum (required, constrained)
    - matched_record_ids: Matched record IDs (required)
    - unmatched_amount: Unmatched amount (optional, Decimal as string)
    - fx_artifact_id: FX artifact reference (required)
    - primary_evidence_item_id: Primary evidence bundle reference (required)
    - evidence_ids: Additional evidence IDs (list)
    - created_at: Deterministic timestamp (required)
    """
    __tablename__ = "engine_financial_forensics_findings"
    __table_args__ = (
        CheckConstraint(
            "confidence in ('exact','within_tolerance','partial','ambiguous')",
            name="ck_engine_financial_forensics_findings_confidence_allowed",
        ),
        CheckConstraint(
            "finding_type in ('exact_match','tolerance_match','partial_match')",
            name="ck_engine_financial_forensics_findings_finding_type_allowed",
        ),
    )

    finding_id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("engine_financial_forensics_runs.run_id"),
        nullable=False,
        index=True,
    )
    dataset_version_id: Mapped[str] = mapped_column(
        String, ForeignKey("dataset_version.id"), nullable=False, index=True
    )
    
    # Rule identifiers (mandatory)
    rule_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    rule_version: Mapped[str] = mapped_column(String, nullable=False)
    
    # Framework version (mandatory, locked value: "financial_forensics_v1")
    framework_version: Mapped[str] = mapped_column(String, nullable=False)
    
    # Finding type (mandatory, constrained enum: exact_match, tolerance_match, partial_match)
    finding_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    
    # Confidence (mandatory, enum-constrained)
    confidence: Mapped[str] = mapped_column(String, nullable=False)

    # Matched records (mandatory)
    matched_record_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    
    # Unmatched amount (optional, stored as Decimal string)
    unmatched_amount: Mapped[str | None] = mapped_column(String, nullable=True)
    
    # FX artifact reference (mandatory)
    fx_artifact_id: Mapped[str] = mapped_column(
        String, ForeignKey("fx_artifacts.fx_artifact_id"), nullable=False
    )
    
    # Primary evidence item reference (mandatory, FK to evidence_records)
    primary_evidence_item_id: Mapped[str] = mapped_column(
        String, ForeignKey("evidence_records.evidence_id"), nullable=False, index=True
    )
    
    # Evidence IDs (list of additional evidence_item_id references)
    evidence_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    
    # Deterministic timestamp (mandatory, must be provided, not system time)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
