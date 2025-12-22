from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text

from backend.app.core.db import get_sessionmaker
from backend.app.core.engine_registry.registry import REGISTRY
from backend.app.core.engine_registry.spec import EngineSpec
from backend.app.core.evidence.models import EvidenceRecord, FindingEvidenceLink, FindingRecord
from backend.app.core.dataset.models import DatasetVersion
from backend.app.core.dataset.raw_models import RawRecord
from backend.app.main import create_app

# Test data directory
TEST_DATA_DIR = Path(__file__).parent / "test_data"


def load_test_data(filename: str) -> Dict[str, Any]:
    """Load test data from a JSON file in the test_data directory."""
    with open(TEST_DATA_DIR / filename, 'r') as f:
        return json.load(f)


def _sample_record(
    record_id: str = "r1",
    scope1: float = 1000,
    scope2: float = 2000,
    scope3: float = 5000,
    revenue: float = 100000000,
    board_diversity: float = 0.2,
    has_esg_committee: bool = True,
    renewable_pct: float = 30.0,
    **kwargs,
) -> Dict[str, Any]:
    """Generate a sample record with configurable parameters.
    
    Args:
        record_id: Unique identifier for the record
        scope1: Scope 1 emissions in tCO2e
        scope2: Scope 2 emissions in tCO2e
        scope3: Scope 3 emissions in tCO2e
        revenue: Annual revenue in EUR
        board_diversity: Ratio of women on the board (0-1)
        has_esg_committee: Whether the company has an ESG committee
        renewable_pct: Percentage of energy from renewable sources
        
    Returns:
        A dictionary representing a sample record
    """
    return {
        "source_system": "test",
        "source_record_id": record_id,
        "esg": {
            "emissions": {
                "scope1": scope1,
                "scope2": scope2,
                "scope3": scope3,
            },
            "energy_consumption": {
                "renewable": renewable_pct,
                "non_renewable": 100.0 - renewable_pct,
            },
            "governance": {
                "board_diversity": board_diversity,
                "esg_committee": has_esg_committee,
            },
        },
        "financial": {
            "revenue": revenue,
            "operating_costs": revenue * 0.8,  # 80% of revenue
            "profit": revenue * 0.2,  # 20% of revenue
            "assets": revenue * 5,  # 5x revenue
        },
    }


def _validate_report_structure(report: Dict[str, Any], dataset_version_id: str) -> None:
    """Validate the structure and required fields of a CSRD report.
    
    Args:
        report: The report dictionary to validate
        dataset_version_id: Expected dataset version ID
    """
    # Check top-level structure
    required_sections = [
        "metadata",
        "executive_summary",
        "materiality_assessment",
        "data_integrity",
        "compliance_summary",
        "emission_calculations",
        "assumptions"
    ]
    
    for section in required_sections:
        assert section in report, f"Missing required section: {section}"
    
    # Validate metadata
    assert report["metadata"]["dataset_version_id"] == dataset_version_id
    assert "generated_at" in report["metadata"]
    
    # Validate materiality assessment
    materiality = report["materiality_assessment"]
    assert "material_topics" in materiality
    assert isinstance(materiality["material_topics"], list)
    
    # Validate emission calculations
    emissions = report["emission_calculations"]
    assert "total_emissions_tco2e" in emissions
    assert "scopes" in emissions
    assert all(scope in emissions["scopes"] for scope in ["scope1", "scope2", "scope3"])
    
    # Validate assumptions
    assert isinstance(report["assumptions"], list)
    for assumption in report["assumptions"]:
        assert all(field in assumption for field in ["id", "description", "impact"])


@pytest.mark.anyio
async def test_csrd_run_generates_report_and_traceability(sqlite_db: None) -> None:
    os.environ["TODISCOPE_ENABLED_ENGINES"] = "engine_csrd"
    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ingest_res = await ac.post("/api/v3/ingest-records", json={"records": [_sample_record()]})
        assert ingest_res.status_code == 200
        dv_id = ingest_res.json()["dataset_version_id"]

        started_at = "2025-01-01T00:00:00+00:00"
        run_res = await ac.post(
            "/api/v3/engines/csrd/run",
            json={"dataset_version_id": dv_id, "started_at": started_at, "parameters": {"carbon_price_eur_per_tco2e": 100}},
        )
        assert run_res.status_code == 200
        body = run_res.json()

    # Validate response structure
    assert body["dataset_version_id"] == dv_id
    assert "report" in body
    assert "material_findings" in body
    
    # Validate report structure
    report = body["report"]
    _validate_report_structure(report, dv_id)
    
    # Validate material findings
    assert isinstance(body["material_findings"], list)
    for finding in body["material_findings"]:
        assert all(field in finding for field in ["id", "title", "description", "materiality"])
        assert finding["materiality"] in ["material", "not_material"]

    # Evidence + finding linkage persisted in core tables.
    emissions_evidence_id = body["emissions_evidence_id"]
    report_evidence_id = body["report_evidence_id"]
    async with get_sessionmaker()() as db:
        emissions_ev = await db.scalar(select(EvidenceRecord).where(EvidenceRecord.evidence_id == emissions_evidence_id))
        assert emissions_ev is not None
        assert emissions_ev.dataset_version_id == dv_id
        assert emissions_ev.engine_id == "engine_csrd"
        assert emissions_ev.kind == "emissions"

        ev = await db.scalar(select(EvidenceRecord).where(EvidenceRecord.evidence_id == report_evidence_id))
        assert ev is not None
        assert ev.dataset_version_id == dv_id
        assert ev.engine_id == "engine_csrd"
        assert ev.kind == "report"

        raw = await db.scalar(select(RawRecord).where(RawRecord.dataset_version_id == dv_id))
        assert raw is not None

        finding = await db.scalar(select(FindingRecord).where(FindingRecord.dataset_version_id == dv_id))
        assert finding is not None
        assert finding.raw_record_id == raw.raw_record_id

        link = await db.scalar(select(FindingEvidenceLink).where(FindingEvidenceLink.finding_id == finding.finding_id))
        assert link is not None
        linked_ev = await db.scalar(select(EvidenceRecord).where(EvidenceRecord.evidence_id == link.evidence_id))
        assert linked_ev is not None
        assert linked_ev.dataset_version_id == dv_id
        assert linked_ev.kind == "finding"


@pytest.mark.anyio
@pytest.mark.parametrize("scope1,scope2,scope3,expected_total", [
    (1000, 2000, 5000, 8000),  # Standard case
    (0, 0, 0, 0),              # No emissions
    (1, 1, 1, 3),              # Minimal emissions
    (1e6, 2e6, 5e6, 8e6),      # Large numbers
])
async def test_emission_calculations(
    sqlite_db: None,
    scope1: float,
    scope2: float,
    scope3: float,
    expected_total: float
) -> None:
    """Test that emission calculations are performed correctly for various input values."""
    os.environ["TODISCOPE_ENABLED_ENGINES"] = "engine_csrd"
    app = create_app()

    # Create a record with the specified emission values
    record = _sample_record(
        record_id=f"emission_test_{scope1}_{scope2}_{scope3}",
        scope1=scope1,
        scope2=scope2,
        scope3=scope3
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Ingest the test record
        ingest_res = await ac.post("/api/v3/ingest-records", json={"records": [record]})
        assert ingest_res.status_code == 200
        dv_id = ingest_res.json()["dataset_version_id"]

        # Run the CSRD engine
        run_res = await ac.post(
            "/api/v3/engines/csrd/run",
            json={
                "dataset_version_id": dv_id,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "parameters": {"carbon_price_eur_per_tco2e": 100}
            },
        )
        assert run_res.status_code == 200
        body = run_res.json()

    # Validate the total emissions calculation
    assert abs(body["total_emissions_tco2e"] - expected_total) < 1e-9
    
    # Validate the report structure
    report = body["report"]
    _validate_report_structure(report, dv_id)
    
    # Check that all scopes are present and have the expected values
    scopes = report["emission_calculations"]["scopes"]
    assert set(scopes.keys()) == {"scope1", "scope2", "scope3"}
    assert abs(scopes["scope1"]["value"] - scope1) < 1e-9
    assert abs(scopes["scope2"]["value"] - scope2) < 1e-9
    assert abs(scopes["scope3"]["value"] - scope3) < 1e-9


@pytest.mark.anyio
@pytest.mark.parametrize("board_diversity,has_esg_committee,expected_material_topics", [
    (0.15, False, ["board_diversity", "esg_governance"]),  # Both below threshold
    (0.35, False, ["esg_governance"]),                     # Only diversity above threshold
    (0.15, True, ["board_diversity"]),                     # Only committee above threshold
    (0.35, True, []),                                       # Both above threshold
])
async def test_materiality_assessment(
    sqlite_db: None,
    board_diversity: float,
    has_esg_committee: bool,
    expected_material_topics: list[str]
) -> None:
    """Test that materiality assessment correctly identifies material topics."""
    os.environ["TODISCOPE_ENABLED_ENGINES"] = "engine_csrd"
    app = create_app()

    # Create a record with the specified governance parameters
    record = _sample_record(
        record_id=f"materiality_test_{board_diversity}_{has_esg_committee}",
        board_diversity=board_diversity,
        has_esg_committee=has_esg_committee
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Ingest the test record
        ingest_res = await ac.post("/api/v3/ingest-records", json={"records": [record]})
        assert ingest_res.status_code == 200
        dv_id = ingest_res.json()["dataset_version_id"]

        # Run the CSRD engine
        run_res = await ac.post(
            "/api/v3/engines/csrd/run",
            json={
                "dataset_version_id": dv_id,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "parameters": {"carbon_price_eur_per_tco2e": 100}
            },
        )
        assert run_res.status_code == 200
        body = run_res.json()

    # Get the material topics from the report
    material_topics = body["report"]["materiality_assessment"]["material_topics"]
    
    # Check that the expected topics are marked as material
    for topic in expected_material_topics:
        assert any(t["id"] == topic for t in material_topics if t["is_material"]), \
            f"Expected {topic} to be material but it wasn't"
    
    # Check that no unexpected topics are marked as material
    for topic in material_topics:
        if topic["is_material"]:
            assert topic["id"] in expected_material_topics, \
                f"Unexpected material topic: {topic['id']}"


@pytest.mark.anyio
async def test_immutable_conflict_on_rerun_with_different_payload(sqlite_db: None) -> None:
    os.environ["TODISCOPE_ENABLED_ENGINES"] = "engine_csrd"
    app = create_app()

    record = _sample_record(record_id="immutable_conflict_test", revenue=100000000, scope1=1000, scope2=2000, scope3=5000)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ingest_res = await ac.post("/api/v3/ingest-records", json={"records": [record]})
        assert ingest_res.status_code == 200
        dv_id = ingest_res.json()["dataset_version_id"]

        started_at = "2025-01-01T00:00:00+00:00"
        first = await ac.post(
            "/api/v3/engines/csrd/run",
            json={"dataset_version_id": dv_id, "started_at": started_at, "parameters": {"carbon_price_eur_per_tco2e": 100}},
        )
        assert first.status_code == 200

        # Second run changes materiality payload while reusing deterministic IDs -> must 409.
        second = await ac.post(
            "/api/v3/engines/csrd/run",
            json={"dataset_version_id": dv_id, "started_at": started_at, "parameters": {"carbon_price_eur_per_tco2e": 200}},
        )
        assert second.status_code == 409


@pytest.mark.anyio
async def test_idempotent_rerun_same_payload_is_ok(sqlite_db: None) -> None:
    os.environ["TODISCOPE_ENABLED_ENGINES"] = "engine_csrd"
    app = create_app()

    record = _sample_record(record_id="idempotent_test", revenue=100000000, scope1=10, scope2=10, scope3=10)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ingest_res = await ac.post("/api/v3/ingest-records", json={"records": [record]})
        assert ingest_res.status_code == 200
        dv_id = ingest_res.json()["dataset_version_id"]

        started_at = "2025-01-01T00:00:00+00:00"
        first = await ac.post(
            "/api/v3/engines/csrd/run",
            json={"dataset_version_id": dv_id, "started_at": started_at, "parameters": {"carbon_price_eur_per_tco2e": 100}},
        )
        assert first.status_code == 200

        second = await ac.post(
            "/api/v3/engines/csrd/run",
            json={"dataset_version_id": dv_id, "started_at": started_at, "parameters": {"carbon_price_eur_per_tco2e": 100}},
        )
        assert second.status_code == 200


@pytest.mark.anyio
async def test_emission_units_and_sources_in_report(sqlite_db: None) -> None:
    os.environ["TODISCOPE_ENABLED_ENGINES"] = "engine_csrd"
    app = create_app()

    record = _sample_record(record_id="units_sources_test", scope1=1, scope2=2, scope3=3)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ingest_res = await ac.post("/api/v3/ingest-records", json={"records": [record]})
        assert ingest_res.status_code == 200
        dv_id = ingest_res.json()["dataset_version_id"]

        run_res = await ac.post(
            "/api/v3/engines/csrd/run",
            json={"dataset_version_id": dv_id, "started_at": "2025-01-01T00:00:00+00:00"},
        )
        assert run_res.status_code == 200
        report = run_res.json()["report"]

    scopes = report["emission_calculations"]["scopes"]
    for scope in ("scope1", "scope2", "scope3"):
        assert scopes[scope]["unit"] == "tCO2e"
        assert isinstance(scopes[scope]["source"], str) and scopes[scope]["source"]
        assert isinstance(scopes[scope]["methodology"], str) and scopes[scope]["methodology"]


@pytest.mark.anyio
async def test_emissions_evidence_payload_contains_traceability(sqlite_db: None) -> None:
    os.environ["TODISCOPE_ENABLED_ENGINES"] = "engine_csrd"
    app = create_app()

    record = _sample_record(record_id="emissions_evidence_trace", scope1=1, scope2=2, scope3=3)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ingest_res = await ac.post("/api/v3/ingest-records", json={"records": [record]})
        assert ingest_res.status_code == 200
        dv_id = ingest_res.json()["dataset_version_id"]

        run_res = await ac.post(
            "/api/v3/engines/csrd/run",
            json={"dataset_version_id": dv_id, "started_at": "2025-01-01T00:00:00+00:00"},
        )
        assert run_res.status_code == 200
        body = run_res.json()

    async with get_sessionmaker()() as db:
        raw = await db.scalar(select(RawRecord).where(RawRecord.dataset_version_id == dv_id))
        assert raw is not None
        emissions_ev = await db.scalar(select(EvidenceRecord).where(EvidenceRecord.evidence_id == body["emissions_evidence_id"]))
        assert emissions_ev is not None
        assert emissions_ev.dataset_version_id == dv_id
        assert emissions_ev.kind == "emissions"
        assert emissions_ev.payload["source_raw_record_id"] == raw.raw_record_id
        assert isinstance(emissions_ev.payload["assumptions"], list)


@pytest.mark.anyio
async def test_emissions_materiality_changes_with_carbon_price(sqlite_db: None) -> None:
    os.environ["TODISCOPE_ENABLED_ENGINES"] = "engine_csrd"
    app = create_app()

    record = _sample_record(record_id="emissions_materiality_price", scope1=100, scope2=0, scope3=0, revenue=10000)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        ingest1 = await ac.post("/api/v3/ingest-records", json={"records": [record]})
        dv1 = ingest1.json()["dataset_version_id"]
        res1 = await ac.post(
            "/api/v3/engines/csrd/run",
            json={"dataset_version_id": dv1, "started_at": "2025-01-01T00:00:00+00:00", "parameters": {"carbon_price_eur_per_tco2e": 0}},
        )
        assert res1.status_code == 200

        ingest2 = await ac.post("/api/v3/ingest-records", json={"records": [record]})
        dv2 = ingest2.json()["dataset_version_id"]
        res2 = await ac.post(
            "/api/v3/engines/csrd/run",
            json={"dataset_version_id": dv2, "started_at": "2025-01-01T00:00:00+00:00", "parameters": {"carbon_price_eur_per_tco2e": 100}},
        )
        assert res2.status_code == 200

    def _emissions_finding_is_material(body: dict) -> bool:
        for f in body["material_findings"]:
            if f.get("metric") == "total_emissions_tco2e":
                return bool(f.get("is_material"))
        raise AssertionError("missing emissions finding")

    assert _emissions_finding_is_material(res1.json()) is False
    assert _emissions_finding_is_material(res2.json()) is True


@pytest.mark.integration
class TestCSRDEngineIntegration:
    """Integration tests for the CSRD engine with real-world scenarios."""
    
    @pytest.fixture(autouse=True)
    async def setup_db(self, sqlite_db):
        """Set up test database with required schema."""
        async with get_sessionmaker()() as session:
            # Create required tables if they don't exist
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS dataset_versions (
                    id TEXT PRIMARY KEY,
                    created_at TIMESTAMP,
                    data JSONB
                )
            """))
            await session.commit()
    
    async def _run_csrd_engine(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Helper method to run the CSRD engine with the given record."""
        os.environ["TODISCOPE_ENABLED_ENGINES"] = "engine_csrd"
        app = create_app()
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # Ingest the test record
            ingest_res = await ac.post("/api/v3/ingest-records", json={"records": [record]})
            assert ingest_res.status_code == 200
            dv_id = ingest_res.json()["dataset_version_id"]
            
            # Run the CSRD engine
            run_res = await ac.post(
                "/api/v3/engines/csrd/run",
                json={
                    "dataset_version_id": dv_id,
                    "started_at": datetime.now(timezone.utc).isoformat(),
                    "parameters": {"carbon_price_eur_per_tco2e": 100}
                },
            )
            assert run_res.status_code == 200
            return run_res.json()
    
    @pytest.mark.anyio
    async def test_full_report_generation(self):
        """Test end-to-end report generation with a comprehensive dataset."""
        # Load test data from file
        test_data = load_test_data("full_company_data.json")
        
        # Run the engine with test data
        result = await self._run_csrd_engine(test_data)
        
        # Validate the report structure
        report = result["report"]
        _validate_report_structure(report, result["dataset_version_id"])
        
        # Check that all required sections have content
        for section in ["executive_summary", "materiality_assessment", "compliance_summary"]:
            assert report[section], f"Section {section} should not be empty"
        
        # Validate material findings
        assert "material_findings" in result
        assert len(result["material_findings"]) > 0
        
        # Check evidence linkage
        assert "report_evidence_id" in result
        assert "emissions_evidence_id" in result
        
        # Verify database records were created
        async with get_sessionmaker()() as db:
            # Check evidence records
            evidence_records = await db.execute(
                select(EvidenceRecord).where(EvidenceRecord.dataset_version_id == result["dataset_version_id"])
            )
            evidence_records = evidence_records.scalars().all()
            assert len(evidence_records) >= 2  # At least report and emissions evidence
            
            # Check finding records
            findings = await db.execute(
                select(FindingRecord).where(FindingRecord.dataset_version_id == result["dataset_version_id"])
            )
            findings = findings.scalars().all()
            assert len(findings) > 0
    
    @pytest.mark.anyio
    async def test_missing_data_handling(self):
        """Test the engine's behavior with incomplete data."""
        # Create a record with missing required fields
        test_data = {
            "source_system": "test",
            "source_record_id": "missing_data_test",
            "esg": {
                # Missing emissions data
                "governance": {
                    "board_diversity": 0.4,
                    "esg_committee": True
                }
            },
            "financial": {
                "revenue": 1000000
            }
        }
        
        # Run the engine and verify it handles missing data gracefully
        result = await self._run_csrd_engine(test_data)
        
        # The report should still be generated but with appropriate warnings
        report = result["report"]
        assert "data_integrity" in report
        assert "warnings" in report["data_integrity"]
        assert len(report["data_integrity"]["warnings"]) > 0
        
        # The material findings should indicate data gaps
        assert any("data gap" in f["description"].lower() for f in result["material_findings"])
    
    @pytest.mark.parametrize("test_file", [
        "manufacturing_company.json",
        "financial_services.json",
        "technology_company.json"
    ])
    @pytest.mark.anyio
    async def test_industry_specific_scenarios(self, test_file):
        """Test the engine with different industry-specific scenarios."""
        # Skip if test data file doesn't exist
        test_path = TEST_DATA_DIR / test_file
        if not test_path.exists():
            pytest.skip(f"Test data file {test_file} not found")
        
        # Load and run the test case
        test_data = load_test_data(test_file)
        result = await self._run_csrd_engine(test_data)
        
        # Basic validation
        report = result["report"]
        _validate_report_structure(report, result["dataset_version_id"])
        
        # Industry-specific assertions
        if "manufacturing" in test_file:
            # Manufacturing companies typically have higher scope 1 & 2 emissions
            scope1 = report["emission_calculations"]["scopes"]["scope1"]["value"]
            scope2 = report["emission_calculations"]["scopes"]["scope2"]["value"]
            assert scope1 > 0 or scope2 > 0, "Manufacturing company should have scope 1 or 2 emissions"
        
        elif "financial" in test_file:
            # Financial services typically have minimal scope 1 & 2 emissions
            scope1 = report["emission_calculations"]["scopes"]["scope1"]["value"]
            scope2 = report["emission_calculations"]["scopes"]["scope2"]["value"]
            scope3 = report["emission_calculations"]["scopes"]["scope3"]["value"]
            assert scope1 + scope2 < scope3, "Financial services should have higher scope 3 emissions"
        
        elif "technology" in test_file:
            # Tech companies may have significant scope 3 emissions from cloud computing
            scope3 = report["emission_calculations"]["scopes"]["scope3"]["value"]
            assert scope3 > 0, "Tech company should have scope 3 emissions"
            
            # Check for cloud-related material topics
            material_topics = [t["id"] for t in report["materiality_assessment"]["material_topics"] if t["is_material"]]
            assert any(topic in material_topics for topic in ["cloud_emissions", "supply_chain_emissions"])


@pytest.fixture(scope="session", autouse=True)
def ensure_test_data_dir():
    """Ensure the test data directory exists."""
    TEST_DATA_DIR.mkdir(exist_ok=True)
    
    # Create a sample test data file if it doesn't exist
    sample_data = {
        "source_system": "test",
        "source_record_id": "sample_company",
        "esg": {
            "emissions": {
                "scope1": 1500,
                "scope2": 3000,
                "scope3": 10000
            },
            "energy_consumption": {
                "renewable": 45.0,
                "non_renewable": 55.0
            },
            "governance": {
                "board_diversity": 0.35,
                "esg_committee": True,
                "esg_policy": True,
                "sustainability_committee": True
            },
            "social": {
                "employee_count": 1000,
                "gender_diversity_ratio": 0.42,
                "employee_turnover_rate": 0.12
            }
        },
        "financial": {
            "revenue": 500000000,  # 500M EUR
            "operating_costs": 400000000,
            "profit": 100000000,
            "assets": 2500000000,
            "market_cap": 3000000000
        },
        "metadata": {
            "reporting_period": "2024",
            "company_name": "Sample Corporation",
            "industry": "Manufacturing"
        }
    }
    
    if not (TEST_DATA_DIR / "full_company_data.json").exists():
        with open(TEST_DATA_DIR / "full_company_data.json", 'w') as f:
            json.dump(sample_data, f, indent=2)
