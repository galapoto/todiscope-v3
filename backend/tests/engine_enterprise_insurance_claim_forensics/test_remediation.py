"""Tests for remediation tasks generation."""

from __future__ import annotations

import pytest

from backend.app.engines.enterprise_insurance_claim_forensics.remediation import build_remediation_tasks


def test_build_remediation_tasks_validation_failures() -> None:
    """Test remediation task generation for validation failures."""
    dataset_version_id = "dv-test"
    run_id = "run-test"
    exposures = [
        {
            "claim_id": "claim-1",
            "claim_amount": 10000.0,
            "claim_status": "open",
            "currency": "USD",
            "severity": "medium",
            "outstanding_exposure": 5000.0,
        },
    ]
    validation_results = {
        "claim-1": {
            "is_valid": False,
            "errors": ["amount_mismatch", "currency_mismatch"],
            "warnings": [],
        },
    }
    
    tasks = build_remediation_tasks(
        dataset_version_id=dataset_version_id,
        run_id=run_id,
        exposures=exposures,
        validation_results=validation_results,
    )
    
    assert len(tasks) > 0
    validation_task = next((t for t in tasks if t["category"] == "validation"), None)
    assert validation_task is not None
    assert validation_task["severity"] == "high"
    assert validation_task["status"] == "pending"
    assert validation_task["claim_id"] == "claim-1"
    assert "errors" in validation_task["details"]


def test_build_remediation_tasks_high_severity_exposure() -> None:
    """Test remediation task generation for high-severity exposures."""
    dataset_version_id = "dv-test"
    run_id = "run-test"
    exposures = [
        {
            "claim_id": "claim-1",
            "claim_amount": 100000.0,
            "claim_status": "open",
            "currency": "USD",
            "severity": "high",
            "outstanding_exposure": 100000.0,
            "expected_loss": 85000.0,
        },
    ]
    validation_results = {
        "claim-1": {
            "is_valid": True,
            "errors": [],
            "warnings": [],
        },
    }
    
    tasks = build_remediation_tasks(
        dataset_version_id=dataset_version_id,
        run_id=run_id,
        exposures=exposures,
        validation_results=validation_results,
    )
    
    assert len(tasks) > 0
    exposure_task = next((t for t in tasks if t["category"] == "exposure"), None)
    assert exposure_task is not None
    assert exposure_task["severity"] == "high"
    assert exposure_task["claim_id"] == "claim-1"
    assert "outstanding_exposure" in exposure_task["details"]


def test_build_remediation_tasks_low_readiness() -> None:
    """Test remediation task generation for low readiness scores."""
    dataset_version_id = "dv-test"
    run_id = "run-test"
    exposures = [
        {
            "claim_id": "claim-1",
            "claim_amount": 10000.0,
            "claim_status": "open",
            "currency": "USD",
            "severity": "medium",
            "outstanding_exposure": 5000.0,
        },
    ]
    validation_results = {
        "claim-1": {
            "is_valid": True,
            "errors": [],
            "warnings": [],
        },
    }
    readiness_scores = {
        "claim-1": {
            "readiness_score": 45.0,
            "readiness_level": "weak",
            "component_scores": {
                "validation": 50.0,
                "severity": 70.0,
                "completeness": 40.0,
                "status": 60.0,
            },
        },
    }
    
    tasks = build_remediation_tasks(
        dataset_version_id=dataset_version_id,
        run_id=run_id,
        exposures=exposures,
        validation_results=validation_results,
        readiness_scores=readiness_scores,
    )
    
    assert len(tasks) > 0
    quality_task = next((t for t in tasks if t["category"] == "data_quality" and t.get("claim_id") == "claim-1"), None)
    assert quality_task is not None
    assert quality_task["severity"] == "medium"
    assert "readiness_score" in quality_task["details"]


def test_build_remediation_tasks_missing_fields() -> None:
    """Test remediation task generation for missing required fields."""
    dataset_version_id = "dv-test"
    run_id = "run-test"
    exposures = [
        {
            "claim_id": "claim-1",
            # Missing claim_amount, claim_status, currency
            "severity": "medium",
        },
    ]
    validation_results = {
        "claim-1": {
            "is_valid": True,
            "errors": [],
            "warnings": [],
        },
    }
    
    tasks = build_remediation_tasks(
        dataset_version_id=dataset_version_id,
        run_id=run_id,
        exposures=exposures,
        validation_results=validation_results,
    )
    
    assert len(tasks) > 0
    missing_fields_task = next((t for t in tasks if t["category"] == "data_quality" and "missing_fields" in t.get("details", {})), None)
    assert missing_fields_task is not None
    assert missing_fields_task["severity"] == "medium"
    assert "missing_fields" in missing_fields_task["details"]


def test_build_remediation_tasks_no_issues() -> None:
    """Test remediation task generation when no issues are found."""
    dataset_version_id = "dv-test"
    run_id = "run-test"
    exposures = [
        {
            "claim_id": "claim-1",
            "claim_amount": 10000.0,
            "claim_status": "closed",
            "currency": "USD",
            "severity": "low",
            "outstanding_exposure": 0.0,
            "evidence_range": {
                "transaction_ids": ["tx-1"],
            },
        },
    ]
    validation_results = {
        "claim-1": {
            "is_valid": True,
            "errors": [],
            "warnings": [],
        },
    }
    
    tasks = build_remediation_tasks(
        dataset_version_id=dataset_version_id,
        run_id=run_id,
        exposures=exposures,
        validation_results=validation_results,
    )
    
    # Should have at least a monitoring task
    assert len(tasks) > 0
    monitoring_task = next((t for t in tasks if t["category"] == "monitoring"), None)
    assert monitoring_task is not None
    assert monitoring_task["severity"] == "low"
    assert monitoring_task["status"] == "completed"


def test_build_remediation_tasks_multiple_claims() -> None:
    """Test remediation task generation for multiple claims."""
    dataset_version_id = "dv-test"
    run_id = "run-test"
    exposures = [
        {
            "claim_id": "claim-1",
            "claim_amount": 10000.0,
            "claim_status": "open",
            "currency": "USD",
            "severity": "high",
            "outstanding_exposure": 10000.0,
        },
        {
            "claim_id": "claim-2",
            "claim_amount": 5000.0,
            "claim_status": "open",
            "currency": "USD",
            "severity": "medium",
            "outstanding_exposure": 5000.0,
        },
    ]
    validation_results = {
        "claim-1": {
            "is_valid": False,
            "errors": ["amount_mismatch"],
            "warnings": [],
        },
        "claim-2": {
            "is_valid": True,
            "errors": [],
            "warnings": [],
        },
    }
    
    tasks = build_remediation_tasks(
        dataset_version_id=dataset_version_id,
        run_id=run_id,
        exposures=exposures,
        validation_results=validation_results,
    )
    
    assert len(tasks) >= 2  # At least one task per claim
    claim_1_tasks = [t for t in tasks if t.get("claim_id") == "claim-1"]
    claim_2_tasks = [t for t in tasks if t.get("claim_id") == "claim-2"]
    assert len(claim_1_tasks) > 0
    assert len(claim_2_tasks) > 0


