"""
FF-3 Review Immutability Tests

Tests:
- Findings cannot be mutated
- Findings cannot be deleted
- Review actions create new artifacts only
"""
import pytest
from datetime import datetime, timezone

from backend.app.engines.financial_forensics.review import (
    FindingMutationError,
    ReviewActionError,
    create_review_action,
    prevent_finding_deletion,
    prevent_finding_mutation,
)


def test_finding_mutation_forbidden() -> None:
    """Test: Findings cannot be mutated."""
    with pytest.raises(FindingMutationError, match="FINDING_MUTATION_FORBIDDEN"):
        prevent_finding_mutation("finding-1")


def test_finding_deletion_forbidden() -> None:
    """Test: Findings cannot be deleted."""
    with pytest.raises(FindingMutationError, match="FINDING_DELETION_FORBIDDEN"):
        prevent_finding_deletion("finding-1")


def test_review_action_creates_artifact() -> None:
    """Test: Review actions create new artifacts (findings not mutated)."""
    action = create_review_action(
        finding_id="finding-1",
        dataset_version_id="dv-1",
        run_id="run-1",
        action="confirmed",
        reviewer_id="reviewer-1",
        comment="Looks good",
        created_at=datetime.now(timezone.utc),
    )
    
    assert action.finding_id == "finding-1"
    assert action.action == "confirmed"
    assert action.reviewer_id == "reviewer-1"
    assert action.comment == "Looks good"
    assert action.review_action_id is not None


def test_review_action_invalid() -> None:
    """Test: Invalid review action raises error."""
    with pytest.raises(ReviewActionError, match="REVIEW_ACTION_INVALID"):
        create_review_action(
            finding_id="finding-1",
            dataset_version_id="dv-1",
            run_id="run-1",
            action="invalid_action",  # Invalid
            reviewer_id=None,
            comment=None,
            created_at=datetime.now(timezone.utc),
        )


def test_review_action_allowed_values() -> None:
    """Test: Only allowed review actions are accepted."""
    allowed = ["confirmed", "dismissed", "inconclusive"]
    
    for action_value in allowed:
        action = create_review_action(
            finding_id="finding-1",
            dataset_version_id="dv-1",
            run_id="run-1",
            action=action_value,
            reviewer_id=None,
            comment=None,
            created_at=datetime.now(timezone.utc),
        )
        assert action.action == action_value


