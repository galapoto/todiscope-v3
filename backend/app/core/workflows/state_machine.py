"""
Core workflow state machine.

Manages state transitions for all workflow entities (draft → review → approved → locked).
Engines can attach findings to states but cannot manage states themselves.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.dataset.models import DatasetVersion
from backend.app.core.audit.service import log_workflow_action
from backend.app.core.rbac.roles import Role
from backend.app.core.workflows.models import WorkflowState, WorkflowTransition
from backend.app.core.calculation.models import CalculationEvidenceLink
from backend.app.core.evidence.models import FindingEvidenceLink
from backend.app.core.reporting.models import ReportArtifact


class WorkflowStateEnum(str, Enum):
    """Workflow state values."""

    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    LOCKED = "locked"


# Valid state transitions
VALID_TRANSITIONS: dict[str, list[str]] = {
    WorkflowStateEnum.DRAFT.value: [WorkflowStateEnum.REVIEW.value],
    WorkflowStateEnum.REVIEW.value: [
        WorkflowStateEnum.DRAFT.value,  # Can go back to draft
        WorkflowStateEnum.APPROVED.value,
    ],
    WorkflowStateEnum.APPROVED.value: [WorkflowStateEnum.LOCKED.value],
    WorkflowStateEnum.LOCKED.value: [],  # Locked is terminal
}


@dataclass(frozen=True, slots=True)
class StateTransitionRule:
    """
    Rule for state transition validation.
    
    Attributes:
        from_state: Source state
        to_state: Target state
        requires_review: Whether review is required before transition
        requires_evidence: Whether evidence linking is required
        requires_approval: Whether explicit approval is required
    """

    from_state: str
    to_state: str
    requires_review: bool = False
    requires_evidence: bool = False
    requires_approval: bool = False


# State transition rules
TRANSITION_RULES: dict[tuple[str, str], StateTransitionRule] = {
    (WorkflowStateEnum.DRAFT.value, WorkflowStateEnum.REVIEW.value): StateTransitionRule(
        from_state=WorkflowStateEnum.DRAFT.value,
        to_state=WorkflowStateEnum.REVIEW.value,
        requires_review=False,
        requires_evidence=False,
        requires_approval=False,
    ),
    (WorkflowStateEnum.REVIEW.value, WorkflowStateEnum.APPROVED.value): StateTransitionRule(
        from_state=WorkflowStateEnum.REVIEW.value,
        to_state=WorkflowStateEnum.APPROVED.value,
        requires_review=True,
        requires_evidence=True,
        requires_approval=True,
    ),
    (WorkflowStateEnum.APPROVED.value, WorkflowStateEnum.LOCKED.value): StateTransitionRule(
        from_state=WorkflowStateEnum.APPROVED.value,
        to_state=WorkflowStateEnum.LOCKED.value,
        requires_review=True,
        requires_evidence=True,
        requires_approval=True,
    ),
    (WorkflowStateEnum.REVIEW.value, WorkflowStateEnum.DRAFT.value): StateTransitionRule(
        from_state=WorkflowStateEnum.REVIEW.value,
        to_state=WorkflowStateEnum.DRAFT.value,
        requires_review=False,
        requires_evidence=False,
        requires_approval=False,
    ),
}


class WorkflowStateError(Exception):
    """Base exception for workflow state errors."""

    pass


class InvalidStateTransitionError(WorkflowStateError):
    """Raised when a state transition is invalid."""

    pass


class MissingPrerequisitesError(WorkflowStateError):
    """Raised when prerequisites for a state transition are missing."""

    pass


async def get_workflow_state(
    db: AsyncSession,
    *,
    dataset_version_id: str,
    subject_type: str,
    subject_id: str,
) -> WorkflowState | None:
    """
    Get current workflow state for a subject.
    
    Args:
        db: Database session
        dataset_version_id: DatasetVersion ID
        subject_type: Type of subject (e.g., "finding", "report", "calculation")
        subject_id: ID of the subject
    
    Returns:
        WorkflowState instance or None if not found
    """
    return await db.scalar(
        select(WorkflowState).where(
            WorkflowState.dataset_version_id == dataset_version_id,
            WorkflowState.subject_type == subject_type,
            WorkflowState.subject_id == subject_id,
        )
    )


async def create_workflow_state(
    db: AsyncSession,
    *,
    dataset_version_id: str,
    subject_type: str,
    subject_id: str,
    initial_state: str = WorkflowStateEnum.DRAFT.value,
    actor_id: str | None = None,
) -> WorkflowState:
    """
    Create initial workflow state for a subject.
    
    Args:
        db: Database session
        dataset_version_id: DatasetVersion ID
        subject_type: Type of subject
        subject_id: ID of the subject
        initial_state: Initial state (default: draft)
        actor_id: ID of the actor creating the state
    
    Returns:
        Created WorkflowState instance
    """
    # Verify DatasetVersion exists
    dv = await db.scalar(select(DatasetVersion).where(DatasetVersion.id == dataset_version_id))
    if dv is None:
        raise ValueError(f"DatasetVersion '{dataset_version_id}' not found")
    
    # Validate initial state
    if initial_state not in [s.value for s in WorkflowStateEnum]:
        raise ValueError(f"Invalid initial state: {initial_state}")
    
    # Check if state already exists
    existing = await get_workflow_state(
        db,
        dataset_version_id=dataset_version_id,
        subject_type=subject_type,
        subject_id=subject_id,
    )
    if existing is not None:
        return existing
    
    # Create workflow state
    now = datetime.now(timezone.utc)
    workflow_state = WorkflowState(
        workflow_state_id=uuid.uuid4().hex,
        dataset_version_id=dataset_version_id,
        subject_type=subject_type,
        subject_id=subject_id,
        current_state=initial_state,
        created_at=now,
        updated_at=now,
        created_by=actor_id,
    )
    
    db.add(workflow_state)
    transition = WorkflowTransition(
        transition_id=uuid.uuid4().hex,
        workflow_state_id=workflow_state.workflow_state_id,
        dataset_version_id=dataset_version_id,
        subject_type=subject_type,
        subject_id=subject_id,
        from_state="none",
        to_state=initial_state,
        actor_id=actor_id,
        reason="initial_state",
        transition_metadata={},
        created_at=now,
    )
    db.add(transition)
    if actor_id:
        await log_workflow_action(
            db,
            actor_id=actor_id,
            dataset_version_id=dataset_version_id,
            from_state="none",
            to_state=initial_state,
            subject_type=subject_type,
            subject_id=subject_id,
            reason="initial_state",
        )
    await db.commit()
    await db.refresh(workflow_state)
    
    return workflow_state


async def _has_evidence_for_subject(
    db: AsyncSession,
    *,
    dataset_version_id: str,
    subject_type: str,
    subject_id: str,
) -> bool:
    if subject_type == "finding":
        exists = await db.scalar(select(1).where(FindingEvidenceLink.finding_id == subject_id))
        return exists is not None
    if subject_type == "calculation":
        exists = await db.scalar(
            select(1).where(CalculationEvidenceLink.calculation_run_id == subject_id)
        )
        return exists is not None
    if subject_type == "report":
        report = await db.scalar(select(ReportArtifact).where(ReportArtifact.report_id == subject_id))
        if report is None:
            return False
        exists = await db.scalar(
            select(1).where(CalculationEvidenceLink.calculation_run_id == report.calculation_run_id)
        )
        return exists is not None
    return False


def _has_approval_for_actor(actor_roles: tuple[str, ...] | None) -> bool:
    if not actor_roles:
        return False
    return Role.ADMIN.value in actor_roles


async def transition_workflow_state(
    db: AsyncSession,
    *,
    dataset_version_id: str,
    subject_type: str,
    subject_id: str,
    to_state: str,
    actor_id: str,
    actor_roles: tuple[str, ...] | None = None,
    reason: str | None = None,
) -> WorkflowState:
    """
    Transition workflow state with validation.
    
    Args:
        db: Database session
        dataset_version_id: DatasetVersion ID
        subject_type: Type of subject
        subject_id: ID of the subject
        to_state: Target state
        actor_id: ID of the actor performing the transition
        reason: Optional reason for the transition
        actor_roles: Roles for the actor performing the transition. Used to enforce
            approval prerequisites (derived from the authenticated principal, not user input).
    
    Returns:
        Updated WorkflowState instance
    
    Raises:
        InvalidStateTransitionError: If transition is invalid
        MissingPrerequisitesError: If prerequisites are missing
    """
    # Get current state
    workflow_state = await get_workflow_state(
        db,
        dataset_version_id=dataset_version_id,
        subject_type=subject_type,
        subject_id=subject_id,
    )
    
    if workflow_state is None:
        # Create initial state if it doesn't exist
        workflow_state = await create_workflow_state(
            db,
            dataset_version_id=dataset_version_id,
            subject_type=subject_type,
            subject_id=subject_id,
            initial_state=WorkflowStateEnum.DRAFT.value,
            actor_id=actor_id,
        )
    
    from_state = workflow_state.current_state
    
    # Validate state transition
    if from_state == to_state:
        return workflow_state  # No transition needed
    
    # Check if transition is valid
    valid_targets = VALID_TRANSITIONS.get(from_state, [])
    if to_state not in valid_targets:
        raise InvalidStateTransitionError(
            f"Invalid state transition from '{from_state}' to '{to_state}'. "
            f"Valid transitions from '{from_state}': {', '.join(valid_targets)}"
        )
    
    # Check transition rules (prerequisites are derived from DB / auth context)
    rule_key = (from_state, to_state)
    if rule_key in TRANSITION_RULES:
        rule = TRANSITION_RULES[rule_key]

        has_evidence = await _has_evidence_for_subject(
            db,
            dataset_version_id=dataset_version_id,
            subject_type=subject_type,
            subject_id=subject_id,
        )
        has_approval = _has_approval_for_actor(actor_roles)
        
        if rule.requires_evidence and not has_evidence:
            raise MissingPrerequisitesError(
                f"State transition from '{from_state}' to '{to_state}' requires evidence linking"
            )
        
        if rule.requires_approval and not has_approval:
            raise MissingPrerequisitesError(
                f"State transition from '{from_state}' to '{to_state}' requires approval"
            )
    
    # Perform transition
    now = datetime.now(timezone.utc)
    workflow_state.current_state = to_state
    workflow_state.updated_at = now
    workflow_state.updated_by = actor_id
    transition = WorkflowTransition(
        transition_id=uuid.uuid4().hex,
        workflow_state_id=workflow_state.workflow_state_id,
        dataset_version_id=dataset_version_id,
        subject_type=subject_type,
        subject_id=subject_id,
        from_state=from_state,
        to_state=to_state,
        actor_id=actor_id,
        reason=reason,
        transition_metadata={"has_evidence": has_evidence, "has_approval": has_approval},
        created_at=now,
    )
    db.add(transition)
    await log_workflow_action(
        db,
        actor_id=actor_id,
        dataset_version_id=dataset_version_id,
        from_state=from_state,
        to_state=to_state,
        subject_type=subject_type,
        subject_id=subject_id,
        reason=reason,
        metadata={"has_evidence": has_evidence, "has_approval": has_approval},
    )
    await db.commit()
    await db.refresh(workflow_state)
    
    return workflow_state




