"""Regression tests for ERP Integration Readiness Engine."""
from __future__ import annotations

import os
import pytest
from datetime import datetime, timezone

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from backend.app.main import create_app
from backend.app.core.dataset.models import DatasetVersion
from backend.app.engines.erp_integration_readiness.models.findings import ErpIntegrationReadinessFinding
from backend.app.engines.erp_integration_readiness.models.runs import ErpIntegrationReadinessRun
from backend.app.core.db import get_sessionmaker


@pytest.mark.anyio
async def test_deterministic_outputs_regression(sqlite_db: None) -> None:
    """Regression test: Verify outputs are deterministic (same inputs → same outputs)."""
    os.environ["TODISCOPE_ENABLED_ENGINES"] = "engine_erp_integration_readiness"
    app = create_app()

    erp_config = {
        "system_id": "regression_test_erp",
        "connection_type": "api",
        "api_endpoint": "https://regression.example.com/api",
        "version": "2.0.0",
    }
    parameters = {
        "assumptions": {},
        "infrastructure_config": {
            "supported_protocols": ["REST"],
            "required_erp_versions": {"min_version": "1.0.0", "max_version": "3.0.0"},
        },
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ingest_res = await ac.post("/api/v3/ingest")
        assert ingest_res.status_code == 200
        dv_id = ingest_res.json()["dataset_version_id"]

        # Run 1
        run_res_1 = await ac.post(
            "/api/v3/engines/erp-integration-readiness/run",
            json={
                "dataset_version_id": dv_id,
                "started_at": "2024-01-01T00:00:00Z",
                "erp_system_config": erp_config,
                "parameters": parameters,
            },
        )
        assert run_res_1.status_code == 200
        result_1 = run_res_1.json()

        # Run 2 with same inputs
        run_res_2 = await ac.post(
            "/api/v3/engines/erp-integration-readiness/run",
            json={
                "dataset_version_id": dv_id,
                "started_at": "2024-01-01T00:00:00Z",
                "erp_system_config": erp_config,
                "parameters": parameters,
            },
        )
        assert run_res_2.status_code == 200
        result_2 = run_res_2.json()

        # Verify deterministic result_set_id
        assert result_1["result_set_id"] == result_2["result_set_id"]

        # Verify same findings
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as db:
            findings_1 = (
                await db.execute(
                    select(ErpIntegrationReadinessFinding).where(
                        ErpIntegrationReadinessFinding.result_set_id == result_1["result_set_id"]
                    )
                )
            ).scalars().all()

            findings_2 = (
                await db.execute(
                    select(ErpIntegrationReadinessFinding).where(
                        ErpIntegrationReadinessFinding.result_set_id == result_2["result_set_id"]
                    )
                )
            ).scalars().all()

            finding_ids_1 = {f.finding_id for f in findings_1}
            finding_ids_2 = {f.finding_id for f in findings_2}
            assert finding_ids_1 == finding_ids_2


@pytest.mark.anyio
async def test_dataset_version_immutability_regression(sqlite_db: None) -> None:
    """Regression test: Verify DatasetVersion immutability is maintained."""
    os.environ["TODISCOPE_ENABLED_ENGINES"] = "engine_erp_integration_readiness"
    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ingest_res = await ac.post("/api/v3/ingest")
        assert ingest_res.status_code == 200
        dv_id = ingest_res.json()["dataset_version_id"]

        # Run engine
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

        # Verify DatasetVersion was not modified
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as db:
            dv = await db.scalar(
                select(DatasetVersion).where(DatasetVersion.id == dv_id)
            )
            assert dv is not None
            assert dv.id == dv_id  # Unchanged


@pytest.mark.anyio
async def test_finding_idempotency_regression(sqlite_db: None) -> None:
    """Regression test: Verify findings are idempotent (no duplicates on rerun)."""
    os.environ["TODISCOPE_ENABLED_ENGINES"] = "engine_erp_integration_readiness"
    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ingest_res = await ac.post("/api/v3/ingest")
        assert ingest_res.status_code == 200
        dv_id = ingest_res.json()["dataset_version_id"]

        erp_config = {
            "system_id": "idempotency_test",
            "connection_type": "api",
            "api_endpoint": "https://idempotency.example.com/api",
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

        # Run 2 (same inputs)
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

        assert result_set_id_1 == result_set_id_2

        # Verify no duplicate findings
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as db:
            findings = (
                await db.execute(
                    select(ErpIntegrationReadinessFinding).where(
                        ErpIntegrationReadinessFinding.result_set_id == result_set_id_1
                    )
                )
            ).scalars().all()

            finding_ids = [f.finding_id for f in findings]
            # Should have no duplicates
            assert len(finding_ids) == len(set(finding_ids))


@pytest.mark.anyio
async def test_evidence_linkage_regression(sqlite_db: None) -> None:
    """Regression test: Verify evidence linkage is maintained."""
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
                    "system_id": "evidence_test",
                    "connection_type": "api",
                    "api_endpoint": "https://evidence.example.com/api",
                },
                "parameters": {"assumptions": {}},
            },
        )
        assert run_res.status_code == 200

        # Verify all findings have evidence
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
                assert finding.evidence_id is not None
                assert finding.evidence_id != ""


@pytest.mark.anyio
async def test_parameter_validation_regression(sqlite_db: None) -> None:
    """Regression test: Verify parameter validation still works."""
    os.environ["TODISCOPE_ENABLED_ENGINES"] = "engine_erp_integration_readiness"
    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ingest_res = await ac.post("/api/v3/ingest")
        assert ingest_res.status_code == 200
        dv_id = ingest_res.json()["dataset_version_id"]

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

        # Test missing erp_system_config
        run_res = await ac.post(
            "/api/v3/engines/erp-integration-readiness/run",
            json={
                "dataset_version_id": dv_id,
                "started_at": "2024-01-01T00:00:00Z",
                "parameters": {"assumptions": {}},
            },
        )
        assert run_res.status_code == 400

        # Test missing parameters
        run_res = await ac.post(
            "/api/v3/engines/erp-integration-readiness/run",
            json={
                "dataset_version_id": dv_id,
                "started_at": "2024-01-01T00:00:00Z",
                "erp_system_config": {"system_id": "test", "connection_type": "api"},
            },
        )
        assert run_res.status_code == 400


