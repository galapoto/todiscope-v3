"""HTTP-level tests for the litigation analysis engine router."""

from datetime import datetime, timezone
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.core.db import get_sessionmaker
from backend.app.core.dataset.models import DatasetVersion
from backend.app.core.dataset.raw_models import RawRecord
from backend.app.core.dataset.uuidv7 import uuid7
from backend.app.core.normalization.models import NormalizedRecord
from backend.app.engines.enterprise_litigation_dispute.constants import ENGINE_ID
from backend.app.main import create_app


async def _seed_dispute_records(sessionmaker, dv_id: str, raw_id: str, payload: dict) -> None:
    async with sessionmaker() as db:
        db.add(DatasetVersion(id=dv_id))
        db.add(
            RawRecord(
                raw_record_id=raw_id,
                dataset_version_id=dv_id,
                source_system="litigation",
                source_record_id="LIT-HTTP-EXPORT",
                payload={"legal_dispute": payload},
                ingested_at=datetime.now(timezone.utc),
            )
        )
        db.add(
            NormalizedRecord(
                normalized_record_id=f"norm-{uuid.uuid4().hex}",
                dataset_version_id=dv_id,
                raw_record_id=raw_id,
                payload={"legal_dispute": payload},
                normalized_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()


@pytest.mark.anyio
async def test_run_endpoint_success(monkeypatch: pytest.MonkeyPatch, sqlite_db: None) -> None:
    monkeypatch.setenv("TODISCOPE_ENABLED_ENGINES", ENGINE_ID)
    dv_id = str(uuid7())
    raw_id = f"raw-{uuid.uuid4().hex}"
    payload_data = {
        "claims": [{"amount": 1_000_000}],
        "damages": {"compensatory": 2_000_000, "punitive": 400_000, "mitigation": 100_000},
        "liability": {"parties": [{"party": "Vendor", "percent": 85, "evidence_strength": 0.8}]},
        "scenarios": [{"name": "low", "probability": 0.7, "expected_damages": 400_000, "liability_multiplier": 1.0}],
        "legal_consistency": {"conflicts": [], "missing_support": []},
    }

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        db.add(DatasetVersion(id=dv_id))
        db.add(
            RawRecord(
                raw_record_id=raw_id,
                dataset_version_id=dv_id,
                source_system="litigation",
                source_record_id="LIT-HTTP-001",
                payload={"legal_dispute": payload_data},
                ingested_at=datetime.now(timezone.utc),
            )
        )
        db.add(
            NormalizedRecord(
                normalized_record_id=f"norm-{uuid.uuid4().hex}",
                dataset_version_id=dv_id,
                raw_record_id=raw_id,
                payload={"legal_dispute": payload_data},
                normalized_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()

    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v3/engines/litigation-analysis/run",
            json={
                "dataset_version_id": dv_id,
                "started_at": "2024-01-01T00:00:00Z",
                "parameters": {
                    "assumptions": {
                        "damage": {"severity_thresholds": {"high": 1_000_000}, "recovery_rate": 0.5},
                        "liability": {"evidence_strength_thresholds": {"strong": 0.7, "weak": 0.4}},
                        "scenario": {"probabilities": 1.0},
                        "legal_consistency": {"completeness_requirements": ["statutes"]},
                    }
                },
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["dataset_version_id"] == dv_id
    assert "damage_assessment" in data
    assert "scenario_comparison" in data
    assert "legal_consistency" in data
    assert "assumptions" in data


@pytest.mark.anyio
async def test_run_endpoint_not_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TODISCOPE_ENABLED_ENGINES", "")
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/v3/engines/litigation-analysis/run", json={})
    assert response.status_code == 404


@pytest.mark.anyio
async def test_export_endpoint_json(monkeypatch: pytest.MonkeyPatch, sqlite_db: None) -> None:
    monkeypatch.setenv("TODISCOPE_ENABLED_ENGINES", ENGINE_ID)
    dv_id = str(uuid7())
    raw_id = f"raw-export-{uuid.uuid4().hex}"
    payload_data = {
        "claims": [{"amount": 500_000}],
        "damages": {"compensatory": 1_000_000, "punitive": 250_000, "mitigation": 100_000},
        "liability": {"parties": [{"party": "Supplier", "percent": 70, "evidence_strength": 0.75}]},
        "scenarios": [{"name": "baseline", "probability": 1.0, "expected_damages": 300_000, "liability_multiplier": 1.0}],
        "legal_consistency": {"conflicts": [], "missing_support": ["witnesses"]},
    }
    await _seed_dispute_records(get_sessionmaker(), dv_id, raw_id, payload_data)

    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        run_response = await ac.post(
            "/api/v3/engines/litigation-analysis/run",
            json={
                "dataset_version_id": dv_id,
                "started_at": "2024-01-01T00:00:00Z",
                "parameters": {
                    "assumptions": {
                        "damage": {"severity_thresholds": {"high": 1_000_000}, "recovery_rate": 0.5},
                        "liability": {"evidence_strength_thresholds": {"strong": 0.7, "weak": 0.3}},
                        "scenario": {"probabilities": 1.0},
                        "legal_consistency": {"completeness_requirements": ["statutes"]},
                    }
                },
            },
        )
        assert run_response.status_code == 200

        export_response = await ac.get(
            "/api/v3/engines/litigation-analysis/export",
            params={"dataset_version_id": dv_id, "format": "json"},
        )

    assert export_response.status_code == 200
    data = export_response.json()
    assert data["metadata"]["dataset_version_id"] == dv_id
    assert "summary" in data
    assert isinstance(data["summary"].get("assumptions"), list)


@pytest.mark.anyio
async def test_export_endpoint_pdf(monkeypatch: pytest.MonkeyPatch, sqlite_db: None) -> None:
    monkeypatch.setenv("TODISCOPE_ENABLED_ENGINES", ENGINE_ID)
    dv_id = str(uuid7())
    raw_id = f"raw-export-{uuid.uuid4().hex}"
    payload_data = {
        "claims": [{"amount": 250_000}],
        "damages": {"compensatory": 500_000, "punitive": 150_000, "mitigation": 50_000},
        "liability": {"parties": [{"party": "Vendor", "percent": 60, "evidence_strength": 0.6}]},
        "scenarios": [{"name": "scenario", "probability": 1.0, "expected_damages": 200_000, "liability_multiplier": 1.0}],
        "legal_consistency": {"conflicts": [], "missing_support": []},
    }
    await _seed_dispute_records(get_sessionmaker(), dv_id, raw_id, payload_data)

    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        run_response = await ac.post(
            "/api/v3/engines/litigation-analysis/run",
            json={
                "dataset_version_id": dv_id,
                "started_at": "2024-01-01T00:00:00Z",
                "parameters": {
                    "assumptions": {
                        "damage": {"severity_thresholds": {"high": 1_000_000}, "recovery_rate": 0.5},
                        "liability": {"evidence_strength_thresholds": {"strong": 0.7, "weak": 0.3}},
                        "scenario": {"probabilities": 1.0},
                        "legal_consistency": {"completeness_requirements": ["statutes"]},
                    }
                },
            },
        )
        assert run_response.status_code == 200

        export_response = await ac.get(
            "/api/v3/engines/litigation-analysis/export",
            params={"dataset_version_id": dv_id, "format": "pdf"},
        )

    assert export_response.status_code == 200
    assert export_response.headers["content-type"] == "application/pdf"
    assert export_response.headers["content-disposition"].startswith("attachment; filename=litigation-report-")
    assert export_response.content.startswith(b"%PDF")


@pytest.mark.anyio
async def test_export_endpoint_invalid_format(monkeypatch: pytest.MonkeyPatch, sqlite_db: None) -> None:
    monkeypatch.setenv("TODISCOPE_ENABLED_ENGINES", ENGINE_ID)
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            "/api/v3/engines/litigation-analysis/export",
            params={"dataset_version_id": "missing", "format": "xml"},
        )
    assert response.status_code == 400


@pytest.mark.anyio
async def test_export_endpoint_missing_run(monkeypatch: pytest.MonkeyPatch, sqlite_db: None) -> None:
    monkeypatch.setenv("TODISCOPE_ENABLED_ENGINES", ENGINE_ID)
    dv_id = str(uuid7())
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            "/api/v3/engines/litigation-analysis/export",
            params={"dataset_version_id": dv_id, "format": "json"},
        )
    assert response.status_code == 404
