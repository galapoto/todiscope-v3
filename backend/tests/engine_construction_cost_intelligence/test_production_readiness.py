"""
Production Readiness Tests: Construction Cost Intelligence Engine

Final validation tests to ensure the engine is ready for production deployment.
Tests include platform integration, data persistence, traceability, and performance.
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select

from backend.app.core.dataset.models import DatasetVersion
from backend.app.core.dataset.raw_models import RawRecord
from backend.app.core.dataset.uuidv7 import uuid7
from backend.app.core.db import get_sessionmaker
from backend.app.core.evidence.models import EvidenceRecord, FindingEvidenceLink, FindingRecord
from backend.app.core.engine_registry.registry import REGISTRY
from backend.app.engines.construction_cost_intelligence.compare import compare_boq_to_actuals
from backend.app.engines.construction_cost_intelligence.models import (
    ComparisonConfig,
    NormalizationMapping,
    normalize_cost_lines,
)
from backend.app.engines.construction_cost_intelligence.report.assembler import assemble_report
from backend.app.engines.construction_cost_intelligence.run import run_engine


@pytest.fixture
def sample_dataset_version_id() -> str:
    return str(uuid7())


@pytest.fixture
def sample_run_id() -> str:
    return f"run-{uuid7()}"


@pytest.mark.anyio
async def test_engine_registration_production_ready() -> None:
    """Verify engine is properly registered and accessible."""
    from backend.app.engines import register_all_engines
    
    register_all_engines()
    
    engine_spec = REGISTRY.get("engine_construction_cost_intelligence")
    assert engine_spec is not None, "Engine must be registered"
    assert engine_spec.engine_id == "engine_construction_cost_intelligence"
    assert engine_spec.engine_version == "v1"
    assert len(engine_spec.routers) > 0, "Engine must have routers"
    assert engine_spec.routers[0].prefix == "/api/v3/engines/cost-intelligence"


@pytest.mark.anyio
async def test_kill_switch_operational() -> None:
    """Verify kill-switch functionality works correctly."""
    from backend.app.core.config import get_settings
    from backend.app.core.engine_registry.kill_switch import is_engine_enabled
    
    # Test with engine disabled
    with pytest.MonkeyPatch().context() as m:
        m.setenv("TODISCOPE_ENABLED_ENGINES", "")
        # Reload settings
        settings = get_settings()
        assert "engine_construction_cost_intelligence" not in settings.enabled_engines
        assert not is_engine_enabled("engine_construction_cost_intelligence")
    
    # Test with engine enabled
    with pytest.MonkeyPatch().context() as m:
        m.setenv("TODISCOPE_ENABLED_ENGINES", "engine_construction_cost_intelligence")
        settings = get_settings()
        assert "engine_construction_cost_intelligence" in settings.enabled_engines
        assert is_engine_enabled("engine_construction_cost_intelligence")


@pytest.mark.anyio
async def test_production_data_flow_end_to_end(
    sqlite_db: None, sample_dataset_version_id: str, sample_run_id: str
) -> None:
    """Test complete production data flow with realistic data volumes."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        # Create DatasetVersion
        dv = DatasetVersion(id=sample_dataset_version_id)
        db.add(dv)
        await db.flush()
        
        # Create realistic production data (50 BOQ items, 55 actual items)
        now = datetime.now(timezone.utc)
        boq_lines_data = [
            {
                "line_id": f"boq-{i:03d}",
                "item_code": f"ITEM{i:03d}",
                "total_cost": str(10000 + i * 100),
                "category": "Materials" if i % 2 == 0 else "Labor",
            }
            for i in range(1, 51)
        ]
        
        actual_lines_data = [
            {
                "line_id": f"actual-{i:03d}",
                "item_code": f"ITEM{i:03d}" if i <= 50 else f"ITEM{i+900:03d}",  # Some unmatched for scope creep
                "total_cost": str(10500 + i * 100 + (i % 10) * 50),  # Add variance
                "category": "Materials" if i % 2 == 0 else "Labor",
                "date_recorded": f"2024-{(i % 12) + 1:02d}-15T00:00:00",
            }
            for i in range(1, 56)
        ]
        
        boq_raw = RawRecord(
            raw_record_id="boq-raw-prod-001",
            dataset_version_id=sample_dataset_version_id,
            source_system="production_system",
            source_record_id="boq-source-prod-001",
            payload={"lines": boq_lines_data},
            ingested_at=now,
        )
        
        actual_raw = RawRecord(
            raw_record_id="actual-raw-prod-001",
            dataset_version_id=sample_dataset_version_id,
            source_system="production_system",
            source_record_id="actual-source-prod-001",
            payload={"lines": actual_lines_data},
            ingested_at=now,
        )
        
        db.add(boq_raw)
        db.add(actual_raw)
        await db.flush()
        
        # Run core engine
        started_at = datetime.now(timezone.utc).isoformat()
        result = await run_engine(
            dataset_version_id=sample_dataset_version_id,
            started_at=started_at,
            boq_raw_record_id="boq-raw-prod-001",
            actual_raw_record_id="actual-raw-prod-001",
            normalization_mapping={
                "line_id": "line_id",
                "identity": {"item_code": "item_code"},
                "total_cost": "total_cost",
                "extras": ["category"],
            },
            comparison_config={
                "identity_fields": ["item_code"],
                "cost_basis": "prefer_total_cost",
                "breakdown_fields": [],
            },
        )
        
        await db.commit()
        
        # Verify core traceability
        assert result["dataset_version_id"] == sample_dataset_version_id
        assert "traceability" in result
        traceability = result["traceability"]
        assert "assumptions_evidence_id" in traceability
        assert len(traceability["inputs_evidence_ids"]) == 2
        
        # Generate variance report with findings
        cfg = ComparisonConfig(identity_fields=("item_code",))
        boq_lines = normalize_cost_lines(
            dataset_version_id=sample_dataset_version_id,
            kind="boq",
            raw_lines=boq_lines_data,
            mapping=NormalizationMapping(
                line_id="line_id",
                identity={"item_code": "item_code"},
                total_cost="total_cost",
                extras=("category",),
            ),
        )
        actual_lines = normalize_cost_lines(
            dataset_version_id=sample_dataset_version_id,
            kind="actual",
            raw_lines=actual_lines_data,
            mapping=NormalizationMapping(
                line_id="line_id",
                identity={"item_code": "item_code"},
                total_cost="total_cost",
                extras=("category",),
            ),
        )
        
        comparison_result = compare_boq_to_actuals(
            dataset_version_id=sample_dataset_version_id,
            boq_lines=boq_lines,
            actual_lines=actual_lines,
            config=cfg,
        )
        
        report = await assemble_report(
            db=db,
            dataset_version_id=sample_dataset_version_id,
            run_id=sample_run_id,
            report_type="cost_variance",
            parameters={
                "comparison_result": comparison_result,
                "boq_raw_record_id": "boq-raw-prod-001",
                "actual_raw_record_id": "actual-raw-prod-001",
                "persist_findings": True,
            },
            created_at=datetime.now(timezone.utc),
            emit_evidence=True,
        )
        
        await db.commit()
        
        # Verify findings persisted
        findings = (
            await db.execute(
                select(FindingRecord).where(FindingRecord.dataset_version_id == sample_dataset_version_id)
            )
        ).scalars().all()
        
        assert len(findings) > 0, "Should have persisted findings from production data"
        
        # Verify evidence linkage
        for finding in findings[:10]:  # Check first 10 findings
            links = (
                await db.execute(
                    select(FindingEvidenceLink).where(FindingEvidenceLink.finding_id == finding.finding_id)
                )
            ).scalars().all()
            assert len(links) > 0, "All findings should be linked to evidence"


@pytest.mark.anyio
async def test_dataset_version_isolation_production_scale(
    sqlite_db: None, sample_dataset_version_id: str
) -> None:
    """Test DatasetVersion isolation with production-scale data."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        # Create multiple DatasetVersions
        dv1 = DatasetVersion(id=sample_dataset_version_id)
        dv2_id = str(uuid7())
        dv2 = DatasetVersion(id=dv2_id)
        dv3_id = str(uuid7())
        dv3 = DatasetVersion(id=dv3_id)
        
        db.add(dv1)
        db.add(dv2)
        db.add(dv3)
        await db.flush()
        
        now = datetime.now(timezone.utc)
        
        # Create RawRecords for each DatasetVersion
        for i, dv_id in enumerate([sample_dataset_version_id, dv2_id, dv3_id], 1):
            boq_raw = RawRecord(
                raw_record_id=f"boq-raw-dv{i}",
                dataset_version_id=dv_id,
                source_system="test_system",
                source_record_id=f"boq-source-dv{i}",
                payload={
                    "lines": [
                        {
                            "line_id": f"boq-dv{i}-1",
                            "item_code": f"ITEM-DV{i}-001",
                            "total_cost": "10000.00",
                        }
                    ]
                },
                ingested_at=now,
            )
            actual_raw = RawRecord(
                raw_record_id=f"actual-raw-dv{i}",
                dataset_version_id=dv_id,
                source_system="test_system",
                source_record_id=f"actual-source-dv{i}",
                payload={
                    "lines": [
                        {
                            "line_id": f"actual-dv{i}-1",
                            "item_code": f"ITEM-DV{i}-001",
                            "total_cost": "10500.00",
                        }
                    ]
                },
                ingested_at=now,
            )
            
            db.add(boq_raw)
            db.add(actual_raw)
        
        await db.flush()
        
        # Run engine for each DatasetVersion
        started_at = datetime.now(timezone.utc).isoformat()
        for i, dv_id in enumerate([sample_dataset_version_id, dv2_id, dv3_id], 1):
            result = await run_engine(
                dataset_version_id=dv_id,
                started_at=started_at,
                boq_raw_record_id=f"boq-raw-dv{i}",
                actual_raw_record_id=f"actual-raw-dv{i}",
                normalization_mapping={
                    "line_id": "line_id",
                    "identity": {"item_code": "item_code"},
                    "total_cost": "total_cost",
                },
                comparison_config={
                    "identity_fields": ["item_code"],
                    "cost_basis": "prefer_total_cost",
                },
            )
            assert result["dataset_version_id"] == dv_id
        
        await db.commit()
        
        # Verify isolation
        for dv_id in [sample_dataset_version_id, dv2_id, dv3_id]:
            evidence = (
                await db.execute(select(EvidenceRecord).where(EvidenceRecord.dataset_version_id == dv_id))
            ).scalars().all()
            
            assert len(evidence) > 0, f"DatasetVersion {dv_id} should have evidence"
            
            for ev in evidence:
                assert ev.dataset_version_id == dv_id, "Evidence should belong to correct DatasetVersion"
                assert ev.dataset_version_id not in [
                    x for x in [sample_dataset_version_id, dv2_id, dv3_id] if x != dv_id
                ], "Evidence should not belong to other DatasetVersions"


@pytest.mark.anyio
async def test_finding_persistence_production_scale(
    sqlite_db: None, sample_dataset_version_id: str, sample_run_id: str
) -> None:
    """Test finding persistence with production-scale variance data."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        # Create DatasetVersion
        dv = DatasetVersion(id=sample_dataset_version_id)
        db.add(dv)
        await db.flush()
        
        # Create data with many variances
        now = datetime.now(timezone.utc)
        boq_lines_data = [
            {
                "line_id": f"boq-{i:03d}",
                "item_code": f"ITEM{i:03d}",
                "total_cost": str(10000 + i * 100),
            }
            for i in range(1, 31)
        ]
        
        actual_lines_data = [
            {
                "line_id": f"actual-{i:03d}",
                "item_code": f"ITEM{i:03d}",
                "total_cost": str(10500 + i * 100 + (i % 5) * 200),  # Create variances
            }
            for i in range(1, 31)
        ] + [
            {
                "line_id": f"actual-creep-{i}",
                "item_code": f"ITEM{900+i:03d}",  # Scope creep
                "total_cost": str(5000 + i * 100),
            }
            for i in range(1, 6)
        ]
        
        boq_raw = RawRecord(
            raw_record_id="boq-raw-scale-001",
            dataset_version_id=sample_dataset_version_id,
            source_system="test_system",
            source_record_id="boq-source-scale-001",
            payload={"lines": boq_lines_data},
            ingested_at=now,
        )
        
        actual_raw = RawRecord(
            raw_record_id="actual-raw-scale-001",
            dataset_version_id=sample_dataset_version_id,
            source_system="test_system",
            source_record_id="actual-source-scale-001",
            payload={"lines": actual_lines_data},
            ingested_at=now,
        )
        
        db.add(boq_raw)
        db.add(actual_raw)
        await db.flush()
        
        # Generate report with findings
        cfg = ComparisonConfig(identity_fields=("item_code",))
        boq_lines = normalize_cost_lines(
            dataset_version_id=sample_dataset_version_id,
            kind="boq",
            raw_lines=boq_lines_data,
            mapping=NormalizationMapping(
                line_id="line_id",
                identity={"item_code": "item_code"},
                total_cost="total_cost",
            ),
        )
        actual_lines = normalize_cost_lines(
            dataset_version_id=sample_dataset_version_id,
            kind="actual",
            raw_lines=actual_lines_data,
            mapping=NormalizationMapping(
                line_id="line_id",
                identity={"item_code": "item_code"},
                total_cost="total_cost",
            ),
        )
        
        comparison_result = compare_boq_to_actuals(
            dataset_version_id=sample_dataset_version_id,
            boq_lines=boq_lines,
            actual_lines=actual_lines,
            config=cfg,
        )
        
        report = await assemble_report(
            db=db,
            dataset_version_id=sample_dataset_version_id,
            run_id=sample_run_id,
            report_type="cost_variance",
            parameters={
                "comparison_result": comparison_result,
                "boq_raw_record_id": "boq-raw-scale-001",
                "actual_raw_record_id": "actual-raw-scale-001",
                "persist_findings": True,
            },
            created_at=datetime.now(timezone.utc),
            emit_evidence=True,
        )
        
        await db.commit()
        
        # Verify findings persisted at scale
        variance_findings = (
            await db.execute(
                select(FindingRecord)
                .where(FindingRecord.dataset_version_id == sample_dataset_version_id)
                .where(FindingRecord.kind == "cost_variance")
            )
        ).scalars().all()
        
        scope_creep_findings = (
            await db.execute(
                select(FindingRecord)
                .where(FindingRecord.dataset_version_id == sample_dataset_version_id)
                .where(FindingRecord.kind == "scope_creep")
            )
        ).scalars().all()
        
        assert len(variance_findings) >= 30, "Should have variance findings for matched items"
        assert len(scope_creep_findings) >= 5, "Should have scope creep findings"
        
        # Verify all findings have evidence links
        all_findings = variance_findings + scope_creep_findings
        for finding in all_findings:
            links = (
                await db.execute(
                    select(FindingEvidenceLink).where(FindingEvidenceLink.finding_id == finding.finding_id)
                )
            ).scalars().all()
            assert len(links) > 0, "All findings must have evidence links"


@pytest.mark.anyio
async def test_time_phased_findings_production_scale(
    sqlite_db: None, sample_dataset_version_id: str, sample_run_id: str
) -> None:
    """Test time-phased findings with production-scale data across multiple periods."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        # Create DatasetVersion
        dv = DatasetVersion(id=sample_dataset_version_id)
        db.add(dv)
        await db.flush()
        
        # Create data across 12 months with varying variance
        cost_lines = []
        for month in range(1, 13):
            for day in [1, 15]:  # 2 entries per month
                # BOQ line
                cost_lines.append(
                    {
                        "line_id": f"boq-{month:02d}-{day:02d}",
                        "item_code": f"ITEM{month:02d}{day:02d}",
                        "total_cost": "10000.00",
                        "kind": "boq",
                        "date_recorded": f"2024-{month:02d}-{day:02d}T00:00:00",
                    }
                )
                # Actual line with significant variance (>25%) for some months
                variance_pct = 30.0 if month % 2 == 0 else 5.0  # Even months have high variance
                actual_cost = Decimal("10000.00") * (1 + Decimal(str(variance_pct)) / 100)
                cost_lines.append(
                    {
                        "line_id": f"actual-{month:02d}-{day:02d}",
                        "item_code": f"ITEM{month:02d}{day:02d}",
                        "total_cost": str(actual_cost),
                        "kind": "actual",
                        "date_recorded": f"2024-{month:02d}-{day:02d}T00:00:00",
                    }
                )
        
        # Convert to CostLine objects
        from backend.app.engines.construction_cost_intelligence.models import CostLine
        
        cost_line_objects = []
        for line_data in cost_lines:
            kind = line_data.pop("kind")
            cost_line_objects.append(
                CostLine(
                    dataset_version_id=sample_dataset_version_id,
                    kind=kind,
                    line_id=line_data["line_id"],
                    identity={"item_code": line_data["item_code"]},
                    total_cost=Decimal(line_data["total_cost"]),
                    attributes={"date_recorded": line_data["date_recorded"]},
                )
            )
        
        # Generate time-phased report
        report = await assemble_report(
            db=db,
            dataset_version_id=sample_dataset_version_id,
            run_id=sample_run_id,
            report_type="time_phased",
            parameters={
                "cost_lines": cost_line_objects,
                "period_type": "monthly",
                "raw_record_id": "raw-time-phased-001",
                "persist_findings": True,
            },
            created_at=datetime.now(timezone.utc),
            emit_evidence=True,
        )
        
        await db.commit()
        
        # Verify time-phased findings persisted (only periods with >25% variance)
        time_phased_findings = (
            await db.execute(
                select(FindingRecord)
                .where(FindingRecord.dataset_version_id == sample_dataset_version_id)
                .where(FindingRecord.kind == "time_phased_variance")
            )
        ).scalars().all()
        
        # Should have findings for even months (30% variance)
        assert len(time_phased_findings) >= 6, "Should have findings for months with >25% variance"
        
        # Verify all findings have evidence links
        for finding in time_phased_findings:
            links = (
                await db.execute(
                    select(FindingEvidenceLink).where(FindingEvidenceLink.finding_id == finding.finding_id)
                )
            ).scalars().all()
            assert len(links) > 0, "All time-phased findings must have evidence links"


@pytest.mark.anyio
async def test_performance_with_realistic_load(
    sqlite_db: None, sample_dataset_version_id: str, sample_run_id: str
) -> None:
    """Test engine performance with realistic production load."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        # Create DatasetVersion
        dv = DatasetVersion(id=sample_dataset_version_id)
        db.add(dv)
        await db.flush()
        
        # Create realistic production dataset (100 BOQ, 105 actual)
        now = datetime.now(timezone.utc)
        boq_lines_data = [
            {
                "line_id": f"boq-{i:03d}",
                "item_code": f"ITEM{i:03d}",
                "total_cost": str(10000 + i * 100),
                "category": "Materials" if i % 2 == 0 else "Labor",
            }
            for i in range(1, 101)
        ]
        
        actual_lines_data = [
            {
                "line_id": f"actual-{i:03d}",
                "item_code": f"ITEM{i:03d}",
                "total_cost": str(10500 + i * 100 + (i % 10) * 50),
                "category": "Materials" if i % 2 == 0 else "Labor",
            }
            for i in range(1, 101)
        ] + [
            {
                "line_id": f"actual-creep-{i}",
                "item_code": f"ITEM{900+i:03d}",
                "total_cost": str(5000 + i * 100),
                "category": "Unexpected",
            }
            for i in range(1, 6)
        ]
        
        boq_raw = RawRecord(
            raw_record_id="boq-raw-perf-001",
            dataset_version_id=sample_dataset_version_id,
            source_system="test_system",
            source_record_id="boq-source-perf-001",
            payload={"lines": boq_lines_data},
            ingested_at=now,
        )
        
        actual_raw = RawRecord(
            raw_record_id="actual-raw-perf-001",
            dataset_version_id=sample_dataset_version_id,
            source_system="test_system",
            source_record_id="actual-source-perf-001",
            payload={"lines": actual_lines_data},
            ingested_at=now,
        )
        
        db.add(boq_raw)
        db.add(actual_raw)
        await db.flush()
        
        # Measure performance
        start_time = time.time()
        
        # Run core engine
        started_at = datetime.now(timezone.utc).isoformat()
        result = await run_engine(
            dataset_version_id=sample_dataset_version_id,
            started_at=started_at,
            boq_raw_record_id="boq-raw-perf-001",
            actual_raw_record_id="actual-raw-perf-001",
            normalization_mapping={
                "line_id": "line_id",
                "identity": {"item_code": "item_code"},
                "total_cost": "total_cost",
                "extras": ["category"],
            },
            comparison_config={
                "identity_fields": ["item_code"],
                "cost_basis": "prefer_total_cost",
                "breakdown_fields": [],
            },
        )
        
        engine_time = time.time() - start_time
        
        # Generate report with findings
        report_start = time.time()
        
        cfg = ComparisonConfig(identity_fields=("item_code",))
        boq_lines = normalize_cost_lines(
            dataset_version_id=sample_dataset_version_id,
            kind="boq",
            raw_lines=boq_lines_data,
            mapping=NormalizationMapping(
                line_id="line_id",
                identity={"item_code": "item_code"},
                total_cost="total_cost",
                extras=("category",),
            ),
        )
        actual_lines = normalize_cost_lines(
            dataset_version_id=sample_dataset_version_id,
            kind="actual",
            raw_lines=actual_lines_data,
            mapping=NormalizationMapping(
                line_id="line_id",
                identity={"item_code": "item_code"},
                total_cost="total_cost",
                extras=("category",),
            ),
        )
        
        comparison_result = compare_boq_to_actuals(
            dataset_version_id=sample_dataset_version_id,
            boq_lines=boq_lines,
            actual_lines=actual_lines,
            config=cfg,
        )
        
        report = await assemble_report(
            db=db,
            dataset_version_id=sample_dataset_version_id,
            run_id=sample_run_id,
            report_type="cost_variance",
            parameters={
                "comparison_result": comparison_result,
                "boq_raw_record_id": "boq-raw-perf-001",
                "actual_raw_record_id": "actual-raw-perf-001",
                "persist_findings": True,
            },
            created_at=datetime.now(timezone.utc),
            emit_evidence=True,
        )
        
        report_time = time.time() - report_start
        total_time = time.time() - start_time
        
        await db.commit()
        
        # Performance assertions (should complete in reasonable time)
        assert engine_time < 5.0, f"Engine run should complete in <5s, took {engine_time:.2f}s"
        assert report_time < 5.0, f"Report generation should complete in <5s, took {report_time:.2f}s"
        assert total_time < 10.0, f"Total processing should complete in <10s, took {total_time:.2f}s"
        
        # Verify results
        findings = (
            await db.execute(
                select(FindingRecord).where(FindingRecord.dataset_version_id == sample_dataset_version_id)
            )
        ).scalars().all()
        
        assert len(findings) >= 100, "Should have persisted findings for all variances"


@pytest.mark.anyio
async def test_zero_downtime_deployment_simulation() -> None:
    """Simulate zero-downtime deployment scenario."""
    from backend.app.core.engine_registry.kill_switch import is_engine_enabled
    
    # Simulate: Engine disabled initially
    with pytest.MonkeyPatch().context() as m:
        m.setenv("TODISCOPE_ENABLED_ENGINES", "")
        assert not is_engine_enabled("engine_construction_cost_intelligence")
    
    # Simulate: Engine enabled after deployment
    with pytest.MonkeyPatch().context() as m:
        m.setenv("TODISCOPE_ENABLED_ENGINES", "engine_construction_cost_intelligence")
        assert is_engine_enabled("engine_construction_cost_intelligence")
    
    # Verify: Engine can be disabled without breaking platform
    with pytest.MonkeyPatch().context() as m:
        m.setenv("TODISCOPE_ENABLED_ENGINES", "")
        assert not is_engine_enabled("engine_construction_cost_intelligence")
        # Platform core functionality should still work
        from backend.app.core.config import get_settings
        settings = get_settings()
        assert settings is not None  # Platform still functional


@pytest.mark.anyio
async def test_complete_traceability_production_scale(
    sqlite_db: None, sample_dataset_version_id: str, sample_run_id: str
) -> None:
    """Verify complete traceability with production-scale data."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        # Create DatasetVersion
        dv = DatasetVersion(id=sample_dataset_version_id)
        db.add(dv)
        await db.flush()
        
        # Create production data
        now = datetime.now(timezone.utc)
        boq_raw = RawRecord(
            raw_record_id="boq-raw-trace-001",
            dataset_version_id=sample_dataset_version_id,
            source_system="test_system",
            source_record_id="boq-source-trace-001",
            payload={
                "lines": [
                    {"line_id": "boq-1", "item_code": "ITEM001", "total_cost": "10000.00"},
                    {"line_id": "boq-2", "item_code": "ITEM002", "total_cost": "20000.00"},
                ]
            },
            ingested_at=now,
        )
        
        actual_raw = RawRecord(
            raw_record_id="actual-raw-trace-001",
            dataset_version_id=sample_dataset_version_id,
            source_system="test_system",
            source_record_id="actual-source-trace-001",
            payload={
                "lines": [
                    {"line_id": "actual-1", "item_code": "ITEM001", "total_cost": "10500.00"},
                    {"line_id": "actual-2", "item_code": "ITEM002", "total_cost": "22000.00"},
                    {"line_id": "actual-3", "item_code": "ITEM999", "total_cost": "5000.00"},  # Scope creep
                ]
            },
            ingested_at=now,
        )
        
        db.add(boq_raw)
        db.add(actual_raw)
        await db.flush()
        
        # Run engine and generate report
        started_at = datetime.now(timezone.utc).isoformat()
        await run_engine(
            dataset_version_id=sample_dataset_version_id,
            started_at=started_at,
            boq_raw_record_id="boq-raw-trace-001",
            actual_raw_record_id="actual-raw-trace-001",
            normalization_mapping={
                "line_id": "line_id",
                "identity": {"item_code": "item_code"},
                "total_cost": "total_cost",
            },
            comparison_config={
                "identity_fields": ["item_code"],
                "cost_basis": "prefer_total_cost",
            },
        )
        
        cfg = ComparisonConfig(identity_fields=("item_code",))
        boq_lines = normalize_cost_lines(
            dataset_version_id=sample_dataset_version_id,
            kind="boq",
            raw_lines=boq_raw.payload["lines"],
            mapping=NormalizationMapping(
                line_id="line_id",
                identity={"item_code": "item_code"},
                total_cost="total_cost",
            ),
        )
        actual_lines = normalize_cost_lines(
            dataset_version_id=sample_dataset_version_id,
            kind="actual",
            raw_lines=actual_raw.payload["lines"],
            mapping=NormalizationMapping(
                line_id="line_id",
                identity={"item_code": "item_code"},
                total_cost="total_cost",
            ),
        )
        
        comparison_result = compare_boq_to_actuals(
            dataset_version_id=sample_dataset_version_id,
            boq_lines=boq_lines,
            actual_lines=actual_lines,
            config=cfg,
        )
        
        report = await assemble_report(
            db=db,
            dataset_version_id=sample_dataset_version_id,
            run_id=sample_run_id,
            report_type="cost_variance",
            parameters={
                "comparison_result": comparison_result,
                "boq_raw_record_id": "boq-raw-trace-001",
                "actual_raw_record_id": "actual-raw-trace-001",
                "persist_findings": True,
            },
            created_at=datetime.now(timezone.utc),
            emit_evidence=True,
        )
        
        await db.commit()
        
        # Verify complete traceability chain for all findings
        findings = (
            await db.execute(
                select(FindingRecord).where(FindingRecord.dataset_version_id == sample_dataset_version_id)
            )
        ).scalars().all()
        
        assert len(findings) > 0, "Should have findings"
        
        for finding in findings:
            # 1. Finding → RawRecord
            raw_record = await db.scalar(
                select(RawRecord).where(RawRecord.raw_record_id == finding.raw_record_id)
            )
            assert raw_record is not None, "RawRecord should exist"
            assert raw_record.dataset_version_id == sample_dataset_version_id, (
                "RawRecord should belong to DatasetVersion"
            )
            
            # 2. Finding → Evidence
            links = (
                await db.execute(
                    select(FindingEvidenceLink).where(FindingEvidenceLink.finding_id == finding.finding_id)
                )
            ).scalars().all()
            assert len(links) > 0, "Finding should be linked to evidence"
            
            # 3. Evidence → DatasetVersion
            for link in links:
                evidence = await db.scalar(
                    select(EvidenceRecord).where(EvidenceRecord.evidence_id == link.evidence_id)
                )
                assert evidence is not None, "Evidence should exist"
                assert evidence.dataset_version_id == sample_dataset_version_id, (
                    "Evidence should belong to DatasetVersion"
                )
                assert evidence.dataset_version_id == finding.dataset_version_id, (
                    "Evidence and Finding should have same DatasetVersion"
                )


