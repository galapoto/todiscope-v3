import os

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from backend.app.core.artifacts.store import get_artifact_store
from backend.app.core.db import get_sessionmaker
from backend.app.core.evidence.models import EvidenceRecord
from backend.app.main import create_app
from backend.app.engines.enterprise_deal_transaction_readiness.engine import ENGINE_ID
from backend.app.engines.enterprise_deal_transaction_readiness.models.findings import (
    EnterpriseDealTransactionReadinessFinding,
)


def _key_from_memory_uri(uri: str) -> str:
    assert uri.startswith("memory://")
    return uri.removeprefix("memory://")


@pytest.mark.anyio
async def test_engine5_missing_optional_input_becomes_finding_and_evidence(sqlite_db: None) -> None:
    os.environ["TODISCOPE_ENABLED_ENGINES"] = ENGINE_ID
    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ingest = await ac.post("/api/v3/ingest")
        dv_id = ingest.json()["dataset_version_id"]

        run_payload = {
            "dataset_version_id": dv_id,
            "started_at": "2025-01-01T00:00:00+00:00",
            "transaction_scope": {"scope_kind": "full_dataset"},
            "parameters": {"fx": {"rates": {}}, "assumptions": {"note": "explicit"}},
            "optional_inputs": {
                "engine2_report": {
                    "artifact_key": "does-not-exist.json",
                    "sha256": "0" * 64,
                    "content_type": "application/json",
                }
            },
        }
        run_res = await ac.post("/api/v3/engines/enterprise-deal-transaction-readiness/run", json=run_payload)
        assert run_res.status_code == 200
        run_body = run_res.json()

        report_res = await ac.post(
            "/api/v3/engines/enterprise-deal-transaction-readiness/report",
            json={"dataset_version_id": dv_id, "run_id": run_body["run_id"], "view_type": "internal"},
        )
        assert report_res.status_code == 200
        report = report_res.json()
        assert report["dataset_version_id"] == dv_id
        assert report["result_set_id"] == run_body["result_set_id"]

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        finding = await db.scalar(
            select(EnterpriseDealTransactionReadinessFinding).where(
                EnterpriseDealTransactionReadinessFinding.result_set_id == run_body["result_set_id"]
            )
        )
        assert finding is not None
        assert finding.kind in ("missing_prerequisite", "prerequisite_invalid", "prerequisite_checksum_mismatch")

        evidence = await db.scalar(select(EvidenceRecord).where(EvidenceRecord.evidence_id == finding.evidence_id))
        assert evidence is not None
        assert evidence.dataset_version_id == dv_id
        assert evidence.engine_id == ENGINE_ID


@pytest.mark.anyio
async def test_engine5_export_produces_immutable_json_and_pdf(sqlite_db: None) -> None:
    os.environ["TODISCOPE_ENABLED_ENGINES"] = ENGINE_ID
    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ingest = await ac.post("/api/v3/ingest")
        dv_id = ingest.json()["dataset_version_id"]

        run_payload = {
            "dataset_version_id": dv_id,
            "started_at": "2025-01-01T00:00:00+00:00",
            "transaction_scope": {"scope_kind": "full_dataset"},
            "parameters": {"fx": {"rates": {}}, "assumptions": {"note": "explicit"}},
        }
        run1 = (await ac.post("/api/v3/engines/enterprise-deal-transaction-readiness/run", json=run_payload)).json()
        run2 = (await ac.post("/api/v3/engines/enterprise-deal-transaction-readiness/run", json=run_payload)).json()

        export1 = (
            await ac.post(
                "/api/v3/engines/enterprise-deal-transaction-readiness/export",
                json={
                    "dataset_version_id": dv_id,
                    "run_id": run1["run_id"],
                    "view_type": "external",
                    "formats": ["json", "pdf"],
                },
            )
        ).json()
        export2 = (
            await ac.post(
                "/api/v3/engines/enterprise-deal-transaction-readiness/export",
                json={
                    "dataset_version_id": dv_id,
                    "run_id": run2["run_id"],
                    "view_type": "external",
                    "formats": ["json", "pdf"],
                },
            )
        ).json()

    sha_by_format_1 = {e["format"]: e["sha256"] for e in export1["exports"]}
    sha_by_format_2 = {e["format"]: e["sha256"] for e in export2["exports"]}
    assert sha_by_format_1["json"] == sha_by_format_2["json"]
    assert sha_by_format_1["pdf"] == sha_by_format_2["pdf"]

    store = get_artifact_store()
    json_uri = next(e["uri"] for e in export1["exports"] if e["format"] == "json")
    json_bytes = await store.get_bytes(key=_key_from_memory_uri(json_uri))
    assert b"artifact_key" not in json_bytes
    assert b"expected_sha256" not in json_bytes
    assert b"sha256" not in json_bytes
    pdf_uri = next(e["uri"] for e in export1["exports"] if e["format"] == "pdf")
    pdf_bytes = await store.get_bytes(key=_key_from_memory_uri(pdf_uri))
    assert pdf_bytes.startswith(b"%PDF")
