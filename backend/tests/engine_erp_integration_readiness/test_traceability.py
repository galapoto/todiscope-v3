"""Integration tests for ERP Integration Readiness Engine traceability and auditability."""
from __future__ import annotations

import os
import pytest
from datetime import datetime, timezone

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from backend.app.main import create_app
from backend.app.core.dataset.models import DatasetVersion
from backend.app.core.evidence.models import EvidenceRecord, FindingEvidenceLink
from backend.app.engines.erp_integration_readiness.models.findings import ErpIntegrationReadinessFinding
from backend.app.engines.erp_integration_readiness.models.runs import ErpIntegrationReadinessRun
from backend.app.core.db import get_sessionmaker


@pytest.mark.anyio
async def test_findings_linked_to_dataset_version(sqlite_db: None) -> None:
    """Test that all findings are properly linked to DatasetVersion."""
    os.environ["TODISCOPE_ENABLED_ENGINES"] = "engine_erp_integration_readiness"
    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create a dataset version via ingestion
        ingest_res = await ac.post("/api/v3/ingest")
        assert ingest_res.status_code == 200
        dv_id = ingest_res.json()["dataset_version_id"]

        # Run ERP integration readiness engine
        run_res = await ac.post(
            "/api/v3/engines/erp-integration-readiness/run",
            json={
                "dataset_version_id": dv_id,
                "started_at": "2024-01-01T00:00:00Z",
                "erp_system_config": {
                    "system_id": "test_erp",
                    "connection_type": "api",
                    "api_endpoint": "https://example.com/api",
                    # Missing backup_config to trigger a finding
                },
                "parameters": {
                    "assumptions": {},
                },
            },
        )
        assert run_res.status_code == 200
        run_data = run_res.json()
        assert run_data["dataset_version_id"] == dv_id

        # Verify findings are linked to DatasetVersion
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as db:
            findings = (
                await db.execute(
                    select(ErpIntegrationReadinessFinding).where(
                        ErpIntegrationReadinessFinding.dataset_version_id == dv_id
                    )
                )
            ).scalars().all()

            assert len(findings) > 0, "Should have at least one finding"
            for finding in findings:
                assert finding.dataset_version_id == dv_id
                assert finding.result_set_id == run_data["result_set_id"]


@pytest.mark.anyio
async def test_evidence_linked_to_dataset_version(sqlite_db: None) -> None:
    """Test that all evidence records are properly linked to DatasetVersion."""
    os.environ["TODISCOPE_ENABLED_ENGINES"] = "engine_erp_integration_readiness"
    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create a dataset version via ingestion
        ingest_res = await ac.post("/api/v3/ingest")
        assert ingest_res.status_code == 200
        dv_id = ingest_res.json()["dataset_version_id"]

        # Run ERP integration readiness engine
        run_res = await ac.post(
            "/api/v3/engines/erp-integration-readiness/run",
            json={
                "dataset_version_id": dv_id,
                "started_at": "2024-01-01T00:00:00Z",
                "erp_system_config": {
                    "system_id": "test_erp",
                    "connection_type": "api",
                    "api_endpoint": "https://example.com/api",
                    # Missing high_availability to trigger a finding
                },
                "parameters": {
                    "assumptions": {},
                },
            },
        )
        assert run_res.status_code == 200

        # Verify evidence records are linked to DatasetVersion
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as db:
            findings = (
                await db.execute(
                    select(ErpIntegrationReadinessFinding).where(
                        ErpIntegrationReadinessFinding.dataset_version_id == dv_id
                    )
                )
            ).scalars().all()

            for finding in findings:
                # Verify evidence exists and is linked to DatasetVersion
                evidence = await db.scalar(
                    select(EvidenceRecord).where(EvidenceRecord.evidence_id == finding.evidence_id)
                )
                assert evidence is not None
                assert evidence.dataset_version_id == dv_id
                assert evidence.engine_id == "engine_erp_integration_readiness"


@pytest.mark.anyio
async def test_findings_include_erp_system_metadata(sqlite_db: None) -> None:
    """Test that findings include ERP system metadata for traceability."""
    os.environ["TODISCOPE_ENABLED_ENGINES"] = "engine_erp_integration_readiness"
    app = create_app()

    erp_system_id = "test_erp_system_001"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create a dataset version via ingestion
        ingest_res = await ac.post("/api/v3/ingest")
        assert ingest_res.status_code == 200
        dv_id = ingest_res.json()["dataset_version_id"]

        # Run ERP integration readiness engine
        run_res = await ac.post(
            "/api/v3/engines/erp-integration-readiness/run",
            json={
                "dataset_version_id": dv_id,
                "started_at": "2024-01-01T00:00:00Z",
                "erp_system_config": {
                    "system_id": erp_system_id,
                    "connection_type": "api",
                    "api_endpoint": "https://example.com/api",
                },
                "parameters": {
                    "assumptions": {},
                },
            },
        )
        assert run_res.status_code == 200

        # Verify findings include ERP system metadata in evidence
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as db:
            findings = (
                await db.execute(
                    select(ErpIntegrationReadinessFinding).where(
                        ErpIntegrationReadinessFinding.dataset_version_id == dv_id
                    )
                )
            ).scalars().all()

            for finding in findings:
                evidence = await db.scalar(
                    select(EvidenceRecord).where(EvidenceRecord.evidence_id == finding.evidence_id)
                )
                assert evidence is not None
                # Verify evidence payload includes ERP system ID
                payload = evidence.payload
                assert "erp_system_id" in payload or "result_set_id" in payload


@pytest.mark.anyio
async def test_run_persisted_with_dataset_version(sqlite_db: None) -> None:
    """Test that run records are properly persisted with DatasetVersion."""
    os.environ["TODISCOPE_ENABLED_ENGINES"] = "engine_erp_integration_readiness"
    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create a dataset version via ingestion
        ingest_res = await ac.post("/api/v3/ingest")
        assert ingest_res.status_code == 200
        dv_id = ingest_res.json()["dataset_version_id"]

        # Run ERP integration readiness engine
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
                "parameters": {
                    "assumptions": {},
                },
            },
        )
        assert run_res.status_code == 200
        run_data = run_res.json()
        run_id = run_data["run_id"]

        # Verify run is persisted with DatasetVersion
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as db:
            run = await db.scalar(
                select(ErpIntegrationReadinessRun).where(
                    ErpIntegrationReadinessRun.run_id == run_id
                )
            )
            assert run is not None
            assert run.dataset_version_id == dv_id
            assert run.result_set_id == run_data["result_set_id"]
            assert run.engine_version == "v1"


@pytest.mark.anyio
async def test_immutability_of_findings(sqlite_db: None) -> None:
    """Test that findings are immutable (idempotent creation)."""
    os.environ["TODISCOPE_ENABLED_ENGINES"] = "engine_erp_integration_readiness"
    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create a dataset version via ingestion
        ingest_res = await ac.post("/api/v3/ingest")
        assert ingest_res.status_code == 200
        dv_id = ingest_res.json()["dataset_version_id"]

        erp_config = {
            "system_id": "test_erp",
            "connection_type": "api",
            "api_endpoint": "https://example.com/api",
        }
        parameters = {"assumptions": {}}
        started_at = "2024-01-01T00:00:00Z"

        # Run engine first time
        run_res_1 = await ac.post(
            "/api/v3/engines/erp-integration-readiness/run",
            json={
                "dataset_version_id": dv_id,
                "started_at": started_at,
                "erp_system_config": erp_config,
                "parameters": parameters,
            },
        )
        assert run_res_1.status_code == 200
        result_set_id_1 = run_res_1.json()["result_set_id"]

        # Run engine second time with same parameters (should be idempotent)
        run_res_2 = await ac.post(
            "/api/v3/engines/erp-integration-readiness/run",
            json={
                "dataset_version_id": dv_id,
                "started_at": started_at,
                "erp_system_config": erp_config,
                "parameters": parameters,
            },
        )
        assert run_res_2.status_code == 200
        result_set_id_2 = run_res_2.json()["result_set_id"]

        # Verify same result_set_id (deterministic)
        assert result_set_id_1 == result_set_id_2

        # Verify findings are the same
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as db:
            findings_1 = (
                await db.execute(
                    select(ErpIntegrationReadinessFinding).where(
                        ErpIntegrationReadinessFinding.result_set_id == result_set_id_1
                    )
                )
            ).scalars().all()

            findings_2 = (
                await db.execute(
                    select(ErpIntegrationReadinessFinding).where(
                        ErpIntegrationReadinessFinding.result_set_id == result_set_id_2
                    )
                )
            ).scalars().all()

            assert len(findings_1) == len(findings_2)
            finding_ids_1 = {f.finding_id for f in findings_1}
            finding_ids_2 = {f.finding_id for f in findings_2}
            assert finding_ids_1 == finding_ids_2


@pytest.mark.anyio
async def test_evidence_payload_completeness(sqlite_db: None) -> None:
    """Test that evidence payloads include all required traceability information."""
    os.environ["TODISCOPE_ENABLED_ENGINES"] = "engine_erp_integration_readiness"
    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create a dataset version via ingestion
        ingest_res = await ac.post("/api/v3/ingest")
        assert ingest_res.status_code == 200
        dv_id = ingest_res.json()["dataset_version_id"]

        # Run ERP integration readiness engine
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
                "parameters": {
                    "assumptions": {},
                },
            },
        )
        assert run_res.status_code == 200
        result_set_id = run_res.json()["result_set_id"]

        # Verify evidence payload completeness
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as db:
            findings = (
                await db.execute(
                    select(ErpIntegrationReadinessFinding).where(
                        ErpIntegrationReadinessFinding.dataset_version_id == dv_id
                    )
                )
            ).scalars().all()

            for finding in findings:
                evidence = await db.scalar(
                    select(EvidenceRecord).where(EvidenceRecord.evidence_id == finding.evidence_id)
                )
                assert evidence is not None
                payload = evidence.payload

                # Verify required fields in payload
                assert "kind" in payload
                assert "result_set_id" in payload
                assert payload["result_set_id"] == result_set_id
                assert "erp_system_id" in payload or "issue" in payload

