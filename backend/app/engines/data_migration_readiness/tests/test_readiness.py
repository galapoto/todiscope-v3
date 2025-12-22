from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal
from types import MappingProxyType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.core.dataset.models import DatasetVersion
from backend.app.core.dataset.raw_models import RawRecord
from backend.app.engines.data_migration_readiness import run as readiness_run
from backend.app.engines.data_migration_readiness.checks import (
    RawRecordSnapshot,
    StructuralCheck,
    QualityCheck,
    MappingCheck,
    IntegrityCheck,
    assess_risks,
    build_collection_index,
    evaluate_mapping,
    evaluate_quality,
    evaluate_structure,
    verify_integrity,
    load_default_config,
)


class _FakeScalars:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeSession:
    def __init__(self, dataset_version, records):
        self._dataset = dataset_version
        self._records = records
        self.add = MagicMock()
        self.flush = AsyncMock()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def scalar(self, query):
        return self._dataset

    async def scalars(self, query):
        return _FakeScalars(self._records)

    async def commit(self):
        return None


class _FakeSessionMaker:
    def __init__(self, dataset_version, records):
        self._dataset = dataset_version
        self._records = records

    def __call__(self):
        return _FakeSession(self._dataset, self._records)


def _build_single_snapshot() -> RawRecordSnapshot:
    payload = {
        "customers": [
            {
                "customer_id": "C1",
                "customer_name": "Name",
                "customer_email": "alert@example.com",
            }
        ],
        "transactions": [
            {
                "transaction_id": "T1",
                "transaction_amount": 100,
                "transaction_currency": "EUR",
                "transaction_timestamp": "2024-01-01T00:00:00Z",
            }
        ],
        "schema_version": "1",
        "source_system": "erp",
        "ingestion_date": "2024-01-01",
    }
    return RawRecordSnapshot(
        raw_record_id="raw-1",
        dataset_version_id="dv-1",
        source_system="erp",
        source_record_id="src-1",
        payload=payload,
    )


def _build_raw_record(record_id: str, source_record_id: str, source_system: str) -> RawRecord:
    return RawRecord(
        raw_record_id=record_id,
        dataset_version_id="dv-test",
        source_system=source_system,
        source_record_id=source_record_id,
        payload={
            "customers": [
                {
                    "customer_id": "C1",
                    "customer_name": "Name",
                    "customer_email": "alert@example.com",
                }
            ],
            "transactions": [
                {
                    "transaction_id": "T1",
                    "transaction_amount": 100,
                    "transaction_currency": "EUR",
                    "transaction_timestamp": "2024-01-01T00:00:00Z",
                }
            ],
            "schema_version": "1",
            "source_system": source_system,
            "ingestion_date": "2024-01-01",
        },
        ingested_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


def test_structure_quality_mapping_flags_missing_collections():
    config = load_default_config()
    snapshot = _build_single_snapshot()
    snapshots = (snapshot,)
    collections = build_collection_index(snapshots)
    structure = evaluate_structure("dv-test", snapshots, collections, config)
    assert "accounts" in structure.missing_collections
    assert not structure.compliant
    quality = evaluate_quality("dv-test", collections, config, Decimal("0"))
    assert "accounts: no rows received" in quality.notes
    assert quality.completeness_score == Decimal("1")
    mapping = evaluate_mapping("dv-test", collections, config)
    assert not mapping.compliant
    integrity = verify_integrity("dv-test", snapshots)
    assert integrity.compliant


def test_assess_risks_attaches_source_systems():
    structure = StructuralCheck(
        dataset_version_id="dv",
        required_collections=("customers",),
        missing_collections=("accounts",),
        missing_fields=MappingProxyType({"accounts": ("account_id",)}),
        metadata_issues=(),
        compliant=False,
    )
    quality = QualityCheck(
        dataset_version_id="dv",
        completeness_score=Decimal("0.7"),
        null_ratio=Decimal("0"),
        duplicate_ratio=Decimal("0"),
        per_collection=MappingProxyType({}),
        passes=False,
        notes=(),
    )
    mapping = MappingCheck(
        dataset_version_id="dv",
        missing_mappings=MappingProxyType({"accounts": ("account_id",)}),
        compliant=False,
    )
    integrity = IntegrityCheck(
        dataset_version_id="dv",
        record_count=1,
        unique_source_records=1,
        duplicate_ratio=Decimal("0"),
        compliant=True,
        notes=(),
    )
    risks = assess_risks(
        "dv",
        structure=structure,
        quality=quality,
        mapping=mapping,
        integrity=integrity,
        config={},
        source_systems=("sys",),
    )
    assert risks
    assert all("source_systems" in risk.metadata for risk in risks)
    assert risks[0].metadata["source_systems"] == ("sys",)


def test_run_readiness_check_logs_traceability(monkeypatch, caplog):
    dataset = DatasetVersion(id="dv-test")
    raw_records = [
        _build_raw_record("raw-1", "src-1", "erp"),
        _build_raw_record("raw-2", "src-1", "erp"),
    ]
    monkeypatch.setattr(
        readiness_run,
        "get_sessionmaker",
        lambda: _FakeSessionMaker(dataset, raw_records),
    )
    caplog.set_level(logging.WARNING, logger=readiness_run.logger.name)
    with patch(
        "backend.app.engines.data_migration_readiness.run._strict_create_evidence",
        new_callable=AsyncMock,
    ), patch(
        "backend.app.engines.data_migration_readiness.run._strict_create_finding",
        new_callable=AsyncMock,
    ), patch(
        "backend.app.engines.data_migration_readiness.run._strict_link",
        new_callable=AsyncMock,
    ):
        result = asyncio.run(
            readiness_run.run_readiness_check(
                dataset_version_id="dv-test",
                started_at="2024-01-02T00:00:00Z",
            )
        )
    assert result["dataset_version_id"] == "dv-test"
    assert result["source_systems"] == ("erp",)
    assert result["risks"]
    assert "run_id" in result
    assert isinstance(result["remediation_tasks"], list)
    assert "summary_evidence_id" in result
    record = next(
        r
        for r in caplog.records
        if "DATA_MIGRATION_READINESS_RISKS" in r.message
    )
    assert "dataset_version_id=dv-test" in record.message
    assert "source_systems=('erp',)" in record.message
