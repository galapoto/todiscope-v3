"""
End-to-end tests for Enterprise Distressed Asset & Debt Stress Engine.

Tests the complete workflow from data ingestion through stress testing to reporting.
Verifies traceability, DatasetVersion binding, and immutability throughout.
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
    verify_evidence_traceability,
)
from backend.app.core.evidence.models import EvidenceRecord, FindingEvidenceLink, FindingRecord
from backend.app.core.normalization.models import NormalizedRecord
from backend.app.core.db import get_sessionmaker
from backend.app.engines.enterprise_distressed_asset_debt_stress.run import run_engine
from backend.app.engines.enterprise_distressed_asset_debt_stress.constants import ENGINE_ID


@pytest.mark.anyio
async def test_end_to_end_workflow(sqlite_db: None) -> None:
    """Test complete end-to-end workflow from ingestion to reporting."""
    install_immutability_guards()
    
    # Step 1: Create DatasetVersion and ingest data
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
                        {"name": "Asset A", "value": 200_000, "recovery_rate_pct": 35},
                        {"name": "Asset B", "value": 150_000, "recovery_rate_pct": 50},
                    ],
                },
                ingested_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()
        
        # Step 2: Normalize data
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
                        {"name": "Asset A", "value": 200_000, "recovery_rate_pct": 35},
                        {"name": "Asset B", "value": 150_000, "recovery_rate_pct": 50},
                    ],
                },
                normalized_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()
    
    # Step 3: Run engine
    started = datetime.now(timezone.utc)
    result = await run_engine(
        dataset_version_id=dv.id,
        started_at=started.isoformat(),
    )
    
    # Step 4: Verify results
    assert result["dataset_version_id"] == dv.id
    assert "debt_exposure_evidence_id" in result
    assert "stress_test_evidence_ids" in result
    assert len(result["stress_test_evidence_ids"]) == 3
    assert "material_findings" in result
    assert len(result["material_findings"]) > 0
    assert "report" in result
    
    # Step 5: Verify evidence traceability
    async with get_sessionmaker()() as db:
        traceability = await verify_evidence_traceability(
            db,
            dataset_version_id=dv.id,
            evidence_ids=[
                result["debt_exposure_evidence_id"],
                *result["stress_test_evidence_ids"].values(),
            ],
        )
        
        assert traceability["valid"] is True
        assert traceability["total_checked"] == 4
        assert len(traceability["mismatches"]) == 0
    
    # Step 6: Verify report structure
    report = result["report"]
    assert "metadata" in report
    assert "debt_exposure" in report
    assert "stress_tests" in report
    assert "assumptions" in report
    
    assert report["metadata"]["dataset_version_id"] == dv.id
    assert report["debt_exposure"]["total_outstanding"] == pytest.approx(1_000_000)
    assert len(report["stress_tests"]) == 3
    
    # Step 7: Verify findings are linked to evidence
    async with get_sessionmaker()() as db:
        findings = await get_findings_by_dataset_version(
            db,
            dataset_version_id=dv.id,
        )
        
        # Filter findings by checking if they're linked to our engine's evidence
        distressed_asset_evidence = await get_evidence_by_dataset_version(
            db,
            dataset_version_id=dv.id,
            engine_id=ENGINE_ID,
        )
        distressed_asset_evidence_ids = {e.evidence_id for e in distressed_asset_evidence}
        distressed_findings = []
        for finding in findings:
            links = (
                await db.scalars(
                    select(FindingEvidenceLink).where(
                        FindingEvidenceLink.finding_id == finding.finding_id
                    )
                )
            ).all()
            if any(link.evidence_id in distressed_asset_evidence_ids for link in links):
                distressed_findings.append(finding)
        assert len(distressed_findings) > 0
        
        # Verify each finding has linked evidence
        for finding in distressed_findings:
            links = (
                await db.scalars(
                    select(FindingEvidenceLink).where(
                        FindingEvidenceLink.finding_id == finding.finding_id
                    )
                )
            ).all()
            
            assert len(links) > 0, f"Finding {finding.finding_id} has no evidence links"


@pytest.mark.anyio
async def test_end_to_end_with_custom_scenarios(sqlite_db: None) -> None:
    """Test end-to-end workflow with custom stress scenarios."""
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
                },
                normalized_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()
    
    # Run engine with custom scenarios
    started = datetime.now(timezone.utc)
    result = await run_engine(
        dataset_version_id=dv.id,
        started_at=started.isoformat(),
        parameters={
            "stress_scenarios": [
                {
                    "scenario_id": "custom_severe",
                    "description": "Custom severe stress scenario",
                    "interest_rate_delta_pct": 5.0,
                    "collateral_market_impact_pct": -0.3,
                    "recovery_degradation_pct": -0.2,
                    "default_risk_increment_pct": 0.1,
                },
            ],
        },
    )
    
    # Verify custom scenario was applied (engine includes defaults + custom)
    assert "custom_severe" in result["stress_test_evidence_ids"]
    assert len(result["stress_test_evidence_ids"]) >= 1
    
    # Verify report includes custom scenario
    report = result["report"]
    assert len(report["stress_tests"]) >= 1
    custom_scenarios = [s for s in report["stress_tests"] if s["scenario_id"] == "custom_severe"]
    assert len(custom_scenarios) == 1
    
    # Verify assumptions document custom scenario
    assumptions = result["assumptions"]
    stress_assumption = [a for a in assumptions if a["id"] == "assumption_stress_scenarios"][0]
    assert "custom_severe" in stress_assumption.get("details", {}).get("override_scenario_ids", [])


@pytest.mark.anyio
async def test_end_to_end_idempotency(sqlite_db: None) -> None:
    """Test that running the engine multiple times with same inputs is idempotent."""
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
                },
                normalized_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()
    
    # Run engine first time
    started = datetime.now(timezone.utc)
    result1 = await run_engine(
        dataset_version_id=dv.id,
        started_at=started.isoformat(),
    )
    
    # Run engine second time with same parameters
    result2 = await run_engine(
        dataset_version_id=dv.id,
        started_at=started.isoformat(),
    )
    
    # Verify idempotency: same evidence IDs
    assert result1["debt_exposure_evidence_id"] == result2["debt_exposure_evidence_id"]
    assert result1["stress_test_evidence_ids"] == result2["stress_test_evidence_ids"]
    
    # Verify findings are the same
    finding_ids1 = {f["id"] for f in result1["material_findings"]}
    finding_ids2 = {f["id"] for f in result2["material_findings"]}
    assert finding_ids1 == finding_ids2
    
    # Verify report data is identical
    assert result1["report"]["debt_exposure"] == result2["report"]["debt_exposure"]
    assert len(result1["report"]["stress_tests"]) == len(result2["report"]["stress_tests"])


@pytest.mark.anyio
async def test_end_to_end_traceability_chain(sqlite_db: None) -> None:
    """Test complete traceability chain from RawRecord to Findings."""
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
    
    # Verify traceability chain
    async with get_sessionmaker()() as db:
        # 1. Verify evidence references normalized_record_id and raw_record_id
        evidence = await get_evidence_by_dataset_version(
            db,
            dataset_version_id=dv.id,
            engine_id=ENGINE_ID,
        )
        
        for ev in evidence:
            assert "normalized_record_id" in ev.payload
            assert "raw_record_id" in ev.payload
            assert ev.payload["raw_record_id"] == raw_id
        
        # 2. Verify findings reference raw_record_id
        findings = await get_findings_by_dataset_version(
            db,
            dataset_version_id=dv.id,
        )
        
        # Filter findings by checking if they're linked to our engine's evidence
        distressed_asset_evidence = await get_evidence_by_dataset_version(
            db,
            dataset_version_id=dv.id,
            engine_id=ENGINE_ID,
        )
        distressed_asset_evidence_ids = {e.evidence_id for e in distressed_asset_evidence}
        distressed_findings = []
        for finding in findings:
            links = (
                await db.scalars(
                    select(FindingEvidenceLink).where(
                        FindingEvidenceLink.finding_id == finding.finding_id
                    )
                )
            ).all()
            if any(link.evidence_id in distressed_asset_evidence_ids for link in links):
                distressed_findings.append(finding)
        for finding in distressed_findings:
            assert finding.raw_record_id == raw_id
            assert finding.dataset_version_id == dv.id
        
        # 3. Verify findings are linked to evidence
        for finding in distressed_findings:
            links = (
                await db.scalars(
                    select(FindingEvidenceLink).where(
                        FindingEvidenceLink.finding_id == finding.finding_id
                    )
                )
            ).all()
            
            assert len(links) > 0
            
            # Verify linked evidence belongs to same DatasetVersion
            for link in links:
                evidence_record = await db.scalar(
                    select(EvidenceRecord).where(EvidenceRecord.evidence_id == link.evidence_id)
                )
                assert evidence_record is not None
                assert evidence_record.dataset_version_id == dv.id
        
        # 4. Verify report includes traceability metadata
        report = result["report"]
        assert report["metadata"]["raw_record_id"] == raw_id
        assert report["metadata"]["normalized_record_id"] == norm_id
        assert report["metadata"]["dataset_version_id"] == dv.id

