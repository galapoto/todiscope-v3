"""
Lifecycle enforcement helpers ensuring the platform follows the immutable Import → Normalize → Calculate → Report → Audit flow.
Everything here is backend-authoritative; UI state is never trusted.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.audit.service import log_action
from backend.app.core.calculation.service import create_calculation_run, get_calculation_run
from backend.app.core.dataset.models import DatasetVersion
from backend.app.core.dataset.raw_models import RawRecord
from backend.app.core.ingestion.models import Import
from backend.app.core.normalization.models import NormalizedRecord
from backend.app.core.workflows.state_machine import (
    WorkflowStateEnum,
    create_workflow_state,
    get_workflow_state,
    transition_workflow_state,
)


class LifecycleStage(Enum):
    IMPORT = "import"
    NORMALIZE = "normalize"
    CALCULATE = "calculate"
    REPORT = "report"


class LifecycleViolationError(Exception):
    """Raised when lifecycle enforceability is violated."""

    def __init__(self, message: str, stage: LifecycleStage) -> None:
        super().__init__(message)
        self.stage = stage
        self.detail = message


async def _log_violation(
    db: AsyncSession,
    *,
    dataset_version_id: str,
    engine_id: str,
    stage: LifecycleStage,
    attempted_action: str,
    actor_id: str,
    reason: str,
) -> None:
    await log_action(
        db,
        actor_id=actor_id,
        actor_type="system",
        action_type="integrity",
        action_label=f"Lifecycle violation ({stage.value})",
        dataset_version_id=dataset_version_id,
        reason=f"{stage.value.capitalize()} stage enforceability violated for engine {engine_id}",
        context={"engine_id": engine_id, "stage": stage.value, "attempted_action": attempted_action},
        metadata={"reason": reason},
        status="failure",
        error_message=reason,
    )
    # Ensure the violation is persisted even when callers use a raw sessionmaker session.
    try:
        await db.commit()
    except Exception:
        await db.rollback()


async def _dataset_exists(db: AsyncSession, dataset_version_id: str) -> bool:
    stmt = select(DatasetVersion.id).where(DatasetVersion.id == dataset_version_id).limit(1)
    result = await db.scalar(stmt)
    return result is not None


async def _import_completed(db: AsyncSession, dataset_version_id: str) -> bool:
    # Check workflow state first (authoritative source)
    workflow_state = await get_workflow_state(
        db,
        dataset_version_id=dataset_version_id,
        subject_type="lifecycle",
        subject_id="import",
    )
    if workflow_state and workflow_state.current_state == WorkflowStateEnum.APPROVED.value:
        return True
    
    # Fallback to record-based check (for backward compatibility during migration)
    import_exists = await db.scalar(
        select(Import.import_id).where(Import.dataset_version_id == dataset_version_id).limit(1)
    )
    if import_exists is None:
        return False
    raw_count = await db.scalar(
        select(func.count(RawRecord.raw_record_id)).where(RawRecord.dataset_version_id == dataset_version_id)
    )
    return bool(raw_count and int(raw_count) > 0)


async def _normalize_completed(db: AsyncSession, dataset_version_id: str) -> bool:
    # Check workflow state first (authoritative source)
    workflow_state = await get_workflow_state(
        db,
        dataset_version_id=dataset_version_id,
        subject_type="lifecycle",
        subject_id="normalize",
    )
    if workflow_state and workflow_state.current_state == WorkflowStateEnum.APPROVED.value:
        return True
    
    # Fallback to record-based check (for backward compatibility during migration)
    raw_count = await db.scalar(
        select(func.count(RawRecord.raw_record_id)).where(RawRecord.dataset_version_id == dataset_version_id)
    )
    if raw_count is None or int(raw_count) == 0:
        return False
    normalized_distinct_raw = await db.scalar(
        select(func.count(func.distinct(NormalizedRecord.raw_record_id)))
        .join(RawRecord, NormalizedRecord.raw_record_id == RawRecord.raw_record_id)
        .where(RawRecord.dataset_version_id == dataset_version_id)
    )
    if normalized_distinct_raw is None:
        return False
    return int(normalized_distinct_raw) == int(raw_count)


async def _calculate_completed(db: AsyncSession, dataset_version_id: str, engine_id: str) -> bool:
    """Check if calculation stage is completed for the given engine and dataset version."""
    # Check workflow state (authoritative source)
    workflow_state = await get_workflow_state(
        db,
        dataset_version_id=dataset_version_id,
        subject_type="lifecycle",
        subject_id=f"calculate:{engine_id}",
    )
    if workflow_state and workflow_state.current_state == WorkflowStateEnum.APPROVED.value:
        return True
    return False


async def verify_import_complete(
    db: AsyncSession,
    *,
    dataset_version_id: str,
    engine_id: str,
    actor_id: str,
    attempted_action: str,
) -> None:
    """
    Verify the Import stage has completed for dataset_version_id.

    This is a wrapper API for engine endpoints; it does not introduce new lifecycle rules.
    """
    if not dataset_version_id or not isinstance(dataset_version_id, str):
        await _log_violation(
            db,
            dataset_version_id=dataset_version_id or "unknown",
            engine_id=engine_id,
            stage=LifecycleStage.IMPORT,
            attempted_action=attempted_action,
            actor_id=actor_id,
            reason="Dataset version identifier is missing or invalid",
        )
        raise LifecycleViolationError("DATASET_VERSION_ID_REQUIRED", LifecycleStage.IMPORT)

    if not await _dataset_exists(db, dataset_version_id):
        await _log_violation(
            db,
            dataset_version_id=dataset_version_id,
            engine_id=engine_id,
            stage=LifecycleStage.IMPORT,
            attempted_action=attempted_action,
            actor_id=actor_id,
            reason="Requested dataset version does not exist",
        )
        raise LifecycleViolationError("DATASET_VERSION_NOT_FOUND", LifecycleStage.IMPORT)

    if not await _import_completed(db, dataset_version_id):
        await _log_violation(
            db,
            dataset_version_id=dataset_version_id,
            engine_id=engine_id,
            stage=LifecycleStage.IMPORT,
            attempted_action=attempted_action,
            actor_id=actor_id,
            reason="No import record found for dataset version",
        )
        raise LifecycleViolationError("IMPORT_NOT_COMPLETE", LifecycleStage.IMPORT)


async def verify_normalize_complete(
    db: AsyncSession,
    *,
    dataset_version_id: str,
    engine_id: str,
    actor_id: str,
    attempted_action: str,
) -> None:
    """
    Verify the Normalize stage has completed for dataset_version_id.

    This is a wrapper API for engine endpoints; it does not introduce new lifecycle rules.
    """
    if await _normalize_completed(db, dataset_version_id):
        return

    workflow_state = await get_workflow_state(
        db,
        dataset_version_id=dataset_version_id,
        subject_type="lifecycle",
        subject_id="normalize",
    )
    if workflow_state is None:
        reason = "Normalization workflow state does not exist. Normalization must be completed first."
    elif workflow_state.current_state != WorkflowStateEnum.APPROVED.value:
        reason = (
            f"Normalization workflow state is '{workflow_state.current_state}', not 'approved'. "
            "Normalization must be completed first."
        )
    else:
        reason = "Normalization has not completed for dataset version"

    await _log_violation(
        db,
        dataset_version_id=dataset_version_id,
        engine_id=engine_id,
        stage=LifecycleStage.NORMALIZE,
        attempted_action=attempted_action,
        actor_id=actor_id,
        reason=reason,
    )
    raise LifecycleViolationError("NORMALIZE_NOT_COMPLETE", LifecycleStage.NORMALIZE)


async def enforce_run_prerequisites(
    db: AsyncSession,
    *,
    dataset_version_id: str,
    engine_id: str,
    actor_id: str,
) -> None:
    await verify_import_complete(
        db,
        dataset_version_id=dataset_version_id,
        engine_id=engine_id,
        actor_id=actor_id,
        attempted_action="run",
    )
    await verify_normalize_complete(
        db,
        dataset_version_id=dataset_version_id,
        engine_id=engine_id,
        actor_id=actor_id,
        attempted_action="run",
    )


async def enforce_report_prerequisites(
    db: AsyncSession,
    *,
    dataset_version_id: str,
    run_id: str,
    engine_id: str,
    actor_id: str,
) -> None:
    if not run_id or not isinstance(run_id, str):
        await _log_violation(
            db,
            dataset_version_id=dataset_version_id,
            engine_id=engine_id,
            stage=LifecycleStage.REPORT,
            attempted_action="report",
            actor_id=actor_id,
            reason="Run ID is missing",
        )
        raise LifecycleViolationError("RUN_ID_REQUIRED", LifecycleStage.REPORT)

    run = await get_calculation_run(db, run_id=run_id)
    if run is None:
        await _log_violation(
            db,
            dataset_version_id=dataset_version_id,
            engine_id=engine_id,
            stage=LifecycleStage.CALCULATE,
            attempted_action="report",
            actor_id=actor_id,
            reason="Calculation run not found",
        )
        raise LifecycleViolationError("RUN_NOT_FOUND", LifecycleStage.CALCULATE)

    if run.engine_id != engine_id or run.dataset_version_id != dataset_version_id:
        await _log_violation(
            db,
            dataset_version_id=dataset_version_id,
            engine_id=engine_id,
            stage=LifecycleStage.REPORT,
            attempted_action="report",
            actor_id=actor_id,
            reason="Run does not belong to specified engine/dataset",
        )
        raise LifecycleViolationError("RUN_MISMATCH", LifecycleStage.REPORT)

    if run.finished_at is None:
        await _log_violation(
            db,
            dataset_version_id=dataset_version_id,
            engine_id=engine_id,
            stage=LifecycleStage.CALCULATE,
            attempted_action="report",
            actor_id=actor_id,
            reason="Calculation run is incomplete",
        )
        raise LifecycleViolationError("RUN_INCOMPLETE", LifecycleStage.CALCULATE)
    
    # Check workflow state (authoritative source) - calculation must be completed
    if not await _calculate_completed(db, dataset_version_id, engine_id):
        workflow_state = await get_workflow_state(
            db,
            dataset_version_id=dataset_version_id,
            subject_type="lifecycle",
            subject_id=f"calculate:{engine_id}",
        )
        if workflow_state is None:
            reason = f"Calculation workflow state does not exist for engine {engine_id}. Calculation must be completed first."
        elif workflow_state.current_state != WorkflowStateEnum.APPROVED.value:
            reason = f"Calculation workflow state is '{workflow_state.current_state}', not 'approved'. Calculation must be completed first."
        else:
            reason = f"Calculation has not completed for engine {engine_id}"
        
        await _log_violation(
            db,
            dataset_version_id=dataset_version_id,
            engine_id=engine_id,
            stage=LifecycleStage.CALCULATE,
            attempted_action="report",
            actor_id=actor_id,
            reason=reason,
        )
        raise LifecycleViolationError("CALCULATE_NOT_COMPLETE", LifecycleStage.CALCULATE)


async def verify_calculate_complete(
    db: AsyncSession,
    *,
    dataset_version_id: str,
    run_id: str,
    engine_id: str,
    actor_id: str,
) -> None:
    """
    Verify the Calculate stage has completed for run_id (and that the run belongs to engine_id + dataset_version_id).

    Wrapper API for engine endpoints; no new lifecycle rules are introduced here.
    """
    await enforce_report_prerequisites(
        db,
        dataset_version_id=dataset_version_id,
        run_id=run_id,
        engine_id=engine_id,
        actor_id=actor_id,
    )


def _parse_started_at(value: object) -> datetime:
    if isinstance(value, str) and value.strip():
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            return datetime.now(timezone.utc)
    return datetime.now(timezone.utc)


async def record_import_completion(
    db: AsyncSession,
    *,
    dataset_version_id: str,
    actor_id: str | None = None,
) -> None:
    """
    Record that import stage is completed by transitioning workflow state to 'approved'.
    This makes the workflow state machine authoritative for lifecycle enforcement.
    """
    workflow_state = await get_workflow_state(
        db,
        dataset_version_id=dataset_version_id,
        subject_type="lifecycle",
        subject_id="import",
    )
    
    if workflow_state is None:
        # Create initial state as 'draft', then transition to 'approved'
        workflow_state = await create_workflow_state(
            db,
            dataset_version_id=dataset_version_id,
            subject_type="lifecycle",
            subject_id="import",
            initial_state=WorkflowStateEnum.DRAFT.value,
            actor_id=actor_id or "system",
        )
    
    # For lifecycle stages, we allow direct transition from draft to approved
    # This bypasses the normal transition rules which require review/evidence
    if workflow_state.current_state != WorkflowStateEnum.APPROVED.value:
        from backend.app.core.workflows.models import WorkflowTransition
        
        now = datetime.now(timezone.utc)
        from_state = workflow_state.current_state
        workflow_state.current_state = WorkflowStateEnum.APPROVED.value
        workflow_state.updated_at = now
        workflow_state.updated_by = actor_id or "system"
        
        transition = WorkflowTransition(
            transition_id=uuid.uuid4().hex,
            workflow_state_id=workflow_state.workflow_state_id,
            dataset_version_id=dataset_version_id,
            subject_type="lifecycle",
            subject_id="import",
            from_state=from_state,
            to_state=WorkflowStateEnum.APPROVED.value,
            actor_id=actor_id or "system",
            reason="Import completed",
            transition_metadata={},
            created_at=now,
        )
        db.add(transition)
        await db.commit()


async def record_normalize_completion(
    db: AsyncSession,
    *,
    dataset_version_id: str,
    actor_id: str | None = None,
) -> None:
    """
    Record that normalize stage is completed by transitioning workflow state to 'approved'.
    This makes the workflow state machine authoritative for lifecycle enforcement.
    """
    workflow_state = await get_workflow_state(
        db,
        dataset_version_id=dataset_version_id,
        subject_type="lifecycle",
        subject_id="normalize",
    )
    
    if workflow_state is None:
        # Create initial state as 'draft', then transition to 'approved'
        workflow_state = await create_workflow_state(
            db,
            dataset_version_id=dataset_version_id,
            subject_type="lifecycle",
            subject_id="normalize",
            initial_state=WorkflowStateEnum.DRAFT.value,
            actor_id=actor_id or "system",
        )
    
    # For lifecycle stages, we allow direct transition from draft to approved
    if workflow_state.current_state != WorkflowStateEnum.APPROVED.value:
        from backend.app.core.workflows.models import WorkflowTransition
        
        now = datetime.now(timezone.utc)
        from_state = workflow_state.current_state
        workflow_state.current_state = WorkflowStateEnum.APPROVED.value
        workflow_state.updated_at = now
        workflow_state.updated_by = actor_id or "system"
        
        transition = WorkflowTransition(
            transition_id=uuid.uuid4().hex,
            workflow_state_id=workflow_state.workflow_state_id,
            dataset_version_id=dataset_version_id,
            subject_type="lifecycle",
            subject_id="normalize",
            from_state=from_state,
            to_state=WorkflowStateEnum.APPROVED.value,
            actor_id=actor_id or "system",
            reason="Normalization completed",
            transition_metadata={},
            created_at=now,
        )
        db.add(transition)
        await db.commit()


async def record_calculation_completion(
    db: AsyncSession,
    *,
    dataset_version_id: str,
    engine_id: str,
    engine_version: str,
    parameter_payload: dict,
    started_at: object,
    finished_at: datetime | None = None,
    actor_id: str | None = None,
) -> str:
    """
    Persist a CalculationRun for a successful engine execution and return the run_id.
    Also transitions workflow state to 'approved' for the calculate stage.
    This makes the workflow state machine authoritative for lifecycle enforcement.
    """
    started_dt = _parse_started_at(started_at)
    finished_dt = finished_at or datetime.now(timezone.utc)
    run = await create_calculation_run(
        db,
        dataset_version_id=dataset_version_id,
        engine_id=engine_id,
        engine_version=engine_version,
        parameter_payload=parameter_payload,
        started_at=started_dt,
        finished_at=finished_dt,
        actor_id=actor_id,
    )
    
    # Transition workflow state to 'approved' for calculate stage
    calculate_subject_id = f"calculate:{engine_id}"
    workflow_state = await get_workflow_state(
        db,
        dataset_version_id=dataset_version_id,
        subject_type="lifecycle",
        subject_id=calculate_subject_id,
    )
    
    if workflow_state is None:
        # Create initial state as 'draft', then transition to 'approved'
        workflow_state = await create_workflow_state(
            db,
            dataset_version_id=dataset_version_id,
            subject_type="lifecycle",
            subject_id=calculate_subject_id,
            initial_state=WorkflowStateEnum.DRAFT.value,
            actor_id=actor_id or "system",
        )
    
    # For lifecycle stages, we allow direct transition from draft to approved
    if workflow_state.current_state != WorkflowStateEnum.APPROVED.value:
        from backend.app.core.workflows.models import WorkflowTransition
        
        now = datetime.now(timezone.utc)
        from_state = workflow_state.current_state
        workflow_state.current_state = WorkflowStateEnum.APPROVED.value
        workflow_state.updated_at = now
        workflow_state.updated_by = actor_id or "system"
        
        transition = WorkflowTransition(
            transition_id=uuid.uuid4().hex,
            workflow_state_id=workflow_state.workflow_state_id,
            dataset_version_id=dataset_version_id,
            subject_type="lifecycle",
            subject_id=calculate_subject_id,
            from_state=from_state,
            to_state=WorkflowStateEnum.APPROVED.value,
            actor_id=actor_id or "system",
            reason="Calculation completed",
            transition_metadata={"run_id": run.run_id, "engine_id": engine_id},
            created_at=now,
        )
        db.add(transition)
    
    await db.commit()
    return run.run_id
