"""
API endpoints for audit log querying and export.

Provides endpoints for external audit tools to access and query audit logs.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.auth.dependencies import require_principal
from backend.app.core.audit.models import AuditLog
from backend.app.core.db import get_db_session
from backend.app.core.rbac.roles import Role
import csv
import io

router = APIRouter(prefix="/api/v3/audit", tags=["audit"])


@router.get("/logs")
async def query_audit_logs(
    dataset_version_id: str | None = Query(None, description="Filter by DatasetVersion ID"),
    calculation_run_id: str | None = Query(None, description="Filter by CalculationRun ID"),
    action_type: str | None = Query(None, description="Filter by action type"),
    actor_id: str | None = Query(None, description="Filter by actor ID"),
    status: str | None = Query(None, description="Filter by status"),
    start_date: datetime | None = Query(None, description="Start date for filtering"),
    end_date: datetime | None = Query(None, description="End date for filtering"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: AsyncSession = Depends(get_db_session),
    _: object = Depends(require_principal(Role.INGEST)),
) -> dict[str, Any]:
    """
    Query audit logs with filtering and pagination.
    
    Returns:
        Dictionary with audit logs and pagination metadata
    """
    # Build query
    query = select(AuditLog)
    
    if dataset_version_id:
        query = query.where(AuditLog.dataset_version_id == dataset_version_id)
    if calculation_run_id:
        query = query.where(AuditLog.calculation_run_id == calculation_run_id)
    if action_type:
        query = query.where(AuditLog.action_type == action_type)
    if actor_id:
        query = query.where(AuditLog.actor_id == actor_id)
    if status:
        query = query.where(AuditLog.status == status)
    if start_date:
        query = query.where(AuditLog.created_at >= start_date)
    if end_date:
        query = query.where(AuditLog.created_at <= end_date)
    
    # Order by created_at descending
    query = query.order_by(AuditLog.created_at.desc())
    
    # Apply pagination
    query = query.limit(limit).offset(offset)
    
    # Execute query
    result = await db.execute(query)
    logs = result.scalars().all()
    
    # Count total (for pagination)
    count_query = select(AuditLog)
    if dataset_version_id:
        count_query = count_query.where(AuditLog.dataset_version_id == dataset_version_id)
    if calculation_run_id:
        count_query = count_query.where(AuditLog.calculation_run_id == calculation_run_id)
    if action_type:
        count_query = count_query.where(AuditLog.action_type == action_type)
    if actor_id:
        count_query = count_query.where(AuditLog.actor_id == actor_id)
    if status:
        count_query = count_query.where(AuditLog.status == status)
    if start_date:
        count_query = count_query.where(AuditLog.created_at >= start_date)
    if end_date:
        count_query = count_query.where(AuditLog.created_at <= end_date)
    
    count_result = await db.execute(count_query)
    total_count = len(count_result.scalars().all())
    
    # Serialize logs
    logs_data = []
    for log in logs:
        logs_data.append({
            "audit_log_id": log.audit_log_id,
            "dataset_version_id": log.dataset_version_id,
            "calculation_run_id": log.calculation_run_id,
            "artifact_id": log.artifact_id,
            "actor_id": log.actor_id,
            "actor_type": log.actor_type,
            "action_type": log.action_type,
            "action_label": log.action_label,
            "created_at": log.created_at.isoformat(),
            "reason": log.reason,
            "context": log.context,
            "metadata": log.event_metadata,
            "status": log.status,
            "error_message": log.error_message,
        })
    
    return {
        "logs": logs_data,
        "total": total_count,
        "limit": limit,
        "offset": offset,
    }


@router.get("/logs/export")
async def export_audit_logs(
    dataset_version_id: str | None = Query(None, description="Filter by DatasetVersion ID"),
    calculation_run_id: str | None = Query(None, description="Filter by CalculationRun ID"),
    action_type: str | None = Query(None, description="Filter by action type"),
    start_date: datetime | None = Query(None, description="Start date for filtering"),
    end_date: datetime | None = Query(None, description="End date for filtering"),
    format: str = Query("csv", description="Export format: csv or json"),
    db: AsyncSession = Depends(get_db_session),
    _: object = Depends(require_principal(Role.INGEST)),
):
    """
    Export audit logs in CSV or JSON format.
    
    Returns:
        StreamingResponse with CSV or JSON data
    """
    # Build query (same as query_audit_logs but without pagination)
    query = select(AuditLog)
    
    if dataset_version_id:
        query = query.where(AuditLog.dataset_version_id == dataset_version_id)
    if calculation_run_id:
        query = query.where(AuditLog.calculation_run_id == calculation_run_id)
    if action_type:
        query = query.where(AuditLog.action_type == action_type)
    if start_date:
        query = query.where(AuditLog.created_at >= start_date)
    if end_date:
        query = query.where(AuditLog.created_at <= end_date)
    
    query = query.order_by(AuditLog.created_at.desc())
    
    # Execute query
    result = await db.execute(query)
    logs = result.scalars().all()
    
    if format == "csv":
        # Generate CSV
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=[
                "audit_log_id",
                "dataset_version_id",
                "calculation_run_id",
                "artifact_id",
                "actor_id",
                "actor_type",
                "action_type",
                "action_label",
                "created_at",
                "reason",
                "status",
                "error_message",
            ],
        )
        writer.writeheader()
        for log in logs:
            writer.writerow({
                "audit_log_id": log.audit_log_id,
                "dataset_version_id": log.dataset_version_id or "",
                "calculation_run_id": log.calculation_run_id or "",
                "artifact_id": log.artifact_id or "",
                "actor_id": log.actor_id,
                "actor_type": log.actor_type,
                "action_type": log.action_type,
                "action_label": log.action_label or "",
                "created_at": log.created_at.isoformat(),
                "reason": log.reason or "",
                "status": log.status,
                "error_message": log.error_message or "",
            })
        
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=audit_logs.csv"},
        )
    else:
        # Generate JSON
        logs_data = []
        for log in logs:
            logs_data.append({
                "audit_log_id": log.audit_log_id,
                "dataset_version_id": log.dataset_version_id,
                "calculation_run_id": log.calculation_run_id,
                "artifact_id": log.artifact_id,
                "actor_id": log.actor_id,
                "actor_type": log.actor_type,
                "action_type": log.action_type,
                "action_label": log.action_label,
                "created_at": log.created_at.isoformat(),
                "reason": log.reason,
                "context": log.context,
                "metadata": log.event_metadata,
                "status": log.status,
                "error_message": log.error_message,
            })
        
        return JSONResponse(content={"logs": logs_data, "total": len(logs_data)})


