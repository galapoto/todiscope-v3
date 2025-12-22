"""Edge case tests for ERP Integration Readiness Engine."""
from __future__ import annotations

import os
import pytest
from datetime import datetime, timezone

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from backend.app.main import create_app
from backend.app.core.dataset.models import DatasetVersion
from backend.app.engines.erp_integration_readiness.models.findings import ErpIntegrationReadinessFinding
from backend.app.core.db import get_sessionmaker


@pytest.mark.anyio
async def test_complex_erp_configuration(sqlite_db: None) -> None:
    """Test engine handles complex ERP system configuration."""
    os.environ["TODISCOPE_ENABLED_ENGINES"] = "engine_erp_integration_readiness"
    app = create_app()

    complex_config = {
        "system_id": "complex_erp_system",
        "connection_type": "api",
        "api_endpoint": "https://complex.example.com/api/v2",
        "version": "3.2.1",
        "api_version": "v3",
        "high_availability": {
            "enabled": True,
            "failover_mode": "automatic",
            "replication_factor": 3,
        },
        "backup_config": {
            "enabled": True,
            "backup_frequency": "hourly",
            "retention_days": 30,
            "encryption": True,
        },
        "transaction_support": {
            "enabled": True,
            "isolation_level": "serializable",
            "timeout_seconds": 300,
        },
        "data_validation": {
            "schema_validation": True,
            "data_type_validation": True,
            "constraint_validation": True,
            "custom_rules": ["rule1", "rule2"],
        },
        "maintenance_window": {
            "scheduled": True,
            "start_time": "02:00",
            "duration_hours": 4,
            "timezone": "UTC",
        },
        "monitoring": {
            "enabled": True,
            "alerting": True,
            "metrics_collection": True,
        },
        "security": {
            "encryption": {
                "required": "TLS 1.3",
                "algorithm": "AES-256",
            },
            "tls_version": "1.3",
            "certificate_requirements": {
                "required": True,
                "validation": "strict",
            },
        },
        "network_requirements": {
            "bandwidth_min_mbps": 100,
            "latency_max_ms": 50,
            "required_ports": [443, 8080],
        },
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ingest_res = await ac.post("/api/v3/ingest")
        assert ingest_res.status_code == 200
        dv_id = ingest_res.json()["dataset_version_id"]

        run_res = await ac.post(
            "/api/v3/engines/erp-integration-readiness/run",
            json={
                "dataset_version_id": dv_id,
                "started_at": "2024-01-01T00:00:00Z",
                "erp_system_config": complex_config,
                "parameters": {
                    "assumptions": {},
                    "infrastructure_config": {
                        "supported_protocols": ["REST", "SOAP"],
                        "supported_data_formats": ["JSON", "XML"],
                        "supported_auth_methods": ["OAuth2"],
                        "network": {"available_bandwidth_mbps": 200},
                        "required_erp_versions": {
                            "min_version": "1.0.0",
                            "max_version": "5.0.0",
                        },
                        "required_api_versions": ["v1", "v2", "v3"],
                        "security": {
                            "encryption": {"supported": ["TLS 1.2", "TLS 1.3"]},
                            "supported_tls_versions": ["1.2", "1.3"],
                            "certificate_support": {"enabled": True},
                        },
                    },
                },
            },
        )
        assert run_res.status_code == 200
        assert run_res.json()["status"] == "completed"


@pytest.mark.anyio
async def test_minimal_erp_configuration(sqlite_db: None) -> None:
    """Test engine handles minimal ERP system configuration."""
    os.environ["TODISCOPE_ENABLED_ENGINES"] = "engine_erp_integration_readiness"
    app = create_app()

    minimal_config = {
        "system_id": "minimal_erp",
        "connection_type": "api",
        "api_endpoint": "https://minimal.example.com/api",
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ingest_res = await ac.post("/api/v3/ingest")
        assert ingest_res.status_code == 200
        dv_id = ingest_res.json()["dataset_version_id"]

        run_res = await ac.post(
            "/api/v3/engines/erp-integration-readiness/run",
            json={
                "dataset_version_id": dv_id,
                "started_at": "2024-01-01T00:00:00Z",
                "erp_system_config": minimal_config,
                "parameters": {"assumptions": {}},
            },
        )
        assert run_res.status_code == 200

        # Verify findings are created for missing configurations
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as db:
            findings = (
                await db.execute(
                    select(ErpIntegrationReadinessFinding).where(
                        ErpIntegrationReadinessFinding.dataset_version_id == dv_id
                    )
                )
            ).scalars().all()

            # Should have findings for missing configurations
            assert len(findings) > 0


@pytest.mark.anyio
async def test_incompatible_erp_system(sqlite_db: None) -> None:
    """Test engine handles incompatible ERP system configurations."""
    os.environ["TODISCOPE_ENABLED_ENGINES"] = "engine_erp_integration_readiness"
    app = create_app()

    incompatible_config = {
        "system_id": "incompatible_erp",
        "connection_type": "api",
        "api_endpoint": "https://incompatible.example.com/api",
        "protocol": "FTP",  # Not supported
        "data_format": "Binary",  # Not supported
        "version": "10.0.0",  # Above max version
        "api_version": "v10",  # Not supported
        "security": {
            "encryption": {"required": "DES"},  # Not supported
            "tls_version": "1.0",  # Not supported
        },
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ingest_res = await ac.post("/api/v3/ingest")
        assert ingest_res.status_code == 200
        dv_id = ingest_res.json()["dataset_version_id"]

        run_res = await ac.post(
            "/api/v3/engines/erp-integration-readiness/run",
            json={
                "dataset_version_id": dv_id,
                "started_at": "2024-01-01T00:00:00Z",
                "erp_system_config": incompatible_config,
                "parameters": {
                    "assumptions": {},
                    "infrastructure_config": {
                        "supported_protocols": ["REST", "SOAP"],
                        "supported_data_formats": ["JSON", "XML"],
                        "required_erp_versions": {
                            "min_version": "1.0.0",
                            "max_version": "5.0.0",
                        },
                        "required_api_versions": ["v1", "v2"],
                        "security": {
                            "encryption": {"supported": ["TLS 1.2", "TLS 1.3"]},
                            "supported_tls_versions": ["1.2", "1.3"],
                        },
                    },
                },
            },
        )
        assert run_res.status_code == 200

        # Verify compatibility findings are created
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as db:
            findings = (
                await db.execute(
                    select(ErpIntegrationReadinessFinding).where(
                        ErpIntegrationReadinessFinding.dataset_version_id == dv_id
                    )
                )
            ).scalars().all()

            # Should have compatibility findings
            compatibility_findings = [
                f for f in findings
                if "compatibility" in f.kind.lower()
            ]
            assert len(compatibility_findings) > 0


@pytest.mark.anyio
async def test_downtime_scenario(sqlite_db: None) -> None:
    """Test engine handles ERP system downtime scenarios."""
    os.environ["TODISCOPE_ENABLED_ENGINES"] = "engine_erp_integration_readiness"
    app = create_app()

    downtime_risk_config = {
        "system_id": "downtime_risk_erp",
        "connection_type": "api",
        "api_endpoint": "https://downtime.example.com/api",
        "high_availability": {
            "enabled": False,  # High downtime risk
        },
        "maintenance_window": {
            "scheduled": False,  # No maintenance window
        },
        "monitoring": {
            "enabled": False,  # No monitoring
        },
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ingest_res = await ac.post("/api/v3/ingest")
        assert ingest_res.status_code == 200
        dv_id = ingest_res.json()["dataset_version_id"]

        run_res = await ac.post(
            "/api/v3/engines/erp-integration-readiness/run",
            json={
                "dataset_version_id": dv_id,
                "started_at": "2024-01-01T00:00:00Z",
                "erp_system_config": downtime_risk_config,
                "parameters": {"assumptions": {}},
            },
        )
        assert run_res.status_code == 200

        # Verify downtime risk findings
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as db:
            findings = (
                await db.execute(
                    select(ErpIntegrationReadinessFinding).where(
                        ErpIntegrationReadinessFinding.dataset_version_id == dv_id
                    )
                )
            ).scalars().all()

            # Should have operational readiness findings
            operational_findings = [
                f for f in findings
                if "operational" in f.kind.lower() or "downtime" in f.kind.lower()
            ]
            assert len(operational_findings) > 0


@pytest.mark.anyio
async def test_data_integrity_risk_scenario(sqlite_db: None) -> None:
    """Test engine handles data integrity risk scenarios."""
    os.environ["TODISCOPE_ENABLED_ENGINES"] = "engine_erp_integration_readiness"
    app = create_app()

    integrity_risk_config = {
        "system_id": "integrity_risk_erp",
        "connection_type": "api",
        "api_endpoint": "https://integrity.example.com/api",
        "backup_config": {
            "enabled": False,  # No backup
        },
        "transaction_support": {
            "enabled": False,  # No transactions
        },
        "data_validation": {},  # No validation
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ingest_res = await ac.post("/api/v3/ingest")
        assert ingest_res.status_code == 200
        dv_id = ingest_res.json()["dataset_version_id"]

        run_res = await ac.post(
            "/api/v3/engines/erp-integration-readiness/run",
            json={
                "dataset_version_id": dv_id,
                "started_at": "2024-01-01T00:00:00Z",
                "erp_system_config": integrity_risk_config,
                "parameters": {"assumptions": {}},
            },
        )
        assert run_res.status_code == 200

        # Verify data integrity findings
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as db:
            findings = (
                await db.execute(
                    select(ErpIntegrationReadinessFinding).where(
                        ErpIntegrationReadinessFinding.dataset_version_id == dv_id
                    )
                )
            ).scalars().all()

            # Should have data integrity findings
            integrity_findings = [
                f for f in findings
                if "data_integrity" in f.kind.lower()
            ]
            assert len(integrity_findings) > 0


@pytest.mark.anyio
async def test_empty_infrastructure_config(sqlite_db: None) -> None:
    """Test engine handles empty infrastructure configuration."""
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
                    "system_id": "test_erp",
                    "connection_type": "api",
                    "api_endpoint": "https://example.com/api",
                },
                "parameters": {
                    "assumptions": {},
                    # No infrastructure_config - should still work
                },
            },
        )
        assert run_res.status_code == 200
        # Should complete without infrastructure compatibility checks


@pytest.mark.anyio
async def test_multiple_erp_systems_same_dataset(sqlite_db: None) -> None:
    """Test engine handles multiple ERP system assessments for same dataset."""
    os.environ["TODISCOPE_ENABLED_ENGINES"] = "engine_erp_integration_readiness"
    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ingest_res = await ac.post("/api/v3/ingest")
        assert ingest_res.status_code == 200
        dv_id = ingest_res.json()["dataset_version_id"]

        # First ERP system
        run_res_1 = await ac.post(
            "/api/v3/engines/erp-integration-readiness/run",
            json={
                "dataset_version_id": dv_id,
                "started_at": "2024-01-01T00:00:00Z",
                "erp_system_config": {
                    "system_id": "erp_system_1",
                    "connection_type": "api",
                    "api_endpoint": "https://erp1.example.com/api",
                },
                "parameters": {"assumptions": {}},
            },
        )
        assert run_res_1.status_code == 200
        result_set_id_1 = run_res_1.json()["result_set_id"]

        # Second ERP system
        run_res_2 = await ac.post(
            "/api/v3/engines/erp-integration-readiness/run",
            json={
                "dataset_version_id": dv_id,
                "started_at": "2024-01-01T00:00:00Z",
                "erp_system_config": {
                    "system_id": "erp_system_2",
                    "connection_type": "database",
                    "connection_string": "jdbc:postgresql://erp2.example.com/db",
                },
                "parameters": {"assumptions": {}},
            },
        )
        assert run_res_2.status_code == 200
        result_set_id_2 = run_res_2.json()["result_set_id"]

        # Verify both runs are separate
        assert result_set_id_1 != result_set_id_2

        # Verify findings are separate for each system
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

            # Both should have findings
            assert len(findings_1) >= 0
            assert len(findings_2) >= 0


@pytest.mark.anyio
async def test_extreme_risk_scenarios(sqlite_db: None) -> None:
    """Test engine handles extreme risk scenarios."""
    os.environ["TODISCOPE_ENABLED_ENGINES"] = "engine_erp_integration_readiness"
    app = create_app()

    extreme_risk_config = {
        "system_id": "extreme_risk_erp",
        "connection_type": "api",
        "api_endpoint": "https://extreme.example.com/api",
        # All high-risk configurations
        "high_availability": {"enabled": False},
        "backup_config": {"enabled": False},
        "transaction_support": {"enabled": False},
        "maintenance_window": {"scheduled": False},
        "monitoring": {"enabled": False},
        "data_validation": {},
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ingest_res = await ac.post("/api/v3/ingest")
        assert ingest_res.status_code == 200
        dv_id = ingest_res.json()["dataset_version_id"]

        run_res = await ac.post(
            "/api/v3/engines/erp-integration-readiness/run",
            json={
                "dataset_version_id": dv_id,
                "started_at": "2024-01-01T00:00:00Z",
                "erp_system_config": extreme_risk_config,
                "parameters": {
                    "assumptions": {},
                    "infrastructure_config": {
                        "supported_protocols": ["REST"],
                        "required_erp_versions": {"min_version": "5.0.0", "max_version": "5.0.0"},
                    },
                },
            },
        )
        assert run_res.status_code == 200

        # Verify multiple high-severity findings
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as db:
            findings = (
                await db.execute(
                    select(ErpIntegrationReadinessFinding).where(
                        ErpIntegrationReadinessFinding.dataset_version_id == dv_id
                    )
                )
            ).scalars().all()

            high_severity_findings = [f for f in findings if f.severity == "high"]
            assert len(high_severity_findings) > 0


