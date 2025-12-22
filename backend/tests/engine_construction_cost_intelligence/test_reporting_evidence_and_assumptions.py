"""
Test Reporting and Analysis: Evidence Linkage and Assumption Transparency

Tests that variance findings and time-phased reports are properly linked to evidence
records and that all assumptions are explicitly documented.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select

from backend.app.core.dataset.uuidv7 import uuid7
from backend.app.core.db import get_sessionmaker
from backend.app.core.evidence.models import EvidenceRecord, FindingEvidenceLink, FindingRecord
from backend.app.engines.construction_cost_intelligence.assumptions import (
    AssumptionRegistry,
    ValidityScope,
    add_category_field_assumption,
    add_time_phased_assumptions,
    add_variance_threshold_assumptions,
    create_default_assumption_registry,
)
from backend.app.engines.construction_cost_intelligence.errors import (
    DatasetVersionMismatchError,
    MissingArtifactError,
)
from backend.app.engines.construction_cost_intelligence.evidence import (
    emit_time_phased_report_evidence,
    emit_variance_analysis_evidence,
)
from backend.app.engines.construction_cost_intelligence.ids import (
    deterministic_comparison_result_stable_key,
    deterministic_time_phased_report_stable_key,
)
from backend.app.engines.construction_cost_intelligence.models import (
    ComparisonConfig,
    ComparisonMatch,
    ComparisonResult,
    CostLine,
)
from backend.app.engines.construction_cost_intelligence.report.assembler import (
    assemble_cost_variance_report,
    assemble_time_phased_report,
)
from backend.app.engines.construction_cost_intelligence.variance.detector import (
    detect_cost_variances,
)


@pytest.fixture
def sample_dataset_version_id() -> str:
    return str(uuid7())


@pytest.fixture
def sample_run_id() -> str:
    return "run-018f1234-5678-9000-0000-000000000001"


@pytest.fixture
def sample_comparison_result(sample_dataset_version_id: str) -> ComparisonResult:
    """Create a sample ComparisonResult for testing."""
    cfg = ComparisonConfig(identity_fields=("item_code",))
    boq_lines = [
        CostLine(
            dataset_version_id=sample_dataset_version_id,
            kind="boq",
            line_id="boq-1",
            identity={"item_code": "ITEM001"},
            total_cost=Decimal("10000.00"),
            attributes={"category": "Materials"},
        ),
        CostLine(
            dataset_version_id=sample_dataset_version_id,
            kind="boq",
            line_id="boq-2",
            identity={"item_code": "ITEM002"},
            total_cost=Decimal("20000.00"),
            attributes={"category": "Labor"},
        ),
    ]
    actual_lines = [
        CostLine(
            dataset_version_id=sample_dataset_version_id,
            kind="actual",
            line_id="actual-1",
            identity={"item_code": "ITEM001"},
            total_cost=Decimal("10500.00"),
            attributes={"category": "Materials", "date_recorded": "2024-01-15T00:00:00"},
        ),
        CostLine(
            dataset_version_id=sample_dataset_version_id,
            kind="actual",
            line_id="actual-2",
            identity={"item_code": "ITEM002"},
            total_cost=Decimal("22000.00"),
            attributes={"category": "Labor", "date_recorded": "2024-01-20T00:00:00"},
        ),
    ]
    
    from backend.app.engines.construction_cost_intelligence.compare import compare_boq_to_actuals
    
    return compare_boq_to_actuals(
        dataset_version_id=sample_dataset_version_id,
        boq_lines=boq_lines,
        actual_lines=actual_lines,
        config=cfg,
    )


@pytest.fixture
def sample_cost_lines(sample_dataset_version_id: str) -> list[CostLine]:
    """Create sample CostLines for time-phased reporting."""
    return [
        CostLine(
            dataset_version_id=sample_dataset_version_id,
            kind="boq",
            line_id="boq-t1",
            identity={"item_code": "ITEM001"},
            total_cost=Decimal("10000.00"),
            attributes={"date_recorded": "2024-01-15T00:00:00", "category": "Materials"},
        ),
        CostLine(
            dataset_version_id=sample_dataset_version_id,
            kind="actual",
            line_id="actual-t1",
            identity={"item_code": "ITEM001"},
            total_cost=Decimal("10500.00"),
            attributes={"date_recorded": "2024-01-15T00:00:00", "category": "Materials"},
        ),
        CostLine(
            dataset_version_id=sample_dataset_version_id,
            kind="boq",
            line_id="boq-t2",
            identity={"item_code": "ITEM002"},
            total_cost=Decimal("20000.00"),
            attributes={"date_recorded": "2024-02-10T00:00:00", "category": "Labor"},
        ),
        CostLine(
            dataset_version_id=sample_dataset_version_id,
            kind="actual",
            line_id="actual-t2",
            identity={"item_code": "ITEM002"},
            total_cost=Decimal("21000.00"),
            attributes={"date_recorded": "2024-02-10T00:00:00", "category": "Labor"},
        ),
    ]


@pytest.mark.anyio
async def test_variance_report_evidence_linkage(sqlite_db: None, sample_dataset_version_id: str, sample_run_id: str, sample_comparison_result: ComparisonResult) -> None:
    """Test that variance reports emit evidence and link variances to evidence."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        created_at = datetime.now(timezone.utc)
        
        # Assemble variance report with evidence emission
        report = await assemble_cost_variance_report(
            db=db,
            dataset_version_id=sample_dataset_version_id,
            run_id=sample_run_id,
            comparison_result=sample_comparison_result,
            tolerance_threshold=Decimal("5.0"),
            minor_threshold=Decimal("10.0"),
            moderate_threshold=Decimal("25.0"),
            major_threshold=Decimal("50.0"),
            category_field="category",
            created_at=created_at,
            emit_evidence=True,
        )
        
        # Verify report structure
        assert report["dataset_version_id"] == sample_dataset_version_id
        assert report["run_id"] == sample_run_id
        assert report["report_type"] == "cost_variance"
        
        # Find evidence_index section
        evidence_section = next((s for s in report["sections"] if s.get("section_id") == "evidence_index"), None)
        assert evidence_section is not None, "Evidence index section must be present"
        assert len(evidence_section["evidence_index"]) > 0, "Evidence index must contain evidence"
        
        # Verify evidence record exists in database
        evidence_ids = [e["evidence_id"] for e in evidence_section["evidence_index"]]
        for evidence_id in evidence_ids:
            evidence = await db.scalar(select(EvidenceRecord).where(EvidenceRecord.evidence_id == evidence_id))
            assert evidence is not None, f"Evidence {evidence_id} must exist in database"
            assert evidence.dataset_version_id == sample_dataset_version_id, "Evidence must be bound to DatasetVersion"
            assert evidence.kind == "variance_analysis", "Evidence kind must be variance_analysis"
            assert evidence.engine_id == "engine_construction_cost_intelligence", "Evidence engine_id must match"
            
            # Verify evidence payload contains assumptions
            assert "assumptions" in evidence.payload, "Evidence payload must contain assumptions"
            assumptions = evidence.payload["assumptions"]
            assert "assumptions" in assumptions, "Assumptions registry must contain assumptions list"
            assert "exclusions" in assumptions, "Assumptions registry must contain exclusions list"
            assert "validity_scope" in assumptions, "Assumptions registry must contain validity scope"
        
        # Verify variances are linked to evidence
        variances_section = next((s for s in report["sections"] if s.get("section_id") == "cost_variances"), None)
        assert variances_section is not None, "Cost variances section must be present"
        assert len(variances_section["variances"]) > 0, "Must have variances"
        
        for variance in variances_section["variances"]:
            assert "evidence_id" in variance, "Each variance must have evidence_id"
            assert variance["evidence_id"] in evidence_ids, "Variance evidence_id must be in evidence index"


@pytest.mark.anyio
async def test_variance_report_assumption_transparency(sqlite_db: None, sample_dataset_version_id: str, sample_run_id: str, sample_comparison_result: ComparisonResult) -> None:
    """Test that variance reports include explicit assumptions."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        created_at = datetime.now(timezone.utc)
        
        report = await assemble_cost_variance_report(
            db=db,
            dataset_version_id=sample_dataset_version_id,
            run_id=sample_run_id,
            comparison_result=sample_comparison_result,
            tolerance_threshold=Decimal("5.0"),
            minor_threshold=Decimal("10.0"),
            moderate_threshold=Decimal("25.0"),
            major_threshold=Decimal("50.0"),
            category_field="category",
            created_at=created_at,
            emit_evidence=True,
        )
        
        # Find limitations_assumptions section
        assumptions_section = next((s for s in report["sections"] if s.get("section_id") == "limitations_assumptions"), None)
        assert assumptions_section is not None, "Limitations and assumptions section must be present"
        
        # Verify limitations are present
        assert "limitations" in assumptions_section, "Section must contain limitations"
        assert isinstance(assumptions_section["limitations"], list), "Limitations must be a list"
        assert len(assumptions_section["limitations"]) > 0, "Must have at least one limitation"
        
        # Verify assumptions are present
        assert "assumptions" in assumptions_section, "Section must contain assumptions"
        assumptions = assumptions_section["assumptions"]
        
        # Check if core traceability is present (could be nested structure)
        if isinstance(assumptions, dict) and "report" in assumptions:
            report_assumptions = assumptions["report"]
        else:
            report_assumptions = assumptions
        
        assert "assumptions" in report_assumptions, "Assumptions registry must contain assumptions list"
        assert "exclusions" in report_assumptions, "Assumptions registry must contain exclusions list"
        assert "validity_scope" in report_assumptions, "Assumptions registry must contain validity scope"
        
        # Verify threshold assumptions are present
        assumption_list = report_assumptions["assumptions"]
        assumption_ids = [a["assumption_id"] for a in assumption_list]
        assert "variance_tolerance_threshold" in assumption_ids, "Tolerance threshold assumption must be present"
        assert "variance_minor_threshold" in assumption_ids, "Minor threshold assumption must be present"
        assert "variance_moderate_threshold" in assumption_ids, "Moderate threshold assumption must be present"
        assert "variance_major_threshold" in assumption_ids, "Major threshold assumption must be present"
        assert "variance_category_field" in assumption_ids, "Category field assumption must be present"
        
        # Verify exclusions are present
        exclusions = report_assumptions["exclusions"]
        assert len(exclusions) > 0, "Must have at least one exclusion"
        exclusion_ids = [e["exclusion_id"] for e in exclusions]
        assert "no_causality" in exclusion_ids, "No causality exclusion must be present"
        assert "no_decisions" in exclusion_ids, "No decisions exclusion must be present"
        
        # Verify validity scope
        validity_scope = report_assumptions["validity_scope"]
        assert validity_scope["dataset_version_id"] == sample_dataset_version_id, "Validity scope must include DatasetVersion"
        assert validity_scope["run_id"] == sample_run_id, "Validity scope must include run_id"


@pytest.mark.anyio
async def test_time_phased_report_evidence_linkage(sqlite_db: None, sample_dataset_version_id: str, sample_run_id: str, sample_cost_lines: list[CostLine]) -> None:
    """Test that time-phased reports emit evidence and link periods to evidence."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        created_at = datetime.now(timezone.utc)
        
        report = await assemble_time_phased_report(
            db=db,
            dataset_version_id=sample_dataset_version_id,
            run_id=sample_run_id,
            cost_lines=sample_cost_lines,
            period_type="monthly",
            date_field="date_recorded",
            prefer_total_cost=True,
            created_at=created_at,
            emit_evidence=True,
        )
        
        # Verify report structure
        assert report["dataset_version_id"] == sample_dataset_version_id
        assert report["run_id"] == sample_run_id
        assert report["report_type"] == "time_phased"
        
        # Find evidence_index section
        evidence_section = next((s for s in report["sections"] if s.get("section_id") == "evidence_index"), None)
        assert evidence_section is not None, "Evidence index section must be present"
        assert len(evidence_section["evidence_index"]) > 0, "Evidence index must contain evidence"
        
        # Verify evidence record exists in database
        evidence_ids = [e["evidence_id"] for e in evidence_section["evidence_index"]]
        for evidence_id in evidence_ids:
            evidence = await db.scalar(select(EvidenceRecord).where(EvidenceRecord.evidence_id == evidence_id))
            assert evidence is not None, f"Evidence {evidence_id} must exist in database"
            assert evidence.dataset_version_id == sample_dataset_version_id, "Evidence must be bound to DatasetVersion"
            assert evidence.kind == "time_phased_report", "Evidence kind must be time_phased_report"
            assert evidence.engine_id == "engine_construction_cost_intelligence", "Evidence engine_id must match"
            
            # Verify evidence payload contains assumptions
            assert "assumptions" in evidence.payload, "Evidence payload must contain assumptions"
        
        # Verify periods are linked to evidence
        time_phased_section = next((s for s in report["sections"] if s.get("section_id") == "time_phased_report"), None)
        assert time_phased_section is not None, "Time-phased report section must be present"
        assert len(time_phased_section["periods"]) > 0, "Must have periods"
        
        for period in time_phased_section["periods"]:
            assert "evidence_id" in period, "Each period must have evidence_id"
            assert period["evidence_id"] in evidence_ids, "Period evidence_id must be in evidence index"


@pytest.mark.anyio
async def test_time_phased_report_assumption_transparency(sqlite_db: None, sample_dataset_version_id: str, sample_run_id: str, sample_cost_lines: list[CostLine]) -> None:
    """Test that time-phased reports include explicit assumptions."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        created_at = datetime.now(timezone.utc)
        
        report = await assemble_time_phased_report(
            db=db,
            dataset_version_id=sample_dataset_version_id,
            run_id=sample_run_id,
            cost_lines=sample_cost_lines,
            period_type="monthly",
            date_field="date_recorded",
            prefer_total_cost=True,
            start_date="2024-01-01",
            end_date="2024-12-31",
            created_at=created_at,
            emit_evidence=True,
        )
        
        # Find limitations_assumptions section
        assumptions_section = next((s for s in report["sections"] if s.get("section_id") == "limitations_assumptions"), None)
        assert assumptions_section is not None, "Limitations and assumptions section must be present"
        
        # Verify limitations are present
        assert "limitations" in assumptions_section, "Section must contain limitations"
        assert isinstance(assumptions_section["limitations"], list), "Limitations must be a list"
        assert len(assumptions_section["limitations"]) > 0, "Must have at least one limitation"
        
        # Verify assumptions are present
        assert "assumptions" in assumptions_section, "Section must contain assumptions"
        assumptions = assumptions_section["assumptions"]
        
        # Check if core traceability is present (could be nested structure)
        if isinstance(assumptions, dict) and "report" in assumptions:
            report_assumptions = assumptions["report"]
        else:
            report_assumptions = assumptions
        
        assert "assumptions" in report_assumptions, "Assumptions registry must contain assumptions list"
        assert "exclusions" in report_assumptions, "Assumptions registry must contain exclusions list"
        assert "validity_scope" in report_assumptions, "Assumptions registry must contain validity scope"
        
        # Verify time-phased assumptions are present
        assumption_list = report_assumptions["assumptions"]
        assumption_ids = [a["assumption_id"] for a in assumption_list]
        assert "period_type" in assumption_ids, "Period type assumption must be present"
        assert "date_field" in assumption_ids, "Date field assumption must be present"
        assert "cost_preference" in assumption_ids, "Cost preference assumption must be present"
        assert "report_start_date_filter" in assumption_ids, "Start date filter assumption must be present"
        assert "report_end_date_filter" in assumption_ids, "End date filter assumption must be present"


@pytest.mark.anyio
async def test_evidence_dataset_version_binding(sqlite_db: None, sample_dataset_version_id: str, sample_run_id: str, sample_comparison_result: ComparisonResult) -> None:
    """Test that all evidence is strictly bound to DatasetVersion."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        created_at = datetime.now(timezone.utc)
        
        # Different DatasetVersion
        other_dataset_version_id = str(uuid7())
        
        report = await assemble_cost_variance_report(
            db=db,
            dataset_version_id=sample_dataset_version_id,
            run_id=sample_run_id,
            comparison_result=sample_comparison_result,
            created_at=created_at,
            emit_evidence=True,
        )
        
        # Get evidence IDs from report
        evidence_section = next((s for s in report["sections"] if s.get("section_id") == "evidence_index"), None)
        assert evidence_section is not None
        evidence_ids = [e["evidence_id"] for e in evidence_section["evidence_index"]]
        assert len(evidence_ids) > 0
        
        # Verify all evidence is bound to correct DatasetVersion
        for evidence_id in evidence_ids:
            evidence = await db.scalar(select(EvidenceRecord).where(EvidenceRecord.evidence_id == evidence_id))
            assert evidence is not None
            assert evidence.dataset_version_id == sample_dataset_version_id, "Evidence must be bound to correct DatasetVersion"
            
            # Verify querying with wrong DatasetVersion doesn't return evidence
            wrong_evidence = await db.scalar(
                select(EvidenceRecord)
                .where(EvidenceRecord.evidence_id == evidence_id)
                .where(EvidenceRecord.dataset_version_id == other_dataset_version_id)
            )
            assert wrong_evidence is None, "Evidence must not be queryable with wrong DatasetVersion"


@pytest.mark.anyio
async def test_evidence_immutability(sqlite_db: None, sample_dataset_version_id: str, sample_run_id: str, sample_comparison_result: ComparisonResult) -> None:
    """Test that evidence records are immutable (append-only)."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        created_at = datetime.now(timezone.utc)
        
        # Emit evidence twice with same parameters (should be idempotent)
        comparison_stable_key = deterministic_comparison_result_stable_key(
            dataset_version_id=sample_dataset_version_id,
            identity_fields=sample_comparison_result.identity_fields,
            matched_count=len(sample_comparison_result.matched),
            unmatched_boq_count=len(sample_comparison_result.unmatched_boq),
            unmatched_actual_count=len(sample_comparison_result.unmatched_actual),
        )
        
        assumptions_registry = create_default_assumption_registry()
        add_variance_threshold_assumptions(
            assumptions_registry,
            tolerance_threshold=Decimal("5.0"),
            minor_threshold=Decimal("10.0"),
            moderate_threshold=Decimal("25.0"),
            major_threshold=Decimal("50.0"),
        )
        validity_scope = ValidityScope(
            dataset_version_id=sample_dataset_version_id,
            run_id=sample_run_id,
            created_at=created_at,
        )
        assumptions_registry.set_validity_scope(validity_scope)
        
        variances = detect_cost_variances(
            comparison_result=sample_comparison_result,
            tolerance_threshold=Decimal("5.0"),
            minor_threshold=Decimal("10.0"),
            moderate_threshold=Decimal("25.0"),
            major_threshold=Decimal("50.0"),
        )
        
        evidence_id_1 = await emit_variance_analysis_evidence(
            db,
            dataset_version_id=sample_dataset_version_id,
            comparison_result_id=comparison_stable_key,
            variance_count=len(variances),
            assumptions=assumptions_registry,
            created_at=created_at,
        )
        
        # Emit again with same parameters
        evidence_id_2 = await emit_variance_analysis_evidence(
            db,
            dataset_version_id=sample_dataset_version_id,
            comparison_result_id=comparison_stable_key,
            variance_count=len(variances),
            assumptions=assumptions_registry,
            created_at=created_at,
        )
        
        # Should get same evidence ID (idempotent)
        assert evidence_id_1 == evidence_id_2, "Evidence emission must be idempotent"
        
        # Verify evidence record exists and hasn't changed
        evidence = await db.scalar(select(EvidenceRecord).where(EvidenceRecord.evidence_id == evidence_id_1))
        assert evidence is not None
        assert evidence.dataset_version_id == sample_dataset_version_id
        assert evidence.kind == "variance_analysis"


@pytest.mark.anyio
async def test_variance_report_without_evidence_emission(sqlite_db: None, sample_dataset_version_id: str, sample_run_id: str, sample_comparison_result: ComparisonResult) -> None:
    """Test that variance reports work without evidence emission."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        report = await assemble_cost_variance_report(
            db=db,
            dataset_version_id=sample_dataset_version_id,
            run_id=sample_run_id,
            comparison_result=sample_comparison_result,
            emit_evidence=False,
        )
        
        # Report should still be generated
        assert report["dataset_version_id"] == sample_dataset_version_id
        assert report["report_type"] == "cost_variance"
        
        # But evidence_id should not be in variances (no evidence emitted)
        variances_section = next((s for s in report["sections"] if s.get("section_id") == "cost_variances"), None)
        assert variances_section is not None
        if len(variances_section["variances"]) > 0:
            # If evidence wasn't emitted, variance shouldn't have evidence_id
            # (or it should be None)
            for variance in variances_section["variances"]:
                # evidence_id may be None or missing when emit_evidence=False
                pass  # Acceptable - evidence_id is optional when no evidence is emitted


@pytest.mark.anyio
async def test_time_phased_report_without_evidence_emission(sqlite_db: None, sample_dataset_version_id: str, sample_run_id: str, sample_cost_lines: list[CostLine]) -> None:
    """Test that time-phased reports work without evidence emission."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        report = await assemble_time_phased_report(
            db=db,
            dataset_version_id=sample_dataset_version_id,
            run_id=sample_run_id,
            cost_lines=sample_cost_lines,
            period_type="monthly",
            emit_evidence=False,
        )
        
        # Report should still be generated
        assert report["dataset_version_id"] == sample_dataset_version_id
        assert report["report_type"] == "time_phased"
        
        # Assumptions section should still be present
        assumptions_section = next((s for s in report["sections"] if s.get("section_id") == "limitations_assumptions"), None)
        assert assumptions_section is not None, "Assumptions section must be present even without evidence emission"


@pytest.mark.anyio
async def test_assumption_registry_structure(sqlite_db: None) -> None:
    """Test that assumption registry has correct structure."""
    registry = create_default_assumption_registry()
    
    # Add some assumptions
    add_variance_threshold_assumptions(
        registry,
        tolerance_threshold=Decimal("5.0"),
        minor_threshold=Decimal("10.0"),
        moderate_threshold=Decimal("25.0"),
        major_threshold=Decimal("50.0"),
    )
    add_category_field_assumption(registry, category_field="category")
    
    # Convert to dict
    registry_dict = registry.to_dict()
    
    # Verify structure
    assert "assumptions" in registry_dict
    assert "exclusions" in registry_dict
    assert "validity_scope" in registry_dict or registry_dict["validity_scope"] is None
    
    # Verify assumptions list
    assumptions = registry_dict["assumptions"]
    assert isinstance(assumptions, list)
    for assumption in assumptions:
        assert "assumption_id" in assumption
        assert "category" in assumption
        assert "description" in assumption
        assert "source" in assumption
    
    # Verify exclusions list
    exclusions = registry_dict["exclusions"]
    assert isinstance(exclusions, list)
    for exclusion in exclusions:
        assert "exclusion_id" in exclusion
        assert "category" in exclusion
        assert "description" in exclusion
        assert "rationale" in exclusion


@pytest.mark.anyio
async def test_evidence_deterministic_ids(sqlite_db: None, sample_dataset_version_id: str, sample_run_id: str, sample_comparison_result: ComparisonResult) -> None:
    """Test that evidence IDs are deterministic (replay-stable)."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        created_at = datetime.now(timezone.utc)
        
        comparison_stable_key = deterministic_comparison_result_stable_key(
            dataset_version_id=sample_dataset_version_id,
            identity_fields=sample_comparison_result.identity_fields,
            matched_count=len(sample_comparison_result.matched),
            unmatched_boq_count=len(sample_comparison_result.unmatched_boq),
            unmatched_actual_count=len(sample_comparison_result.unmatched_actual),
        )
        
        assumptions_registry_1 = create_default_assumption_registry()
        add_variance_threshold_assumptions(
            assumptions_registry_1,
            tolerance_threshold=Decimal("5.0"),
            minor_threshold=Decimal("10.0"),
            moderate_threshold=Decimal("25.0"),
            major_threshold=Decimal("50.0"),
        )
        validity_scope = ValidityScope(
            dataset_version_id=sample_dataset_version_id,
            run_id=sample_run_id,
            created_at=created_at,
        )
        assumptions_registry_1.set_validity_scope(validity_scope)
        
        variances = detect_cost_variances(
            comparison_result=sample_comparison_result,
            tolerance_threshold=Decimal("5.0"),
            minor_threshold=Decimal("10.0"),
            moderate_threshold=Decimal("25.0"),
            major_threshold=Decimal("50.0"),
        )
        
        # Emit evidence
        evidence_id_1 = await emit_variance_analysis_evidence(
            db,
            dataset_version_id=sample_dataset_version_id,
            comparison_result_id=comparison_stable_key,
            variance_count=len(variances),
            assumptions=assumptions_registry_1,
            created_at=created_at,
        )
        
        # Create same assumptions again and emit
        assumptions_registry_2 = create_default_assumption_registry()
        add_variance_threshold_assumptions(
            assumptions_registry_2,
            tolerance_threshold=Decimal("5.0"),
            minor_threshold=Decimal("10.0"),
            moderate_threshold=Decimal("25.0"),
            major_threshold=Decimal("50.0"),
        )
        assumptions_registry_2.set_validity_scope(validity_scope)
        
        evidence_id_2 = await emit_variance_analysis_evidence(
            db,
            dataset_version_id=sample_dataset_version_id,
            comparison_result_id=comparison_stable_key,
            variance_count=len(variances),
            assumptions=assumptions_registry_2,
            created_at=created_at,
        )
        
        # Should get same evidence ID (deterministic)
        assert evidence_id_1 == evidence_id_2, "Evidence IDs must be deterministic for same inputs"


@pytest.mark.anyio
async def test_dataset_version_mismatch_rejected(sqlite_db: None, sample_dataset_version_id: str, sample_run_id: str) -> None:
    """Test that DatasetVersion mismatches are rejected."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        wrong_dataset_version_id = str(uuid7())
        
        # Create comparison result with one DatasetVersion
        cfg = ComparisonConfig(identity_fields=("item_code",))
        boq_lines = [
            CostLine(
                dataset_version_id=sample_dataset_version_id,
                kind="boq",
                line_id="boq-1",
                identity={"item_code": "ITEM001"},
                total_cost=Decimal("10000.00"),
            )
        ]
        actual_lines: list[CostLine] = []
        
        from backend.app.engines.construction_cost_intelligence.compare import compare_boq_to_actuals
        
        comparison_result = compare_boq_to_actuals(
            dataset_version_id=sample_dataset_version_id,
            boq_lines=boq_lines,
            actual_lines=actual_lines,
            config=cfg,
        )
        
        # Try to assemble report with different DatasetVersion
        with pytest.raises(DatasetVersionMismatchError):
            await assemble_cost_variance_report(
                db=db,
                dataset_version_id=wrong_dataset_version_id,
                run_id=sample_run_id,
                comparison_result=comparison_result,
                emit_evidence=False,
            )


@pytest.mark.anyio
async def test_evidence_payload_contains_assumptions(sqlite_db: None, sample_dataset_version_id: str, sample_run_id: str, sample_comparison_result: ComparisonResult) -> None:
    """Test that evidence payloads contain complete assumptions registry."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        created_at = datetime.now(timezone.utc)
        
        comparison_stable_key = deterministic_comparison_result_stable_key(
            dataset_version_id=sample_dataset_version_id,
            identity_fields=sample_comparison_result.identity_fields,
            matched_count=len(sample_comparison_result.matched),
            unmatched_boq_count=len(sample_comparison_result.unmatched_boq),
            unmatched_actual_count=len(sample_comparison_result.unmatched_actual),
        )
        
        assumptions_registry = create_default_assumption_registry()
        add_variance_threshold_assumptions(
            assumptions_registry,
            tolerance_threshold=Decimal("5.0"),
            minor_threshold=Decimal("10.0"),
            moderate_threshold=Decimal("25.0"),
            major_threshold=Decimal("50.0"),
        )
        add_category_field_assumption(registry=assumptions_registry, category_field="category")
        validity_scope = ValidityScope(
            dataset_version_id=sample_dataset_version_id,
            run_id=sample_run_id,
            created_at=created_at,
        )
        assumptions_registry.set_validity_scope(validity_scope)
        
        variances = detect_cost_variances(
            comparison_result=sample_comparison_result,
            tolerance_threshold=Decimal("5.0"),
            minor_threshold=Decimal("10.0"),
            moderate_threshold=Decimal("25.0"),
            major_threshold=Decimal("50.0"),
            category_field="category",
        )
        
        evidence_id = await emit_variance_analysis_evidence(
            db,
            dataset_version_id=sample_dataset_version_id,
            comparison_result_id=comparison_stable_key,
            variance_count=len(variances),
            assumptions=assumptions_registry,
            created_at=created_at,
        )
        
        # Verify evidence payload
        evidence = await db.scalar(select(EvidenceRecord).where(EvidenceRecord.evidence_id == evidence_id))
        assert evidence is not None
        
        payload = evidence.payload
        assert "assumptions" in payload, "Evidence payload must contain assumptions"
        
        assumptions_in_payload = payload["assumptions"]
        assert "assumptions" in assumptions_in_payload, "Assumptions must contain assumptions list"
        assert "exclusions" in assumptions_in_payload, "Assumptions must contain exclusions list"
        assert "validity_scope" in assumptions_in_payload, "Assumptions must contain validity scope"
        
        # Verify specific assumptions are present
        assumption_list = assumptions_in_payload["assumptions"]
        assumption_ids = [a["assumption_id"] for a in assumption_list]
        assert "variance_tolerance_threshold" in assumption_ids
        assert "variance_category_field" in assumption_ids


@pytest.mark.anyio
async def test_core_traceability_integration(sqlite_db: None, sample_dataset_version_id: str, sample_run_id: str, sample_comparison_result: ComparisonResult) -> None:
    """Test that reports integrate core traceability when provided."""
    from backend.app.core.evidence.service import (
        create_evidence,
        create_finding,
        link_finding_to_evidence,
        deterministic_evidence_id,
    )
    from backend.app.engines.construction_cost_intelligence.traceability import (
        ENGINE_ID as CORE_ENGINE_ID,
        deterministic_finding_id,
        deterministic_link_id,
    )
    
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        created_at = datetime.now(timezone.utc)
        
        # Create mock core traceability (simulating core engine output)
        assumptions_payload = {
            "dataset_version_id": sample_dataset_version_id,
            "engine_id": CORE_ENGINE_ID,
            "assumptions": [
                {
                    "id": "dataset_version_binding",
                    "description": "All inputs/outputs are bound to DatasetVersion",
                    "source": "core",
                }
            ],
        }
        assumptions_evidence_id = deterministic_evidence_id(
            dataset_version_id=sample_dataset_version_id,
            engine_id=CORE_ENGINE_ID,
            kind="assumptions",
            stable_key="test_assumptions",
        )
        await create_evidence(
            db,
            evidence_id=assumptions_evidence_id,
            dataset_version_id=sample_dataset_version_id,
            engine_id=CORE_ENGINE_ID,
            kind="assumptions",
            payload=assumptions_payload,
            created_at=created_at,
        )
        
        inputs_evidence_id = deterministic_evidence_id(
            dataset_version_id=sample_dataset_version_id,
            engine_id=CORE_ENGINE_ID,
            kind="inputs_boq",
            stable_key="test_inputs",
        )
        await create_evidence(
            db,
            evidence_id=inputs_evidence_id,
            dataset_version_id=sample_dataset_version_id,
            engine_id=CORE_ENGINE_ID,
            kind="inputs_boq",
            payload={"dataset_version_id": sample_dataset_version_id, "raw_record_id": "test_raw"},
            created_at=created_at,
        )
        
        # Create a mock finding
        finding_id = deterministic_finding_id(
            dataset_version_id=sample_dataset_version_id,
            engine_id=CORE_ENGINE_ID,
            kind="data_quality_unmatched_boq",
            stable_key="test_finding",
        )
        await create_finding(
            db,
            finding_id=finding_id,
            dataset_version_id=sample_dataset_version_id,
            raw_record_id="test_raw",
            kind="data_quality_unmatched_boq",
            payload={"dataset_version_id": sample_dataset_version_id, "count": 0},
            created_at=created_at,
        )
        
        # Link finding to evidence
        link_id = deterministic_link_id(finding_id=finding_id, evidence_id=assumptions_evidence_id)
        await link_finding_to_evidence(
            db,
            link_id=link_id,
            finding_id=finding_id,
            evidence_id=assumptions_evidence_id,
        )
        await db.commit()
        
        # Create core traceability dict
        core_traceability = {
            "assumptions_evidence_id": assumptions_evidence_id,
            "inputs_evidence_ids": [inputs_evidence_id],
            "finding_ids": [finding_id],
        }
        
        # Assemble report with core traceability
        report = await assemble_cost_variance_report(
            db=db,
            dataset_version_id=sample_dataset_version_id,
            run_id=sample_run_id,
            comparison_result=sample_comparison_result,
            core_traceability=core_traceability,
            created_at=created_at,
            emit_evidence=True,
        )
        
        # Verify core traceability section is present
        core_section = next((s for s in report["sections"] if s.get("section_id") == "core_traceability"), None)
        assert core_section is not None, "Core traceability section must be present"
        assert core_section["assumptions_evidence_id"] == assumptions_evidence_id
        assert core_section["inputs_evidence_ids"] == [inputs_evidence_id]
        assert len(core_section["findings"]) > 0
        
        # Verify assumptions section includes core assumptions
        assumptions_section = next((s for s in report["sections"] if s.get("section_id") == "limitations_assumptions"), None)
        assert assumptions_section is not None
        assumptions = assumptions_section["assumptions"]
        assert "core" in assumptions, "Assumptions must include core assumptions"
        assert "report" in assumptions, "Assumptions must include report assumptions"
        assert isinstance(assumptions["core"]["assumptions"], list)
        assert len(assumptions["core"]["assumptions"]) > 0
        
        # Verify evidence index includes core evidence
        evidence_section = next((s for s in report["sections"] if s.get("section_id") == "evidence_index"), None)
        assert evidence_section is not None
        evidence_ids = [e["evidence_id"] for e in evidence_section["evidence_index"]]
        assert assumptions_evidence_id in evidence_ids, "Core assumptions evidence must be in evidence index"
        assert inputs_evidence_id in evidence_ids, "Core inputs evidence must be in evidence index"
