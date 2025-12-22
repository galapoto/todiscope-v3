from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal


class FindingMutationError(RuntimeError):
    pass


class ReviewActionError(ValueError):
    pass


ReviewActionValue = Literal["confirmed", "dismissed", "inconclusive"]


@dataclass(frozen=True)
class ReviewAction:
    review_action_id: str
    finding_id: str
    dataset_version_id: str
    run_id: str
    action: ReviewActionValue
    reviewer_id: str | None
    comment: str | None
    created_at: datetime


def prevent_finding_mutation(_finding_id: str) -> None:
    raise FindingMutationError("FINDING_MUTATION_FORBIDDEN")


def prevent_finding_deletion(_finding_id: str) -> None:
    raise FindingMutationError("FINDING_DELETION_FORBIDDEN")


def create_review_action(
    *,
    finding_id: str,
    dataset_version_id: str,
    run_id: str,
    action: str,
    reviewer_id: str | None,
    comment: str | None,
    created_at: datetime,
) -> ReviewAction:
    allowed: set[str] = {"confirmed", "dismissed", "inconclusive"}
    if action not in allowed:
        raise ReviewActionError("REVIEW_ACTION_INVALID")
    review_action_id = f"{dataset_version_id}:{run_id}:{finding_id}:{action}:{created_at.isoformat()}"
    return ReviewAction(
        review_action_id=review_action_id,
        finding_id=finding_id,
        dataset_version_id=dataset_version_id,
        run_id=run_id,
        action=action,  # type: ignore[arg-type]
        reviewer_id=reviewer_id,
        comment=comment,
        created_at=created_at,
    )


__all__ = [
    "FindingMutationError",
    "ReviewActionError",
    "ReviewAction",
    "create_review_action",
    "prevent_finding_deletion",
    "prevent_finding_mutation",
]


