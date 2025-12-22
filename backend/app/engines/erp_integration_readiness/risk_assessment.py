"""
Risk Assessment Logic for ERP System Integration

This module implements deterministic risk assessment for ERP system integration,
evaluating risks related to system downtime, compatibility issues, and other disruptions.

All assessments are:
- Deterministic: same inputs produce same outputs
- Immutable: assessments do not modify input data
- Traceable: all findings linked to DatasetVersion
"""
from __future__ import annotations

from typing import Any


def assess_downtime_risk(
    *,
    erp_system_config: dict,
    readiness_results: dict[str, Any],
    compatibility_results: dict[str, Any],
    dataset_version_id: str,
) -> dict[str, Any]:
    """
    Assess the risk of system downtime during ERP integration.
    
    Args:
        erp_system_config: ERP system configuration dictionary
        readiness_results: Results from readiness checks
        compatibility_results: Results from compatibility checks
        dataset_version_id: Dataset version ID for traceability
        
    Returns:
        Dictionary with risk assessment:
        - risk_level: str indicating risk level (low, medium, high, critical)
        - risk_score: float risk score (0.0 to 1.0)
        - factors: list of risk factors
        - evidence: evidence data for traceability
    """
    risk_factors: list[dict[str, Any]] = []
    risk_score = 0.0
    evidence_data: dict[str, Any] = {
        "assessment_type": "downtime_risk",
        "dataset_version_id": dataset_version_id,
        "erp_system_id": erp_system_config.get("system_id", "unknown"),
    }
    
    # Factor 1: High availability configuration
    ha_enabled = erp_system_config.get("high_availability", {}).get("enabled", False)
    if not ha_enabled:
        risk_factors.append({
            "factor": "high_availability_disabled",
            "description": "High availability not enabled - system may be unavailable during integration",
            "weight": 0.3,
        })
        risk_score += 0.3
    
    # Factor 2: Maintenance window availability
    maintenance_window = erp_system_config.get("maintenance_window", {})
    if not maintenance_window.get("scheduled", False):
        risk_factors.append({
            "factor": "no_maintenance_window",
            "description": "No scheduled maintenance window - integration timing may cause disruption",
            "weight": 0.2,
        })
        risk_score += 0.2
    
    # Factor 3: Operational readiness issues
    operational_ready = readiness_results.get("operational_readiness", {}).get("ready", False)
    if not operational_ready:
        operational_issues = readiness_results.get("operational_readiness", {}).get("issues", [])
        high_severity_issues = [i for i in operational_issues if i.get("severity") == "high"]
        if high_severity_issues:
            risk_factors.append({
                "factor": "operational_readiness_issues",
                "description": f"{len(high_severity_issues)} high-severity operational readiness issues",
                "weight": 0.25,
                "issues": high_severity_issues,
            })
            risk_score += 0.25
    
    # Factor 4: Compatibility issues
    infrastructure_compatible = compatibility_results.get("infrastructure_compatibility", {}).get("compatible", False)
    if not infrastructure_compatible:
        compat_issues = compatibility_results.get("infrastructure_compatibility", {}).get("issues", [])
        high_severity_issues = [i for i in compat_issues if i.get("severity") == "high"]
        if high_severity_issues:
            risk_factors.append({
                "factor": "infrastructure_compatibility_issues",
                "description": f"{len(high_severity_issues)} high-severity compatibility issues",
                "weight": 0.25,
                "issues": high_severity_issues,
            })
            risk_score += 0.25
    
    # Determine risk level
    if risk_score >= 0.75:
        risk_level = "critical"
    elif risk_score >= 0.5:
        risk_level = "high"
    elif risk_score >= 0.25:
        risk_level = "medium"
    else:
        risk_level = "low"
    
    evidence_data["risk_factors"] = risk_factors
    evidence_data["risk_score"] = risk_score
    evidence_data["risk_level"] = risk_level
    
    return {
        "risk_level": risk_level,
        "risk_score": risk_score,
        "factors": risk_factors,
        "evidence": evidence_data,
    }


def assess_data_integrity_risk(
    *,
    erp_system_config: dict,
    readiness_results: dict[str, Any],
    dataset_version_id: str,
) -> dict[str, Any]:
    """
    Assess the risk of data integrity issues during ERP integration.
    
    Args:
        erp_system_config: ERP system configuration dictionary
        readiness_results: Results from readiness checks
        dataset_version_id: Dataset version ID for traceability
        
    Returns:
        Dictionary with risk assessment:
        - risk_level: str indicating risk level (low, medium, high, critical)
        - risk_score: float risk score (0.0 to 1.0)
        - factors: list of risk factors
        - evidence: evidence data for traceability
    """
    risk_factors: list[dict[str, Any]] = []
    risk_score = 0.0
    evidence_data: dict[str, Any] = {
        "assessment_type": "data_integrity_risk",
        "dataset_version_id": dataset_version_id,
        "erp_system_id": erp_system_config.get("system_id", "unknown"),
    }
    
    # Factor 1: Data validation configuration
    data_integrity_ready = readiness_results.get("data_integrity_requirements", {}).get("ready", False)
    if not data_integrity_ready:
        integrity_issues = readiness_results.get("data_integrity_requirements", {}).get("issues", [])
        high_severity_issues = [i for i in integrity_issues if i.get("severity") == "high"]
        if high_severity_issues:
            risk_factors.append({
                "factor": "data_integrity_requirements_not_met",
                "description": f"{len(high_severity_issues)} high-severity data integrity issues",
                "weight": 0.4,
                "issues": high_severity_issues,
            })
            risk_score += 0.4
    
    # Factor 2: Backup and rollback capabilities
    backup_config = erp_system_config.get("backup_config", {})
    if not backup_config.get("enabled", False):
        risk_factors.append({
            "factor": "backup_not_enabled",
            "description": "Backup not enabled - data recovery may not be possible",
            "weight": 0.3,
        })
        risk_score += 0.3
    
    # Factor 3: Transaction support
    transaction_support = erp_system_config.get("transaction_support", {})
    if not transaction_support.get("enabled", False):
        risk_factors.append({
            "factor": "transaction_support_disabled",
            "description": "Transaction support not enabled - data consistency may be compromised",
            "weight": 0.3,
        })
        risk_score += 0.3
    
    # Determine risk level
    if risk_score >= 0.75:
        risk_level = "critical"
    elif risk_score >= 0.5:
        risk_level = "high"
    elif risk_score >= 0.25:
        risk_level = "medium"
    else:
        risk_level = "low"
    
    evidence_data["risk_factors"] = risk_factors
    evidence_data["risk_score"] = risk_score
    evidence_data["risk_level"] = risk_level
    
    return {
        "risk_level": risk_level,
        "risk_score": risk_score,
        "factors": risk_factors,
        "evidence": evidence_data,
    }


def assess_compatibility_risk(
    *,
    compatibility_results: dict[str, Any],
    dataset_version_id: str,
) -> dict[str, Any]:
    """
    Assess the risk of compatibility issues during ERP integration.
    
    Args:
        compatibility_results: Results from compatibility checks
        dataset_version_id: Dataset version ID for traceability
        
    Returns:
        Dictionary with risk assessment:
        - risk_level: str indicating risk level (low, medium, high, critical)
        - risk_score: float risk score (0.0 to 1.0)
        - factors: list of risk factors
        - evidence: evidence data for traceability
    """
    risk_factors: list[dict[str, Any]] = []
    risk_score = 0.0
    evidence_data: dict[str, Any] = {
        "assessment_type": "compatibility_risk",
        "dataset_version_id": dataset_version_id,
    }
    
    # Factor 1: Infrastructure compatibility
    infrastructure_compatible = compatibility_results.get("infrastructure_compatibility", {}).get("compatible", False)
    if not infrastructure_compatible:
        compat_issues = compatibility_results.get("infrastructure_compatibility", {}).get("issues", [])
        high_severity_issues = [i for i in compat_issues if i.get("severity") == "high"]
        if high_severity_issues:
            risk_factors.append({
                "factor": "infrastructure_incompatibility",
                "description": f"{len(high_severity_issues)} high-severity infrastructure compatibility issues",
                "weight": 0.3,
                "issues": high_severity_issues,
            })
            risk_score += 0.3
    
    # Factor 2: Version compatibility
    version_compatible = compatibility_results.get("version_compatibility", {}).get("compatible", False)
    if not version_compatible:
        version_issues = compatibility_results.get("version_compatibility", {}).get("issues", [])
        high_severity_issues = [i for i in version_issues if i.get("severity") == "high"]
        if high_severity_issues:
            risk_factors.append({
                "factor": "version_incompatibility",
                "description": f"{len(high_severity_issues)} high-severity version compatibility issues",
                "weight": 0.3,
                "issues": high_severity_issues,
            })
            risk_score += 0.3
    
    # Factor 3: Security compatibility
    security_compatible = compatibility_results.get("security_compatibility", {}).get("compatible", False)
    if not security_compatible:
        security_issues = compatibility_results.get("security_compatibility", {}).get("issues", [])
        high_severity_issues = [i for i in security_issues if i.get("severity") == "high"]
        if high_severity_issues:
            risk_factors.append({
                "factor": "security_incompatibility",
                "description": f"{len(high_severity_issues)} high-severity security compatibility issues",
                "weight": 0.4,
                "issues": high_severity_issues,
            })
            risk_score += 0.4
    
    # Determine risk level
    if risk_score >= 0.75:
        risk_level = "critical"
    elif risk_score >= 0.5:
        risk_level = "high"
    elif risk_score >= 0.25:
        risk_level = "medium"
    else:
        risk_level = "low"
    
    evidence_data["risk_factors"] = risk_factors
    evidence_data["risk_score"] = risk_score
    evidence_data["risk_level"] = risk_level
    
    return {
        "risk_level": risk_level,
        "risk_score": risk_score,
        "factors": risk_factors,
        "evidence": evidence_data,
    }


