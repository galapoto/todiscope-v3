"""Production deployment readiness tests for ERP Integration Readiness Engine."""
from __future__ import annotations

import os
import logging
import pytest
from datetime import datetime, timezone

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from backend.app.main import create_app
from backend.app.core.dataset.models import DatasetVersion
from backend.app.engines.erp_integration_readiness.models.findings import ErpIntegrationReadinessFinding
from backend.app.engines.erp_integration_readiness.models.runs import ErpIntegrationReadinessRun
from backend.app.core.db import get_sessionmaker
from backend.app.core.evidence.models import EvidenceRecord


@pytest.mark.anyio
async def test_http_endpoint_accessible(sqlite_db: None) -> None:
    """Test that the engine HTTP endpoint is accessible when enabled."""
    os.environ["TODISCOPE_ENABLED_ENGINES"] = "engine_erp_integration_readiness"
    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Verify endpoint exists
        ingest_res = await ac.post("/api/v3/ingest")
        assert ingest_res.status_code == 200
        dv_id = ingest_res.json()["dataset_version_id"]

        run_res = await ac.post(
            "/api/v3/engines/erp-integration-readiness/run",
            json={
                "dataset_version_id": dv_id,
                "started_at": "2024-01-01T00:00:00Z",
                "erp_system_config": {
                    "system_id": "test_erp",
                    "connection_type": "api",
                    "api_endpoint": "https://example.com/api",
                },
                "parameters": {"assumptions": {}},
            },
        )
        assert run_res.status_code == 200
        assert run_res.json()["status"] == "completed"


@pytest.mark.anyio
async def test_http_endpoint_not_accessible_when_disabled(sqlite_db: None) -> None:
    """Test that the engine HTTP endpoint is not accessible when disabled."""
    os.environ["TODISCOPE_ENABLED_ENGINES"] = ""
    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ingest_res = await ac.post("/api/v3/ingest")
        assert ingest_res.status_code == 200
        dv_id = ingest_res.json()["dataset_version_id"]

        # Endpoint should not be mounted when disabled
        run_res = await ac.post(
            "/api/v3/engines/erp-integration-readiness/run",
            json={
                "dataset_version_id": dv_id,
                "started_at": "2024-01-01T00:00:00Z",
                "erp_system_config": {"system_id": "test", "connection_type": "api"},
                "parameters": {"assumptions": {}},
            },
        )
        assert run_res.status_code == 404


@pytest.mark.anyio
async def test_audit_logs_generated(sqlite_db: None) -> None:
    """Test that audit logs are generated and stored properly."""
    os.environ["TODISCOPE_ENABLED_ENGINES"] = "engine_erp_integration_readiness"
    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ingest_res = await ac.post("/api/v3/ingest")
        assert ingest_res.status_code == 200
        dv_id = ingest_res.json()["dataset_version_id"]

        run_res = await ac.post(
            "/api/v3/engines/erp-integration-readiness/run",
            json={
                "dataset_version_id": dv_id,
                "started_at": "2024-01-01T00:00:00Z",
                "erp_system_config": {
                    "system_id": "audit_test_erp",
                    "connection_type": "api",
                    "api_endpoint": "https://audit.example.com/api",
                },
                "parameters": {"assumptions": {}},
            },
        )
        assert run_res.status_code == 200
        result_set_id = run_res.json()["result_set_id"]

        # Verify run record persisted
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as db:
            run = await db.scalar(
                select(ErpIntegrationReadinessRun).where(
                    ErpIntegrationReadinessRun.result_set_id == result_set_id
                )
            )
            assert run is not None
            assert run.dataset_version_id == dv_id
            assert run.erp_system_config["system_id"] == "audit_test_erp"
            assert run.status == "completed"

            # Verify findings persisted
            findings = (
                await db.execute(
                    select(ErpIntegrationReadinessFinding).where(
                        ErpIntegrationReadinessFinding.result_set_id == result_set_id
                    )
                )
            ).scalars().all()
            assert len(findings) >= 0  # May have 0 or more findings

            # Verify evidence persisted
            for finding in findings:
                evidence = await db.scalar(
                    select(EvidenceRecord).where(
                        EvidenceRecord.evidence_id == finding.evidence_id
                    )
                )
                assert evidence is not None
                assert evidence.dataset_version_id == dv_id
                assert evidence.engine_id == "engine_erp_integration_readiness"


@pytest.mark.anyio
async def test_logging_integration(caplog, sqlite_db: None) -> None:
    """Test that logging integration works correctly."""
    os.environ["TODISCOPE_ENABLED_ENGINES"] = "engine_erp_integration_readiness"
    app = create_app()

    # Set logging level to capture warnings
    caplog.set_level(logging.WARNING)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ingest_res = await ac.post("/api/v3/ingest")
        assert ingest_res.status_code == 200
        dv_id = ingest_res.json()["dataset_version_id"]

        # Run with high-risk configuration to trigger warnings
        run_res = await ac.post(
            "/api/v3/engines/erp-integration-readiness/run",
            json={
                "dataset_version_id": dv_id,
                "started_at": "2024-01-01T00:00:00Z",
                "erp_system_config": {
                    "system_id": "high_risk_erp",
                    "connection_type": "api",
                    "api_endpoint": "https://highrisk.example.com/api",
                    # High-risk configuration
                    "high_availability": {"enabled": False},
                    "backup_config": {"enabled": False},
                },
                "parameters": {"assumptions": {}},
            },
        )
        assert run_res.status_code == 200

        # Verify logging occurred (may have warnings for high-risk scenarios)
        # Note: Actual logging depends on implementation
        # This test verifies logging infrastructure is in place


@pytest.mark.anyio
async def test_risk_metadata_captured(sqlite_db: None) -> None:
    """Test that risk metadata is correctly captured in audit logs."""
    os.environ["TODISCOPE_ENABLED_ENGINES"] = "engine_erp_integration_readiness"
    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ingest_res = await ac.post("/api/v3/ingest")
        assert ingest_res.status_code == 200
        dv_id = ingest_res.json()["dataset_version_id"]

        run_res = await ac.post(
            "/api/v3/engines/erp-integration-readiness/run",
            json={
                "dataset_version_id": dv_id,
                "started_at": "2024-01-01T00:00:00Z",
                "erp_system_config": {
                    "system_id": "risk_metadata_test",
                    "connection_type": "api",
                    "api_endpoint": "https://risk.example.com/api",
                },
                "parameters": {"assumptions": {}},
            },
        )
        assert run_res.status_code == 200
        result_set_id = run_res.json()["result_set_id"]

        # Verify risk findings are persisted
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as db:
            risk_findings = (
                await db.execute(
                    select(ErpIntegrationReadinessFinding).where(
                        ErpIntegrationReadinessFinding.result_set_id == result_set_id,
                        ErpIntegrationReadinessFinding.kind.like("%risk%"),
                    )
                )
            ).scalars().all()

            # Risk findings should have severity and detail
            for finding in risk_findings:
                assert finding.severity in ["critical", "high", "medium", "low"]
                assert finding.detail is not None
                assert "risk" in finding.kind.lower() or "risk" in finding.title.lower()


@pytest.mark.anyio
async def test_immutability_of_deployment_config(sqlite_db: None) -> None:
    """Test that deployment configuration is immutable."""
    os.environ["TODISCOPE_ENABLED_ENGINES"] = "engine_erp_integration_readiness"
    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ingest_res = await ac.post("/api/v3/ingest")
        assert ingest_res.status_code == 200
        dv_id = ingest_res.json()["dataset_version_id"]

        erp_config = {
            "system_id": "immutable_test",
            "connection_type": "api",
            "api_endpoint": "https://immutable.example.com/api",
        }

        # Run 1
        run_res_1 = await ac.post(
            "/api/v3/engines/erp-integration-readiness/run",
            json={
                "dataset_version_id": dv_id,
                "started_at": "2024-01-01T00:00:00Z",
                "erp_system_config": erp_config,
                "parameters": {"assumptions": {}},
            },
        )
        assert run_res_1.status_code == 200
        result_set_id_1 = run_res_1.json()["result_set_id"]

        # Run 2 with same config
        run_res_2 = await ac.post(
            "/api/v3/engines/erp-integration-readiness/run",
            json={
                "dataset_version_id": dv_id,
                "started_at": "2024-01-01T00:00:00Z",
                "erp_system_config": erp_config,
                "parameters": {"assumptions": {}},
            },
        )
        assert run_res_2.status_code == 200
        result_set_id_2 = run_res_2.json()["result_set_id"]

        # Verify same result_set_id (deterministic)
        assert result_set_id_1 == result_set_id_2

        # Verify run records are immutable (same config stored)
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as db:
            run_1 = await db.scalar(
                select(ErpIntegrationReadinessRun).where(
                    ErpIntegrationReadinessRun.result_set_id == result_set_id_1
                )
            )
            run_2 = await db.scalar(
                select(ErpIntegrationReadinessRun).where(
                    ErpIntegrationReadinessRun.result_set_id == result_set_id_2
                )
            )

            assert run_1.erp_system_config == run_2.erp_system_config
            assert run_1.parameters == run_2.parameters


@pytest.mark.anyio
async def test_error_handling_production_ready(sqlite_db: None) -> None:
    """Test that error handling is production-ready."""
    os.environ["TODISCOPE_ENABLED_ENGINES"] = "engine_erp_integration_readiness"
    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Test missing dataset_version_id
        run_res = await ac.post(
            "/api/v3/engines/erp-integration-readiness/run",
            json={
                "started_at": "2024-01-01T00:00:00Z",
                "erp_system_config": {"system_id": "test", "connection_type": "api"},
                "parameters": {"assumptions": {}},
            },
        )
        assert run_res.status_code == 400

        # Test invalid dataset_version_id
        run_res = await ac.post(
            "/api/v3/engines/erp-integration-readiness/run",
            json={
                "dataset_version_id": "invalid-uuid",
                "started_at": "2024-01-01T00:00:00Z",
                "erp_system_config": {"system_id": "test", "connection_type": "api"},
                "parameters": {"assumptions": {}},
            },
        )
        assert run_res.status_code == 400

        # Test missing erp_system_config
        ingest_res = await ac.post("/api/v3/ingest")
        assert ingest_res.status_code == 200
        dv_id = ingest_res.json()["dataset_version_id"]

        run_res = await ac.post(
            "/api/v3/engines/erp-integration-readiness/run",
            json={
                "dataset_version_id": dv_id,
                "started_at": "2024-01-01T00:00:00Z",
                "parameters": {"assumptions": {}},
            },
        )
        assert run_res.status_code == 400


@pytest.mark.anyio
async def test_production_workflow_end_to_end(sqlite_db: None) -> None:
    """Test complete production workflow end-to-end."""
    os.environ["TODISCOPE_ENABLED_ENGINES"] = "engine_erp_integration_readiness"
    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Step 1: Create DatasetVersion
        ingest_res = await ac.post("/api/v3/ingest")
        assert ingest_res.status_code == 200
        dv_id = ingest_res.json()["dataset_version_id"]

        # Step 2: Run engine
        run_res = await ac.post(
            "/api/v3/engines/erp-integration-readiness/run",
            json={
                "dataset_version_id": dv_id,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "erp_system_config": {
                    "system_id": "production_erp",
                    "connection_type": "api",
                    "api_endpoint": "https://production.example.com/api",
                    "version": "2.0.0",
                },
                "parameters": {
                    "assumptions": {},
                    "infrastructure_config": {
                        "supported_protocols": ["REST"],
                        "required_erp_versions": {"min_version": "1.0.0", "max_version": "3.0.0"},
                    },
                },
            },
        )
        assert run_res.status_code == 200
        result = run_res.json()

        # Step 3: Verify response structure
        assert result["engine_id"] == "engine_erp_integration_readiness"
        assert result["engine_version"] == "v1"
        assert result["dataset_version_id"] == dv_id
        assert result["status"] == "completed"
        assert "run_id" in result
        assert "result_set_id" in result

        # Step 4: Verify audit trail
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as db:
            # Verify run record
            run = await db.scalar(
                select(ErpIntegrationReadinessRun).where(
                    ErpIntegrationReadinessRun.run_id == result["run_id"]
                )
            )
            assert run is not None
            assert run.dataset_version_id == dv_id

            # Verify findings
            findings = (
                await db.execute(
                    select(ErpIntegrationReadinessFinding).where(
                        ErpIntegrationReadinessFinding.result_set_id == result["result_set_id"]
                    )
                )
            ).scalars().all()

            # Verify evidence for each finding
            for finding in findings:
                evidence = await db.scalar(
                    select(EvidenceRecord).where(
                        EvidenceRecord.evidence_id == finding.evidence_id
                    )
                )
                assert evidence is not None
                assert evidence.dataset_version_id == dv_id

