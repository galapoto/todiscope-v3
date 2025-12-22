"""
Test Compliance Mapping Logic

Tests to ensure controls are correctly mapped to regulatory frameworks
and that the logic remains framework-neutral.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from backend.app.core.db import get_sessionmaker
from backend.app.core.evidence.models import EvidenceRecord, FindingRecord
from backend.app.engines.audit_readiness.evidence_integration import map_evidence_to_controls
from backend.app.main import create_app


@pytest.mark.anyio
async def test_compliance_mapping_framework_neutral(sqlite_db: None) -> None:
    """Test that compliance mapping works with different frameworks."""
    os.environ["TODISCOPE_ENABLED_ENGINES"] = "engine_audit_readiness"
    app = create_app()

    # Test with Framework A (e.g., SOX-like)
    framework_a_catalog = {
        "frameworks": {
            "framework_a": {
                "metadata": {"name": "Framework A", "version": "v1"},
                "controls": [
                    {
                        "control_id": "ctrl_a_001",
                        "control_name": "Financial Controls",
                        "critical": True,
                    }
                ],
                "required_evidence_types": {
                    "ctrl_a_001": ["financial_evidence"]
                }
            }
        }
    }

    # Test with Framework B (e.g., GDPR-like)
    framework_b_catalog = {
        "frameworks": {
            "framework_b": {
                "metadata": {"name": "Framework B", "version": "v1"},
                "controls": [
                    {
                        "control_id": "ctrl_b_001",
                        "control_name": "Privacy Controls",
                        "critical": True,
                    }
                ],
                "required_evidence_types": {
                    "ctrl_b_001": ["privacy_evidence"]
                }
            }
        }
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create dataset version
        ingest_res = await ac.post("/api/v3/ingest-records", json={"records": [{"test": "data"}]})
        assert ingest_res.status_code == 200
        dv_id = ingest_res.json()["dataset_version_id"]

        # Run with Framework A
        run_res_a = await ac.post(
            "/api/v3/engines/audit-readiness/run",
            json={
                "dataset_version_id": dv_id,
                "started_at": "2025-01-01T00:00:00+00:00",
                "regulatory_frameworks": ["framework_a"],
                "control_catalog": framework_a_catalog,
            },
        )
        assert run_res_a.status_code == 200
        result_a = run_res_a.json()
        assert len(result_a["regulatory_results"]) == 1
        assert result_a["regulatory_results"][0]["framework_id"] == "framework_a"

        # Create new dataset version for Framework B
        ingest_res_b = await ac.post("/api/v3/ingest-records", json={"records": [{"test": "data"}]})
        assert ingest_res_b.status_code == 200
        dv_id_b = ingest_res_b.json()["dataset_version_id"]

        # Run with Framework B
        run_res_b = await ac.post(
            "/api/v3/engines/audit-readiness/run",
            json={
                "dataset_version_id": dv_id_b,
                "started_at": "2025-01-01T00:00:00+00:00",
                "regulatory_frameworks": ["framework_b"],
                "control_catalog": framework_b_catalog,
            },
        )
        assert run_res_b.status_code == 200
        result_b = run_res_b.json()
        assert len(result_b["regulatory_results"]) == 1
        assert result_b["regulatory_results"][0]["framework_id"] == "framework_b"

        # Verify frameworks are independent
        assert result_a["regulatory_results"][0]["framework_id"] != result_b["regulatory_results"][0]["framework_id"]


@pytest.mark.anyio
async def test_multiple_frameworks_single_run(sqlite_db: None) -> None:
    """Test evaluating multiple frameworks in a single run."""
    os.environ["TODISCOPE_ENABLED_ENGINES"] = "engine_audit_readiness"
    app = create_app()

    control_catalog = {
        "frameworks": {
            "framework_1": {
                "metadata": {"name": "Framework 1", "version": "v1"},
                "controls": [
                    {
                        "control_id": "ctrl_1_001",
                        "control_name": "Control 1",
                        "critical": False,
                    }
                ],
                "required_evidence_types": {
                    "ctrl_1_001": ["evidence_type_1"]
                }
            },
            "framework_2": {
                "metadata": {"name": "Framework 2", "version": "v1"},
                "controls": [
                    {
                        "control_id": "ctrl_2_001",
                        "control_name": "Control 2",
                        "critical": False,
                    }
                ],
                "required_evidence_types": {
                    "ctrl_2_001": ["evidence_type_2"]
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
                "regulatory_frameworks": ["framework_1", "framework_2"],
                "control_catalog": control_catalog,
            },
        )
        assert run_res.status_code == 200
        result = run_res.json()

        # Verify both frameworks were evaluated
        assert len(result["regulatory_results"]) == 2
        framework_ids = [r["framework_id"] for r in result["regulatory_results"]]
        assert "framework_1" in framework_ids
        assert "framework_2" in framework_ids


@pytest.mark.anyio
async def test_control_to_framework_mapping(sqlite_db: None) -> None:
    """Test that controls are correctly mapped to their frameworks."""
    os.environ["TODISCOPE_ENABLED_ENGINES"] = "engine_audit_readiness"
    app = create_app()

    control_catalog = {
        "frameworks": {
            "framework_1": {
                "metadata": {"name": "Framework 1", "version": "v1"},
                "controls": [
                    {
                        "control_id": "ctrl_001",
                        "control_name": "Control 1",
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

        # Verify control gaps reference correct framework
        regulatory_result = result["regulatory_results"][0]
        assert regulatory_result["framework_id"] == "framework_1"

        # Verify findings reference correct framework
        async with get_sessionmaker()() as db:
            findings = await db.scalars(
                select(FindingRecord).where(FindingRecord.dataset_version_id == dv_id)
            )
            findings_list = list(findings.all())
            assert len(findings_list) > 0
            for finding in findings_list:
                assert finding.payload["framework_id"] == "framework_1"


@pytest.mark.anyio
async def test_evidence_mapping_to_controls(sqlite_db: None) -> None:
    """Test that evidence is correctly mapped to controls."""
    os.environ["TODISCOPE_ENABLED_ENGINES"] = "engine_audit_readiness"
    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ingest_res = await ac.post("/api/v3/ingest-records", json={"records": [{"test": "data"}]})
        assert ingest_res.status_code == 200
        dv_id = ingest_res.json()["dataset_version_id"]

        # Create evidence with control_id references
        async with get_sessionmaker()() as db:
            from backend.app.core.evidence.service import create_evidence, deterministic_evidence_id

            # Create evidence linked to control
            evidence_id_1 = deterministic_evidence_id(
                dataset_version_id=dv_id,
                engine_id="engine_audit_readiness",
                kind="control_evidence",
                stable_key="ctrl_001_ev_1",
            )
            await create_evidence(
                db,
                evidence_id=evidence_id_1,
                dataset_version_id=dv_id,
                engine_id="engine_audit_readiness",
                kind="control_evidence",
                payload={"control_ids": ["ctrl_001"], "data": "evidence data"},
                created_at=datetime.now(timezone.utc),
            )
            await db.commit()

        # Test evidence mapping
        control_catalog = {
            "frameworks": {
                "framework_1": {
                    "metadata": {"name": "Framework 1", "version": "v1"},
                    "controls": [
                        {
                            "control_id": "ctrl_001",
                            "control_name": "Control 1",
                            "critical": False,
                        }
                    ],
                    "required_evidence_types": {
                        "ctrl_001": ["evidence_type_1"]
                    }
                }
            }
        }

        async with get_sessionmaker()() as db:
            evidence_map = await map_evidence_to_controls(db, dv_id, control_catalog["frameworks"]["framework_1"])
            assert "ctrl_001" in evidence_map
            assert evidence_id_1 in evidence_map["ctrl_001"]


@pytest.mark.anyio
async def test_framework_agnostic_control_structure(sqlite_db: None) -> None:
    """Test that the system works with different control structures."""
    os.environ["TODISCOPE_ENABLED_ENGINES"] = "engine_audit_readiness"
    app = create_app()

    # Framework with minimal control structure
    minimal_catalog = {
        "frameworks": {
            "minimal_framework": {
                "metadata": {"name": "Minimal Framework", "version": "v1"},
                "controls": [
                    {
                        "control_id": "ctrl_min_001",
                        "control_name": "Minimal Control",
                    }
                ],
                "required_evidence_types": {
                    "ctrl_min_001": []
                }
            }
        }
    }

    # Framework with extensive control structure
    extensive_catalog = {
        "frameworks": {
            "extensive_framework": {
                "metadata": {
                    "name": "Extensive Framework",
                    "version": "v1",
                    "description": "A comprehensive framework",
                    "authority": "Test Authority",
                },
                "controls": [
                    {
                        "control_id": "ctrl_ext_001",
                        "control_name": "Extensive Control",
                        "critical": True,
                        "ownership": "IT Security",
                        "status": "active",
                        "risk_type": "security",
                        "required_evidence_types": ["ev_type_1", "ev_type_2"],
                        "remediation_guidance": "Follow best practices",
                    }
                ],
                "required_evidence_types": {
                    "ctrl_ext_001": ["ev_type_1", "ev_type_2"]
                }
            }
        }
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Test minimal framework
        ingest_res_1 = await ac.post("/api/v3/ingest-records", json={"records": [{"test": "data"}]})
        assert ingest_res_1.status_code == 200
        dv_id_1 = ingest_res_1.json()["dataset_version_id"]

        run_res_1 = await ac.post(
            "/api/v3/engines/audit-readiness/run",
            json={
                "dataset_version_id": dv_id_1,
                "started_at": "2025-01-01T00:00:00+00:00",
                "regulatory_frameworks": ["minimal_framework"],
                "control_catalog": minimal_catalog,
            },
        )
        assert run_res_1.status_code == 200

        # Test extensive framework
        ingest_res_2 = await ac.post("/api/v3/ingest-records", json={"records": [{"test": "data"}]})
        assert ingest_res_2.status_code == 200
        dv_id_2 = ingest_res_2.json()["dataset_version_id"]

        run_res_2 = await ac.post(
            "/api/v3/engines/audit-readiness/run",
            json={
                "dataset_version_id": dv_id_2,
                "started_at": "2025-01-01T00:00:00+00:00",
                "regulatory_frameworks": ["extensive_framework"],
                "control_catalog": extensive_catalog,
            },
        )
        assert run_res_2.status_code == 200

        # Both should work regardless of structure complexity
        result_1 = run_res_1.json()
        result_2 = run_res_2.json()
        assert len(result_1["regulatory_results"]) == 1
        assert len(result_2["regulatory_results"]) == 1

