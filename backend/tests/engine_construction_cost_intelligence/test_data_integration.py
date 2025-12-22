"""
Data Integration Tests: Construction Cost Intelligence Engine

Tests end-to-end data flow from ingestion through report generation,
ensuring proper DatasetVersion binding and evidence traceability.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select

from backend.app.core.dataset.models import DatasetVersion
from backend.app.core.dataset.raw_models import RawRecord
from backend.app.core.dataset.uuidv7 import uuid7
from backend.app.core.db import get_sessionmaker
from backend.app.core.evidence.models import EvidenceRecord, FindingEvidenceLink, FindingRecord
from backend.app.engines.construction_cost_intelligence.run import run_engine
from backend.app.engines.construction_cost_intelligence.report.assembler import assemble_report


@pytest.fixture
def sample_dataset_version_id() -> str:
    return str(uuid7())


@pytest.fixture
def sample_run_id() -> str:
    return f"run-{uuid7()}"


@pytest.mark.anyio
async def test_end_to_end_data_flow_with_findings(
    sqlite_db: None, sample_dataset_version_id: str, sample_run_id: str
) -> None:
    """Test complete data flow from RawRecord ingestion through FindingRecord persistence."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        # Create DatasetVersion
        dv = DatasetVersion(id=sample_dataset_version_id)
        db.add(dv)
        await db.flush()
        
        # Create RawRecords with BOQ and actual data
        boq_raw_record_id = "boq-raw-001"
        actual_raw_record_id = "actual-raw-001"
        
        now = datetime.now(timezone.utc)
        boq_raw = RawRecord(
            raw_record_id=boq_raw_record_id,
            dataset_version_id=sample_dataset_version_id,
            source_system="test_system",
            source_record_id="boq-source-001",
            payload={
                "lines": [
                    {
                        "line_id": "boq-1",
                        "item_code": "ITEM001",
                        "total_cost": "10000.00",
                        "category": "Materials",
                    },
                    {
                        "line_id": "boq-2",
                        "item_code": "ITEM002",
                        "total_cost": "20000.00",
                        "category": "Labor",
                    },
                ]
            },
            ingested_at=now,
        )
        
        actual_raw = RawRecord(
            raw_record_id=actual_raw_record_id,
            dataset_version_id=sample_dataset_version_id,
            source_system="test_system",
            source_record_id="actual-source-001",
            payload={
                "lines": [
                    {
                        "line_id": "actual-1",
                        "item_code": "ITEM001",
                        "total_cost": "10500.00",
                        "category": "Materials",
                    },
                    {
                        "line_id": "actual-2",
                        "item_code": "ITEM002",
                        "total_cost": "22000.00",
                        "category": "Labor",
                    },
                    {
                        "line_id": "actual-3",
                        "item_code": "ITEM999",  # Scope creep
                        "total_cost": "5000.00",
                        "category": "Unexpected",
                    },
                ]
            },
            ingested_at=now,
        )
        
        db.add(boq_raw)
        db.add(actual_raw)
        await db.flush()
        
        # Run core engine to create comparison result
        started_at = datetime.now(timezone.utc).isoformat()
        result = await run_engine(
            dataset_version_id=sample_dataset_version_id,
            started_at=started_at,
            boq_raw_record_id=boq_raw_record_id,
            actual_raw_record_id=actual_raw_record_id,
            normalization_mapping={
                "line_id": "line_id",
                "identity": {"item_code": "item_code"},
                "total_cost": "total_cost",
                "extras": ["category"],
            },
            comparison_config={
                "identity_fields": ["item_code"],
                "cost_basis": "prefer_total_cost",
                "breakdown_fields": [],
            },
        )
        
        await db.commit()
        
        # Verify core traceability was created
        assert result["dataset_version_id"] == sample_dataset_version_id
        assert "traceability" in result
        traceability = result["traceability"]
        assert "assumptions_evidence_id" in traceability
        assert "inputs_evidence_ids" in traceability
        assert "finding_ids" in traceability
        
        # Generate variance report with finding persistence
        from backend.app.engines.construction_cost_intelligence.compare import compare_boq_to_actuals
        from backend.app.engines.construction_cost_intelligence.models import (
            ComparisonConfig,
            CostLine,
            NormalizationMapping,
            normalize_cost_lines,
        )
        
        # Recreate comparison for report (normally this would come from run_engine result)
        cfg = ComparisonConfig(identity_fields=("item_code",))
        boq_lines = normalize_cost_lines(
            dataset_version_id=sample_dataset_version_id,
            kind="boq",
            raw_lines=boq_raw.payload["lines"],
            mapping=NormalizationMapping(
                line_id="line_id",
                identity={"item_code": "item_code"},
                total_cost="total_cost",
                extras=("category",),
            ),
        )
        actual_lines = normalize_cost_lines(
            dataset_version_id=sample_dataset_version_id,
            kind="actual",
            raw_lines=actual_raw.payload["lines"],
            mapping=NormalizationMapping(
                line_id="line_id",
                identity={"item_code": "item_code"},
                total_cost="total_cost",
                extras=("category",),
            ),
        )
        
        comparison_result = compare_boq_to_actuals(
            dataset_version_id=sample_dataset_version_id,
            boq_lines=boq_lines,
            actual_lines=actual_lines,
            config=cfg,
        )
        
        # Generate report with findings
        report = await assemble_report(
            db=db,
            dataset_version_id=sample_dataset_version_id,
            run_id=sample_run_id,
            report_type="cost_variance",
            parameters={
                "comparison_result": comparison_result,
                "boq_raw_record_id": boq_raw_record_id,
                "actual_raw_record_id": actual_raw_record_id,
                "persist_findings": True,
            },
            created_at=datetime.now(timezone.utc),
            emit_evidence=True,
        )
        
        await db.commit()
        
        # Verify findings were persisted
        findings = (
            await db.execute(
                select(FindingRecord).where(FindingRecord.dataset_version_id == sample_dataset_version_id)
            )
        ).scalars().all()
        
        assert len(findings) > 0, "Should have persisted findings"
        
        # Verify all findings are bound to DatasetVersion
        for finding in findings:
            assert finding.dataset_version_id == sample_dataset_version_id
            assert finding.raw_record_id in (boq_raw_record_id, actual_raw_record_id)
        
        # Verify evidence linkage
        for finding in findings:
            links = (
                await db.execute(
                    select(FindingEvidenceLink).where(FindingEvidenceLink.finding_id == finding.finding_id)
                )
            ).scalars().all()
            assert len(links) > 0, "Each finding should be linked to evidence"


@pytest.mark.anyio
async def test_dataset_version_isolation(
    sqlite_db: None, sample_dataset_version_id: str, sample_run_id: str
) -> None:
    """Test that findings are isolated by DatasetVersion with no cross-contamination."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        # Create two DatasetVersions
        dv1 = DatasetVersion(id=sample_dataset_version_id)
        dv2_id = str(uuid7())
        dv2 = DatasetVersion(id=dv2_id)
        
        db.add(dv1)
        db.add(dv2)
        await db.flush()
        
        now = datetime.now(timezone.utc)
        # Create RawRecords for DatasetVersion 1
        boq_raw1 = RawRecord(
            raw_record_id="boq-raw-001",
            dataset_version_id=sample_dataset_version_id,
            source_system="test_system",
            source_record_id="boq-source-001",
            payload={"lines": [{"line_id": "boq-1", "item_code": "ITEM001", "total_cost": "10000.00"}]},
            ingested_at=now,
        )
        actual_raw1 = RawRecord(
            raw_record_id="actual-raw-001",
            dataset_version_id=sample_dataset_version_id,
            source_system="test_system",
            source_record_id="actual-source-001",
            payload={"lines": [{"line_id": "actual-1", "item_code": "ITEM001", "total_cost": "10500.00"}]},
            ingested_at=now,
        )
        
        # Create RawRecords for DatasetVersion 2
        boq_raw2 = RawRecord(
            raw_record_id="boq-raw-002",
            dataset_version_id=dv2_id,
            source_system="test_system",
            source_record_id="boq-source-002",
            payload={"lines": [{"line_id": "boq-2", "item_code": "ITEM002", "total_cost": "20000.00"}]},
            ingested_at=now,
        )
        actual_raw2 = RawRecord(
            raw_record_id="actual-raw-002",
            dataset_version_id=dv2_id,
            source_system="test_system",
            source_record_id="actual-source-002",
            payload={"lines": [{"line_id": "actual-2", "item_code": "ITEM002", "total_cost": "22000.00"}]},
            ingested_at=now,
        )
        
        db.add(boq_raw1)
        db.add(actual_raw1)
        db.add(boq_raw2)
        db.add(actual_raw2)
        await db.flush()
        
        # Run engine for DatasetVersion 1
        started_at = datetime.now(timezone.utc).isoformat()
        result1 = await run_engine(
            dataset_version_id=sample_dataset_version_id,
            started_at=started_at,
            boq_raw_record_id="boq-raw-001",
            actual_raw_record_id="actual-raw-001",
            normalization_mapping={
                "line_id": "line_id",
                "identity": {"item_code": "item_code"},
                "total_cost": "total_cost",
            },
            comparison_config={"identity_fields": ["item_code"], "cost_basis": "prefer_total_cost"},
        )
        
        # Run engine for DatasetVersion 2
        result2 = await run_engine(
            dataset_version_id=dv2_id,
            started_at=started_at,
            boq_raw_record_id="boq-raw-002",
            actual_raw_record_id="actual-raw-002",
            normalization_mapping={
                "line_id": "line_id",
                "identity": {"item_code": "item_code"},
                "total_cost": "total_cost",
            },
            comparison_config={"identity_fields": ["item_code"], "cost_basis": "prefer_total_cost"},
        )
        
        await db.commit()
        
        # Verify evidence isolation
        evidence1 = (
            await db.execute(
                select(EvidenceRecord).where(EvidenceRecord.dataset_version_id == sample_dataset_version_id)
            )
        ).scalars().all()
        
        evidence2 = (
            await db.execute(select(EvidenceRecord).where(EvidenceRecord.dataset_version_id == dv2_id))
        ).scalars().all()
        
        assert len(evidence1) > 0, "DatasetVersion 1 should have evidence"
        assert len(evidence2) > 0, "DatasetVersion 2 should have evidence"
        
        # Verify no cross-contamination
        for ev in evidence1:
            assert ev.dataset_version_id == sample_dataset_version_id
            assert ev.dataset_version_id != dv2_id
        
        for ev in evidence2:
            assert ev.dataset_version_id == dv2_id
            assert ev.dataset_version_id != sample_dataset_version_id


@pytest.mark.anyio
async def test_full_traceability_chain(
    sqlite_db: None, sample_dataset_version_id: str, sample_run_id: str
) -> None:
    """Test complete traceability chain: RawRecord → FindingRecord → EvidenceRecord."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        # Create DatasetVersion
        dv = DatasetVersion(id=sample_dataset_version_id)
        db.add(dv)
        await db.flush()
        
        # Create RawRecords
        now = datetime.now(timezone.utc)
        boq_raw = RawRecord(
            raw_record_id="boq-raw-001",
            dataset_version_id=sample_dataset_version_id,
            source_system="test_system",
            source_record_id="boq-source-001",
            payload={"lines": [{"line_id": "boq-1", "item_code": "ITEM001", "total_cost": "10000.00"}]},
            ingested_at=now,
        )
        actual_raw = RawRecord(
            raw_record_id="actual-raw-001",
            dataset_version_id=sample_dataset_version_id,
            source_system="test_system",
            source_record_id="actual-source-001",
            payload={"lines": [{"line_id": "actual-1", "item_code": "ITEM001", "total_cost": "10500.00"}]},
            ingested_at=now,
        )
        
        db.add(boq_raw)
        db.add(actual_raw)
        await db.flush()
        
        # Run core engine
        started_at = datetime.now(timezone.utc).isoformat()
        result = await run_engine(
            dataset_version_id=sample_dataset_version_id,
            started_at=started_at,
            boq_raw_record_id="boq-raw-001",
            actual_raw_record_id="actual-raw-001",
            normalization_mapping={
                "line_id": "line_id",
                "identity": {"item_code": "item_code"},
                "total_cost": "total_cost",
            },
            comparison_config={"identity_fields": ["item_code"], "cost_basis": "prefer_total_cost"},
        )
        
        await db.commit()
        
        # Generate report with findings
        from backend.app.engines.construction_cost_intelligence.compare import compare_boq_to_actuals
        from backend.app.engines.construction_cost_intelligence.models import (
            ComparisonConfig,
            NormalizationMapping,
            normalize_cost_lines,
        )
        
        cfg = ComparisonConfig(identity_fields=("item_code",))
        boq_lines = normalize_cost_lines(
            dataset_version_id=sample_dataset_version_id,
            kind="boq",
            raw_lines=boq_raw.payload["lines"],
            mapping=NormalizationMapping(
                line_id="line_id",
                identity={"item_code": "item_code"},
                total_cost="total_cost",
            ),
        )
        actual_lines = normalize_cost_lines(
            dataset_version_id=sample_dataset_version_id,
            kind="actual",
            raw_lines=actual_raw.payload["lines"],
            mapping=NormalizationMapping(
                line_id="line_id",
                identity={"item_code": "item_code"},
                total_cost="total_cost",
            ),
        )
        
        comparison_result = compare_boq_to_actuals(
            dataset_version_id=sample_dataset_version_id,
            boq_lines=boq_lines,
            actual_lines=actual_lines,
            config=cfg,
        )
        
        report = await assemble_report(
            db=db,
            dataset_version_id=sample_dataset_version_id,
            run_id=sample_run_id,
            report_type="cost_variance",
            parameters={
                "comparison_result": comparison_result,
                "boq_raw_record_id": "boq-raw-001",
                "actual_raw_record_id": "actual-raw-001",
                "persist_findings": True,
            },
            created_at=datetime.now(timezone.utc),
            emit_evidence=True,
        )
        
        await db.commit()
        
        # Verify full traceability chain
        findings = (
            await db.execute(
                select(FindingRecord).where(FindingRecord.dataset_version_id == sample_dataset_version_id)
            )
        ).scalars().all()
        
        assert len(findings) > 0, "Should have findings"
        
        for finding in findings:
            # 1. Finding links to RawRecord
            assert finding.raw_record_id in ("boq-raw-001", "actual-raw-001")
            
            # 2. Finding linked to Evidence
            links = (
                await db.execute(
                    select(FindingEvidenceLink).where(FindingEvidenceLink.finding_id == finding.finding_id)
                )
            ).scalars().all()
            assert len(links) > 0, "Finding should be linked to evidence"
            
            # 3. Evidence linked to DatasetVersion
            for link in links:
                evidence = await db.scalar(
                    select(EvidenceRecord).where(EvidenceRecord.evidence_id == link.evidence_id)
                )
                assert evidence is not None, "Evidence should exist"
                assert evidence.dataset_version_id == sample_dataset_version_id, (
                    "Evidence should belong to DatasetVersion"
                )
                
                # 4. Verify RawRecord belongs to same DatasetVersion
                raw_record = await db.scalar(
                    select(RawRecord).where(RawRecord.raw_record_id == finding.raw_record_id)
                )
                assert raw_record is not None, "RawRecord should exist"
                assert raw_record.dataset_version_id == sample_dataset_version_id, (
                    "RawRecord should belong to DatasetVersion"
                )


@pytest.mark.anyio
async def test_findings_queryable_by_dataset_version(
    sqlite_db: None, sample_dataset_version_id: str, sample_run_id: str
) -> None:
    """Test that findings are queryable by DatasetVersion."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        # Create DatasetVersion
        dv = DatasetVersion(id=sample_dataset_version_id)
        db.add(dv)
        await db.flush()
        
        # Create RawRecords
        now = datetime.now(timezone.utc)
        boq_raw = RawRecord(
            raw_record_id="boq-raw-001",
            dataset_version_id=sample_dataset_version_id,
            source_system="test_system",
            source_record_id="boq-source-001",
            payload={"lines": [{"line_id": "boq-1", "item_code": "ITEM001", "total_cost": "10000.00"}]},
            ingested_at=now,
        )
        actual_raw = RawRecord(
            raw_record_id="actual-raw-001",
            dataset_version_id=sample_dataset_version_id,
            source_system="test_system",
            source_record_id="actual-source-001",
            payload={
                "lines": [
                    {"line_id": "actual-1", "item_code": "ITEM001", "total_cost": "10500.00"},
                    {"line_id": "actual-2", "item_code": "ITEM999", "total_cost": "5000.00"},  # Scope creep
                ]
            },
            ingested_at=now,
        )
        
        db.add(boq_raw)
        db.add(actual_raw)
        await db.flush()
        
        # Generate report with findings
        from backend.app.engines.construction_cost_intelligence.compare import compare_boq_to_actuals
        from backend.app.engines.construction_cost_intelligence.models import (
            ComparisonConfig,
            NormalizationMapping,
            normalize_cost_lines,
        )
        
        cfg = ComparisonConfig(identity_fields=("item_code",))
        boq_lines = normalize_cost_lines(
            dataset_version_id=sample_dataset_version_id,
            kind="boq",
            raw_lines=boq_raw.payload["lines"],
            mapping=NormalizationMapping(
                line_id="line_id",
                identity={"item_code": "item_code"},
                total_cost="total_cost",
            ),
        )
        actual_lines = normalize_cost_lines(
            dataset_version_id=sample_dataset_version_id,
            kind="actual",
            raw_lines=actual_raw.payload["lines"],
            mapping=NormalizationMapping(
                line_id="line_id",
                identity={"item_code": "item_code"},
                total_cost="total_cost",
            ),
        )
        
        comparison_result = compare_boq_to_actuals(
            dataset_version_id=sample_dataset_version_id,
            boq_lines=boq_lines,
            actual_lines=actual_lines,
            config=cfg,
        )
        
        report = await assemble_report(
            db=db,
            dataset_version_id=sample_dataset_version_id,
            run_id=sample_run_id,
            report_type="cost_variance",
            parameters={
                "comparison_result": comparison_result,
                "boq_raw_record_id": "boq-raw-001",
                "actual_raw_record_id": "actual-raw-001",
                "persist_findings": True,
            },
            created_at=datetime.now(timezone.utc),
            emit_evidence=True,
        )
        
        await db.commit()
        
        # Query findings by DatasetVersion
        findings = (
            await db.execute(
                select(FindingRecord).where(FindingRecord.dataset_version_id == sample_dataset_version_id)
            )
        ).scalars().all()
        
        assert len(findings) > 0, "Should be able to query findings by DatasetVersion"
        
        # Verify all returned findings belong to DatasetVersion
        for finding in findings:
            assert finding.dataset_version_id == sample_dataset_version_id
        
        # Query by DatasetVersion and kind
        variance_findings = (
            await db.execute(
                select(FindingRecord)
                .where(FindingRecord.dataset_version_id == sample_dataset_version_id)
                .where(FindingRecord.kind == "cost_variance")
            )
        ).scalars().all()
        
        scope_creep_findings = (
            await db.execute(
                select(FindingRecord)
                .where(FindingRecord.dataset_version_id == sample_dataset_version_id)
                .where(FindingRecord.kind == "scope_creep")
            )
        ).scalars().all()
        
        assert len(variance_findings) > 0, "Should have variance findings"
        assert len(scope_creep_findings) > 0, "Should have scope creep findings"

