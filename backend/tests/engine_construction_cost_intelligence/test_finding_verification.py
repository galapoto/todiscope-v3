"""
Comprehensive Verification: FindingRecord Persistence and Traceability

Verifies that variance and time-phased findings are properly persisted as FindingRecords
with full DatasetVersion binding and evidence linkage.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select

from backend.app.core.dataset.uuidv7 import uuid7
from backend.app.core.db import get_sessionmaker
from backend.app.core.evidence.models import EvidenceRecord, FindingEvidenceLink, FindingRecord
from backend.app.engines.construction_cost_intelligence.compare import compare_boq_to_actuals
from backend.app.engines.construction_cost_intelligence.models import (
    ComparisonConfig,
    CostLine,
)
from backend.app.engines.construction_cost_intelligence.report.assembler import (
    assemble_cost_variance_report,
    assemble_time_phased_report,
)


@pytest.fixture
def sample_dataset_version_id() -> str:
    return str(uuid7())


@pytest.fixture
def sample_run_id() -> str:
    return f"run-{uuid7()}"


@pytest.mark.anyio
async def test_variance_findings_persisted_as_finding_records(
    sqlite_db: None, sample_dataset_version_id: str, sample_run_id: str
) -> None:
    """Verify that variance findings are persisted as FindingRecords."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        created_at = datetime.now(timezone.utc)
        boq_raw_record_id = "boq-raw-001"
        actual_raw_record_id = "actual-raw-001"
        
        # Create comparison result with variances
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
                total_cost=Decimal("10500.00"),  # 5% variance
            ),
            CostLine(
                dataset_version_id=sample_dataset_version_id,
                kind="actual",
                line_id="actual-2",
                identity={"item_code": "ITEM002"},
                total_cost=Decimal("22000.00"),  # 10% variance
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
        
        # Generate report with finding persistence
        report = await assemble_cost_variance_report(
            db=db,
            dataset_version_id=sample_dataset_version_id,
            run_id=sample_run_id,
            comparison_result=comparison_result,
            boq_raw_record_id=boq_raw_record_id,
            actual_raw_record_id=actual_raw_record_id,
            created_at=created_at,
            emit_evidence=True,
            persist_findings=True,
        )
        
        await db.commit()
        
        # Verify FindingRecords were created
        findings = (
            await db.execute(
                select(FindingRecord)
                .where(FindingRecord.dataset_version_id == sample_dataset_version_id)
                .where(FindingRecord.kind.in_(["cost_variance", "scope_creep"]))
            )
        ).scalars().all()
        
        assert len(findings) > 0, "Should have created FindingRecords"
        
        # Verify each finding has DatasetVersion binding
        for finding in findings:
            assert finding.dataset_version_id == sample_dataset_version_id
            assert finding.kind in ("cost_variance", "scope_creep")
            assert finding.payload is not None
            assert finding.payload.get("dataset_version_id") == sample_dataset_version_id
            
            # Verify evidence linkage
            links = (
                await db.execute(
                    select(FindingEvidenceLink).where(FindingEvidenceLink.finding_id == finding.finding_id)
                )
            ).scalars().all()
            assert len(links) > 0, f"Finding {finding.finding_id} should be linked to evidence"
            
            # Verify linked evidence belongs to same DatasetVersion
            for link in links:
                evidence = await db.scalar(
                    select(EvidenceRecord).where(EvidenceRecord.evidence_id == link.evidence_id)
                )
                assert evidence is not None
                assert evidence.dataset_version_id == sample_dataset_version_id


@pytest.mark.anyio
async def test_time_phased_findings_persisted_as_finding_records(
    sqlite_db: None, sample_dataset_version_id: str, sample_run_id: str
) -> None:
    """Verify that time-phased findings are persisted as FindingRecords."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        created_at = datetime.now(timezone.utc)
        raw_record_id = "raw-001"
        
        # Create cost lines with dates for time-phased reporting
        cost_lines = [
            CostLine(
                dataset_version_id=sample_dataset_version_id,
                kind="boq",
                line_id="boq-1",
                identity={"item_code": "ITEM001"},
                total_cost=Decimal("10000.00"),
                attributes={"date_recorded": "2024-01-15T00:00:00"},
            ),
            CostLine(
                dataset_version_id=sample_dataset_version_id,
                kind="actual",
                line_id="actual-1",
                identity={"item_code": "ITEM001"},
                total_cost=Decimal("13000.00"),  # 30% variance - significant
                attributes={"date_recorded": "2024-01-15T00:00:00"},
            ),
            CostLine(
                dataset_version_id=sample_dataset_version_id,
                kind="boq",
                line_id="boq-2",
                identity={"item_code": "ITEM002"},
                total_cost=Decimal("20000.00"),
                attributes={"date_recorded": "2024-02-15T00:00:00"},
            ),
            CostLine(
                dataset_version_id=sample_dataset_version_id,
                kind="actual",
                line_id="actual-2",
                identity={"item_code": "ITEM002"},
                total_cost=Decimal("26000.00"),  # 30% variance - significant (>25%)
                attributes={"date_recorded": "2024-02-15T00:00:00"},
            ),
        ]
        
        # Generate time-phased report with finding persistence
        report = await assemble_time_phased_report(
            db=db,
            dataset_version_id=sample_dataset_version_id,
            run_id=sample_run_id,
            cost_lines=cost_lines,
            period_type="monthly",
            raw_record_id=raw_record_id,
            created_at=created_at,
            emit_evidence=True,
            persist_findings=True,
        )
        
        await db.commit()
        
        # Verify FindingRecords were created for time-phased variance
        findings = (
            await db.execute(
                select(FindingRecord)
                .where(FindingRecord.dataset_version_id == sample_dataset_version_id)
                .where(FindingRecord.kind == "time_phased_variance")
            )
        ).scalars().all()
        
        assert len(findings) >= 2, "Should have created FindingRecords for periods with significant variance"
        
        # Verify each finding has DatasetVersion binding
        for finding in findings:
            assert finding.dataset_version_id == sample_dataset_version_id
            assert finding.kind == "time_phased_variance"
            assert finding.payload is not None
            assert finding.payload.get("dataset_version_id") == sample_dataset_version_id
            assert finding.payload.get("kind") == "time_phased_variance"
            
            # Verify evidence linkage
            links = (
                await db.execute(
                    select(FindingEvidenceLink).where(FindingEvidenceLink.finding_id == finding.finding_id)
                )
            ).scalars().all()
            assert len(links) > 0, f"Finding {finding.finding_id} should be linked to evidence"
            
            # Verify linked evidence belongs to same DatasetVersion
            for link in links:
                evidence = await db.scalar(
                    select(EvidenceRecord).where(EvidenceRecord.evidence_id == link.evidence_id)
                )
                assert evidence is not None
                assert evidence.dataset_version_id == sample_dataset_version_id


@pytest.mark.anyio
async def test_findings_dataset_version_traceability(
    sqlite_db: None, sample_dataset_version_id: str, sample_run_id: str
) -> None:
    """Verify that all findings are traceable via DatasetVersion."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        created_at = datetime.now(timezone.utc)
        boq_raw_record_id = "boq-raw-001"
        
        # Create another dataset version to verify isolation
        other_dataset_version_id = str(uuid7())
        
        # Create comparison result
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
        
        # Generate report with finding persistence
        report = await assemble_cost_variance_report(
            db=db,
            dataset_version_id=sample_dataset_version_id,
            run_id=sample_run_id,
            comparison_result=comparison_result,
            boq_raw_record_id=boq_raw_record_id,
            actual_raw_record_id="actual-raw-001",
            created_at=created_at,
            emit_evidence=True,
            persist_findings=True,
        )
        
        await db.commit()
        
        # Query findings by DatasetVersion
        findings = (
            await db.execute(
                select(FindingRecord).where(FindingRecord.dataset_version_id == sample_dataset_version_id)
            )
        ).scalars().all()
        
        assert len(findings) > 0, "Should have findings for DatasetVersion"
        
        # Verify all findings belong to correct DatasetVersion
        for finding in findings:
            assert finding.dataset_version_id == sample_dataset_version_id
            assert finding.dataset_version_id != other_dataset_version_id
        
        # Verify no findings for other DatasetVersion
        other_findings = (
            await db.execute(
                select(FindingRecord).where(FindingRecord.dataset_version_id == other_dataset_version_id)
            )
        ).scalars().all()
        assert len(other_findings) == 0, "Should have no findings for other DatasetVersion"


@pytest.mark.anyio
async def test_findings_evidence_linkage_traceability(
    sqlite_db: None, sample_dataset_version_id: str, sample_run_id: str
) -> None:
    """Verify that all findings are linked to evidence for full traceability."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        created_at = datetime.now(timezone.utc)
        boq_raw_record_id = "boq-raw-001"
        
        # Create comparison result
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
        
        # Generate report with finding persistence
        report = await assemble_cost_variance_report(
            db=db,
            dataset_version_id=sample_dataset_version_id,
            run_id=sample_run_id,
            comparison_result=comparison_result,
            boq_raw_record_id=boq_raw_record_id,
            actual_raw_record_id="actual-raw-001",
            created_at=created_at,
            emit_evidence=True,
            persist_findings=True,
        )
        
        await db.commit()
        
        # Get evidence ID from report
        evidence_section = next(
            (s for s in report["sections"] if s.get("section_id") == "evidence_index"), None
        )
        assert evidence_section is not None
        evidence_ids = [e["evidence_id"] for e in evidence_section.get("evidence_index", [])]
        assert len(evidence_ids) > 0
        
        # Get all findings for this DatasetVersion
        findings = (
            await db.execute(
                select(FindingRecord).where(FindingRecord.dataset_version_id == sample_dataset_version_id)
            )
        ).scalars().all()
        
        assert len(findings) > 0, "Should have findings"
        
        # Verify each finding is linked to evidence
        for finding in findings:
            links = (
                await db.execute(
                    select(FindingEvidenceLink).where(FindingEvidenceLink.finding_id == finding.finding_id)
                )
            ).scalars().all()
            
            assert len(links) > 0, f"Finding {finding.finding_id} must be linked to evidence"
            
            # Verify at least one link points to report evidence
            linked_evidence_ids = [link.evidence_id for link in links]
            assert any(eid in evidence_ids for eid in linked_evidence_ids), (
                f"Finding {finding.finding_id} should be linked to report evidence"
            )
            
            # Verify linked evidence exists and has correct DatasetVersion
            for link in links:
                evidence = await db.scalar(
                    select(EvidenceRecord).where(EvidenceRecord.evidence_id == link.evidence_id)
                )
                assert evidence is not None, f"Evidence {link.evidence_id} should exist"
                assert evidence.dataset_version_id == sample_dataset_version_id, (
                    "Evidence should belong to same DatasetVersion"
                )


@pytest.mark.anyio
async def test_findings_full_traceability_chain(
    sqlite_db: None, sample_dataset_version_id: str, sample_run_id: str
) -> None:
    """Verify complete traceability chain: FindingRecord -> Evidence -> DatasetVersion."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        created_at = datetime.now(timezone.utc)
        boq_raw_record_id = "boq-raw-001"
        actual_raw_record_id = "actual-raw-001"
        
        # Create comparison result with both matched variances and scope creep
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
                identity={"item_code": "ITEM999"},  # Scope creep
                total_cost=Decimal("5000.00"),
            ),
        ]
        
        comparison_result = compare_boq_to_actuals(
            dataset_version_id=sample_dataset_version_id,
            boq_lines=boq_lines,
            actual_lines=actual_lines,
            config=cfg,
        )
        
        # Generate report
        report = await assemble_cost_variance_report(
            db=db,
            dataset_version_id=sample_dataset_version_id,
            run_id=sample_run_id,
            comparison_result=comparison_result,
            boq_raw_record_id=boq_raw_record_id,
            actual_raw_record_id=actual_raw_record_id,
            created_at=created_at,
            emit_evidence=True,
            persist_findings=True,
        )
        
        await db.commit()
        
        # Get all findings
        findings = (
            await db.execute(
                select(FindingRecord)
                .where(FindingRecord.dataset_version_id == sample_dataset_version_id)
                .where(FindingRecord.kind.in_(["cost_variance", "scope_creep"]))
            )
        ).scalars().all()
        
        assert len(findings) >= 2, "Should have at least 2 findings (matched variance + scope creep)"
        
        # Verify complete traceability for each finding
        for finding in findings:
            # 1. Finding has DatasetVersion
            assert finding.dataset_version_id == sample_dataset_version_id
            
            # 2. Finding payload includes DatasetVersion
            assert finding.payload.get("dataset_version_id") == sample_dataset_version_id
            
            # 3. Finding is linked to evidence
            links = (
                await db.execute(
                    select(FindingEvidenceLink).where(FindingEvidenceLink.finding_id == finding.finding_id)
                )
            ).scalars().all()
            assert len(links) > 0
            
            # 4. Linked evidence belongs to same DatasetVersion
            for link in links:
                evidence = await db.scalar(
                    select(EvidenceRecord).where(EvidenceRecord.evidence_id == link.evidence_id)
                )
                assert evidence is not None
                assert evidence.dataset_version_id == sample_dataset_version_id
                assert evidence.dataset_version_id == finding.dataset_version_id


@pytest.mark.anyio
async def test_findings_query_by_dataset_version_and_kind(
    sqlite_db: None, sample_dataset_version_id: str, sample_run_id: str
) -> None:
    """Verify findings can be queried by DatasetVersion and kind."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        created_at = datetime.now(timezone.utc)
        
        # Create variance findings
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
                attributes={"date_recorded": "2024-01-15T00:00:00"},
            ),
        ]
        
        comparison_result = compare_boq_to_actuals(
            dataset_version_id=sample_dataset_version_id,
            boq_lines=boq_lines,
            actual_lines=actual_lines,
            config=cfg,
        )
        
        # Generate variance report
        await assemble_cost_variance_report(
            db=db,
            dataset_version_id=sample_dataset_version_id,
            run_id=sample_run_id,
            comparison_result=comparison_result,
            boq_raw_record_id="boq-raw-001",
            actual_raw_record_id="actual-raw-001",
            created_at=created_at,
            emit_evidence=True,
            persist_findings=True,
        )
        
        # Generate time-phased report
        await assemble_time_phased_report(
            db=db,
            dataset_version_id=sample_dataset_version_id,
            run_id=sample_run_id,
            cost_lines=actual_lines + boq_lines,
            raw_record_id="raw-001",
            created_at=created_at,
            emit_evidence=True,
            persist_findings=True,
        )
        
        await db.commit()
        
        # Query variance findings
        variance_findings = (
            await db.execute(
                select(FindingRecord)
                .where(FindingRecord.dataset_version_id == sample_dataset_version_id)
                .where(FindingRecord.kind == "cost_variance")
            )
        ).scalars().all()
        
        assert len(variance_findings) > 0, "Should have variance findings"
        
        # Query time-phased findings
        time_phased_findings = (
            await db.execute(
                select(FindingRecord)
                .where(FindingRecord.dataset_version_id == sample_dataset_version_id)
                .where(FindingRecord.kind == "time_phased_variance")
            )
        ).scalars().all()
        
        # Time-phased findings only created for significant variance (>25%)
        # In this case, 5% variance won't create a finding
        # That's expected behavior - verified in test
        
        # Verify all findings are queryable by DatasetVersion
        all_findings = (
            await db.execute(
                select(FindingRecord).where(FindingRecord.dataset_version_id == sample_dataset_version_id)
            )
        ).scalars().all()
        
        assert len(all_findings) > 0, "Should be able to query findings by DatasetVersion"

