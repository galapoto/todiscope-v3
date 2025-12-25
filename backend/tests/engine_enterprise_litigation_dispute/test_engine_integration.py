"""
Integration tests for Enterprise Litigation & Dispute Analysis Engine.

Tests cover:
- Full engine execution workflow
- Evidence creation and traceability
- Finding creation and linking
- Integration with evidence aggregation and reporting services
"""

from __future__ import annotations

from datetime import datetime, timezone
import uuid

import pytest
from sqlalchemy import select

from backend.app.core.dataset.service import create_dataset_version_via_ingestion
from backend.app.core.db import get_sessionmaker
from backend.app.core.dataset.models import DatasetVersion
from backend.app.core.dataset.raw_models import RawRecord
from backend.app.core.evidence.aggregation import (
    get_evidence_by_dataset_version,
    get_evidence_for_findings,
    get_findings_by_dataset_version,
    verify_evidence_traceability,
)
from backend.app.core.evidence.models import EvidenceRecord, FindingEvidenceLink, FindingRecord
from backend.app.core.normalization.models import NormalizedRecord
from backend.app.core.reporting.service import (
    generate_litigation_report,
    generate_evidence_summary_report,
)
from backend.app.engines.enterprise_litigation_dispute.constants import ENGINE_ID
from backend.app.engines.enterprise_litigation_dispute.run import run_engine


@pytest.mark.anyio
async def test_full_engine_execution(sqlite_db: None) -> None:
    """Test full engine execution with complete workflow."""
    now = datetime.now(timezone.utc)

    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)

        # Create raw record
        raw_id = str(uuid.uuid4())
        db.add(
            RawRecord(
                raw_record_id=raw_id,
                dataset_version_id=dv.id,
                source_system="legal_system",
                source_record_id="dispute_001",
                payload={
                    "legal_dispute": {
                        "claims": [{"amount": 1000000}],
                        "damages": {"compensatory": 800000, "punitive": 200000, "mitigation": 100000},
                        "liability": {
                            "parties": [{"party": "Defendant Corp", "percent": 80.0, "evidence_strength": 0.85}],
                            "admissions": ["Admission 1"],
                        },
                        "scenarios": [
                            {"name": "Best Case", "probability": 0.3, "expected_damages": 500000, "liability_multiplier": 1.0},
                            {"name": "Worst Case", "probability": 0.5, "expected_damages": 1200000, "liability_multiplier": 1.5},
                        ],
                        "legal_consistency": {
                            "conflicts": [],
                            "missing_support": [],
                        },
                    },
                },
                ingested_at=now,
            )
        )
        await db.commit()

        # Create normalized record
        norm_id = str(uuid.uuid4())
        db.add(
            NormalizedRecord(
                normalized_record_id=norm_id,
                dataset_version_id=dv.id,
                raw_record_id=raw_id,
                payload={
                    "legal_dispute": {
                        "claims": [{"amount": 1000000}],
                        "damages": {"compensatory": 800000, "punitive": 200000, "mitigation": 100000},
                        "liability": {
                            "parties": [{"party": "Defendant Corp", "percent": 80.0, "evidence_strength": 0.85}],
                            "admissions": ["Admission 1"],
                        },
                        "scenarios": [
                            {"name": "Best Case", "probability": 0.3, "expected_damages": 500000, "liability_multiplier": 1.0},
                            {"name": "Worst Case", "probability": 0.5, "expected_damages": 1200000, "liability_multiplier": 1.5},
                        ],
                        "legal_consistency": {
                            "conflicts": [],
                            "missing_support": [],
                        },
                    },
                },
                normalized_at=now,
            )
        )
        await db.commit()

    # Run engine
    result = await run_engine(
        dataset_version_id=dv.id,
        started_at=now.isoformat(),
        parameters={
            "assumptions": {
                "damage": {
                    "recovery_rate": 1.0,
                    "severity_thresholds": {"high": 1000000.0, "medium": 250000.0},
                },
                "liability": {
                    "evidence_strength_thresholds": {"strong": 0.75, "weak": 0.4},
                },
            },
        },
    )

    # Verify result structure
    assert result["dataset_version_id"] == dv.id
    assert "damage_assessment" in result
    assert "liability_assessment" in result
    assert "scenario_comparison" in result
    assert "legal_consistency" in result
    assert "findings" in result
    assert "evidence" in result
    assert "assumptions" in result

    # Verify findings
    assert len(result["findings"]) == 4  # damage, liability, scenario, consistency

    # Verify evidence IDs
    assert "damage" in result["evidence"]
    assert "liability" in result["evidence"]
    assert "scenario" in result["evidence"]
    assert "legal_consistency" in result["evidence"]
    assert "summary" in result["evidence"]

    # Verify assumptions are documented
    assert len(result["assumptions"]) > 0
    for assumption in result["assumptions"]:
        assert "id" in assumption
        assert "description" in assumption
        assert "source" in assumption


@pytest.mark.anyio
async def test_evidence_traceability_after_engine_run(sqlite_db: None) -> None:
    """Test that all evidence created by engine is traceable to dataset version."""
    now = datetime.now(timezone.utc)

    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)

        raw_id = str(uuid.uuid4())
        db.add(
            RawRecord(
                raw_record_id=raw_id,
                dataset_version_id=dv.id,
                source_system="legal_system",
                source_record_id="dispute_002",
                payload={
                    "legal_dispute": {
                        "claims": [{"amount": 500000}],
                        "damages": {"compensatory": 400000, "punitive": 100000},
                        "liability": {"parties": [{"party": "Party A", "percent": 70.0, "evidence_strength": 0.7}]},
                        "scenarios": [],
                        "legal_consistency": {"conflicts": [], "missing_support": []},
                    },
                },
                ingested_at=now,
            )
        )
        await db.commit()

        norm_id = str(uuid.uuid4())
        db.add(
            NormalizedRecord(
                normalized_record_id=norm_id,
                dataset_version_id=dv.id,
                raw_record_id=raw_id,
                payload={
                    "legal_dispute": {
                        "claims": [{"amount": 500000}],
                        "damages": {"compensatory": 400000, "punitive": 100000},
                        "liability": {"parties": [{"party": "Party A", "percent": 70.0, "evidence_strength": 0.7}]},
                        "scenarios": [],
                        "legal_consistency": {"conflicts": [], "missing_support": []},
                    },
                },
                normalized_at=now,
            )
        )
        await db.commit()

    # Run engine
    result = await run_engine(
        dataset_version_id=dv.id,
        started_at=now.isoformat(),
        parameters={},
    )

    # Verify evidence traceability
    async with get_sessionmaker()() as db:
        evidence_ids = list(result["evidence"].values())
        traceability_result = await verify_evidence_traceability(
            db, dataset_version_id=dv.id, evidence_ids=evidence_ids
        )

        assert traceability_result["valid"] is True
        assert traceability_result["total_checked"] == len(evidence_ids)
        assert len(traceability_result["mismatches"]) == 0

        # Verify all evidence belongs to correct dataset version
        evidence_records = await get_evidence_by_dataset_version(db, dataset_version_id=dv.id)
        assert len(evidence_records) >= len(evidence_ids)
        assert all(e.dataset_version_id == dv.id for e in evidence_records)
        assert all(e.engine_id == ENGINE_ID for e in evidence_records)


@pytest.mark.anyio
async def test_findings_linked_to_evidence(sqlite_db: None) -> None:
    """Test that findings are properly linked to evidence."""
    now = datetime.now(timezone.utc)

    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)

        raw_id = str(uuid.uuid4())
        db.add(
            RawRecord(
                raw_record_id=raw_id,
                dataset_version_id=dv.id,
                source_system="legal_system",
                source_record_id="dispute_003",
                payload={
                    "legal_dispute": {
                        "claims": [{"amount": 750000}],
                        "damages": {"compensatory": 600000, "punitive": 150000},
                        "liability": {"parties": [{"party": "Party B", "percent": 60.0, "evidence_strength": 0.6}]},
                        "scenarios": [
                            {"name": "Scenario 1", "probability": 0.4, "expected_damages": 600000, "liability_multiplier": 1.0},
                        ],
                        "legal_consistency": {"conflicts": [], "missing_support": []},
                    },
                },
                ingested_at=now,
            )
        )
        await db.commit()

        norm_id = str(uuid.uuid4())
        db.add(
            NormalizedRecord(
                normalized_record_id=norm_id,
                dataset_version_id=dv.id,
                raw_record_id=raw_id,
                payload={
                    "legal_dispute": {
                        "claims": [{"amount": 750000}],
                        "damages": {"compensatory": 600000, "punitive": 150000},
                        "liability": {"parties": [{"party": "Party B", "percent": 60.0, "evidence_strength": 0.6}]},
                        "scenarios": [
                            {"name": "Scenario 1", "probability": 0.4, "expected_damages": 600000, "liability_multiplier": 1.0},
                        ],
                        "legal_consistency": {"conflicts": [], "missing_support": []},
                    },
                },
                normalized_at=now,
            )
        )
        await db.commit()

    # Run engine
    result = await run_engine(
        dataset_version_id=dv.id,
        started_at=now.isoformat(),
        parameters={},
    )

    # Verify findings and evidence links
    async with get_sessionmaker()() as db:
        findings = await get_findings_by_dataset_version(db, dataset_version_id=dv.id)
        assert len(findings) == 4

        finding_ids = [f.finding_id for f in findings]
        evidence_by_finding = await get_evidence_for_findings(
            db, finding_ids=finding_ids, dataset_version_id=dv.id
        )

        # Each finding should have at least one evidence link
        for finding_id in finding_ids:
            assert finding_id in evidence_by_finding
            assert len(evidence_by_finding[finding_id]) > 0


@pytest.mark.anyio
async def test_report_generation_from_engine_output(sqlite_db: None) -> None:
    """Test that reports can be generated from engine outputs."""
    now = datetime.now(timezone.utc)

    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)

        raw_id = str(uuid.uuid4())
        db.add(
            RawRecord(
                raw_record_id=raw_id,
                dataset_version_id=dv.id,
                source_system="legal_system",
                source_record_id="dispute_004",
                payload={
                    "legal_dispute": {
                        "claims": [{"amount": 2000000}],
                        "damages": {"compensatory": 1500000, "punitive": 500000, "mitigation": 200000},
                        "liability": {
                            "parties": [{"party": "Defendant", "percent": 90.0, "evidence_strength": 0.9}],
                            "admissions": ["Admission"],
                        },
                        "scenarios": [
                            {"name": "Best", "probability": 0.2, "expected_damages": 1000000, "liability_multiplier": 1.0},
                            {"name": "Worst", "probability": 0.6, "expected_damages": 2500000, "liability_multiplier": 1.5},
                        ],
                        "legal_consistency": {"conflicts": [], "missing_support": []},
                    },
                },
                ingested_at=now,
            )
        )
        await db.commit()

        norm_id = str(uuid.uuid4())
        db.add(
            NormalizedRecord(
                normalized_record_id=norm_id,
                dataset_version_id=dv.id,
                raw_record_id=raw_id,
                payload={
                    "legal_dispute": {
                        "claims": [{"amount": 2000000}],
                        "damages": {"compensatory": 1500000, "punitive": 500000, "mitigation": 200000},
                        "liability": {
                            "parties": [{"party": "Defendant", "percent": 90.0, "evidence_strength": 0.9}],
                            "admissions": ["Admission"],
                        },
                        "scenarios": [
                            {"name": "Best", "probability": 0.2, "expected_damages": 1000000, "liability_multiplier": 1.0},
                            {"name": "Worst", "probability": 0.6, "expected_damages": 2500000, "liability_multiplier": 1.5},
                        ],
                        "legal_consistency": {"conflicts": [], "missing_support": []},
                    },
                },
                normalized_at=now,
            )
        )
        await db.commit()

    # Run engine
    await run_engine(
        dataset_version_id=dv.id,
        started_at=now.isoformat(),
        parameters={},
    )

    # Generate litigation report
    async with get_sessionmaker()() as db:
        report = await generate_litigation_report(
            db,
            dataset_version_id=dv.id,
            report_title="Test Litigation Report",
            include_assumptions=True,
            include_evidence_index=True,
            format_as_ranges=False,
        )

        # Verify report structure
        assert report["metadata"]["dataset_version_id"] == dv.id
        assert report["metadata"]["total_findings"] == 4
        assert len(report["findings"]) == 4
        assert "assumptions" in report
        assert "evidence_index" in report
        assert report["scope"]["traceability_verified"] is True

        # Verify findings are formatted as scenarios
        for finding in report["findings"]:
            assert "scenario_description" in finding
            assert "evidence_references" in finding
            assert len(finding["evidence_references"]) > 0

        # Generate evidence summary report
        summary_report = await generate_evidence_summary_report(db, dataset_version_id=dv.id)

        assert summary_report["dataset_version_id"] == dv.id
        assert summary_report["summary"]["total_evidence_count"] > 0
        assert summary_report["traceability"]["valid"] is True






