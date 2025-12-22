import os

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from backend.app.core.db import get_sessionmaker
from backend.app.core.evidence.models import EvidenceRecord
from backend.app.main import create_app


@pytest.mark.anyio
async def test_deterministic_rule_ordering_exact_match(sqlite_db: None) -> None:
    os.environ["TODISCOPE_ARTIFACT_STORE_KIND"] = "memory"
    os.environ["TODISCOPE_ENABLED_ENGINES"] = "engine_financial_forensics"
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ingest = await ac.post(
            "/api/v3/ingest-records",
            json={
                "records": [
                    {
                        "source_system": "erp",
                        "source_record_id": "inv-1",
                        "record_type": "invoice",
                        "posted_at": "2026-01-01T00:00:00+00:00",
                        "counterparty_id": "c1",
                        "amount_original": "100.00",
                        "currency_original": "USD",
                        "direction": "debit",
                        "reference_ids": ["doc-1"],
                    },
                    {
                        "source_system": "erp",
                        "source_record_id": "pay-1",
                        "record_type": "payment",
                        "posted_at": "2026-01-02T00:00:00+00:00",
                        "counterparty_id": "c1",
                        "amount_original": "100.00",
                        "currency_original": "USD",
                        "direction": "credit",
                        "reference_ids": ["doc-1"],
                    },
                ]
            },
        )
        dv_id = ingest.json()["dataset_version_id"]
        _ = await ac.post("/api/v3/engines/financial-forensics/normalize", json={"dataset_version_id": dv_id})
        fx = await ac.post(
            "/api/v3/fx-artifacts",
            json={
                "dataset_version_id": dv_id,
                "base_currency": "USD",
                "effective_date": "2026-01-31",
                "created_at": "2026-01-01T00:00:00+00:00",
                "rates": {"USD": "1"},
            },
        )
        fx_id = fx.json()["fx_artifact_id"]

        params = {"rounding_mode": "ROUND_HALF_UP", "rounding_quantum": "0.01"}
        r1 = await ac.post(
            "/api/v3/engines/financial-forensics/run",
            json={"dataset_version_id": dv_id, "fx_artifact_id": fx_id, "started_at": "2026-02-01T00:00:00+00:00", "parameters": params},
        )
        r2 = await ac.post(
            "/api/v3/engines/financial-forensics/run",
            json={"dataset_version_id": dv_id, "fx_artifact_id": fx_id, "started_at": "2026-02-01T00:00:00+00:00", "parameters": params},
        )
    assert r1.status_code == 200 and r2.status_code == 200
    f1 = r1.json()["findings"]
    f2 = r2.json()["findings"]
    assert f1 == f2
    assert len(f1) == 1
    assert f1[0]["confidence"] == "exact"
    assert f1[0]["rule_id"] == "ff.match.invoice_payment.exact"


@pytest.mark.anyio
async def test_partial_match_balance_remaining_amount(sqlite_db: None) -> None:
    os.environ["TODISCOPE_ARTIFACT_STORE_KIND"] = "memory"
    os.environ["TODISCOPE_ENABLED_ENGINES"] = "engine_financial_forensics"
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ingest = await ac.post(
            "/api/v3/ingest-records",
            json={
                "records": [
                    {
                        "source_system": "erp",
                        "source_record_id": "inv-2",
                        "record_type": "invoice",
                        "posted_at": "2026-01-01T00:00:00+00:00",
                        "counterparty_id": "c2",
                        "amount_original": "100.00",
                        "currency_original": "USD",
                        "direction": "debit",
                        "reference_ids": ["doc-2"],
                    },
                    {
                        "source_system": "erp",
                        "source_record_id": "pay-2a",
                        "record_type": "payment",
                        "posted_at": "2026-01-02T00:00:00+00:00",
                        "counterparty_id": "c2",
                        "amount_original": "30.00",
                        "currency_original": "USD",
                        "direction": "credit",
                        "reference_ids": ["doc-2"],
                    },
                    {
                        "source_system": "erp",
                        "source_record_id": "pay-2b",
                        "record_type": "payment",
                        "posted_at": "2026-01-03T00:00:00+00:00",
                        "counterparty_id": "c2",
                        "amount_original": "20.00",
                        "currency_original": "USD",
                        "direction": "credit",
                        "reference_ids": ["doc-2"],
                    },
                ]
            },
        )
        dv_id = ingest.json()["dataset_version_id"]
        _ = await ac.post("/api/v3/engines/financial-forensics/normalize", json={"dataset_version_id": dv_id})
        fx = await ac.post(
            "/api/v3/fx-artifacts",
            json={
                "dataset_version_id": dv_id,
                "base_currency": "USD",
                "effective_date": "2026-01-31",
                "created_at": "2026-01-01T00:00:00+00:00",
                "rates": {"USD": "1"},
            },
        )
        fx_id = fx.json()["fx_artifact_id"]
        params = {"rounding_mode": "ROUND_HALF_UP", "rounding_quantum": "0.01"}
        res = await ac.post(
            "/api/v3/engines/financial-forensics/run",
            json={"dataset_version_id": dv_id, "fx_artifact_id": fx_id, "started_at": "2026-02-01T00:00:00+00:00", "parameters": params},
        )
    assert res.status_code == 200
    findings = res.json()["findings"]
    assert len(findings) == 1
    assert findings[0]["confidence"] == "partial"
    assert findings[0]["rule_id"] == "ff.match.invoice_payment.partial"
    assert findings[0]["unmatched_amount"] == "50.00"


@pytest.mark.anyio
async def test_partial_many_to_one_payment_groups_invoices_deterministically(sqlite_db: None) -> None:
    os.environ["TODISCOPE_ARTIFACT_STORE_KIND"] = "memory"
    os.environ["TODISCOPE_ENABLED_ENGINES"] = "engine_financial_forensics"
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ingest = await ac.post(
            "/api/v3/ingest-records",
            json={
                "records": [
                    {
                        "source_system": "erp",
                        "source_record_id": "inv-a",
                        "record_type": "invoice",
                        "posted_at": "2026-01-01T00:00:00+00:00",
                        "counterparty_id": "c4",
                        "amount_original": "40.00",
                        "currency_original": "USD",
                        "direction": "debit",
                        "reference_ids": ["doc-4"],
                    },
                    {
                        "source_system": "erp",
                        "source_record_id": "inv-b",
                        "record_type": "invoice",
                        "posted_at": "2026-01-02T00:00:00+00:00",
                        "counterparty_id": "c4",
                        "amount_original": "40.00",
                        "currency_original": "USD",
                        "direction": "debit",
                        "reference_ids": ["doc-4"],
                    },
                    {
                        "source_system": "erp",
                        "source_record_id": "pay-a",
                        "record_type": "payment",
                        "posted_at": "2026-01-03T00:00:00+00:00",
                        "counterparty_id": "c4",
                        "amount_original": "50.00",
                        "currency_original": "USD",
                        "direction": "credit",
                        "reference_ids": ["doc-4"],
                    },
                ]
            },
        )
        dv_id = ingest.json()["dataset_version_id"]
        _ = await ac.post("/api/v3/engines/financial-forensics/normalize", json={"dataset_version_id": dv_id})
        fx = await ac.post(
            "/api/v3/fx-artifacts",
            json={
                "dataset_version_id": dv_id,
                "base_currency": "USD",
                "effective_date": "2026-01-31",
                "created_at": "2026-01-01T00:00:00+00:00",
                "rates": {"USD": "1"},
            },
        )
        fx_id = fx.json()["fx_artifact_id"]
        params = {"rounding_mode": "ROUND_HALF_UP", "rounding_quantum": "0.01"}
        res = await ac.post(
            "/api/v3/engines/financial-forensics/run",
            json={
                "dataset_version_id": dv_id,
                "fx_artifact_id": fx_id,
                "started_at": "2026-02-01T00:00:00+00:00",
                "parameters": params,
            },
        )
    assert res.status_code == 200
    findings = res.json()["findings"]
    assert len(findings) == 1
    assert findings[0]["confidence"] == "partial"
    assert findings[0]["rule_id"] == "ff.match.invoice_payment.partial_many_to_one"
    assert findings[0]["unmatched_amount"] == "30.00"


@pytest.mark.anyio
async def test_evidence_emitted_for_each_finding(sqlite_db: None) -> None:
    os.environ["TODISCOPE_ARTIFACT_STORE_KIND"] = "memory"
    os.environ["TODISCOPE_ENABLED_ENGINES"] = "engine_financial_forensics"
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ingest = await ac.post(
            "/api/v3/ingest-records",
            json={
                "records": [
                    {
                        "source_system": "erp",
                        "source_record_id": "inv-3",
                        "record_type": "invoice",
                        "posted_at": "2026-01-01T00:00:00+00:00",
                        "counterparty_id": "c3",
                        "amount_original": "100.00",
                        "currency_original": "USD",
                        "direction": "debit",
                        "reference_ids": ["doc-3"],
                    },
                    {
                        "source_system": "erp",
                        "source_record_id": "pay-3",
                        "record_type": "payment",
                        "posted_at": "2026-01-02T00:00:00+00:00",
                        "counterparty_id": "c3",
                        "amount_original": "99.50",
                        "currency_original": "USD",
                        "direction": "credit",
                        "reference_ids": ["doc-3"],
                    },
                ]
            },
        )
        dv_id = ingest.json()["dataset_version_id"]
        _ = await ac.post("/api/v3/engines/financial-forensics/normalize", json={"dataset_version_id": dv_id})
        fx = await ac.post(
            "/api/v3/fx-artifacts",
            json={
                "dataset_version_id": dv_id,
                "base_currency": "USD",
                "effective_date": "2026-01-31",
                "created_at": "2026-01-01T00:00:00+00:00",
                "rates": {"USD": "1"},
            },
        )
        fx_id = fx.json()["fx_artifact_id"]
        params = {
            "rounding_mode": "ROUND_HALF_UP",
            "rounding_quantum": "0.01",
            "tolerance_amount": "1.00",
        }
        res = await ac.post(
            "/api/v3/engines/financial-forensics/run",
            json={"dataset_version_id": dv_id, "fx_artifact_id": fx_id, "started_at": "2026-02-01T00:00:00+00:00", "parameters": params},
        )
    assert res.status_code == 200
    findings = res.json()["findings"]
    assert len(findings) == 1
    assert findings[0]["confidence"] == "within_tolerance"
    evidence_ids = findings[0]["evidence_ids"]
    assert isinstance(evidence_ids, list) and len(evidence_ids) == 1

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        ev = await db.scalar(select(EvidenceRecord).where(EvidenceRecord.evidence_id == evidence_ids[0]))
        assert ev is not None
        assert ev.dataset_version_id == dv_id
        payload = ev.payload
        for required in [
            "rule_identity",
            "amount_comparison",
            "date_comparison",
            "reference_comparison",
            "counterparty",
            "match_selection",
            "primary_sources",
        ]:
            assert required in payload
        assert payload["rule_identity"]["rule_id"] == "ff.match.invoice_payment.tolerance"
