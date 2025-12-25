"""
Unit tests for reporting service.

Tests verify:
- Finding formatting as scenarios and ranges
- Litigation report generation
- Evidence summary report generation
- Assumptions documentation
- Traceability in reports
"""

from __future__ import annotations

from datetime import datetime, timezone
import uuid

import pytest

from backend.app.core.dataset.service import create_dataset_version_via_ingestion
from backend.app.core.db import get_sessionmaker
from backend.app.core.evidence.aggregation import get_evidence_for_findings
from backend.app.core.evidence.models import EvidenceRecord, FindingRecord
from backend.app.core.evidence.service import (
    create_evidence,
    create_finding,
    deterministic_evidence_id,
    link_finding_to_evidence,
)
from backend.app.core.reporting.service import (
    InvalidFindingError,
    ReportingError,
    format_finding_as_range,
    format_finding_as_scenario,
    generate_evidence_summary_report,
    generate_litigation_report,
)
from backend.app.core.dataset.raw_models import RawRecord


@pytest.mark.anyio
async def test_format_finding_as_scenario(sqlite_db: None) -> None:
    """Test formatting a finding as a scenario."""
    now = datetime.now(timezone.utc)
    
    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)
        
        raw_id = str(uuid.uuid4())
        db.add(
            RawRecord(
                raw_record_id=raw_id,
                dataset_version_id=dv.id,
                source_system="sys1",
                source_record_id="r1",
                payload={"data": "value1"},
                ingested_at=now,
            )
        )
        await db.commit()
        
        finding_id = str(uuid.uuid4())
        finding = await create_finding(
            db,
            finding_id=finding_id,
            dataset_version_id=dv.id,
            raw_record_id=raw_id,
            kind="test_scenario",
            payload={
                "description": "Test scenario description",
                "assumptions": ["assumption1", "assumption2"],
            },
            created_at=now,
        )
        
        # Create evidence
        evidence_id = deterministic_evidence_id(
            dataset_version_id=dv.id,
            engine_id="test_engine",
            kind="evidence_kind",
            stable_key="key1",
        )
        evidence = await create_evidence(
            db,
            evidence_id=evidence_id,
            dataset_version_id=dv.id,
            engine_id="test_engine",
            kind="evidence_kind",
            payload={"data": "evidence"},
            created_at=now,
        )
        
        await db.commit()
    
    # Format finding
    formatted = format_finding_as_scenario(finding, evidence_records=[evidence])
    
    assert formatted["finding_id"] == finding_id
    assert formatted["dataset_version_id"] == dv.id
    assert formatted["kind"] == "test_scenario"
    assert "scenario_description" in formatted
    assert formatted["scenario_description"] == "Test scenario description"
    assert formatted["evidence_references"] == [evidence_id]
    assert len(formatted["assumptions"]) == 2
    assert "assumption1" in formatted["assumptions"]
    assert "assumption2" in formatted["assumptions"]
    assert "created_at" in formatted


@pytest.mark.anyio
async def test_format_finding_as_range(sqlite_db: None) -> None:
    """Test formatting a finding with ranges."""
    now = datetime.now(timezone.utc)
    
    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)
        
        raw_id = str(uuid.uuid4())
        db.add(
            RawRecord(
                raw_record_id=raw_id,
                dataset_version_id=dv.id,
                source_system="sys1",
                source_record_id="r1",
                payload={"data": "value1"},
                ingested_at=now,
            )
        )
        await db.commit()
        
        finding_id = str(uuid.uuid4())
        finding = await create_finding(
            db,
            finding_id=finding_id,
            dataset_version_id=dv.id,
            raw_record_id=raw_id,
            kind="test_range",
            payload={
                "min_value": 10.0,
                "max_value": 20.0,
                "value": 15.0,
                "assumptions": ["range assumption"],
            },
            created_at=now,
        )
        
        await db.commit()
    
    # Format finding as range
    formatted = format_finding_as_range(finding, evidence_records=[])
    
    assert formatted["finding_id"] == finding_id
    assert formatted["dataset_version_id"] == dv.id
    assert "ranges" in formatted
    assert formatted["ranges"]["min_value"] == 10.0
    assert formatted["ranges"]["max_value"] == 20.0
    assert formatted["ranges"]["value"] == 15.0
    assert len(formatted["assumptions"]) == 1
    assert formatted["assumptions"][0] == "range assumption"


@pytest.mark.anyio
async def test_format_finding_as_range_with_custom_fields(sqlite_db: None) -> None:
    """Test formatting a finding as range with custom range fields."""
    now = datetime.now(timezone.utc)
    
    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)
        
        raw_id = str(uuid.uuid4())
        db.add(
            RawRecord(
                raw_record_id=raw_id,
                dataset_version_id=dv.id,
                source_system="sys1",
                source_record_id="r1",
                payload={"data": "value1"},
                ingested_at=now,
            )
        )
        await db.commit()
        
        finding_id = str(uuid.uuid4())
        finding = await create_finding(
            db,
            finding_id=finding_id,
            dataset_version_id=dv.id,
            raw_record_id=raw_id,
            kind="test_range",
            payload={
                "custom_min": 5.0,
                "custom_max": 25.0,
                "other_field": "not a range",
            },
            created_at=now,
        )
        
        await db.commit()
    
    # Format with custom range fields
    formatted = format_finding_as_range(
        finding, evidence_records=[], range_fields=["custom_min", "custom_max"]
    )
    
    assert "ranges" in formatted
    assert "custom_min" in formatted["ranges"]
    assert "custom_max" in formatted["ranges"]
    assert "other_field" not in formatted["ranges"]


@pytest.mark.anyio
async def test_generate_litigation_report(sqlite_db: None) -> None:
    """Test generating a litigation support report."""
    now = datetime.now(timezone.utc)
    
    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)
        
        # Create raw records
        raw_id_1 = str(uuid.uuid4())
        db.add(
            RawRecord(
                raw_record_id=raw_id_1,
                dataset_version_id=dv.id,
                source_system="sys1",
                source_record_id="r1",
                payload={"data": "value1"},
                ingested_at=now,
            )
        )
        
        raw_id_2 = str(uuid.uuid4())
        db.add(
            RawRecord(
                raw_record_id=raw_id_2,
                dataset_version_id=dv.id,
                source_system="sys2",
                source_record_id="r2",
                payload={"data": "value2"},
                ingested_at=now,
            )
        )
        await db.commit()
        
        # Create findings
        finding_id_1 = str(uuid.uuid4())
        finding_1 = await create_finding(
            db,
            finding_id=finding_id_1,
            dataset_version_id=dv.id,
            raw_record_id=raw_id_1,
            kind="scenario_1",
            payload={
                "description": "First scenario",
                "assumptions": ["assumption1"],
            },
            created_at=now,
        )
        
        finding_id_2 = str(uuid.uuid4())
        finding_2 = await create_finding(
            db,
            finding_id=finding_id_2,
            dataset_version_id=dv.id,
            raw_record_id=raw_id_2,
            kind="scenario_2",
            payload={
                "description": "Second scenario",
                "assumptions": ["assumption2"],
            },
            created_at=now,
        )
        
        # Create evidence
        evidence_id_1 = deterministic_evidence_id(
            dataset_version_id=dv.id,
            engine_id="test_engine",
            kind="evidence_kind",
            stable_key="key1",
        )
        evidence_1 = await create_evidence(
            db,
            evidence_id=evidence_id_1,
            dataset_version_id=dv.id,
            engine_id="test_engine",
            kind="evidence_kind",
            payload={"data": "evidence1"},
            created_at=now,
        )
        
        evidence_id_2 = deterministic_evidence_id(
            dataset_version_id=dv.id,
            engine_id="test_engine",
            kind="evidence_kind",
            stable_key="key2",
        )
        evidence_2 = await create_evidence(
            db,
            evidence_id=evidence_id_2,
            dataset_version_id=dv.id,
            engine_id="test_engine",
            kind="evidence_kind",
            payload={"data": "evidence2"},
            created_at=now,
        )
        
        # Link evidence to findings
        link_id_1 = str(uuid.uuid4())
        await link_finding_to_evidence(
            db, link_id=link_id_1, finding_id=finding_id_1, evidence_id=evidence_id_1
        )
        
        link_id_2 = str(uuid.uuid4())
        await link_finding_to_evidence(
            db, link_id=link_id_2, finding_id=finding_id_2, evidence_id=evidence_id_2
        )
        
        await db.commit()
    
    async with get_sessionmaker()() as db:
        # Generate report
        report = await generate_litigation_report(
            db,
            dataset_version_id=dv.id,
            report_title="Test Litigation Report",
            include_assumptions=True,
            include_evidence_index=True,
            format_as_ranges=False,
        )
        
        # Verify report structure
        assert "metadata" in report
        assert report["metadata"]["report_title"] == "Test Litigation Report"
        assert report["metadata"]["dataset_version_id"] == dv.id
        assert report["metadata"]["total_findings"] == 2
        assert report["metadata"]["format_type"] == "scenarios"
        
        assert "scope" in report
        assert report["scope"]["dataset_version_id"] == dv.id
        assert report["scope"]["traceability_verified"] is True
        
        assert "findings" in report
        assert len(report["findings"]) == 2
        
        assert "assumptions" in report
        assert len(report["assumptions"]) == 2
        assert "assumption1" in report["assumptions"]
        assert "assumption2" in report["assumptions"]
        
        assert "evidence_index" in report
        assert len(report["evidence_index"]) == 2
        
        assert "limitations" in report
        assert len(report["limitations"]) > 0


@pytest.mark.anyio
async def test_generate_litigation_report_as_ranges(sqlite_db: None) -> None:
    """Test generating a litigation report with ranges format."""
    now = datetime.now(timezone.utc)
    
    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)
        
        raw_id = str(uuid.uuid4())
        db.add(
            RawRecord(
                raw_record_id=raw_id,
                dataset_version_id=dv.id,
                source_system="sys1",
                source_record_id="r1",
                payload={"data": "value1"},
                ingested_at=now,
            )
        )
        await db.commit()
        
        finding_id = str(uuid.uuid4())
        finding = await create_finding(
            db,
            finding_id=finding_id,
            dataset_version_id=dv.id,
            raw_record_id=raw_id,
            kind="range_finding",
            payload={
                "min_value": 10.0,
                "max_value": 20.0,
            },
            created_at=now,
        )
        
        await db.commit()
    
    async with get_sessionmaker()() as db:
        report = await generate_litigation_report(
            db,
            dataset_version_id=dv.id,
            format_as_ranges=True,
        )
        
        assert report["metadata"]["format_type"] == "ranges"
        assert len(report["findings"]) == 1
        assert "ranges" in report["findings"][0]


@pytest.mark.anyio
async def test_generate_litigation_report_without_assumptions(sqlite_db: None) -> None:
    """Test generating a litigation report without assumptions section."""
    now = datetime.now(timezone.utc)
    
    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)
        
        raw_id = str(uuid.uuid4())
        db.add(
            RawRecord(
                raw_record_id=raw_id,
                dataset_version_id=dv.id,
                source_system="sys1",
                source_record_id="r1",
                payload={"data": "value1"},
                ingested_at=now,
            )
        )
        await db.commit()
        
        finding_id = str(uuid.uuid4())
        finding = await create_finding(
            db,
            finding_id=finding_id,
            dataset_version_id=dv.id,
            raw_record_id=raw_id,
            kind="test_kind",
            payload={"description": "Test finding"},
            created_at=now,
        )
        
        await db.commit()
    
    async with get_sessionmaker()() as db:
        report = await generate_litigation_report(
            db,
            dataset_version_id=dv.id,
            include_assumptions=False,
        )
        
        assert "assumptions" not in report


@pytest.mark.anyio
async def test_generate_litigation_report_without_evidence_index(sqlite_db: None) -> None:
    """Test generating a litigation report without evidence index."""
    now = datetime.now(timezone.utc)
    
    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)
        
        raw_id = str(uuid.uuid4())
        db.add(
            RawRecord(
                raw_record_id=raw_id,
                dataset_version_id=dv.id,
                source_system="sys1",
                source_record_id="r1",
                payload={"data": "value1"},
                ingested_at=now,
            )
        )
        await db.commit()
        
        finding_id = str(uuid.uuid4())
        finding = await create_finding(
            db,
            finding_id=finding_id,
            dataset_version_id=dv.id,
            raw_record_id=raw_id,
            kind="test_kind",
            payload={"description": "Test finding"},
            created_at=now,
        )
        
        await db.commit()
    
    async with get_sessionmaker()() as db:
        report = await generate_litigation_report(
            db,
            dataset_version_id=dv.id,
            include_evidence_index=False,
        )
        
        assert "evidence_index" not in report


@pytest.mark.anyio
async def test_generate_evidence_summary_report(sqlite_db: None) -> None:
    """Test generating an evidence summary report."""
    now = datetime.now(timezone.utc)
    
    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)
        
        # Create evidence with different kinds and engines
        for i, (kind, engine_id) in enumerate([
            ("kind_a", "engine_1"),
            ("kind_b", "engine_1"),
            ("kind_a", "engine_2"),
        ]):
            evidence_id = deterministic_evidence_id(
                dataset_version_id=dv.id,
                engine_id=engine_id,
                kind=kind,
                stable_key=f"key{i}",
            )
            await create_evidence(
                db,
                evidence_id=evidence_id,
                dataset_version_id=dv.id,
                engine_id=engine_id,
                kind=kind,
                payload={"data": f"value{i}"},
                created_at=now,
            )
        
        await db.commit()
    
    async with get_sessionmaker()() as db:
        report = await generate_evidence_summary_report(db, dataset_version_id=dv.id)
        
        assert report["dataset_version_id"] == dv.id
        assert "summary" in report
        assert report["summary"]["total_evidence_count"] == 3
        
        assert "evidence_by_kind" in report
        assert len(report["evidence_by_kind"]) == 2
        kind_counts = {item["kind"]: item["count"] for item in report["evidence_by_kind"]}
        assert kind_counts["kind_a"] == 2
        assert kind_counts["kind_b"] == 1
        
        assert "evidence_by_engine" in report
        assert len(report["evidence_by_engine"]) == 2
        engine_counts = {item["engine_id"]: item["count"] for item in report["evidence_by_engine"]}
        assert engine_counts["engine_1"] == 2
        assert engine_counts["engine_2"] == 1
        
        assert "traceability" in report
        assert report["traceability"]["valid"] is True
        
        assert "generated_at" in report


@pytest.mark.anyio
async def test_generate_litigation_report_empty_dataset(sqlite_db: None) -> None:
    """Test generating a litigation report for an empty dataset."""
    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)
        await db.commit()
    
    async with get_sessionmaker()() as db:
        report = await generate_litigation_report(db, dataset_version_id=dv.id)
        
        assert report["metadata"]["total_findings"] == 0
        assert report["findings"] == []
        assert report["scope"]["traceability_verified"] is True


@pytest.mark.anyio
async def test_scenario_description_from_payload(sqlite_db: None) -> None:
    """Test that scenario description is built from payload fields."""
    now = datetime.now(timezone.utc)
    
    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)
        
        raw_id = str(uuid.uuid4())
        db.add(
            RawRecord(
                raw_record_id=raw_id,
                dataset_version_id=dv.id,
                source_system="sys1",
                source_record_id="r1",
                payload={"data": "value1"},
                ingested_at=now,
            )
        )
        await db.commit()
        
        # Test with description field
        finding_1 = await create_finding(
            db,
            finding_id=str(uuid.uuid4()),
            dataset_version_id=dv.id,
            raw_record_id=raw_id,
            kind="test_kind",
            payload={"description": "Custom description"},
            created_at=now,
        )
        
        # Test with summary field
        finding_2 = await create_finding(
            db,
            finding_id=str(uuid.uuid4()),
            dataset_version_id=dv.id,
            raw_record_id=raw_id,
            kind="test_kind",
            payload={"summary": "Custom summary"},
            created_at=now,
        )
        
        # Test with type/category fields
        finding_3 = await create_finding(
            db,
            finding_id=str(uuid.uuid4()),
            dataset_version_id=dv.id,
            raw_record_id=raw_id,
            kind="test_kind",
            payload={"type": "error", "category": "validation"},
            created_at=now,
        )
        
        await db.commit()
    
    formatted_1 = format_finding_as_scenario(finding_1)
    assert formatted_1["scenario_description"] == "Custom description"
    
    formatted_2 = format_finding_as_scenario(finding_2)
    assert formatted_2["scenario_description"] == "Custom summary"
    
    formatted_3 = format_finding_as_scenario(finding_3)
    assert "test_kind" in formatted_3["scenario_description"]
    assert "type=error" in formatted_3["scenario_description"]
    assert "category=validation" in formatted_3["scenario_description"]






