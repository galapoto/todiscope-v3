from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.models.base import Base


class ErpIntegrationReadinessRun(Base):
    __tablename__ = "engine_erp_integration_readiness_runs"

    run_id: Mapped[str] = mapped_column(String, primary_key=True)
    result_set_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    dataset_version_id: Mapped[str] = mapped_column(
        String, ForeignKey("dataset_version.id"), nullable=False, index=True
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)

    erp_system_config: Mapped[dict] = mapped_column(JSON, nullable=False)
    parameters: Mapped[dict] = mapped_column(JSON, nullable=False)
    optional_inputs: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    engine_version: Mapped[str] = mapped_column(String, nullable=False)






