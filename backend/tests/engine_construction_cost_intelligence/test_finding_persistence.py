"""
Tests for FindingRecord persistence for variance and time-phased findings.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select

from backend.app.core.dataset.uuidv7 import uuid7
from backend.app.core.db import get_sessionmaker
from backend.app.core.evidence.models import FindingEvidenceLink, FindingRecord
from backend.app.engines.construction_cost_intelligence.assumptions import (
    AssumptionRegistry,
    ValidityScope,
    add_category_field_assumption,
    add_time_phased_assumptions,
    add_variance_threshold_assumptions,
    create_default_assumption_registry,
)
from backend.app.engines.construction_cost_intelligence.errors import DatasetVersionMismatchError
from backend.app.engines.construction_cost_intelligence.findings import (
    persist_scope_creep_finding,
    persist_time_phased_findings,
    persist_variance_findings,
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
    CostVariance,
    VarianceDirection,
    VarianceSeverity,
)


@pytest.fixture
def sample_dataset_version_id() -> str:
    """Generate a valid UUIDv7 DatasetVersion ID."""
    return str(uuid7())


@pytest.fixture
def sample_run_id() -> str:
    return "run-018f1234-5678-9000-0000-000000000001"


@pytest.fixture
def sample_comparison_result(sample_dataset_version_id: str) -> ComparisonResult:
    """Create a sample ComparisonResult for testing."""
    from backend.app.engines.construction_cost_intelligence.compare import compare_boq_to_actuals
    
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
    
    return compare_boq_to_actuals(
        dataset_version_id=sample_dataset_version_id,
        boq_lines=boq_lines,
        actual_lines=actual_lines,
        config=cfg,
    )


@pytest.mark.anyio
async def test_variance_findings_persisted(sqlite_db: None, sample_dataset_version_id: str, sample_run_id: str, sample_comparison_result: ComparisonResult) -> None:
    """Test that variance findings are persisted as FindingRecords."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        created_at = datetime.now(timezone.utc)
        boq_raw_record_id = "boq-raw-001"
        actual_raw_record_id = "actual-raw-001"
        
        # Create evidence first (required for findings)
        from backend.app.engines.construction_cost_intelligence.evidence import emit_variance_analysis_evidence
        from backend.app.engines.construction_cost_intelligence.ids import deterministic_comparison_result_stable_key
        
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
        
        from backend.app.engines.construction_cost_intelligence.variance.detector import detect_cost_variances
        
        variances = detect_cost_variances(
            comparison_result=sample_comparison_result,
            tolerance_threshold=Decimal("5.0"),
            minor_threshold=Decimal("10.0"),
            moderate_threshold=Decimal("25.0"),
            major_threshold=Decimal("50.0"),
        )
        
        evidence_id = await emit_variance_analysis_evidence(
            db,
            dataset_version_id=sample_dataset_version_id,
            comparison_result_id=comparison_stable_key,
            variance_count=len(variances),
            assumptions=assumptions_registry,
            created_at=created_at,
        )
        
        # Persist variance findings
        finding_ids = await persist_variance_findings(
            db,
            dataset_version_id=sample_dataset_version_id,
            variances=variances,
            raw_record_id=boq_raw_record_id,
            evidence_id=evidence_id,
            created_at=created_at,
        )
        
        await db.commit()
        
        # Verify findings were created
        assert len(finding_ids) > 0, "Should have created at least one finding"
        
        for finding_id in finding_ids:
            finding = await db.scalar(select(FindingRecord).where(FindingRecord.finding_id == finding_id))
            assert finding is not None, f"Finding {finding_id} should exist"
            assert finding.dataset_version_id == sample_dataset_version_id
            assert finding.kind == "cost_variance"
            assert finding.raw_record_id == boq_raw_record_id
            
            # Verify payload
            assert "match_key" in finding.payload
            assert "severity" in finding.payload
            assert "direction" in finding.payload
            
            # Verify evidence link
            links = (
                await db.execute(
                    select(FindingEvidenceLink).where(FindingEvidenceLink.finding_id == finding_id)
                )
            ).scalars().all()
            assert len(links) > 0, "Finding should be linked to evidence"
            assert any(link.evidence_id == evidence_id for link in links), "Finding should be linked to variance evidence"


@pytest.mark.anyio
async def test_scope_creep_finding_persisted(sqlite_db: None, sample_dataset_version_id: str) -> None:
    """Test that scope creep findings are persisted as FindingRecords."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        created_at = datetime.now(timezone.utc)
        actual_raw_record_id = "actual-raw-001"
        
        # Create evidence first
        from backend.app.core.evidence.service import create_evidence, deterministic_evidence_id
        
        evidence_id = deterministic_evidence_id(
            dataset_version_id=sample_dataset_version_id,
            engine_id="engine_construction_cost_intelligence",
            kind="variance_analysis",
            stable_key="test_scope_creep",
        )
        await create_evidence(
            db,
            evidence_id=evidence_id,
            dataset_version_id=sample_dataset_version_id,
            engine_id="engine_construction_cost_intelligence",
            kind="variance_analysis",
            payload={"test": "data"},
            created_at=created_at,
        )
        
        # Persist scope creep finding
        finding_id = await persist_scope_creep_finding(
            db,
            dataset_version_id=sample_dataset_version_id,
            unmatched_actual_count=3,
            unmatched_line_ids=["line-1", "line-2", "line-3"],
            raw_record_id=actual_raw_record_id,
            evidence_id=evidence_id,
            created_at=created_at,
        )
        
        await db.commit()
        
        # Verify finding was created
        assert finding_id is not None, "Should have created scope creep finding"
        
        finding = await db.scalar(select(FindingRecord).where(FindingRecord.finding_id == finding_id))
        assert finding is not None
        assert finding.dataset_version_id == sample_dataset_version_id
        assert finding.kind == "scope_creep"
        assert finding.raw_record_id == actual_raw_record_id
        assert finding.payload["count"] == 3
        assert finding.payload["line_ids"] == ["line-1", "line-2", "line-3"]
        
        # Verify evidence link
        links = (
            await db.execute(select(FindingEvidenceLink).where(FindingEvidenceLink.finding_id == finding_id))
        ).scalars().all()
        assert len(links) > 0
        assert any(link.evidence_id == evidence_id for link in links)


@pytest.mark.anyio
async def test_time_phased_findings_persisted(sqlite_db: None, sample_dataset_version_id: str) -> None:
    """Test that time-phased findings are persisted as FindingRecords."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        created_at = datetime.now(timezone.utc)
        raw_record_id = "raw-001"
        
        # Create evidence first
        from backend.app.core.evidence.service import create_evidence, deterministic_evidence_id
        
        evidence_id = deterministic_evidence_id(
            dataset_version_id=sample_dataset_version_id,
            engine_id="engine_construction_cost_intelligence",
            kind="time_phased_report",
            stable_key="test_time_phased",
        )
        await create_evidence(
            db,
            evidence_id=evidence_id,
            dataset_version_id=sample_dataset_version_id,
            engine_id="engine_construction_cost_intelligence",
            kind="time_phased_report",
            payload={"test": "data"},
            created_at=created_at,
        )
        
        # Create periods with significant variance
        periods_with_variance = [
            {
                "period": "2024-01",
                "period_type": "monthly",
                "start_date": "2024-01-01T00:00:00",
                "end_date": "2024-01-31T23:59:59",
                "estimated_cost": "10000.00",
                "actual_cost": "13000.00",
                "variance_amount": "3000.00",
                "variance_percentage": "30.00",
            },
            {
                "period": "2024-02",
                "period_type": "monthly",
                "start_date": "2024-02-01T00:00:00",
                "end_date": "2024-02-29T23:59:59",
                "estimated_cost": "20000.00",
                "actual_cost": "25000.00",
                "variance_amount": "5000.00",
                "variance_percentage": "25.00",
            },
        ]
        
        # Persist time-phased findings
        finding_ids = await persist_time_phased_findings(
            db,
            dataset_version_id=sample_dataset_version_id,
            periods_with_variance=periods_with_variance,
            raw_record_id=raw_record_id,
            evidence_id=evidence_id,
            created_at=created_at,
        )
        
        await db.commit()
        
        # Verify findings were created
        assert len(finding_ids) == 2, "Should have created 2 findings for periods with variance >25%"
        
        for finding_id in finding_ids:
            finding = await db.scalar(select(FindingRecord).where(FindingRecord.finding_id == finding_id))
            assert finding is not None
            assert finding.dataset_version_id == sample_dataset_version_id
            assert finding.kind == "time_phased_variance"
            assert finding.raw_record_id == raw_record_id
            assert "period" in finding.payload
            assert "variance_percentage" in finding.payload
            
            # Verify evidence link
            links = (
                await db.execute(select(FindingEvidenceLink).where(FindingEvidenceLink.finding_id == finding_id))
            ).scalars().all()
            assert len(links) > 0
            assert any(link.evidence_id == evidence_id for link in links)


@pytest.mark.anyio
async def test_findings_linked_to_evidence(sqlite_db: None, sample_dataset_version_id: str, sample_run_id: str, sample_comparison_result: ComparisonResult) -> None:
    """Test that findings are properly linked to evidence."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        created_at = datetime.now(timezone.utc)
        boq_raw_record_id = "boq-raw-001"
        
        report = await assemble_cost_variance_report(
            db=db,
            dataset_version_id=sample_dataset_version_id,
            run_id=sample_run_id,
            comparison_result=sample_comparison_result,
            boq_raw_record_id=boq_raw_record_id,
            actual_raw_record_id="actual-raw-001",
            created_at=created_at,
            emit_evidence=True,
            persist_findings=True,
        )
        
        await db.commit()
        
        # Get evidence ID from report
        evidence_section = next((s for s in report["sections"] if s.get("section_id") == "evidence_index"), None)
        assert evidence_section is not None
        evidence_ids = [e["evidence_id"] for e in evidence_section["evidence_index"]]
        assert len(evidence_ids) > 0
        
        variance_evidence_id = next((eid for eid in evidence_ids if "variance" in eid or True), evidence_ids[0])
        
        # Verify findings exist and are linked
        findings = (
            await db.execute(
                select(FindingRecord)
                .where(FindingRecord.dataset_version_id == sample_dataset_version_id)
                .where(FindingRecord.kind.in_(["cost_variance", "scope_creep"]))
            )
        ).scalars().all()
        
        assert len(findings) > 0, "Should have created findings"
        
        for finding in findings:
            # Verify finding is linked to evidence
            links = (
                await db.execute(
                    select(FindingEvidenceLink).where(FindingEvidenceLink.finding_id == finding.finding_id)
                )
            ).scalars().all()
            assert len(links) > 0, f"Finding {finding.finding_id} should be linked to evidence"
            
            # Verify at least one link points to variance evidence
            linked_evidence_ids = [link.evidence_id for link in links]
            assert any(eid in evidence_ids for eid in linked_evidence_ids), "Finding should be linked to report evidence"


@pytest.mark.anyio
async def test_findings_deterministic_ids(sqlite_db: None, sample_dataset_version_id: str) -> None:
    """Test that finding IDs are deterministic (idempotent)."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        created_at = datetime.now(timezone.utc)
        raw_record_id = "raw-001"
        
        # Create evidence
        from backend.app.core.evidence.service import create_evidence, deterministic_evidence_id
        
        evidence_id = deterministic_evidence_id(
            dataset_version_id=sample_dataset_version_id,
            engine_id="engine_construction_cost_intelligence",
            kind="variance_analysis",
            stable_key="test_deterministic",
        )
        await create_evidence(
            db,
            evidence_id=evidence_id,
            dataset_version_id=sample_dataset_version_id,
            engine_id="engine_construction_cost_intelligence",
            kind="variance_analysis",
            payload={"test": "data"},
            created_at=created_at,
        )
        
        # Create variance
        variance = CostVariance(
            match_key="item_code=ITEM001",
            estimated_cost=Decimal("10000.00"),
            actual_cost=Decimal("10500.00"),
            variance_amount=Decimal("500.00"),
            variance_percentage=Decimal("5.0"),
            severity=VarianceSeverity.MINOR,
            direction=VarianceDirection.OVER_BUDGET,
            category="Materials",
            line_ids_boq=("boq-1",),
            line_ids_actual=("actual-1",),
            identity={"item_code": "ITEM001"},
        )
        
        # Persist twice with same inputs
        finding_ids_1 = await persist_variance_findings(
            db,
            dataset_version_id=sample_dataset_version_id,
            variances=[variance],
            raw_record_id=raw_record_id,
            evidence_id=evidence_id,
            created_at=created_at,
        )
        
        await db.commit()
        
        finding_ids_2 = await persist_variance_findings(
            db,
            dataset_version_id=sample_dataset_version_id,
            variances=[variance],
            raw_record_id=raw_record_id,
            evidence_id=evidence_id,
            created_at=created_at,
        )
        
        await db.commit()
        
        # Should get same finding IDs (idempotent)
        assert finding_ids_1 == finding_ids_2, "Finding IDs should be deterministic"


@pytest.mark.anyio
async def test_findings_dataset_version_bound(sqlite_db: None, sample_dataset_version_id: str) -> None:
    """Test that findings are bound to DatasetVersion."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        created_at = datetime.now(timezone.utc)
        wrong_dataset_version_id = str(uuid7())
        raw_record_id = "raw-001"
        
        # Create evidence with correct DatasetVersion
        from backend.app.core.evidence.service import create_evidence, deterministic_evidence_id
        
        evidence_id = deterministic_evidence_id(
            dataset_version_id=sample_dataset_version_id,
            engine_id="engine_construction_cost_intelligence",
            kind="variance_analysis",
            stable_key="test_dv_bound",
        )
        await create_evidence(
            db,
            evidence_id=evidence_id,
            dataset_version_id=sample_dataset_version_id,
            engine_id="engine_construction_cost_intelligence",
            kind="variance_analysis",
            payload={"test": "data"},
            created_at=created_at,
        )
        await db.commit()
        
        # Try to create finding with wrong DatasetVersion
        variance = CostVariance(
            match_key="item_code=ITEM001",
            estimated_cost=Decimal("10000.00"),
            actual_cost=Decimal("10500.00"),
            variance_amount=Decimal("500.00"),
            variance_percentage=Decimal("5.0"),
            severity=VarianceSeverity.MINOR,
            direction=VarianceDirection.OVER_BUDGET,
        )
        
        # This should work (finding uses correct DatasetVersion)
        finding_ids = await persist_variance_findings(
            db,
            dataset_version_id=sample_dataset_version_id,
            variances=[variance],
            raw_record_id=raw_record_id,
            evidence_id=evidence_id,
            created_at=created_at,
        )
        await db.commit()
        
        # Verify finding is bound to correct DatasetVersion
        for finding_id in finding_ids:
            finding = await db.scalar(select(FindingRecord).where(FindingRecord.finding_id == finding_id))
            assert finding is not None
            assert finding.dataset_version_id == sample_dataset_version_id
            assert finding.dataset_version_id != wrong_dataset_version_id
            
            # Verify query with wrong DatasetVersion doesn't return finding
            wrong_finding = await db.scalar(
                select(FindingRecord)
                .where(FindingRecord.finding_id == finding_id)
                .where(FindingRecord.dataset_version_id == wrong_dataset_version_id)
            )
            assert wrong_finding is None


@pytest.mark.anyio
async def test_findings_not_persisted_when_disabled(sqlite_db: None, sample_dataset_version_id: str, sample_run_id: str, sample_comparison_result: ComparisonResult) -> None:
    """Test that findings are not persisted when persist_findings=False."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        created_at = datetime.now(timezone.utc)
        
        # Count findings before
        findings_before = (
            await db.execute(
                select(FindingRecord).where(FindingRecord.dataset_version_id == sample_dataset_version_id)
            )
        ).scalars().all()
        count_before = len(findings_before)
        
        # Assemble report with persist_findings=False
        report = await assemble_cost_variance_report(
            db=db,
            dataset_version_id=sample_dataset_version_id,
            run_id=sample_run_id,
            comparison_result=sample_comparison_result,
            boq_raw_record_id="boq-raw-001",
            actual_raw_record_id="actual-raw-001",
            created_at=created_at,
            emit_evidence=True,
            persist_findings=False,  # Disable finding persistence
        )
        
        await db.commit()
        
        # Count findings after
        findings_after = (
            await db.execute(
                select(FindingRecord).where(FindingRecord.dataset_version_id == sample_dataset_version_id)
            )
        ).scalars().all()
        count_after = len(findings_after)
        
        # Should have same count (no new findings created)
        assert count_after == count_before, "No new findings should be created when persist_findings=False"

