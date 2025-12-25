"""
Tests for scope creep detection in the Construction Cost Intelligence Engine.

Verifies that unmatched actuals are correctly flagged as scope creep and properly
labeled in the report output.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from backend.app.core.dataset.uuidv7 import uuid7
from backend.app.core.db import get_sessionmaker
from backend.app.engines.construction_cost_intelligence.compare import compare_boq_to_actuals
from backend.app.engines.construction_cost_intelligence.models import (
    ComparisonConfig,
    CostLine,
)
from backend.app.engines.construction_cost_intelligence.report.assembler import (
    assemble_cost_variance_report,
)
from backend.app.engines.construction_cost_intelligence.variance.detector import (
    VarianceSeverity,
    detect_cost_variances,
    detect_scope_creep,
)


@pytest.fixture
def sample_dataset_version_id() -> str:
    return str(uuid7())


@pytest.fixture
def sample_run_id() -> str:
    return f"run-{uuid7()}"


@pytest.mark.anyio
async def test_scope_creep_detection_basic(sample_dataset_version_id: str) -> None:
    """Test that unmatched actuals are detected as scope creep."""
    cfg = ComparisonConfig(identity_fields=("item_code",))
    
    # BOQ lines
    boq_lines = [
        CostLine(
            dataset_version_id=sample_dataset_version_id,
            kind="boq",
            line_id="boq-1",
            identity={"item_code": "ITEM001"},
            total_cost=Decimal("10000.00"),
        ),
    ]
    
    # Actual lines: one matched, one unmatched (scope creep)
    actual_lines = [
        CostLine(
            dataset_version_id=sample_dataset_version_id,
            kind="actual",
            line_id="actual-1",
            identity={"item_code": "ITEM001"},
            total_cost=Decimal("10500.00"),
        ),
        CostLine(
            dataset_version_id=sample_dataset_version_id,
            kind="actual",
            line_id="actual-2",
            identity={"item_code": "ITEM999"},  # Unmatched - should be scope creep
            total_cost=Decimal("5000.00"),
        ),
    ]
    
    comparison_result = compare_boq_to_actuals(
        dataset_version_id=sample_dataset_version_id,
        boq_lines=boq_lines,
        actual_lines=actual_lines,
        config=cfg,
    )
    
    # Verify unmatched actual exists
    assert len(comparison_result.unmatched_actual) == 1
    assert comparison_result.unmatched_actual[0].line_id == "actual-2"
    
    # Detect scope creep
    scope_creep_variances = detect_scope_creep(
        comparison_result=comparison_result,
        category_field=None,
    )
    
    # Verify scope creep detected
    assert len(scope_creep_variances) == 1
    assert scope_creep_variances[0].scope_creep is True
    assert scope_creep_variances[0].severity == VarianceSeverity.SCOPE_CREEP
    assert scope_creep_variances[0].match_key.startswith("scope_creep|line_id=")
    assert scope_creep_variances[0].estimated_cost == Decimal("0")
    assert scope_creep_variances[0].actual_cost == Decimal("5000.00")
    assert scope_creep_variances[0].variance_amount == Decimal("5000.00")
    assert scope_creep_variances[0].line_ids_actual == ("actual-2",)
    assert scope_creep_variances[0].line_ids_boq == ()


@pytest.mark.anyio
async def test_scope_creep_with_category(sample_dataset_version_id: str) -> None:
    """Test that scope creep preserves category information."""
    cfg = ComparisonConfig(identity_fields=("item_code",))
    
    boq_lines = [
        CostLine(
            dataset_version_id=sample_dataset_version_id,
            kind="boq",
            line_id="boq-1",
            identity={"item_code": "ITEM001"},
            total_cost=Decimal("10000.00"),
        ),
    ]
    
    actual_lines = [
        CostLine(
            dataset_version_id=sample_dataset_version_id,
            kind="actual",
            line_id="actual-1",
            identity={"item_code": "ITEM999"},
            total_cost=Decimal("5000.00"),
            attributes={"category": "Unexpected Work"},
        ),
    ]
    
    comparison_result = compare_boq_to_actuals(
        dataset_version_id=sample_dataset_version_id,
        boq_lines=boq_lines,
        actual_lines=actual_lines,
        config=cfg,
    )
    
    scope_creep_variances = detect_scope_creep(
        comparison_result=comparison_result,
        category_field="category",
    )
    
    assert len(scope_creep_variances) == 1
    assert scope_creep_variances[0].category == "Unexpected Work"


@pytest.mark.anyio
async def test_scope_creep_labeled_in_report(
    sqlite_db: None, sample_dataset_version_id: str, sample_run_id: str
) -> None:
    """Test that scope creep is correctly labeled in report output."""
    cfg = ComparisonConfig(identity_fields=("item_code",))
    
    boq_lines = [
        CostLine(
            dataset_version_id=sample_dataset_version_id,
            kind="boq",
            line_id="boq-1",
            identity={"item_code": "ITEM001"},
            total_cost=Decimal("10000.00"),
        ),
    ]
    
    actual_lines = [
        CostLine(
            dataset_version_id=sample_dataset_version_id,
            kind="actual",
            line_id="actual-1",
            identity={"item_code": "ITEM001"},
            total_cost=Decimal("10500.00"),
        ),
        CostLine(
            dataset_version_id=sample_dataset_version_id,
            kind="actual",
            line_id="actual-2",
            identity={"item_code": "ITEM999"},
            total_cost=Decimal("5000.00"),
        ),
    ]
    
    comparison_result = compare_boq_to_actuals(
        dataset_version_id=sample_dataset_version_id,
        boq_lines=boq_lines,
        actual_lines=actual_lines,
        config=cfg,
    )
    
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        report = await assemble_cost_variance_report(
            db=db,
            dataset_version_id=sample_dataset_version_id,
            run_id=sample_run_id,
            comparison_result=comparison_result,
            created_at=datetime.now(timezone.utc),
            emit_evidence=False,
            persist_findings=False,
        )
    
    # Find cost variances section
    variances_section = next(
        (s for s in report["sections"] if s.get("section_id") == "cost_variances"),
        None,
    )
    assert variances_section is not None
    
    variances = variances_section.get("variances", [])
    assert len(variances) >= 1  # At least one variance (matched) plus scope creep
    
    # Find scope creep entry
    scope_creep_entries = [v for v in variances if v.get("scope_creep") is True]
    assert len(scope_creep_entries) == 1, "Should have exactly one scope creep entry"
    
    scope_creep_entry = scope_creep_entries[0]
    
    # Verify scope creep labeling
    assert scope_creep_entry["scope_creep"] is True
    assert scope_creep_entry["severity"] == "scope_creep"
    assert scope_creep_entry["match_key"].startswith("scope_creep|line_id=")
    assert scope_creep_entry["estimated_cost"] == "0"
    assert scope_creep_entry["actual_cost"] == "5000.00"
    assert scope_creep_entry["variance_amount"] == "5000.00"
    assert scope_creep_entry["line_ids_boq"] == []
    assert "actual-2" in scope_creep_entry["line_ids_actual"]


@pytest.mark.anyio
async def test_scope_creep_no_unmatched_actuals(sample_dataset_version_id: str) -> None:
    """Test that no scope creep is detected when all actuals are matched."""
    cfg = ComparisonConfig(identity_fields=("item_code",))
    
    boq_lines = [
        CostLine(
            dataset_version_id=sample_dataset_version_id,
            kind="boq",
            line_id="boq-1",
            identity={"item_code": "ITEM001"},
            total_cost=Decimal("10000.00"),
        ),
    ]
    
    actual_lines = [
        CostLine(
            dataset_version_id=sample_dataset_version_id,
            kind="actual",
            line_id="actual-1",
            identity={"item_code": "ITEM001"},
            total_cost=Decimal("10500.00"),
        ),
    ]
    
    comparison_result = compare_boq_to_actuals(
        dataset_version_id=sample_dataset_version_id,
        boq_lines=boq_lines,
        actual_lines=actual_lines,
        config=cfg,
    )
    
    # Verify no unmatched actuals
    assert len(comparison_result.unmatched_actual) == 0
    
    # Detect scope creep
    scope_creep_variances = detect_scope_creep(comparison_result=comparison_result)
    
    # Verify no scope creep detected
    assert len(scope_creep_variances) == 0


@pytest.mark.anyio
async def test_scope_creep_multiple_unmatched(sample_dataset_version_id: str) -> None:
    """Test that multiple unmatched actuals are all detected as scope creep."""
    cfg = ComparisonConfig(identity_fields=("item_code",))
    
    boq_lines = [
        CostLine(
            dataset_version_id=sample_dataset_version_id,
            kind="boq",
            line_id="boq-1",
            identity={"item_code": "ITEM001"},
            total_cost=Decimal("10000.00"),
        ),
    ]
    
    actual_lines = [
        CostLine(
            dataset_version_id=sample_dataset_version_id,
            kind="actual",
            line_id="actual-1",
            identity={"item_code": "ITEM999"},  # Unmatched
            total_cost=Decimal("5000.00"),
        ),
        CostLine(
            dataset_version_id=sample_dataset_version_id,
            kind="actual",
            line_id="actual-2",
            identity={"item_code": "ITEM998"},  # Unmatched
            total_cost=Decimal("3000.00"),
        ),
        CostLine(
            dataset_version_id=sample_dataset_version_id,
            kind="actual",
            line_id="actual-3",
            identity={"item_code": "ITEM001"},  # Matched
            total_cost=Decimal("10500.00"),
        ),
    ]
    
    comparison_result = compare_boq_to_actuals(
        dataset_version_id=sample_dataset_version_id,
        boq_lines=boq_lines,
        actual_lines=actual_lines,
        config=cfg,
    )
    
    # Verify two unmatched actuals
    assert len(comparison_result.unmatched_actual) == 2
    
    # Detect scope creep
    scope_creep_variances = detect_scope_creep(comparison_result=comparison_result)
    
    # Verify both detected as scope creep
    assert len(scope_creep_variances) == 2
    assert all(v.scope_creep is True for v in scope_creep_variances)
    assert all(v.severity == VarianceSeverity.SCOPE_CREEP for v in scope_creep_variances)
    
    # Verify they're sorted by match_key
    match_keys = [v.match_key for v in scope_creep_variances]
    assert match_keys == sorted(match_keys)


@pytest.mark.anyio
async def test_scope_creep_separate_from_variance(
    sqlite_db: None, sample_dataset_version_id: str, sample_run_id: str
) -> None:
    """Test that scope creep is separate from matched variances in reports."""
    cfg = ComparisonConfig(identity_fields=("item_code",))
    
    boq_lines = [
        CostLine(
            dataset_version_id=sample_dataset_version_id,
            kind="boq",
            line_id="boq-1",
            identity={"item_code": "ITEM001"},
            total_cost=Decimal("10000.00"),
        ),
        CostLine(
            dataset_version_id=sample_dataset_version_id,
            kind="boq",
            line_id="boq-2",
            identity={"item_code": "ITEM002"},
            total_cost=Decimal("20000.00"),
        ),
    ]
    
    actual_lines = [
        CostLine(
            dataset_version_id=sample_dataset_version_id,
            kind="actual",
            line_id="actual-1",
            identity={"item_code": "ITEM001"},
            total_cost=Decimal("10500.00"),  # Matched with 5% variance
        ),
        CostLine(
            dataset_version_id=sample_dataset_version_id,
            kind="actual",
            line_id="actual-2",
            identity={"item_code": "ITEM002"},
            total_cost=Decimal("22000.00"),  # Matched with 10% variance
        ),
        CostLine(
            dataset_version_id=sample_dataset_version_id,
            kind="actual",
            line_id="actual-3",
            identity={"item_code": "ITEM999"},  # Unmatched - scope creep
            total_cost=Decimal("5000.00"),
        ),
    ]
    
    comparison_result = compare_boq_to_actuals(
        dataset_version_id=sample_dataset_version_id,
        boq_lines=boq_lines,
        actual_lines=actual_lines,
        config=cfg,
    )
    
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        report = await assemble_cost_variance_report(
            db=db,
            dataset_version_id=sample_dataset_version_id,
            run_id=sample_run_id,
            comparison_result=comparison_result,
            created_at=datetime.now(timezone.utc),
            emit_evidence=False,
            persist_findings=False,
        )
    
    # Find cost variances section
    variances_section = next(
        (s for s in report["sections"] if s.get("section_id") == "cost_variances"),
        None,
    )
    assert variances_section is not None
    
    variances = variances_section.get("variances", [])
    
    # Should have 2 matched variances + 1 scope creep
    matched_variances = [v for v in variances if not v.get("scope_creep")]
    scope_creep_variances = [v for v in variances if v.get("scope_creep")]
    
    assert len(matched_variances) == 2, "Should have 2 matched variances"
    assert len(scope_creep_variances) == 1, "Should have 1 scope creep entry"
    
    # Verify matched variances don't have scope_creep flag
    assert all(not v.get("scope_creep") for v in matched_variances)
    assert all(v.get("severity") != "scope_creep" for v in matched_variances)
    
    # Verify scope creep entry
    assert scope_creep_variances[0]["scope_creep"] is True
    assert scope_creep_variances[0]["severity"] == "scope_creep"






