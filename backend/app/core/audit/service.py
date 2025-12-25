"""
Core audit logging service.

Provides functions to log all platform actions with full traceability.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.audit.models import AuditLog
from backend.app.core.dataset.models import DatasetVersion


async def log_action(
    db: AsyncSession,
    *,
    actor_id: str,
    actor_type: str,
    action_type: str,
    action_label: str | None = None,
    dataset_version_id: str | None = None,
    calculation_run_id: str | None = None,
    artifact_id: str | None = None,
    reason: str | None = None,
    context: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    status: str = "success",
    error_message: str | None = None,
    timestamp: datetime | None = None,
) -> AuditLog:
    """
    Log a platform action to the audit log.
    
    Args:
        db: Database session
        actor_id: ID of the actor performing the action
        actor_type: Type of actor ("user", "system", "engine")
        action_type: Type of action ("import", "normalization", "calculation", "reporting", "workflow")
        action_label: Optional human-readable label for the action
        dataset_version_id: Optional DatasetVersion ID
        calculation_run_id: Optional CalculationRun ID
        artifact_id: Optional Artifact ID
        reason: Optional reason for the action
        context: Optional context dictionary
        metadata: Optional metadata dictionary
        status: Action status ("success", "failure", "warning")
        error_message: Optional error message if status is "failure"
        timestamp: Optional timestamp (defaults to now)
    
    Returns:
        Created AuditLog instance
    """
    # Validate required fields
    if not actor_id or not isinstance(actor_id, str):
        raise ValueError("actor_id is required and must be a non-empty string")
    if not actor_type or not isinstance(actor_type, str):
        raise ValueError("actor_type is required and must be a non-empty string")
    if not action_type or not isinstance(action_type, str):
        raise ValueError("action_type is required and must be a non-empty string")
    
    # Validate actor_type
    if actor_type not in ("user", "system", "engine"):
        raise ValueError(f"actor_type must be one of: user, system, engine")
    
    # Validate action_type
    valid_action_types = (
        "import",
        "mapping",
        "normalization",
        "calculation",
        "reporting",
        "workflow",
        "integrity",
        "maintenance",
    )
    if action_type not in valid_action_types:
        raise ValueError(f"action_type must be one of: {', '.join(valid_action_types)}")
    
    # Validate status
    if status not in ("success", "failure", "warning"):
        raise ValueError("status must be one of: success, failure, warning")
    
    # Verify DatasetVersion exists if provided
    if dataset_version_id:
        exists = await db.scalar(select(1).where(DatasetVersion.id == dataset_version_id))
        if exists is None:
            raise ValueError(f"DatasetVersion '{dataset_version_id}' not found")
    
    # Create audit log entry
    audit_log = AuditLog(
        audit_log_id=uuid.uuid4().hex,
        dataset_version_id=dataset_version_id,
        calculation_run_id=calculation_run_id,
        artifact_id=artifact_id,
        actor_id=actor_id.strip(),
        actor_type=actor_type.strip(),
        action_type=action_type.strip(),
        action_label=action_label.strip() if action_label else None,
        created_at=timestamp if timestamp else datetime.now(timezone.utc),
        reason=reason,
        context=context or {},
        event_metadata=metadata or {},
        status=status,
        error_message=error_message,
    )
    
    db.add(audit_log)
    return audit_log


async def log_import_action(
    db: AsyncSession,
    *,
    actor_id: str,
    dataset_version_id: str,
    import_id: str,
    record_count: int,
    status: str = "success",
    error_message: str | None = None,
    reason: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    """Log an import action."""
    return await log_action(
        db,
        actor_id=actor_id,
        actor_type="user",
        action_type="import",
        action_label=f"Import {import_id}",
        dataset_version_id=dataset_version_id,
        reason=reason or f"Imported {record_count} records",
        context={"import_id": import_id, "record_count": record_count},
        metadata=metadata or {},
        status=status,
        error_message=error_message,
    )


async def log_normalization_action(
    db: AsyncSession,
    *,
    actor_id: str,
    dataset_version_id: str,
    records_normalized: int,
    records_skipped: int,
    action_label: str | None = None,
    status: str = "success",
    error_message: str | None = None,
    reason: str | None = None,
    context: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    """Log a normalization action."""
    return await log_action(
        db,
        actor_id=actor_id,
        actor_type="user",
        action_type="normalization",
        action_label=action_label or "Normalize dataset",
        dataset_version_id=dataset_version_id,
        reason=reason or f"Normalized {records_normalized} records, skipped {records_skipped}",
        context=context or {"records_normalized": records_normalized, "records_skipped": records_skipped},
        metadata=metadata or {},
        status=status,
        error_message=error_message,
    )


async def log_calculation_action(
    db: AsyncSession,
    *,
    actor_id: str,
    dataset_version_id: str,
    calculation_run_id: str,
    engine_id: str,
    status: str = "success",
    error_message: str | None = None,
    reason: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    """Log a calculation action."""
    return await log_action(
        db,
        actor_id=actor_id,
        actor_type="engine",
        action_type="calculation",
        action_label=f"Calculation run {calculation_run_id}",
        dataset_version_id=dataset_version_id,
        calculation_run_id=calculation_run_id,
        reason=reason or f"Calculation run executed by {engine_id}",
        context={"engine_id": engine_id, "calculation_run_id": calculation_run_id},
        metadata=metadata or {},
        status=status,
        error_message=error_message,
    )


async def log_reporting_action(
    db: AsyncSession,
    *,
    actor_id: str,
    dataset_version_id: str,
    calculation_run_id: str | None,
    artifact_id: str | None = None,
    report_type: str,
    status: str = "success",
    error_message: str | None = None,
    reason: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    """Log a reporting action."""
    return await log_action(
        db,
        actor_id=actor_id,
        actor_type="user",
        action_type="reporting",
        action_label=f"Generate {report_type} report",
        dataset_version_id=dataset_version_id,
        calculation_run_id=calculation_run_id,
        artifact_id=artifact_id,
        reason=reason or f"Generated {report_type} report",
        context={"report_type": report_type, "calculation_run_id": calculation_run_id},
        metadata=metadata or {},
        status=status,
        error_message=error_message,
    )


async def log_workflow_action(
    db: AsyncSession,
    *,
    actor_id: str,
    dataset_version_id: str,
    from_state: str,
    to_state: str,
    subject_type: str,
    subject_id: str,
    status: str = "success",
    error_message: str | None = None,
    reason: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    """Log a workflow state transition action."""
    return await log_action(
        db,
        actor_id=actor_id,
        actor_type="user",
        action_type="workflow",
        action_label=f"State transition: {from_state} → {to_state}",
        dataset_version_id=dataset_version_id,
        reason=reason or f"Transitioned {subject_type} {subject_id} from {from_state} to {to_state}",
        context={
            "from_state": from_state,
            "to_state": to_state,
            "subject_type": subject_type,
            "subject_id": subject_id,
        },
        metadata=metadata or {},
        status=status,
        error_message=error_message,
    )




