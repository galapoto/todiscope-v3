"""
Integration Tests for Audit Readiness Engine

End-to-end tests validating the complete system integration.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from backend.app.core.db import get_sessionmaker
from backend.app.core.evidence.models import EvidenceRecord, FindingEvidenceLink, FindingRecord
from backend.app.engines.audit_readiness.models.runs import AuditReadinessRun
from backend.app.main import create_app


@pytest.mark.anyio
async def test_end_to_end_regulatory_readiness_evaluation(sqlite_db: None) -> None:
    """Test complete end-to-end regulatory readiness evaluation."""
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
                    },
                    {
                        "control_id": "ctrl_002",
                        "control_name": "Data Encryption",
                        "critical": False,
                    }
                ],
                "required_evidence_types": {
                    "ctrl_001": ["access_evidence"],
                    "ctrl_002": ["encryption_evidence"]
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
        result = run_res.json()

        # Verify response structure
        assert "dataset_version_id" in result
        assert "run_id" in result
        assert "regulatory_results" in result
        assert "findings_count" in result
        assert "evidence_ids" in result
        assert "audit_trail_entries" in result

        # Verify regulatory results
        assert len(result["regulatory_results"]) == 1
        regulatory_result = result["regulatory_results"][0]
        assert regulatory_result["framework_id"] == "framework_1"
        assert "check_status" in regulatory_result
        assert "risk_level" in regulatory_result
        assert "controls_assessed" in regulatory_result
        assert regulatory_result["controls_assessed"] == 2

        # Verify database records
        async with get_sessionmaker()() as db:
            # Verify run record
            run = await db.scalar(
                select(AuditReadinessRun).where(AuditReadinessRun.run_id == result["run_id"])
            )
            assert run is not None
            assert run.dataset_version_id == dv_id
            assert run.status == "completed"
            assert "framework_1" in run.regulatory_frameworks

            # Verify evidence records
            evidence_count = 0
            for evidence_id in result["evidence_ids"]:
                evidence = await db.scalar(
                    select(EvidenceRecord).where(EvidenceRecord.evidence_id == evidence_id)
                )
                assert evidence is not None
                assert evidence.dataset_version_id == dv_id
                evidence_count += 1
            assert evidence_count > 0

            # Verify findings
            findings = await db.scalars(
                select(FindingRecord).where(FindingRecord.dataset_version_id == dv_id)
            )
            findings_list = list(findings.all())
            assert len(findings_list) == result["findings_count"]

            # Verify finding-evidence links
            for finding in findings_list:
                links = await db.scalars(
                    select(FindingEvidenceLink).where(
                        FindingEvidenceLink.finding_id == finding.finding_id
                    )
                )
                links_list = list(links.all())
                assert len(links_list) > 0


@pytest.mark.anyio
async def test_audit_trail_traceability(sqlite_db: None) -> None:
    """Test that audit trail provides full traceability."""
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
                    "ctrl_001": ["access_evidence"]
                }
            }
        }
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ingest_res = await ac.post("/api/v3/ingest-records", json={"records": [{"test": "data"}]})
        assert ingest_res.status_code == 200
        dv_id = ingest_res.json()["dataset_version_id"]

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
        result = run_res.json()

        # Verify audit trail entries exist
        assert result["audit_trail_entries"] > 0

        # Verify audit trail evidence records
        async with get_sessionmaker()() as db:
            audit_trail_evidence = await db.scalars(
                select(EvidenceRecord).where(
                    EvidenceRecord.dataset_version_id == dv_id,
                    EvidenceRecord.kind == "audit_trail"
                )
            )
            audit_list = list(audit_trail_evidence.all())
            assert len(audit_list) == result["audit_trail_entries"]

            # Verify audit trail entries contain required information
            for audit_entry in audit_list:
                assert "action_type" in audit_entry.payload
                assert "action_details" in audit_entry.payload
                assert audit_entry.payload["dataset_version_id"] == dv_id


@pytest.mark.anyio
async def test_deterministic_run_id(sqlite_db: None) -> None:
    """Test that run_id is deterministic for same inputs."""
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
                    "ctrl_001": ["access_evidence"]
                }
            }
        }
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ingest_res = await ac.post("/api/v3/ingest-records", json={"records": [{"test": "data"}]})
        assert ingest_res.status_code == 200
        dv_id = ingest_res.json()["dataset_version_id"]

        # First run
        run_res_1 = await ac.post(
            "/api/v3/engines/audit-readiness/run",
            json={
                "dataset_version_id": dv_id,
                "started_at": "2025-01-01T00:00:00+00:00",
                "regulatory_frameworks": ["framework_1"],
                "control_catalog": control_catalog,
                "parameters": {"test_param": "value"},
            },
        )
        assert run_res_1.status_code == 200
        run_id_1 = run_res_1.json()["run_id"]

        # Second run with same inputs (different timestamp should not matter)
        run_res_2 = await ac.post(
            "/api/v3/engines/audit-readiness/run",
            json={
                "dataset_version_id": dv_id,
                "started_at": "2025-01-02T00:00:00+00:00",  # Different timestamp
                "regulatory_frameworks": ["framework_1"],
                "control_catalog": control_catalog,
                "parameters": {"test_param": "value"},  # Same parameters
            },
        )
        assert run_res_2.status_code == 200
        run_id_2 = run_res_2.json()["run_id"]

        # Run IDs should be the same (deterministic)
        assert run_id_1 == run_id_2


@pytest.mark.anyio
async def test_idempotent_runs(sqlite_db: None) -> None:
    """Test that identical runs are idempotent."""
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
                    "ctrl_001": ["access_evidence"]
                }
            }
        }
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ingest_res = await ac.post("/api/v3/ingest-records", json={"records": [{"test": "data"}]})
        assert ingest_res.status_code == 200
        dv_id = ingest_res.json()["dataset_version_id"]

        # First run
        run_res_1 = await ac.post(
            "/api/v3/engines/audit-readiness/run",
            json={
                "dataset_version_id": dv_id,
                "started_at": "2025-01-01T00:00:00+00:00",
                "regulatory_frameworks": ["framework_1"],
                "control_catalog": control_catalog,
            },
        )
        assert run_res_1.status_code == 200

        # Second identical run
        run_res_2 = await ac.post(
            "/api/v3/engines/audit-readiness/run",
            json={
                "dataset_version_id": dv_id,
                "started_at": "2025-01-01T00:00:00+00:00",
                "regulatory_frameworks": ["framework_1"],
                "control_catalog": control_catalog,
            },
        )
        assert run_res_2.status_code == 200

        # Both should succeed (idempotent)
        result_1 = run_res_1.json()
        result_2 = run_res_2.json()
        assert result_1["run_id"] == result_2["run_id"]


@pytest.mark.anyio
async def test_error_handling_framework_not_found(sqlite_db: None) -> None:
    """Test error handling when framework is not found in catalog."""
    os.environ["TODISCOPE_ENABLED_ENGINES"] = "engine_audit_readiness"
    app = create_app()

    control_catalog = {
        "frameworks": {
            "framework_1": {
                "metadata": {"name": "Test Framework", "version": "v1"},
                "controls": [],
            }
        }
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ingest_res = await ac.post("/api/v3/ingest-records", json={"records": [{"test": "data"}]})
        assert ingest_res.status_code == 200
        dv_id = ingest_res.json()["dataset_version_id"]

        # Request non-existent framework
        run_res = await ac.post(
            "/api/v3/engines/audit-readiness/run",
            json={
                "dataset_version_id": dv_id,
                "started_at": "2025-01-01T00:00:00+00:00",
                "regulatory_frameworks": ["nonexistent_framework"],
                "control_catalog": control_catalog,
            },
        )
        assert run_res.status_code == 200  # Engine continues with other frameworks
        result = run_res.json()
        # Framework evaluation should fail but be logged
        assert len(result["regulatory_results"]) == 1
        assert result["regulatory_results"][0]["check_status"] == "error"

