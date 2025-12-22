"""
Tests for the /report endpoint of Enterprise Litigation & Dispute Analysis Engine.

Tests cover:
- Report endpoint accessibility
- Report generation from findings and evidence
- Report content validation (damage assessment, scenario comparison, evidence)
- Error handling (missing findings, missing evidence, invalid inputs)
- DatasetVersion validation
"""

from __future__ import annotations

from datetime import datetime, timezone
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.core.dataset.service import create_dataset_version_via_ingestion
from backend.app.core.db import get_sessionmaker
from backend.app.core.dataset.raw_models import RawRecord
from backend.app.core.normalization.models import NormalizedRecord
from backend.app.engines.enterprise_litigation_dispute.constants import ENGINE_ID
from backend.app.engines.enterprise_litigation_dispute.run import run_engine
from backend.app.main import create_app


@pytest.mark.anyio
async def test_report_endpoint_generates_report(monkeypatch: pytest.MonkeyPatch, sqlite_db: None) -> None:
    """Test that /report endpoint generates a complete report."""
    now = datetime.now(timezone.utc)

    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)

        raw_id = str(uuid.uuid4())
        db.add(
            RawRecord(
                raw_record_id=raw_id,
                dataset_version_id=dv.id,
                source_system="legal_system",
                source_record_id="report_test_001",
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

    # Run engine to create findings and evidence
    await run_engine(
        dataset_version_id=dv.id,
        started_at=now.isoformat(),
        parameters={},
    )

    # Enable engine and generate report via endpoint
    monkeypatch.setenv("TODISCOPE_ENABLED_ENGINES", ENGINE_ID)
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v3/engines/litigation-analysis/report",
            json={"dataset_version_id": dv.id},
        )

    assert response.status_code == 200
    report = response.json()

    # Verify report structure
    assert "metadata" in report
    assert report["metadata"]["engine_id"] == ENGINE_ID
    assert report["metadata"]["dataset_version_id"] == dv.id
    assert "generated_at" in report["metadata"]

    # Verify executive summary
    assert "executive_summary" in report
    assert report["executive_summary"]["total_findings"] == 4
    assert "net_damage" in report["executive_summary"]
    assert "damage_severity" in report["executive_summary"]

    # Verify analysis results
    assert "damage_assessment" in report
    assert "liability_assessment" in report
    assert "scenario_comparison" in report
    assert "legal_consistency" in report

    # Verify findings
    assert "findings" in report
    assert len(report["findings"]) == 4

    # Verify evidence index
    assert "evidence_index" in report
    assert len(report["evidence_index"]) > 0

    # Verify assumptions
    assert "assumptions" in report
    assert isinstance(report["assumptions"], list)

    # Verify limitations
    assert "limitations" in report
    assert isinstance(report["limitations"], list)
    assert len(report["limitations"]) > 0


@pytest.mark.anyio
async def test_report_endpoint_contains_damage_assessment(monkeypatch: pytest.MonkeyPatch, sqlite_db: None) -> None:
    """Test that report contains detailed damage assessment."""
    now = datetime.now(timezone.utc)

    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)

        raw_id = str(uuid.uuid4())
        db.add(
            RawRecord(
                raw_record_id=raw_id,
                dataset_version_id=dv.id,
                source_system="legal_system",
                source_record_id="damage_test_001",
                payload={
                    "legal_dispute": {
                        "claims": [{"amount": 2000000}],
                        "damages": {"compensatory": 1500000, "punitive": 500000, "mitigation": 200000},
                        "liability": {"parties": [{"party": "Defendant", "percent": 90.0, "evidence_strength": 0.9}]},
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
                        "claims": [{"amount": 2000000}],
                        "damages": {"compensatory": 1500000, "punitive": 500000, "mitigation": 200000},
                        "liability": {"parties": [{"party": "Defendant", "percent": 90.0, "evidence_strength": 0.9}]},
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

    # Enable engine and generate report
    monkeypatch.setenv("TODISCOPE_ENABLED_ENGINES", ENGINE_ID)
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v3/engines/litigation-analysis/report",
            json={"dataset_version_id": dv.id},
        )

    assert response.status_code == 200
    report = response.json()

    # Verify damage assessment details
    assert "damage_assessment" in report
    damage = report["damage_assessment"]
    assert "net_damage" in damage
    assert "gross_damages" in damage
    assert "mitigation" in damage
    assert "severity" in damage
    assert "severity_score" in damage
    assert "confidence" in damage
    assert damage["net_damage"] > 0
    assert damage["severity"] in ("high", "medium", "low")


@pytest.mark.anyio
async def test_report_endpoint_contains_scenario_comparison(monkeypatch: pytest.MonkeyPatch, sqlite_db: None) -> None:
    """Test that report contains scenario comparison details."""
    now = datetime.now(timezone.utc)

    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)

        raw_id = str(uuid.uuid4())
        db.add(
            RawRecord(
                raw_record_id=raw_id,
                dataset_version_id=dv.id,
                source_system="legal_system",
                source_record_id="scenario_test_001",
                payload={
                    "legal_dispute": {
                        "claims": [{"amount": 500000}],
                        "damages": {"compensatory": 400000, "punitive": 100000},
                        "liability": {"parties": [{"party": "Defendant", "percent": 70.0, "evidence_strength": 0.7}]},
                        "scenarios": [
                            {"name": "Settlement", "probability": 0.4, "expected_damages": 300000, "liability_multiplier": 0.8},
                            {"name": "Trial", "probability": 0.6, "expected_damages": 800000, "liability_multiplier": 1.2},
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
                        "claims": [{"amount": 500000}],
                        "damages": {"compensatory": 400000, "punitive": 100000},
                        "liability": {"parties": [{"party": "Defendant", "percent": 70.0, "evidence_strength": 0.7}]},
                        "scenarios": [
                            {"name": "Settlement", "probability": 0.4, "expected_damages": 300000, "liability_multiplier": 0.8},
                            {"name": "Trial", "probability": 0.6, "expected_damages": 800000, "liability_multiplier": 1.2},
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

    # Enable engine and generate report
    monkeypatch.setenv("TODISCOPE_ENABLED_ENGINES", ENGINE_ID)
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v3/engines/litigation-analysis/report",
            json={"dataset_version_id": dv.id},
        )

    assert response.status_code == 200
    report = response.json()

    # Verify scenario comparison details
    assert "scenario_comparison" in report
    scenario = report["scenario_comparison"]
    assert "scenarios" in scenario
    assert len(scenario["scenarios"]) == 2
    assert "best_case" in scenario
    assert "worst_case" in scenario
    assert "total_probability" in scenario
    assert scenario["best_case"] is not None
    assert scenario["worst_case"] is not None


@pytest.mark.anyio
async def test_report_endpoint_contains_evidence_linking(monkeypatch: pytest.MonkeyPatch, sqlite_db: None) -> None:
    """Test that report contains evidence linking information."""
    now = datetime.now(timezone.utc)

    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)

        raw_id = str(uuid.uuid4())
        db.add(
            RawRecord(
                raw_record_id=raw_id,
                dataset_version_id=dv.id,
                source_system="legal_system",
                source_record_id="evidence_test_001",
                payload={
                    "legal_dispute": {
                        "claims": [{"amount": 750000}],
                        "damages": {"compensatory": 600000, "punitive": 150000},
                        "liability": {"parties": [{"party": "Defendant", "percent": 75.0, "evidence_strength": 0.75}]},
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
                        "claims": [{"amount": 750000}],
                        "damages": {"compensatory": 600000, "punitive": 150000},
                        "liability": {"parties": [{"party": "Defendant", "percent": 75.0, "evidence_strength": 0.75}]},
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

    # Enable engine and generate report
    monkeypatch.setenv("TODISCOPE_ENABLED_ENGINES", ENGINE_ID)
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v3/engines/litigation-analysis/report",
            json={"dataset_version_id": dv.id},
        )

    assert response.status_code == 200
    report = response.json()

    # Verify evidence index
    assert "evidence_index" in report
    assert len(report["evidence_index"]) > 0

    # Verify findings have evidence references
    for finding in report["findings"]:
        assert "evidence_ids" in finding
        assert isinstance(finding["evidence_ids"], list)
        assert len(finding["evidence_ids"]) > 0

    # Verify evidence index structure
    for evidence in report["evidence_index"]:
        assert "evidence_id" in evidence
        assert "kind" in evidence
        assert "engine_id" in evidence
        assert evidence["engine_id"] == ENGINE_ID
        assert evidence["dataset_version_id"] == dv.id


@pytest.mark.anyio
async def test_report_endpoint_missing_dataset_version(monkeypatch: pytest.MonkeyPatch, sqlite_db: None) -> None:
    """Test that /report endpoint returns 400 for missing dataset_version_id."""
    monkeypatch.setenv("TODISCOPE_ENABLED_ENGINES", ENGINE_ID)
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v3/engines/litigation-analysis/report",
            json={},
        )

    assert response.status_code == 400


@pytest.mark.anyio
async def test_report_endpoint_invalid_dataset_version(monkeypatch: pytest.MonkeyPatch, sqlite_db: None) -> None:
    """Test that /report endpoint returns 400 for invalid dataset_version_id."""
    monkeypatch.setenv("TODISCOPE_ENABLED_ENGINES", ENGINE_ID)
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v3/engines/litigation-analysis/report",
            json={"dataset_version_id": ""},
        )

    assert response.status_code == 400


@pytest.mark.anyio
async def test_report_endpoint_no_findings(monkeypatch: pytest.MonkeyPatch, sqlite_db: None) -> None:
    """Test that /report endpoint returns 404 when no findings exist."""
    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)
        await db.commit()

    monkeypatch.setenv("TODISCOPE_ENABLED_ENGINES", ENGINE_ID)
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v3/engines/litigation-analysis/report",
            json={"dataset_version_id": dv.id},
        )

    assert response.status_code == 404
    assert "findings" in response.json()["detail"].lower() or "not found" in response.json()["detail"].lower()


@pytest.mark.anyio
async def test_report_endpoint_respects_dataset_version(monkeypatch: pytest.MonkeyPatch, sqlite_db: None) -> None:
    """Test that report only includes findings and evidence for the specified dataset version."""
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
                source_record_id="dv1_test",
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
    await run_engine(
        dataset_version_id=dv1.id,
        started_at=now.isoformat(),
        parameters={},
    )

    # Enable engine
    monkeypatch.setenv("TODISCOPE_ENABLED_ENGINES", ENGINE_ID)
    app = create_app()
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Try to generate report for dv2 (should return 404)
        response = await ac.post(
            "/api/v3/engines/litigation-analysis/report",
            json={"dataset_version_id": dv2.id},
        )

        assert response.status_code == 404

        # Generate report for dv1 (should succeed)
        response = await ac.post(
            "/api/v3/engines/litigation-analysis/report",
            json={"dataset_version_id": dv1.id},
        )

        assert response.status_code == 200
        report = response.json()
    assert report["metadata"]["dataset_version_id"] == dv1.id

    # Verify all findings and evidence belong to dv1
    for finding in report["findings"]:
        assert finding.get("finding_id") is not None

    for evidence in report["evidence_index"]:
        assert evidence["dataset_version_id"] == dv1.id

