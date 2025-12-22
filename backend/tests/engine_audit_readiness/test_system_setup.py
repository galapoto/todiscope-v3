"""
Test System Setup

Tests to verify DatasetVersion enforcement and data flow between components.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from backend.app.core.db import get_sessionmaker
from backend.app.core.dataset.models import DatasetVersion
from backend.app.core.dataset.raw_models import RawRecord
from backend.app.core.evidence.models import EvidenceRecord, FindingEvidenceLink, FindingRecord
from backend.app.engines.audit_readiness.models.runs import AuditReadinessRun
from backend.app.main import create_app


@pytest.mark.anyio
async def test_dataset_version_enforcement_required(sqlite_db: None) -> None:
    """Test that dataset_version_id is required and validated."""
    os.environ["TODISCOPE_ENABLED_ENGINES"] = "engine_audit_readiness"
    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Test missing dataset_version_id
        res = await ac.post(
            "/api/v3/engines/audit-readiness/run",
            json={
                "started_at": "2025-01-01T00:00:00+00:00",
                "regulatory_frameworks": ["framework_1"],
            },
        )
        assert res.status_code == 400
        assert "DATASET_VERSION_ID_REQUIRED" in res.text

        # Test None dataset_version_id
        res = await ac.post(
            "/api/v3/engines/audit-readiness/run",
            json={
                "dataset_version_id": None,
                "started_at": "2025-01-01T00:00:00+00:00",
                "regulatory_frameworks": ["framework_1"],
            },
        )
        assert res.status_code == 400

        # Test empty dataset_version_id
        res = await ac.post(
            "/api/v3/engines/audit-readiness/run",
            json={
                "dataset_version_id": "",
                "started_at": "2025-01-01T00:00:00+00:00",
                "regulatory_frameworks": ["framework_1"],
            },
        )
        assert res.status_code == 400


@pytest.mark.anyio
async def test_dataset_version_not_found(sqlite_db: None) -> None:
    """Test that non-existent dataset_version_id is rejected."""
    os.environ["TODISCOPE_ENABLED_ENGINES"] = "engine_audit_readiness"
    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            "/api/v3/engines/audit-readiness/run",
            json={
                "dataset_version_id": "00000000-0000-7000-0000-000000000000",
                "started_at": "2025-01-01T00:00:00+00:00",
                "regulatory_frameworks": ["framework_1"],
            },
        )
        assert res.status_code == 404
        assert "DATASET_VERSION_NOT_FOUND" in res.text


@pytest.mark.anyio
async def test_dataset_version_binding_to_outputs(sqlite_db: None) -> None:
    """Test that all outputs are bound to DatasetVersion."""
    os.environ["TODISCOPE_ENABLED_ENGINES"] = "engine_audit_readiness"
    app = create_app()

    control_catalog = {
        "frameworks": {
            "framework_1": {
                "metadata": {"name": "Test Framework", "version": "v1"},
                "controls": [
                    {
                        "control_id": "ctrl_001",
                        "control_name": "Access Control",
                        "critical": False,
                    }
                ],
                "required_evidence_types": {
                    "ctrl_001": ["evidence_type_1"]
                }
            }
        }
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create dataset version
        ingest_res = await ac.post("/api/v3/ingest-records", json={"records": [{"test": "data"}]})
        assert ingest_res.status_code == 200
        dv_id = ingest_res.json()["dataset_version_id"]

        # Run engine
        run_res = await ac.post(
            "/api/v3/engines/audit-readiness/run",
            json={
                "dataset_version_id": dv_id,
                "started_at": "2025-01-01T00:00:00+00:00",
                "regulatory_frameworks": ["framework_1"],
                "control_catalog": control_catalog,
            },
        )
        assert run_res.status_code == 200
        body = run_res.json()

        # Verify DatasetVersion binding
        assert body["dataset_version_id"] == dv_id

        # Verify run record is bound to DatasetVersion
        async with get_sessionmaker()() as db:
            run = await db.scalar(
                select(AuditReadinessRun).where(AuditReadinessRun.run_id == body["run_id"])
            )
            assert run is not None
            assert run.dataset_version_id == dv_id

            # Verify evidence is bound to DatasetVersion
            for evidence_id in body["evidence_ids"]:
                evidence = await db.scalar(
                    select(EvidenceRecord).where(EvidenceRecord.evidence_id == evidence_id)
                )
                assert evidence is not None
                assert evidence.dataset_version_id == dv_id

            # Verify findings are bound to DatasetVersion
            findings = await db.scalars(
                select(FindingRecord).where(FindingRecord.dataset_version_id == dv_id)
            )
            findings_list = list(findings.all())
            assert len(findings_list) > 0
            for finding in findings_list:
                assert finding.dataset_version_id == dv_id


@pytest.mark.anyio
async def test_data_flow_through_components(sqlite_db: None) -> None:
    """Test data flow through all components."""
    os.environ["TODISCOPE_ENABLED_ENGINES"] = "engine_audit_readiness"
    app = create_app()

    control_catalog = {
        "frameworks": {
            "framework_1": {
                "metadata": {"name": "Test Framework", "version": "v1"},
                "controls": [
                    {
                        "control_id": "ctrl_001",
                        "control_name": "Access Control",
                        "critical": True,
                    }
                ],
                "required_evidence_types": {
                    "ctrl_001": ["evidence_type_1"]
                }
            }
        }
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create dataset version with raw records
        ingest_res = await ac.post("/api/v3/ingest-records", json={"records": [{"test": "data"}]})
        assert ingest_res.status_code == 200
        dv_id = ingest_res.json()["dataset_version_id"]

        # Verify raw records exist
        async with get_sessionmaker()() as db:
            raw_records = await db.scalars(
                select(RawRecord).where(RawRecord.dataset_version_id == dv_id)
            )
            raw_list = list(raw_records.all())
            assert len(raw_list) > 0

        # Run engine
        run_res = await ac.post(
            "/api/v3/engines/audit-readiness/run",
            json={
                "dataset_version_id": dv_id,
                "started_at": "2025-01-01T00:00:00+00:00",
                "regulatory_frameworks": ["framework_1"],
                "control_catalog": control_catalog,
            },
        )
        assert run_res.status_code == 200
        body = run_res.json()

        # Verify data flow: RawRecord -> Finding -> Evidence
        async with get_sessionmaker()() as db:
            # Get raw record
            raw_record = await db.scalar(
                select(RawRecord).where(RawRecord.dataset_version_id == dv_id)
            )
            assert raw_record is not None

            # Get findings linked to raw record
            findings = await db.scalars(
                select(FindingRecord).where(
                    FindingRecord.raw_record_id == raw_record.raw_record_id
                )
            )
            findings_list = list(findings.all())
            assert len(findings_list) > 0

            # Get evidence linked to findings
            for finding in findings_list:
                links = await db.scalars(
                    select(FindingEvidenceLink).where(
                        FindingEvidenceLink.finding_id == finding.finding_id
                    )
                )
                links_list = list(links.all())
                assert len(links_list) > 0

                for link in links_list:
                    evidence = await db.scalar(
                        select(EvidenceRecord).where(
                            EvidenceRecord.evidence_id == link.evidence_id
                        )
                    )
                    assert evidence is not None
                    assert evidence.dataset_version_id == dv_id


@pytest.mark.anyio
async def test_started_at_validation(sqlite_db: None) -> None:
    """Test that started_at is validated."""
    os.environ["TODISCOPE_ENABLED_ENGINES"] = "engine_audit_readiness"
    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ingest_res = await ac.post("/api/v3/ingest-records", json={"records": [{"test": "data"}]})
        assert ingest_res.status_code == 200
        dv_id = ingest_res.json()["dataset_version_id"]

        # Test missing started_at
        res = await ac.post(
            "/api/v3/engines/audit-readiness/run",
            json={
                "dataset_version_id": dv_id,
                "regulatory_frameworks": ["framework_1"],
            },
        )
        assert res.status_code == 400
        assert "STARTED_AT_REQUIRED" in res.text

        # Test invalid started_at format
        res = await ac.post(
            "/api/v3/engines/audit-readiness/run",
            json={
                "dataset_version_id": dv_id,
                "started_at": "invalid-date",
                "regulatory_frameworks": ["framework_1"],
            },
        )
        assert res.status_code == 400


@pytest.mark.anyio
async def test_kill_switch_enforcement(sqlite_db: None) -> None:
    """Test that kill-switch prevents engine execution when disabled."""
    os.environ.pop("TODISCOPE_ENABLED_ENGINES", None)
    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ingest_res = await ac.post("/api/v3/ingest-records", json={"records": [{"test": "data"}]})
        assert ingest_res.status_code == 200
        dv_id = ingest_res.json()["dataset_version_id"]

        res = await ac.post(
            "/api/v3/engines/audit-readiness/run",
            json={
                "dataset_version_id": dv_id,
                "started_at": "2025-01-01T00:00:00+00:00",
                "regulatory_frameworks": ["framework_1"],
            },
        )
        assert res.status_code == 503
        assert "ENGINE_DISABLED" in res.text

