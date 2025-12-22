"""
Edge case tests for Enterprise Litigation & Dispute Analysis Engine.

Tests cover:
- Conflicting evidence scenarios
- Different jurisdictional inputs
- Complex legal scenarios
- Boundary conditions
- Error handling
"""

from __future__ import annotations

from datetime import datetime, timezone
import uuid

import pytest
from sqlalchemy import select

from backend.app.core.dataset.service import create_dataset_version_via_ingestion
from backend.app.core.db import get_sessionmaker
from backend.app.core.dataset.raw_models import RawRecord
from backend.app.core.evidence.aggregation import (
    DatasetVersionMismatchError,
    get_evidence_by_dataset_version,
    verify_evidence_traceability,
)
from backend.app.core.normalization.models import NormalizedRecord
from backend.app.engines.enterprise_litigation_dispute.errors import (
    DatasetVersionNotFoundError,
    LegalPayloadMissingError,
    NormalizedRecordMissingError,
)
from backend.app.engines.enterprise_litigation_dispute.run import run_engine


@pytest.mark.anyio
async def test_conflicting_evidence_scenario(sqlite_db: None) -> None:
    """Test engine handling of conflicting evidence in dispute payload."""
    now = datetime.now(timezone.utc)

    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)

        raw_id = str(uuid.uuid4())
        db.add(
            RawRecord(
                raw_record_id=raw_id,
                dataset_version_id=dv.id,
                source_system="legal_system",
                source_record_id="conflict_001",
                payload={
                    "legal_dispute": {
                        "claims": [{"amount": 1000000}],
                        "damages": {"compensatory": 800000, "punitive": 200000},
                        "liability": {
                            "parties": [
                                {"party": "Party A", "percent": 60.0, "evidence_strength": 0.8},
                                {"party": "Party B", "percent": 50.0, "evidence_strength": 0.7},
                            ],
                        },
                        "scenarios": [],
                        "legal_consistency": {
                            "conflicts": ["Conflicting statute interpretation", "Contradictory evidence"],
                            "missing_support": ["Missing precedent"],
                        },
                    },
                },
                ingested_at=now,
            )
        )
        await db.commit()

        norm_id = str(uuid.uuid4())
        db.add(
            NormalizedRecord(
                normalized_record_id=norm_id,
                dataset_version_id=dv.id,
                raw_record_id=raw_id,
                payload={
                    "legal_dispute": {
                        "claims": [{"amount": 1000000}],
                        "damages": {"compensatory": 800000, "punitive": 200000},
                        "liability": {
                            "parties": [
                                {"party": "Party A", "percent": 60.0, "evidence_strength": 0.8},
                                {"party": "Party B", "percent": 50.0, "evidence_strength": 0.7},
                            ],
                        },
                        "scenarios": [],
                        "legal_consistency": {
                            "conflicts": ["Conflicting statute interpretation", "Contradictory evidence"],
                            "missing_support": ["Missing precedent"],
                        },
                    },
                },
                normalized_at=now,
            )
        )
        await db.commit()

    # Run engine - should handle conflicts gracefully
    result = await run_engine(
        dataset_version_id=dv.id,
        started_at=now.isoformat(),
        parameters={},
    )

    # Verify legal consistency check identifies conflicts
    assert result["legal_consistency"]["consistent"] is False
    assert len(result["legal_consistency"]["issues"]) > 0
    assert any("Conflict" in issue for issue in result["legal_consistency"]["issues"])
    assert any("Lacking support" in issue for issue in result["legal_consistency"]["issues"])

    # Verify liability assessment handles multiple parties
    assert result["liability_assessment"]["responsible_party"] in ("Party A", "Party B")
    assert result["liability_assessment"]["responsibility_pct"] > 0


@pytest.mark.parametrize(
    "jurisdiction,statutes,expected_handling",
    [
        ("US_Federal", ["Federal Statute A"], "handled"),
        ("US_State_CA", ["California Civil Code"], "handled"),
        ("EU_GDPR", ["GDPR Article 6"], "handled"),
        ("UK", ["UK Companies Act"], "handled"),
    ],
)
@pytest.mark.anyio
async def test_different_jurisdictions(
    sqlite_db: None,
    jurisdiction: str,
    statutes: list[str],
    expected_handling: str,
) -> None:
    """Test engine handling of different jurisdictional inputs."""
    now = datetime.now(timezone.utc)

    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)

        raw_id = str(uuid.uuid4())
        db.add(
            RawRecord(
                raw_record_id=raw_id,
                dataset_version_id=dv.id,
                source_system="legal_system",
                source_record_id=f"jurisdiction_{jurisdiction}",
                payload={
                    "legal_dispute": {
                        "claims": [{"amount": 500000}],
                        "damages": {"compensatory": 400000, "punitive": 100000},
                        "liability": {
                            "parties": [{"party": "Defendant", "percent": 80.0, "evidence_strength": 0.75}],
                            "regulations": statutes,
                        },
                        "scenarios": [],
                        "legal_consistency": {"conflicts": [], "missing_support": []},
                    },
                },
                ingested_at=now,
            )
        )
        await db.commit()

        norm_id = str(uuid.uuid4())
        db.add(
            NormalizedRecord(
                normalized_record_id=norm_id,
                dataset_version_id=dv.id,
                raw_record_id=raw_id,
                payload={
                    "legal_dispute": {
                        "claims": [{"amount": 500000}],
                        "damages": {"compensatory": 400000, "punitive": 100000},
                        "liability": {
                            "parties": [{"party": "Defendant", "percent": 80.0, "evidence_strength": 0.75}],
                            "regulations": statutes,
                        },
                        "scenarios": [],
                        "legal_consistency": {"conflicts": [], "missing_support": []},
                    },
                },
                normalized_at=now,
            )
        )
        await db.commit()

    # Run engine - should handle different jurisdictions
    result = await run_engine(
        dataset_version_id=dv.id,
        started_at=now.isoformat(),
        parameters={},
    )

    # Verify engine processes jurisdiction-specific data
    assert result["dataset_version_id"] == dv.id
    assert result["liability_assessment"]["indicators"] is not None
    if statutes:
        assert any("Regulatory" in ind for ind in result["liability_assessment"]["indicators"])


@pytest.mark.anyio
async def test_complex_multi_scenario_case(sqlite_db: None) -> None:
    """Test engine with complex multi-scenario litigation case."""
    now = datetime.now(timezone.utc)

    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)

        raw_id = str(uuid.uuid4())
        db.add(
            RawRecord(
                raw_record_id=raw_id,
                dataset_version_id=dv.id,
                source_system="legal_system",
                source_record_id="complex_001",
                payload={
                    "legal_dispute": {
                        "claims": [
                            {"amount": 500000},
                            {"amount": 300000},
                            {"amount": 200000},
                        ],
                        "damages": {
                            "compensatory": 800000,
                            "punitive": 200000,
                            "mitigation": 150000,
                        },
                        "liability": {
                            "parties": [
                                {"party": "Primary Defendant", "percent": 70.0, "evidence_strength": 0.85},
                                {"party": "Secondary Defendant", "percent": 30.0, "evidence_strength": 0.6},
                            ],
                            "admissions": ["Admission 1", "Admission 2"],
                            "regulations": ["Regulation A", "Regulation B", "Regulation C"],
                        },
                        "scenarios": [
                            {"name": "Settlement", "probability": 0.4, "expected_damages": 600000, "liability_multiplier": 0.8},
                            {"name": "Trial Win", "probability": 0.2, "expected_damages": 0, "liability_multiplier": 0.0},
                            {"name": "Trial Loss", "probability": 0.3, "expected_damages": 1200000, "liability_multiplier": 1.5},
                            {"name": "Appeal", "probability": 0.1, "expected_damages": 1500000, "liability_multiplier": 2.0},
                        ],
                        "legal_consistency": {
                            "conflicts": ["Minor conflict in interpretation"],
                            "missing_support": [],
                        },
                    },
                },
                ingested_at=now,
            )
        )
        await db.commit()

        norm_id = str(uuid.uuid4())
        db.add(
            NormalizedRecord(
                normalized_record_id=norm_id,
                dataset_version_id=dv.id,
                raw_record_id=raw_id,
                payload={
                    "legal_dispute": {
                        "claims": [
                            {"amount": 500000},
                            {"amount": 300000},
                            {"amount": 200000},
                        ],
                        "damages": {
                            "compensatory": 800000,
                            "punitive": 200000,
                            "mitigation": 150000,
                        },
                        "liability": {
                            "parties": [
                                {"party": "Primary Defendant", "percent": 70.0, "evidence_strength": 0.85},
                                {"party": "Secondary Defendant", "percent": 30.0, "evidence_strength": 0.6},
                            ],
                            "admissions": ["Admission 1", "Admission 2"],
                            "regulations": ["Regulation A", "Regulation B", "Regulation C"],
                        },
                        "scenarios": [
                            {"name": "Settlement", "probability": 0.4, "expected_damages": 600000, "liability_multiplier": 0.8},
                            {"name": "Trial Win", "probability": 0.2, "expected_damages": 0, "liability_multiplier": 0.0},
                            {"name": "Trial Loss", "probability": 0.3, "expected_damages": 1200000, "liability_multiplier": 1.5},
                            {"name": "Appeal", "probability": 0.1, "expected_damages": 1500000, "liability_multiplier": 2.0},
                        ],
                        "legal_consistency": {
                            "conflicts": ["Minor conflict in interpretation"],
                            "missing_support": [],
                        },
                    },
                },
                normalized_at=now,
            )
        )
        await db.commit()

    # Run engine
    result = await run_engine(
        dataset_version_id=dv.id,
        started_at=now.isoformat(),
        parameters={},
    )

    # Verify complex scenario handling
    assert result["damage_assessment"]["total_claim_value"] == 1000000.0
    assert result["scenario_comparison"]["total_probability"] <= 1.01  # Account for floating point precision
    assert len(result["scenario_comparison"]["scenarios"]) == 4
    assert result["scenario_comparison"]["best_case"] is not None
    assert result["scenario_comparison"]["worst_case"] is not None

    # Verify best case has lower expected loss than worst case
    best_loss = result["scenario_comparison"]["best_case"]["expected_loss"]
    worst_loss = result["scenario_comparison"]["worst_case"]["expected_loss"]
    assert best_loss <= worst_loss

    # Verify multiple parties handled
    assert result["liability_assessment"]["responsible_party"] in ("Primary Defendant", "Secondary Defendant")


@pytest.mark.anyio
async def test_missing_dataset_version(sqlite_db: None) -> None:
    """Test error handling for missing dataset version."""
    now = datetime.now(timezone.utc)

    with pytest.raises(DatasetVersionNotFoundError):
        await run_engine(
            dataset_version_id="non-existent-dv-id",
            started_at=now.isoformat(),
            parameters={},
        )


@pytest.mark.anyio
async def test_missing_normalized_record(sqlite_db: None) -> None:
    """Test error handling for missing normalized record."""
    now = datetime.now(timezone.utc)

    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)
        await db.commit()

    with pytest.raises(NormalizedRecordMissingError):
        await run_engine(
            dataset_version_id=dv.id,
            started_at=now.isoformat(),
            parameters={},
        )


@pytest.mark.anyio
async def test_missing_legal_payload(sqlite_db: None) -> None:
    """Test error handling for missing legal payload."""
    now = datetime.now(timezone.utc)

    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)

        raw_id = str(uuid.uuid4())
        db.add(
            RawRecord(
                raw_record_id=raw_id,
                dataset_version_id=dv.id,
                source_system="legal_system",
                source_record_id="missing_payload",
                payload={"other_data": "value"},
                ingested_at=now,
            )
        )
        await db.commit()

        norm_id = str(uuid.uuid4())
        db.add(
            NormalizedRecord(
                normalized_record_id=norm_id,
                dataset_version_id=dv.id,
                raw_record_id=raw_id,
                payload={"other_data": "value"},
                normalized_at=now,
            )
        )
        await db.commit()

    with pytest.raises(LegalPayloadMissingError):
        await run_engine(
            dataset_version_id=dv.id,
            started_at=now.isoformat(),
            parameters={},
        )


@pytest.mark.anyio
async def test_extreme_damage_values(sqlite_db: None) -> None:
    """Test engine handling of extreme damage values."""
    now = datetime.now(timezone.utc)

    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)

        raw_id = str(uuid.uuid4())
        db.add(
            RawRecord(
                raw_record_id=raw_id,
                dataset_version_id=dv.id,
                source_system="legal_system",
                source_record_id="extreme_001",
                payload={
                    "legal_dispute": {
                        "claims": [{"amount": 1000000000}],  # 1 billion
                        "damages": {"compensatory": 500000000, "punitive": 500000000},
                        "liability": {"parties": [{"party": "Defendant", "percent": 100.0, "evidence_strength": 0.9}]},
                        "scenarios": [],
                        "legal_consistency": {"conflicts": [], "missing_support": []},
                    },
                },
                ingested_at=now,
            )
        )
        await db.commit()

        norm_id = str(uuid.uuid4())
        db.add(
            NormalizedRecord(
                normalized_record_id=norm_id,
                dataset_version_id=dv.id,
                raw_record_id=raw_id,
                payload={
                    "legal_dispute": {
                        "claims": [{"amount": 1000000000}],
                        "damages": {"compensatory": 500000000, "punitive": 500000000},
                        "liability": {"parties": [{"party": "Defendant", "percent": 100.0, "evidence_strength": 0.9}]},
                        "scenarios": [],
                        "legal_consistency": {"conflicts": [], "missing_support": []},
                    },
                },
                normalized_at=now,
            )
        )
        await db.commit()

    # Run engine - should handle extreme values
    result = await run_engine(
        dataset_version_id=dv.id,
        started_at=now.isoformat(),
        parameters={},
    )

    # Verify extreme values are handled correctly
    assert result["damage_assessment"]["total_claim_value"] == 1000000000.0
    assert result["damage_assessment"]["gross_damages"] == 1000000000.0
    assert result["damage_assessment"]["severity"] == "high"


@pytest.mark.anyio
async def test_zero_damages_case(sqlite_db: None) -> None:
    """Test engine handling of zero damages case."""
    now = datetime.now(timezone.utc)

    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)

        raw_id = str(uuid.uuid4())
        db.add(
            RawRecord(
                raw_record_id=raw_id,
                dataset_version_id=dv.id,
                source_system="legal_system",
                source_record_id="zero_001",
                payload={
                    "legal_dispute": {
                        "claims": [],
                        "damages": {"compensatory": 0, "punitive": 0},
                        "liability": {"parties": []},
                        "scenarios": [],
                        "legal_consistency": {"conflicts": [], "missing_support": []},
                    },
                },
                ingested_at=now,
            )
        )
        await db.commit()

        norm_id = str(uuid.uuid4())
        db.add(
            NormalizedRecord(
                normalized_record_id=norm_id,
                dataset_version_id=dv.id,
                raw_record_id=raw_id,
                payload={
                    "legal_dispute": {
                        "claims": [],
                        "damages": {"compensatory": 0, "punitive": 0},
                        "liability": {"parties": []},
                        "scenarios": [],
                        "legal_consistency": {"conflicts": [], "missing_support": []},
                    },
                },
                normalized_at=now,
            )
        )
        await db.commit()

    # Run engine - should handle zero damages
    result = await run_engine(
        dataset_version_id=dv.id,
        started_at=now.isoformat(),
        parameters={},
    )

    # Verify zero damages handled
    assert result["damage_assessment"]["total_claim_value"] == 0.0
    assert result["damage_assessment"]["net_damage"] == 0.0
    assert result["damage_assessment"]["severity"] == "low"
    assert result["liability_assessment"]["responsible_party"] == "undetermined"

