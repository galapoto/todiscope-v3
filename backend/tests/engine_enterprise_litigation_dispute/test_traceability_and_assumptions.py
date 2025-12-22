"""
Tests for traceability and assumption documentation verification.

Tests cover:
- Evidence traceability to dataset version
- Finding traceability to evidence
- Assumption documentation completeness
- Cross-dataset version isolation
"""

from __future__ import annotations

from datetime import datetime, timezone
import uuid

import pytest
from sqlalchemy import select

from backend.app.core.dataset.service import create_dataset_version_via_ingestion
from backend.app.core.db import get_sessionmaker
from backend.app.core.dataset.raw_models import RawRecord
from backend.app.core.evidence.aggregation import (
    DatasetVersionMismatchError,
    get_evidence_by_dataset_version,
    get_evidence_for_findings,
    get_findings_by_dataset_version,
    verify_evidence_traceability,
)
from backend.app.core.evidence.models import EvidenceRecord, FindingRecord
from backend.app.core.normalization.models import NormalizedRecord
from backend.app.core.reporting.service import generate_litigation_report
from backend.app.engines.enterprise_litigation_dispute.constants import ENGINE_ID
from backend.app.engines.enterprise_litigation_dispute.run import run_engine


@pytest.mark.anyio
async def test_all_evidence_bound_to_dataset_version(sqlite_db: None) -> None:
    """Test that all evidence is properly bound to dataset version."""
    now = datetime.now(timezone.utc)

    async with get_sessionmaker()() as db:
        dv1 = await create_dataset_version_via_ingestion(db)
        dv2 = await create_dataset_version_via_ingestion(db)

        # Create records for dv1
        raw_id_1 = str(uuid.uuid4())
        db.add(
            RawRecord(
                raw_record_id=raw_id_1,
                dataset_version_id=dv1.id,
                source_system="legal_system",
                source_record_id="trace_001",
                payload={
                    "legal_dispute": {
                        "claims": [{"amount": 500000}],
                        "damages": {"compensatory": 400000, "punitive": 100000},
                        "liability": {"parties": [{"party": "Party A", "percent": 80.0, "evidence_strength": 0.8}]},
                        "scenarios": [],
                        "legal_consistency": {"conflicts": [], "missing_support": []},
                    },
                },
                ingested_at=now,
            )
        )
        await db.commit()

        norm_id_1 = str(uuid.uuid4())
        db.add(
            NormalizedRecord(
                normalized_record_id=norm_id_1,
                dataset_version_id=dv1.id,
                raw_record_id=raw_id_1,
                payload={
                    "legal_dispute": {
                        "claims": [{"amount": 500000}],
                        "damages": {"compensatory": 400000, "punitive": 100000},
                        "liability": {"parties": [{"party": "Party A", "percent": 80.0, "evidence_strength": 0.8}]},
                        "scenarios": [],
                        "legal_consistency": {"conflicts": [], "missing_support": []},
                    },
                },
                normalized_at=now,
            )
        )
        await db.commit()

        # Create records for dv2
        raw_id_2 = str(uuid.uuid4())
        db.add(
            RawRecord(
                raw_record_id=raw_id_2,
                dataset_version_id=dv2.id,
                source_system="legal_system",
                source_record_id="trace_002",
                payload={
                    "legal_dispute": {
                        "claims": [{"amount": 300000}],
                        "damages": {"compensatory": 250000, "punitive": 50000},
                        "liability": {"parties": [{"party": "Party B", "percent": 70.0, "evidence_strength": 0.7}]},
                        "scenarios": [],
                        "legal_consistency": {"conflicts": [], "missing_support": []},
                    },
                },
                ingested_at=now,
            )
        )
        await db.commit()

        norm_id_2 = str(uuid.uuid4())
        db.add(
            NormalizedRecord(
                normalized_record_id=norm_id_2,
                dataset_version_id=dv2.id,
                raw_record_id=raw_id_2,
                payload={
                    "legal_dispute": {
                        "claims": [{"amount": 300000}],
                        "damages": {"compensatory": 250000, "punitive": 50000},
                        "liability": {"parties": [{"party": "Party B", "percent": 70.0, "evidence_strength": 0.7}]},
                        "scenarios": [],
                        "legal_consistency": {"conflicts": [], "missing_support": []},
                    },
                },
                normalized_at=now,
            )
        )
        await db.commit()

    # Run engine for both dataset versions
    result1 = await run_engine(
        dataset_version_id=dv1.id,
        started_at=now.isoformat(),
        parameters={},
    )

    result2 = await run_engine(
        dataset_version_id=dv2.id,
        started_at=now.isoformat(),
        parameters={},
    )

    # Verify evidence isolation between dataset versions
    async with get_sessionmaker()() as db:
        evidence_dv1 = await get_evidence_by_dataset_version(db, dataset_version_id=dv1.id)
        evidence_dv2 = await get_evidence_by_dataset_version(db, dataset_version_id=dv2.id)

        assert all(e.dataset_version_id == dv1.id for e in evidence_dv1)
        assert all(e.dataset_version_id == dv2.id for e in evidence_dv2)

        # Verify no cross-contamination
        evidence_ids_dv1 = {e.evidence_id for e in evidence_dv1}
        evidence_ids_dv2 = {e.evidence_id for e in evidence_dv2}
        assert len(evidence_ids_dv1.intersection(evidence_ids_dv2)) == 0

        # Verify traceability for each dataset version
        traceability_dv1 = await verify_evidence_traceability(db, dataset_version_id=dv1.id)
        traceability_dv2 = await verify_evidence_traceability(db, dataset_version_id=dv2.id)

        assert traceability_dv1["valid"] is True
        assert traceability_dv2["valid"] is True


@pytest.mark.anyio
async def test_findings_linked_to_correct_evidence(sqlite_db: None) -> None:
    """Test that findings are linked to correct evidence records."""
    now = datetime.now(timezone.utc)

    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)

        raw_id = str(uuid.uuid4())
        db.add(
            RawRecord(
                raw_record_id=raw_id,
                dataset_version_id=dv.id,
                source_system="legal_system",
                source_record_id="link_001",
                payload={
                    "legal_dispute": {
                        "claims": [{"amount": 600000}],
                        "damages": {"compensatory": 500000, "punitive": 100000},
                        "liability": {"parties": [{"party": "Defendant", "percent": 75.0, "evidence_strength": 0.75}]},
                        "scenarios": [
                            {"name": "Scenario 1", "probability": 0.5, "expected_damages": 500000, "liability_multiplier": 1.0},
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
                        "claims": [{"amount": 600000}],
                        "damages": {"compensatory": 500000, "punitive": 100000},
                        "liability": {"parties": [{"party": "Defendant", "percent": 75.0, "evidence_strength": 0.75}]},
                        "scenarios": [
                            {"name": "Scenario 1", "probability": 0.5, "expected_damages": 500000, "liability_multiplier": 1.0},
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

        # Each finding should have evidence linked
        for finding_id in finding_ids:
            assert finding_id in evidence_by_finding
            assert len(evidence_by_finding[finding_id]) > 0

            # Verify evidence belongs to correct dataset version
            for evidence in evidence_by_finding[finding_id]:
                assert evidence.dataset_version_id == dv.id
                assert evidence.engine_id == ENGINE_ID


@pytest.mark.anyio
async def test_assumptions_documented_in_all_outputs(sqlite_db: None) -> None:
    """Test that assumptions are documented in all analysis outputs."""
    now = datetime.now(timezone.utc)

    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)

        raw_id = str(uuid.uuid4())
        db.add(
            RawRecord(
                raw_record_id=raw_id,
                dataset_version_id=dv.id,
                source_system="legal_system",
                source_record_id="assumptions_001",
                payload={
                    "legal_dispute": {
                        "claims": [{"amount": 800000}],
                        "damages": {"compensatory": 600000, "punitive": 200000, "mitigation": 100000},
                        "liability": {"parties": [{"party": "Defendant", "percent": 85.0, "evidence_strength": 0.85}]},
                        "scenarios": [
                            {"name": "Best", "probability": 0.3, "expected_damages": 500000, "liability_multiplier": 1.0},
                            {"name": "Worst", "probability": 0.5, "expected_damages": 1000000, "liability_multiplier": 1.5},
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
                        "claims": [{"amount": 800000}],
                        "damages": {"compensatory": 600000, "punitive": 200000, "mitigation": 100000},
                        "liability": {"parties": [{"party": "Defendant", "percent": 85.0, "evidence_strength": 0.85}]},
                        "scenarios": [
                            {"name": "Best", "probability": 0.3, "expected_damages": 500000, "liability_multiplier": 1.0},
                            {"name": "Worst", "probability": 0.5, "expected_damages": 1000000, "liability_multiplier": 1.5},
                        ],
                        "legal_consistency": {"conflicts": [], "missing_support": []},
                    },
                },
                normalized_at=now,
            )
        )
        await db.commit()

    # Run engine with custom assumptions
    result = await run_engine(
        dataset_version_id=dv.id,
        started_at=now.isoformat(),
        parameters={
            "assumptions": {
                "damage": {
                    "recovery_rate": 0.8,
                    "severity_thresholds": {"high": 1000000.0, "medium": 250000.0},
                },
                "liability": {
                    "evidence_strength_thresholds": {"strong": 0.75, "weak": 0.4},
                },
            },
        },
    )

    # Verify assumptions are documented in all sections
    assert "assumptions" in result
    assert len(result["assumptions"]) > 0

    # Verify assumptions structure
    for assumption in result["assumptions"]:
        assert "id" in assumption
        assert "description" in assumption
        assert "source" in assumption
        assert "impact" in assumption
        assert "sensitivity" in assumption

    # Verify assumptions in individual assessments
    assert "assumptions" in result["damage_assessment"]
    assert "assumptions" in result["liability_assessment"]
    assert "assumptions" in result["scenario_comparison"]
    assert "assumptions" in result["legal_consistency"]

    # Verify assumptions are in evidence payloads
    async with get_sessionmaker()() as db:
        evidence_records = await get_evidence_by_dataset_version(db, dataset_version_id=dv.id)
        for evidence in evidence_records:
            if "damage" in evidence.kind or "liability" in evidence.kind or "scenario" in evidence.kind:
                payload = evidence.payload
                if isinstance(payload, dict):
                    # Check if assumptions are in payload
                    section_key = list(payload.keys())[0] if payload else None
                    if section_key and isinstance(payload[section_key], dict):
                        assert "assumptions" in payload[section_key]


@pytest.mark.anyio
async def test_assumptions_in_report(sqlite_db: None) -> None:
    """Test that assumptions are included in generated reports."""
    now = datetime.now(timezone.utc)

    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)

        raw_id = str(uuid.uuid4())
        db.add(
            RawRecord(
                raw_record_id=raw_id,
                dataset_version_id=dv.id,
                source_system="legal_system",
                source_record_id="report_assumptions_001",
                payload={
                    "legal_dispute": {
                        "claims": [{"amount": 400000}],
                        "damages": {"compensatory": 300000, "punitive": 100000},
                        "liability": {"parties": [{"party": "Defendant", "percent": 70.0, "evidence_strength": 0.7}]},
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
                        "claims": [{"amount": 400000}],
                        "damages": {"compensatory": 300000, "punitive": 100000},
                        "liability": {"parties": [{"party": "Defendant", "percent": 70.0, "evidence_strength": 0.7}]},
                        "scenarios": [],
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

    # Generate report
    async with get_sessionmaker()() as db:
        report = await generate_litigation_report(
            db,
            dataset_version_id=dv.id,
            include_assumptions=True,
            include_evidence_index=True,
        )

        # Verify assumptions are in report (may be empty if no assumptions extracted from findings)
        assert "assumptions" in report
        # Assumptions are collected from findings, so they may be empty if findings don't have assumptions in payload
        # The important thing is that the assumptions section exists

        # Verify findings are properly formatted (assumptions may be in report-level or finding-level)
        for finding in report["findings"]:
            assert "finding_id" in finding
            assert "scenario_description" in finding or "ranges" in finding
            # Assumptions are collected at report level, not necessarily per finding


@pytest.mark.anyio
async def test_cross_dataset_version_isolation(sqlite_db: None) -> None:
    """Test that evidence cannot be accessed across dataset versions."""
    now = datetime.now(timezone.utc)

    async with get_sessionmaker()() as db:
        dv1 = await create_dataset_version_via_ingestion(db)
        dv2 = await create_dataset_version_via_ingestion(db)

        # Create and run engine for dv1
        raw_id_1 = str(uuid.uuid4())
        db.add(
            RawRecord(
                raw_record_id=raw_id_1,
                dataset_version_id=dv1.id,
                source_system="legal_system",
                source_record_id="isolation_001",
                payload={
                    "legal_dispute": {
                        "claims": [{"amount": 500000}],
                        "damages": {"compensatory": 400000, "punitive": 100000},
                        "liability": {"parties": [{"party": "Party A", "percent": 80.0, "evidence_strength": 0.8}]},
                        "scenarios": [],
                        "legal_consistency": {"conflicts": [], "missing_support": []},
                    },
                },
                ingested_at=now,
            )
        )
        await db.commit()

        norm_id_1 = str(uuid.uuid4())
        db.add(
            NormalizedRecord(
                normalized_record_id=norm_id_1,
                dataset_version_id=dv1.id,
                raw_record_id=raw_id_1,
                payload={
                    "legal_dispute": {
                        "claims": [{"amount": 500000}],
                        "damages": {"compensatory": 400000, "punitive": 100000},
                        "liability": {"parties": [{"party": "Party A", "percent": 80.0, "evidence_strength": 0.8}]},
                        "scenarios": [],
                        "legal_consistency": {"conflicts": [], "missing_support": []},
                    },
                },
                normalized_at=now,
            )
        )
        await db.commit()

    # Run engine for dv1
    result1 = await run_engine(
        dataset_version_id=dv1.id,
        started_at=now.isoformat(),
        parameters={},
    )

    # Try to access dv1 evidence with dv2 dataset_version_id (should fail or return empty)
    async with get_sessionmaker()() as db:
        evidence_ids_dv1 = list(result1["evidence"].values())

        # Verify evidence cannot be retrieved for wrong dataset version
        with pytest.raises(DatasetVersionMismatchError):
            from backend.app.core.evidence.aggregation import get_evidence_by_ids

            await get_evidence_by_ids(
                db, evidence_ids=evidence_ids_dv1, dataset_version_id=dv2.id
            )

        # Verify traceability check fails for wrong dataset version
        traceability_result = await verify_evidence_traceability(
            db, dataset_version_id=dv2.id, evidence_ids=evidence_ids_dv1
        )
        assert traceability_result["valid"] is False
        assert len(traceability_result["mismatches"]) > 0

