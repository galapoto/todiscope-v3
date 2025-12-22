"""Remediation Tasks Generation for Enterprise Insurance Claim Forensics Engine.

This module generates actionable remediation tasks based on:
- Validation failures
- High-severity exposures
- Data quality issues
- Missing required fields

Platform Law Compliance:
- Deterministic: Same inputs → same outputs
- All tasks bound to DatasetVersion
- Task IDs are deterministic
"""

from __future__ import annotations

from typing import Any

from backend.app.engines.enterprise_insurance_claim_forensics.ids import deterministic_id


def build_remediation_tasks(
    *,
    dataset_version_id: str,
    run_id: str,
    exposures: list[dict[str, Any]],
    validation_results: dict[str, dict[str, Any]],
    readiness_scores: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """
    Build remediation tasks based on findings.
    
    Args:
        dataset_version_id: Dataset version ID
        run_id: Run ID
        exposures: List of exposure dictionaries
        validation_results: Dictionary mapping claim_id to validation results
        readiness_scores: Optional dictionary mapping claim_id to readiness scores
    
    Returns:
        List of remediation task dictionaries with:
        - id: Deterministic task ID
        - category: Task category (validation/exposure/data_quality)
        - severity: high/medium/low
        - description: Human-readable description
        - details: Task-specific details
        - status: pending/completed
        - claim_id: Associated claim ID (if applicable)
    """
    tasks: list[dict[str, Any]] = []
    
    # Track which claims have tasks to avoid duplicates
    claims_with_tasks: set[str] = set()
    
    for exposure in exposures:
        claim_id = exposure.get("claim_id")
        if not claim_id:
            continue
        
        validation_result = validation_results.get(claim_id, {})
        readiness_score = readiness_scores.get(claim_id, {}) if readiness_scores else {}
        
        # Task 1: Validation failures (high severity)
        if not validation_result.get("is_valid", False):
            errors = validation_result.get("errors", [])
            if errors:
                task_id = deterministic_id(dataset_version_id, run_id, claim_id, "validation_failure")
                tasks.append({
                    "id": task_id,
                    "category": "validation",
                    "severity": "high",
                    "description": f"Resolve validation errors for claim {claim_id}",
                    "details": {
                        "claim_id": claim_id,
                        "errors": errors,
                        "error_count": len(errors),
                        "validation_result": validation_result,
                    },
                    "status": "pending",
                    "claim_id": claim_id,
                })
                claims_with_tasks.add(claim_id)
        
        # Task 2: High-severity exposures (high severity)
        if exposure.get("severity") == "high":
            task_id = deterministic_id(dataset_version_id, run_id, claim_id, "high_severity_exposure")
            tasks.append({
                "id": task_id,
                "category": "exposure",
                "severity": "high",
                "description": f"Review high-severity exposure for claim {claim_id}",
                "details": {
                    "claim_id": claim_id,
                    "outstanding_exposure": exposure.get("outstanding_exposure", 0.0),
                    "expected_loss": exposure.get("expected_loss", 0.0),
                    "claim_status": exposure.get("claim_status"),
                    "severity": exposure.get("severity"),
                },
                "status": "pending",
                "claim_id": claim_id,
            })
            claims_with_tasks.add(claim_id)
        
        # Task 3: Low readiness scores (medium severity)
        if readiness_score and readiness_score.get("readiness_level") == "weak":
            task_id = deterministic_id(dataset_version_id, run_id, claim_id, "low_readiness")
            tasks.append({
                "id": task_id,
                "category": "data_quality",
                "severity": "medium",
                "description": f"Improve data quality for claim {claim_id} (readiness score: {readiness_score.get('readiness_score', 0):.2f})",
                "details": {
                    "claim_id": claim_id,
                    "readiness_score": readiness_score.get("readiness_score", 0.0),
                    "readiness_level": readiness_score.get("readiness_level"),
                    "component_scores": readiness_score.get("component_scores", {}),
                },
                "status": "pending",
                "claim_id": claim_id,
            })
            claims_with_tasks.add(claim_id)
        
        # Task 4: Missing required fields (medium severity)
        required_fields = ["claim_id", "claim_amount", "claim_status", "currency"]
        missing_fields = [field for field in required_fields if exposure.get(field) is None]
        if missing_fields:
            task_id = deterministic_id(dataset_version_id, run_id, claim_id, "missing_fields")
            tasks.append({
                "id": task_id,
                "category": "data_quality",
                "severity": "medium",
                "description": f"Complete missing required fields for claim {claim_id}",
                "details": {
                    "claim_id": claim_id,
                    "missing_fields": missing_fields,
                },
                "status": "pending",
                "claim_id": claim_id,
            })
            claims_with_tasks.add(claim_id)
        
        # Task 5: Medium-severity exposures (medium severity)
        if exposure.get("severity") == "medium" and exposure.get("outstanding_exposure", 0.0) > 0:
            task_id = deterministic_id(dataset_version_id, run_id, claim_id, "medium_severity_exposure")
            tasks.append({
                "id": task_id,
                "category": "exposure",
                "severity": "medium",
                "description": f"Monitor medium-severity exposure for claim {claim_id}",
                "details": {
                    "claim_id": claim_id,
                    "outstanding_exposure": exposure.get("outstanding_exposure", 0.0),
                    "expected_loss": exposure.get("expected_loss", 0.0),
                    "claim_status": exposure.get("claim_status"),
                },
                "status": "pending",
                "claim_id": claim_id,
            })
            claims_with_tasks.add(claim_id)
    
    # Task 6: Portfolio-level monitoring (low severity, if no other tasks)
    if not tasks:
        task_id = deterministic_id(dataset_version_id, run_id, "portfolio", "monitoring")
        tasks.append({
            "id": task_id,
            "category": "monitoring",
            "severity": "low",
            "description": "Continue monitoring claim portfolio and maintain data quality standards",
            "details": {
                "total_claims": len(exposures),
                "message": "No critical issues detected. Continue regular monitoring.",
            },
            "status": "completed",
            "claim_id": None,
        })
    
    return tasks


