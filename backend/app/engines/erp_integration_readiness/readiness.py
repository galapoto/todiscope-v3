"""
ERP System Readiness Check Logic

This module implements deterministic checks to assess whether an ERP system
is ready for integration without causing operational downtime or data integrity issues.

All checks are:
- Deterministic: same inputs produce same outputs
- Immutable: checks do not modify input data
- Traceable: all findings linked to DatasetVersion
"""
from __future__ import annotations

from typing import Any


def check_erp_system_availability(
    *,
    erp_system_config: dict,
    dataset_version_id: str,
) -> dict[str, Any]:
    """
    Check if ERP system is available and accessible.
    
    Args:
        erp_system_config: ERP system configuration dictionary
        dataset_version_id: Dataset version ID for traceability
        
    Returns:
        Dictionary with check result:
        - ready: bool indicating if system is available
        - issues: list of issues found
        - evidence: evidence data for traceability
    """
    issues: list[dict[str, Any]] = []
    evidence_data: dict[str, Any] = {
        "check_type": "erp_system_availability",
        "dataset_version_id": dataset_version_id,
        "erp_system_id": erp_system_config.get("system_id", "unknown"),
    }
    
    # Check required fields
    required_fields = ["system_id", "connection_type", "api_endpoint"]
    for field in required_fields:
        if field not in erp_system_config:
            issues.append({
                "field": field,
                "issue": f"Missing required field: {field}",
                "severity": "high",
            })
    
    # Check connection type validity
    valid_connection_types = ["api", "database", "file_export", "sftp"]
    connection_type = erp_system_config.get("connection_type")
    if connection_type and connection_type not in valid_connection_types:
        issues.append({
            "field": "connection_type",
            "issue": f"Invalid connection type: {connection_type}. Must be one of {valid_connection_types}",
            "severity": "high",
        })
    
    # Check API endpoint format if connection type is API
    if connection_type == "api":
        api_endpoint = erp_system_config.get("api_endpoint")
        if not api_endpoint:
            issues.append({
                "field": "api_endpoint",
                "issue": "API endpoint required for API connection type",
                "severity": "high",
            })
        elif not isinstance(api_endpoint, str) or not api_endpoint.startswith(("http://", "https://")):
            issues.append({
                "field": "api_endpoint",
                "issue": "API endpoint must be a valid HTTP/HTTPS URL",
                "severity": "high",
            })
    
    evidence_data["issues"] = issues
    evidence_data["ready"] = len(issues) == 0
    
    return {
        "ready": len(issues) == 0,
        "issues": issues,
        "evidence": evidence_data,
    }


def check_data_integrity_requirements(
    *,
    erp_system_config: dict,
    dataset_version_id: str,
) -> dict[str, Any]:
    """
    Check if ERP system meets data integrity requirements for integration.
    
    Args:
        erp_system_config: ERP system configuration dictionary
        dataset_version_id: Dataset version ID for traceability
        
    Returns:
        Dictionary with check result:
        - ready: bool indicating if data integrity requirements are met
        - issues: list of issues found
        - evidence: evidence data for traceability
    """
    issues: list[dict[str, Any]] = []
    evidence_data: dict[str, Any] = {
        "check_type": "data_integrity_requirements",
        "dataset_version_id": dataset_version_id,
        "erp_system_id": erp_system_config.get("system_id", "unknown"),
    }
    
    # Check for data validation capabilities
    validation_config = erp_system_config.get("data_validation", {})
    if not validation_config:
        issues.append({
            "field": "data_validation",
            "issue": "Data validation configuration not specified",
            "severity": "medium",
        })
    else:
        # Check for required validation rules
        required_validation_rules = ["schema_validation", "data_type_validation"]
        for rule in required_validation_rules:
            if rule not in validation_config:
                issues.append({
                    "field": f"data_validation.{rule}",
                    "issue": f"Required validation rule not configured: {rule}",
                    "severity": "medium",
                })
    
    # Check for backup/rollback capabilities
    backup_config = erp_system_config.get("backup_config", {})
    if not backup_config:
        issues.append({
            "field": "backup_config",
            "issue": "Backup configuration not specified - rollback capability may be limited",
            "severity": "high",
        })
    else:
        if not backup_config.get("enabled", False):
            issues.append({
                "field": "backup_config.enabled",
                "issue": "Backup is not enabled - data recovery may not be possible",
                "severity": "high",
            })
    
    # Check for transaction support
    transaction_support = erp_system_config.get("transaction_support", {})
    if not transaction_support.get("enabled", False):
        issues.append({
            "field": "transaction_support.enabled",
            "issue": "Transaction support not enabled - data consistency may be compromised",
            "severity": "high",
        })
    
    evidence_data["issues"] = issues
    evidence_data["ready"] = len([i for i in issues if i["severity"] == "high"]) == 0
    
    return {
        "ready": len([i for i in issues if i["severity"] == "high"]) == 0,
        "issues": issues,
        "evidence": evidence_data,
    }


def check_operational_readiness(
    *,
    erp_system_config: dict,
    dataset_version_id: str,
) -> dict[str, Any]:
    """
    Check if ERP system is operationally ready (no downtime risk).
    
    Args:
        erp_system_config: ERP system configuration dictionary
        dataset_version_id: Dataset version ID for traceability
        
    Returns:
        Dictionary with check result:
        - ready: bool indicating if system is operationally ready
        - issues: list of issues found
        - evidence: evidence data for traceability
    """
    issues: list[dict[str, Any]] = []
    evidence_data: dict[str, Any] = {
        "check_type": "operational_readiness",
        "dataset_version_id": dataset_version_id,
        "erp_system_id": erp_system_config.get("system_id", "unknown"),
    }
    
    # Check for maintenance window configuration
    maintenance_config = erp_system_config.get("maintenance_window", {})
    if not maintenance_config:
        issues.append({
            "field": "maintenance_window",
            "issue": "Maintenance window not configured - integration may cause operational disruption",
            "severity": "high",
        })
    else:
        if not maintenance_config.get("scheduled", False):
            issues.append({
                "field": "maintenance_window.scheduled",
                "issue": "No scheduled maintenance window - integration timing may be risky",
                "severity": "medium",
            })
    
    # Check for load balancing / high availability
    ha_config = erp_system_config.get("high_availability", {})
    if not ha_config.get("enabled", False):
        issues.append({
            "field": "high_availability.enabled",
            "issue": "High availability not enabled - system may be unavailable during integration",
            "severity": "high",
        })
    
    # Check for monitoring and alerting
    monitoring_config = erp_system_config.get("monitoring", {})
    if not monitoring_config.get("enabled", False):
        issues.append({
            "field": "monitoring.enabled",
            "issue": "Monitoring not enabled - integration issues may go undetected",
            "severity": "medium",
        })
    
    evidence_data["issues"] = issues
    evidence_data["ready"] = len([i for i in issues if i["severity"] == "high"]) == 0
    
    return {
        "ready": len([i for i in issues if i["severity"] == "high"]) == 0,
        "issues": issues,
        "evidence": evidence_data,
    }


