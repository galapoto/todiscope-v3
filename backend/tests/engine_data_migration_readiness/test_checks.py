"""Tests for data migration readiness checks."""
from __future__ import annotations

import json
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.dataset.models import DatasetVersion
from backend.app.core.dataset.raw_models import RawRecord
from backend.app.engines.data_migration_readiness.checks import (
    QualityCheck,
    RiskSignal,
    StructuralCheck,
    MappingCheck,
    IntegrityCheck,
    RawRecordSnapshot,
    evaluate_quality,
    evaluate_structure,
    evaluate_mapping,
    verify_integrity,
    assess_risks,
    load_default_config,
)


@pytest.fixture
def sample_config() -> dict[str, Any]:
    """Return a sample configuration for testing."""
    return {
        "structural_requirements": {
            "collections": {
                "invoices": ["id", "amount", "date"],
                "customers": ["id", "name", "email"],
            },
            "metadata_keys": ["source_system", "import_timestamp"],
        },
        "quality_thresholds": {
            "completeness": 0.9,
            "duplicate_ratio": 0.05,
            "null_ratio": 0.1,
        },
        "mapping_expectations": {
            "invoices": {
                "field_mappings": {
                    "invoice_id": "id",
                    "invoice_amount": "amount",
                    "invoice_date": "date",
                }
            }
        },
        "risk_thresholds": {
            "high_risk_completeness": 0.7,
            "medium_risk_completeness": 0.9,
            "high_risk_duplicate_ratio": 0.1,
        },
    }


@pytest.fixture
def sample_raw_records() -> list[RawRecord]:
    """Return sample raw records for testing."""
    return [
        RawRecord(
            raw_record_id="1",
            dataset_version_id="test-dv-1",
            source_system="test_system",
            source_record_id="rec1",
            payload={
                "id": "inv1",
                "amount": "100.50",
                "date": "2023-01-01",
                "customer_id": "cust1",
                "items": [
                    {"id": "item1", "name": "Product A", "quantity": 2, "price": "50.25"},
                    {"id": "item2", "name": "Product B", "quantity": 1, "price": "50.00"},
                ],
                "source_system": "erp1",
                "import_timestamp": "2023-01-01T00:00:00Z",
            },
        ),
        RawRecord(
            raw_record_id="2",
            dataset_version_id="test-dv-1",
            source_system="test_system",
            source_record_id="rec2",
            payload={
                "id": "inv2",
                "amount": "200.00",
                "date": "2023-01-02",
                "customer_id": "cust2",
                "items": [
                    {"id": "item3", "name": "Product C", "quantity": 1, "price": "200.00"},
                ],
                "source_system": "erp1",
                "import_timestamp": "2023-01-02T00:00:00Z",
            },
        ),
    ]


def test_evaluate_structure(sample_config, sample_raw_records):
    """Test structural evaluation of raw records."""
    snapshots = [
        RawRecordSnapshot(
            raw_record_id=rec.raw_record_id,
            dataset_version_id=rec.dataset_version_id,
            source_system=rec.source_system,
            source_record_id=rec.source_record_id,
            payload=rec.payload,
        )
        for rec in sample_raw_records
    ]
    
    collections = {
        "invoices": tuple(rec.payload for rec in sample_raw_records),
        "items": tuple(
            item
            for rec in sample_raw_records
            for item in rec.payload.get("items", [])
        ),
    }
    
    result = evaluate_structure(
        dataset_version_id="test-dv-1",
        records=snapshots,
        collections=collections,
        config=sample_config,
    )
    
    assert isinstance(result, StructuralCheck)
    assert result.dataset_version_id == "test-dv-1"
    assert result.compliant is False  # Missing 'customers' collection


def test_verify_integrity():
    """Test data integrity verification."""
    snapshots = [
        RawRecordSnapshot(
            raw_record_id=f"{i}",
            dataset_version_id="test-dv-1",
            source_system="test_system",
            source_record_id=f"rec{i}",
            payload={"id": f"inv{i}", "amount": str(100 * i)},
        )
        for i in range(5)
    ]
    # Add a duplicate
    snapshots.append(snapshots[0])
    
    result = verify_integrity("test-dv-1", snapshots)
    
    assert isinstance(result, IntegrityCheck)
    assert result.record_count == 6
    assert result.unique_source_records == 5
    assert result.duplicate_ratio == Decimal("0.1666666666666666666666666667")  # 1/6
    assert result.compliant is False


def test_evaluate_quality(sample_config):
    """Test data quality evaluation."""
    collections = {
        "invoices": [
            {"id": "1", "amount": "100.00", "date": "2023-01-01"},  # Complete
            {"id": "2", "amount": None, "date": "2023-01-02"},      # Missing amount
            {"id": "3", "amount": "300.00", "date": None},        # Missing date
        ],
        "customers": [
            {"id": "c1", "name": "Alice", "email": "alice@example.com"},
            {"id": "c2", "name": "Bob", "email": None},  # Missing email
        ],
    }
    
    result = evaluate_quality(
        dataset_version_id="test-dv-1",
        collections=collections,
        config=sample_config,
        duplicate_ratio=Decimal("0.05"),
    )
    
    assert isinstance(result, QualityCheck)
    assert result.dataset_version_id == "test-dv-1"
    assert result.completeness_score < Decimal("1.0")
    assert result.null_ratio > Decimal("0.0")
    assert result.duplicate_ratio == Decimal("0.05")
    assert not result.passes


def test_evaluate_mapping(sample_config):
    """Test field mapping evaluation."""
    collections = {
        "invoices": [
            {"id": "1", "amount": "100.00", "date": "2023-01-01"},
            {"id": "2", "amount": "200.00", "date": "2023-01-02"},
        ],
        # Missing required 'customers' collection
    }
    
    result = evaluate_mapping("test-dv-1", collections, sample_config)
    
    assert isinstance(result, MappingCheck)
    assert result.dataset_version_id == "test-dv-1"
    assert not result.compliant
    assert "invoices" in result.missing_mappings


def test_assess_risks(sample_config):
    """Test risk assessment."""
    structure = StructuralCheck(
        dataset_version_id="test-dv-1",
        required_collections=("invoices", "customers"),
        missing_collections=("customers",),
        missing_fields={"invoices": ("tax_amount",)},
        metadata_issues=(),
        compliant=False,
    )
    
    quality = QualityCheck(
        dataset_version_id="test-dv-1",
        completeness_score=Decimal("0.75"),
        null_ratio=Decimal("0.15"),
        duplicate_ratio=Decimal("0.05"),
        per_collection={"invoices": Decimal("0.8")},
        passes=False,
        notes=("Some data quality issues found",),
    )
    
    mapping = MappingCheck(
        dataset_version_id="test-dv-1",
        missing_mappings={"invoices": ["tax_amount"]},
        compliant=False,
    )
    
    integrity = IntegrityCheck(
        dataset_version_id="test-dv-1",
        record_count=100,
        unique_source_records=95,
        duplicate_ratio=Decimal("0.05"),
        compliant=True,
        notes=(),
    )
    
    risks = assess_risks(
        dataset_version_id="test-dv-1",
        structure=structure,
        quality=quality,
        mapping=mapping,
        integrity=integrity,
        config=sample_config,
    )
    
    assert isinstance(risks, list)
    assert len(risks) > 0
    assert all(isinstance(risk, RiskSignal) for risk in risks)
    assert any(risk.severity == "high" for risk in risks)  # Due to completeness < 0.7


def test_load_default_config():
    """Test loading the default configuration."""
    config = load_default_config()
    assert isinstance(config, dict)
    assert "structural_requirements" in config
    assert "quality_thresholds" in config
    assert "mapping_expectations" in config
    assert "risk_thresholds" in config


@pytest.mark.asyncio
async def test_run_readiness_check(sample_config, sample_raw_records):
    """Test the full readiness check workflow."""
    from backend.app.engines.data_migration_readiness.run import run_readiness_check
    
    # Mock the database session
    mock_session = AsyncSession()
    mock_session.scalar = AsyncMock()
    mock_session.scalars = AsyncMock(return_value=sample_raw_records)
    
    # Mock get_sessionmaker to return our mock session
    with patch("backend.app.engines.data_migration_readiness.run.get_sessionmaker") as mock_get_sessionmaker:
        mock_get_sessionmaker.return_value = AsyncMock(return_value=mock_session)
        
        # Mock load_default_config to return our test config
        with patch("backend.app.engines.data_migration_readiness.run.load_default_config") as mock_load_config:
            mock_load_config.return_value = sample_config
            
            # Call the function under test
            result = await run_readiness_check(
                dataset_version_id="test-dv-1",
                started_at="2023-01-01T00:00:00Z",
                parameters={"config_overrides": {}},
            )
    
    # Verify the result structure
    assert "dataset_version_id" in result
    assert "started_at" in result
    assert "structure" in result
    assert "quality" in result
    assert "mapping" in result
    assert "integrity" in result
    assert "risks" in result
    assert "assumptions" in result
    
    # Verify the structure of nested results
    assert isinstance(result["structure"], dict)
    assert isinstance(result["quality"], dict)
    assert isinstance(result["mapping"], dict)
    assert isinstance(result["integrity"], dict)
    assert isinstance(result["risks"], list)
    assert isinstance(result["assumptions"], dict)
