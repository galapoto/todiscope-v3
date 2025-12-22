"""
Integration tests for Enterprise Distressed Asset & Debt Stress Engine.

Tests integration with other TodiScope engines:
- Financial Forensics & Leakage Engine
- Capital & Debt Readiness Engine

Verifies DatasetVersion binding and data flow between engines.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from backend.app.core.dataset.immutability import install_immutability_guards
from backend.app.core.dataset.models import DatasetVersion
from backend.app.core.dataset.service import create_dataset_version_via_ingestion
from backend.app.core.evidence.aggregation import (
    get_evidence_by_dataset_version,
    get_findings_by_dataset_version,
)
from backend.app.core.evidence.models import EvidenceRecord, FindingEvidenceLink, FindingRecord
from backend.app.core.normalization.models import NormalizedRecord
from backend.app.core.db import get_sessionmaker
from backend.app.engines.enterprise_distressed_asset_debt_stress.run import run_engine
from backend.app.engines.enterprise_distressed_asset_debt_stress.constants import ENGINE_ID


@pytest.mark.anyio
async def test_distressed_asset_engine_produces_consumable_evidence(sqlite_db: None) -> None:
    """Test that Distressed Asset engine produces evidence that other engines can consume."""
    install_immutability_guards()
    
    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)
        
        import uuid
        from backend.app.core.dataset.raw_models import RawRecord
        
        raw_id = str(uuid.uuid4())
        db.add(
            RawRecord(
                raw_record_id=raw_id,
                dataset_version_id=dv.id,
                source_system="test",
                source_record_id="test-1",
                payload={
                    "financial": {
                        "debt": {
                            "total_outstanding": 1_000_000,
                            "interest_rate_pct": 5.0,
                            "collateral_value": 750_000,
                        },
                        "assets": {"total": 2_000_000},
                    },
                    "distressed_assets": [
                        {"value": 200_000, "recovery_rate_pct": 35},
                    ],
                },
                ingested_at=datetime.now(timezone.utc),
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
                    "financial": {
                        "debt": {
                            "total_outstanding": 1_000_000,
                            "interest_rate_pct": 5.0,
                            "collateral_value": 750_000,
                        },
                        "assets": {"total": 2_000_000},
                    },
                    "distressed_assets": [
                        {"value": 200_000, "recovery_rate_pct": 35},
                    ],
                },
                normalized_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()
    
    # Run Distressed Asset engine
    started = datetime.now(timezone.utc)
    result = await run_engine(
        dataset_version_id=dv.id,
        started_at=started.isoformat(),
    )
    
    # Verify evidence is stored and can be retrieved by other engines
    async with get_sessionmaker()() as db:
        evidence = await get_evidence_by_dataset_version(
            db,
            dataset_version_id=dv.id,
            engine_id=ENGINE_ID,
        )
        
        assert len(evidence) > 0
        
        # Verify debt_exposure evidence exists
        debt_exposure_evidence = [e for e in evidence if e.kind == "debt_exposure"]
        assert len(debt_exposure_evidence) == 1
        
        # Verify stress_test evidence exists
        stress_test_evidence = [e for e in evidence if e.kind == "stress_test"]
        assert len(stress_test_evidence) == 3  # Three default scenarios
        
        # Verify all evidence is bound to DatasetVersion
        for e in evidence:
            assert e.dataset_version_id == dv.id
            assert e.engine_id == ENGINE_ID
        
        # Verify findings are stored
        findings = await get_findings_by_dataset_version(
            db,
            dataset_version_id=dv.id,
        )
        
        # Filter findings by checking if they're linked to our engine's evidence
        distressed_asset_evidence_ids = {e.evidence_id for e in evidence}
        distressed_asset_findings = []
        for finding in findings:
            links = (
                await db.scalars(
                    select(FindingEvidenceLink).where(
                        FindingEvidenceLink.finding_id == finding.finding_id
                    )
                )
            ).all()
            if any(link.evidence_id in distressed_asset_evidence_ids for link in links):
                distressed_asset_findings.append(finding)
        
        assert len(distressed_asset_findings) > 0
        
        # Verify all findings are bound to DatasetVersion
        for f in distressed_asset_findings:
            assert f.dataset_version_id == dv.id


@pytest.mark.anyio
async def test_capital_debt_readiness_can_consume_distressed_asset_evidence(sqlite_db: None) -> None:
    """Test that Capital & Debt Readiness engine can consume Distressed Asset engine evidence."""
    install_immutability_guards()
    
    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)
        
        import uuid
        from backend.app.core.dataset.raw_models import RawRecord
        
        raw_id = str(uuid.uuid4())
        db.add(
            RawRecord(
                raw_record_id=raw_id,
                dataset_version_id=dv.id,
                source_system="test",
                source_record_id="test-1",
                payload={
                    "financial": {
                        "debt": {
                            "total_outstanding": 1_000_000,
                            "interest_rate_pct": 5.0,
                            "collateral_value": 750_000,
                        },
                        "assets": {"total": 2_000_000},
                    },
                    "distressed_assets": [
                        {"value": 200_000, "recovery_rate_pct": 35},
                    ],
                },
                ingested_at=datetime.now(timezone.utc),
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
                    "financial": {
                        "debt": {
                            "total_outstanding": 1_000_000,
                            "interest_rate_pct": 5.0,
                            "collateral_value": 750_000,
                        },
                        "assets": {"total": 2_000_000},
                    },
                    "distressed_assets": [
                        {"value": 200_000, "recovery_rate_pct": 35},
                    ],
                },
                normalized_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()
    
    # Run Distressed Asset engine first
    started = datetime.now(timezone.utc)
    distressed_result = await run_engine(
        dataset_version_id=dv.id,
        started_at=started.isoformat(),
    )
    
    # Now simulate Capital & Debt Readiness engine consuming the evidence
    async with get_sessionmaker()() as db:
        # Load evidence from Distressed Asset engine
        distressed_evidence = await get_evidence_by_dataset_version(
            db,
            dataset_version_id=dv.id,
            engine_id=ENGINE_ID,
        )
        
        assert len(distressed_evidence) > 0
        
        # Verify we can extract debt exposure data
        debt_exposure_evidence = [e for e in distressed_evidence if e.kind == "debt_exposure"]
        assert len(debt_exposure_evidence) == 1
        
        debt_payload = debt_exposure_evidence[0].payload
        assert "debt_exposure" in debt_payload
        
        debt_data = debt_payload["debt_exposure"]
        assert "total_outstanding" in debt_data
        assert "net_exposure_after_recovery" in debt_data
        assert "interest_rate_pct" in debt_data
        
        # Verify we can extract stress test data
        stress_test_evidence = [e for e in distressed_evidence if e.kind == "stress_test"]
        assert len(stress_test_evidence) == 3
        
        # Verify stress test data structure
        for stress_ev in stress_test_evidence:
            assert "stress_test" in stress_ev.payload
            stress_data = stress_ev.payload["stress_test"]
            assert "scenario_id" in stress_data
            assert "loss_estimate" in stress_data
            assert "impact_score" in stress_data
        
        # Verify DatasetVersion binding
        for e in distressed_evidence:
            assert e.dataset_version_id == dv.id


@pytest.mark.anyio
async def test_dataset_version_isolation_in_integration(sqlite_db: None) -> None:
    """Test that engines maintain DatasetVersion isolation when consuming cross-engine data."""
    install_immutability_guards()
    
    async with get_sessionmaker()() as db:
        dv1 = await create_dataset_version_via_ingestion(db)
        dv2 = await create_dataset_version_via_ingestion(db)
        
        import uuid
        from backend.app.core.dataset.raw_models import RawRecord
        
        # Create records for dv1
        raw_id1 = str(uuid.uuid4())
        db.add(
            RawRecord(
                raw_record_id=raw_id1,
                dataset_version_id=dv1.id,
                source_system="test",
                source_record_id="test-1",
                payload={
                    "financial": {
                        "debt": {"total_outstanding": 1_000_000, "interest_rate_pct": 5.0},
                        "assets": {"total": 2_000_000},
                    },
                },
                ingested_at=datetime.now(timezone.utc),
            )
        )
        
        # Create records for dv2
        raw_id2 = str(uuid.uuid4())
        db.add(
            RawRecord(
                raw_record_id=raw_id2,
                dataset_version_id=dv2.id,
                source_system="test",
                source_record_id="test-2",
                payload={
                    "financial": {
                        "debt": {"total_outstanding": 500_000, "interest_rate_pct": 4.0},
                        "assets": {"total": 1_000_000},
                    },
                },
                ingested_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()
        
        norm_id1 = str(uuid.uuid4())
        db.add(
            NormalizedRecord(
                normalized_record_id=norm_id1,
                dataset_version_id=dv1.id,
                raw_record_id=raw_id1,
                payload={
                    "financial": {
                        "debt": {"total_outstanding": 1_000_000, "interest_rate_pct": 5.0},
                        "assets": {"total": 2_000_000},
                    },
                },
                normalized_at=datetime.now(timezone.utc),
            )
        )
        
        norm_id2 = str(uuid.uuid4())
        db.add(
            NormalizedRecord(
                normalized_record_id=norm_id2,
                dataset_version_id=dv2.id,
                raw_record_id=raw_id2,
                payload={
                    "financial": {
                        "debt": {"total_outstanding": 500_000, "interest_rate_pct": 4.0},
                        "assets": {"total": 1_000_000},
                    },
                },
                normalized_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()
    
    # Run engine for both DatasetVersions
    started = datetime.now(timezone.utc)
    result1 = await run_engine(
        dataset_version_id=dv1.id,
        started_at=started.isoformat(),
    )
    
    result2 = await run_engine(
        dataset_version_id=dv2.id,
        started_at=started.isoformat(),
    )
    
    # Verify isolation: querying dv1 should not return dv2 evidence
    async with get_sessionmaker()() as db:
        dv1_evidence = await get_evidence_by_dataset_version(
            db,
            dataset_version_id=dv1.id,
            engine_id=ENGINE_ID,
        )
        
        dv2_evidence = await get_evidence_by_dataset_version(
            db,
            dataset_version_id=dv2.id,
            engine_id=ENGINE_ID,
        )
        
        # Verify no cross-contamination
        dv1_evidence_ids = {e.evidence_id for e in dv1_evidence}
        dv2_evidence_ids = {e.evidence_id for e in dv2_evidence}
        
        assert len(dv1_evidence_ids & dv2_evidence_ids) == 0  # No overlap
        
        # Verify all evidence is bound to correct DatasetVersion
        for e in dv1_evidence:
            assert e.dataset_version_id == dv1.id
        
        for e in dv2_evidence:
            assert e.dataset_version_id == dv2.id


@pytest.mark.anyio
async def test_evidence_structure_for_consumption(sqlite_db: None) -> None:
    """Test that evidence structure is suitable for consumption by other engines."""
    install_immutability_guards()
    
    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)
        
        import uuid
        from backend.app.core.dataset.raw_models import RawRecord
        
        raw_id = str(uuid.uuid4())
        db.add(
            RawRecord(
                raw_record_id=raw_id,
                dataset_version_id=dv.id,
                source_system="test",
                source_record_id="test-1",
                payload={
                    "financial": {
                        "debt": {
                            "total_outstanding": 1_000_000,
                            "interest_rate_pct": 5.0,
                            "collateral_value": 750_000,
                        },
                        "assets": {"total": 2_000_000},
                    },
                    "distressed_assets": [
                        {"value": 200_000, "recovery_rate_pct": 35},
                        {"value": 150_000, "recovery_rate_pct": 50},
                    ],
                },
                ingested_at=datetime.now(timezone.utc),
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
                    "financial": {
                        "debt": {
                            "total_outstanding": 1_000_000,
                            "interest_rate_pct": 5.0,
                            "collateral_value": 750_000,
                        },
                        "assets": {"total": 2_000_000},
                    },
                    "distressed_assets": [
                        {"value": 200_000, "recovery_rate_pct": 35},
                        {"value": 150_000, "recovery_rate_pct": 50},
                    ],
                },
                normalized_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()
    
    # Run engine
    started = datetime.now(timezone.utc)
    result = await run_engine(
        dataset_version_id=dv.id,
        started_at=started.isoformat(),
    )
    
    # Verify evidence structure
    async with get_sessionmaker()() as db:
        evidence = await get_evidence_by_dataset_version(
            db,
            dataset_version_id=dv.id,
            engine_id=ENGINE_ID,
        )
        
        # Verify debt_exposure evidence structure
        debt_evidence = [e for e in evidence if e.kind == "debt_exposure"][0]
        debt_payload = debt_evidence.payload
        
        # Required fields for consumption
        assert "debt_exposure" in debt_payload
        assert "normalized_record_id" in debt_payload
        assert "raw_record_id" in debt_payload
        assert "assumptions" in debt_payload
        
        debt_data = debt_payload["debt_exposure"]
        required_fields = [
            "total_outstanding",
            "interest_rate_pct",
            "interest_payment",
            "collateral_value",
            "net_exposure_after_recovery",
            "distressed_asset_value",
            "distressed_asset_recovery",
        ]
        
        for field in required_fields:
            assert field in debt_data, f"Missing required field: {field}"
        
        # Verify stress_test evidence structure
        stress_evidence = [e for e in evidence if e.kind == "stress_test"]
        assert len(stress_evidence) == 3
        
        for stress_ev in stress_evidence:
            stress_payload = stress_ev.payload
            assert "stress_test" in stress_payload
            assert "normalized_record_id" in stress_payload
            assert "raw_record_id" in stress_payload
            assert "assumptions" in stress_payload
            
            stress_data = stress_payload["stress_test"]
            required_stress_fields = [
                "scenario_id",
                "loss_estimate",
                "impact_score",
                "interest_payment",
                "collateral_loss",
                "default_risk_buffer",
            ]
            
            for field in required_stress_fields:
                assert field in stress_data, f"Missing required field in stress_test: {field}"

