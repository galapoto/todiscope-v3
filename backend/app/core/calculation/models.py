from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.models.base import Base


class CalculationRun(Base):
    """
    Core CalculationRun model for tracking all calculation executions.
    
    This model provides a unified abstraction for all engines, ensuring
    traceability, reproducibility, and full introspection of calculation parameters.
    
    Attributes:
        run_id: Unique identifier for the calculation run (UUIDv7)
        dataset_version_id: Link to DatasetVersion for traceability
        engine_id: Link to engine registry entry
        engine_version: Version of the engine used for this calculation
        parameter_payload: Complete parameter payload (JSON) for full introspection
        parameters_hash: SHA256 hash of parameters for reproducibility checks
        started_at: Timestamp when calculation started
        finished_at: Timestamp when calculation finished
    """

    __tablename__ = "calculation_run"

    run_id: Mapped[str] = mapped_column(String, primary_key=True)
    dataset_version_id: Mapped[str] = mapped_column(
        String, ForeignKey("dataset_version.id"), nullable=False, index=True
    )
    engine_id: Mapped[str] = mapped_column(
        String, ForeignKey("engine_registry_entry.engine_id"), nullable=False, index=True
    )
    engine_version: Mapped[str] = mapped_column(String, nullable=False, index=True)
    parameter_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    parameters_hash: Mapped[str] = mapped_column(String, nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CalculationEvidenceLink(Base):
    __tablename__ = "calculation_evidence_link"

    link_id: Mapped[str] = mapped_column(String, primary_key=True)
    calculation_run_id: Mapped[str] = mapped_column(
        String, ForeignKey("calculation_run.run_id"), nullable=False, index=True
    )
    evidence_id: Mapped[str] = mapped_column(
        String, ForeignKey("evidence_records.evidence_id"), nullable=False, index=True
    )
