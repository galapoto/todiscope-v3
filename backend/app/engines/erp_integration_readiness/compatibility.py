"""
System Compatibility Check Logic

This module implements deterministic checks to assess the compatibility of the ERP system
with existing infrastructure and flag potential compatibility issues.

All checks are:
- Deterministic: same inputs produce same outputs
- Immutable: checks do not modify input data
- Traceable: all findings linked to DatasetVersion
"""
from __future__ import annotations

from typing import Any


def check_infrastructure_compatibility(
    *,
    erp_system_config: dict,
    infrastructure_config: dict,
    dataset_version_id: str,
) -> dict[str, Any]:
    """
    Check if ERP system is compatible with existing infrastructure.
    
    Args:
        erp_system_config: ERP system configuration dictionary
        infrastructure_config: Infrastructure configuration dictionary
        dataset_version_id: Dataset version ID for traceability
        
    Returns:
        Dictionary with check result:
        - compatible: bool indicating if systems are compatible
        - issues: list of compatibility issues found
        - evidence: evidence data for traceability
    """
    issues: list[dict[str, Any]] = []
    evidence_data: dict[str, Any] = {
        "check_type": "infrastructure_compatibility",
        "dataset_version_id": dataset_version_id,
        "erp_system_id": erp_system_config.get("system_id", "unknown"),
    }
    
    # Check protocol compatibility
    erp_protocol = erp_system_config.get("protocol", "").lower()
    supported_protocols = infrastructure_config.get("supported_protocols", [])
    if erp_protocol and supported_protocols:
        if erp_protocol not in [p.lower() for p in supported_protocols]:
            issues.append({
                "field": "protocol",
                "issue": f"ERP protocol '{erp_protocol}' not supported by infrastructure. Supported: {supported_protocols}",
                "severity": "high",
            })
    
    # Check data format compatibility
    erp_data_format = erp_system_config.get("data_format", "").lower()
    supported_formats = infrastructure_config.get("supported_data_formats", [])
    if erp_data_format and supported_formats:
        if erp_data_format not in [f.lower() for f in supported_formats]:
            issues.append({
                "field": "data_format",
                "issue": f"ERP data format '{erp_data_format}' not supported. Supported: {supported_formats}",
                "severity": "high",
            })
    
    # Check authentication method compatibility
    erp_auth_method = erp_system_config.get("authentication", {}).get("method", "").lower()
    supported_auth_methods = infrastructure_config.get("supported_auth_methods", [])
    if erp_auth_method and supported_auth_methods:
        if erp_auth_method not in [a.lower() for a in supported_auth_methods]:
            issues.append({
                "field": "authentication.method",
                "issue": f"ERP authentication method '{erp_auth_method}' not supported. Supported: {supported_auth_methods}",
                "severity": "high",
            })
    
    # Check network requirements
    erp_network_requirements = erp_system_config.get("network_requirements", {})
    infrastructure_network = infrastructure_config.get("network", {})
    
    if erp_network_requirements.get("bandwidth_min_mbps"):
        available_bandwidth = infrastructure_network.get("available_bandwidth_mbps", 0)
        if available_bandwidth < erp_network_requirements["bandwidth_min_mbps"]:
            issues.append({
                "field": "network_requirements.bandwidth",
                "issue": f"Insufficient bandwidth: required {erp_network_requirements['bandwidth_min_mbps']} Mbps, available {available_bandwidth} Mbps",
                "severity": "high",
            })
    
    evidence_data["issues"] = issues
    evidence_data["compatible"] = len([i for i in issues if i["severity"] == "high"]) == 0
    
    return {
        "compatible": len([i for i in issues if i["severity"] == "high"]) == 0,
        "issues": issues,
        "evidence": evidence_data,
    }


def check_version_compatibility(
    *,
    erp_system_config: dict,
    infrastructure_config: dict,
    dataset_version_id: str,
) -> dict[str, Any]:
    """
    Check if ERP system version is compatible with infrastructure requirements.
    
    Args:
        erp_system_config: ERP system configuration dictionary
        infrastructure_config: Infrastructure configuration dictionary
        dataset_version_id: Dataset version ID for traceability
        
    Returns:
        Dictionary with check result:
        - compatible: bool indicating if versions are compatible
        - issues: list of version compatibility issues found
        - evidence: evidence data for traceability
    """
    issues: list[dict[str, Any]] = []
    evidence_data: dict[str, Any] = {
        "check_type": "version_compatibility",
        "dataset_version_id": dataset_version_id,
        "erp_system_id": erp_system_config.get("system_id", "unknown"),
    }
    
    erp_version = erp_system_config.get("version", "")
    required_versions = infrastructure_config.get("required_erp_versions", {})
    
    if not erp_version:
        issues.append({
            "field": "version",
            "issue": "ERP system version not specified",
            "severity": "high",
        })
    elif required_versions:
        min_version = required_versions.get("min_version")
        max_version = required_versions.get("max_version")
        
        if min_version and _version_compare(erp_version, min_version) < 0:
            issues.append({
                "field": "version",
                "issue": f"ERP version '{erp_version}' is below minimum required version '{min_version}'",
                "severity": "high",
            })
        
        if max_version and _version_compare(erp_version, max_version) > 0:
            issues.append({
                "field": "version",
                "issue": f"ERP version '{erp_version}' exceeds maximum supported version '{max_version}'",
                "severity": "high",
            })
    
    # Check API version compatibility
    erp_api_version = erp_system_config.get("api_version", "")
    required_api_versions = infrastructure_config.get("required_api_versions", [])
    if erp_api_version and required_api_versions:
        if erp_api_version not in required_api_versions:
            issues.append({
                "field": "api_version",
                "issue": f"ERP API version '{erp_api_version}' not in supported versions: {required_api_versions}",
                "severity": "high",
            })
    
    evidence_data["issues"] = issues
    evidence_data["compatible"] = len([i for i in issues if i["severity"] == "high"]) == 0
    
    return {
        "compatible": len([i for i in issues if i["severity"] == "high"]) == 0,
        "issues": issues,
        "evidence": evidence_data,
    }


def _version_compare(version1: str, version2: str) -> int:
    """
    Compare two version strings.
    
    Returns:
        -1 if version1 < version2
        0 if version1 == version2
        1 if version1 > version2
    """
    def normalize_version(v: str) -> list[int]:
        parts = v.split(".")
        return [int(p) for p in parts if p.isdigit()]
    
    v1_parts = normalize_version(version1)
    v2_parts = normalize_version(version2)
    
    # Pad with zeros to make same length
    max_len = max(len(v1_parts), len(v2_parts))
    v1_parts.extend([0] * (max_len - len(v1_parts)))
    v2_parts.extend([0] * (max_len - len(v2_parts)))
    
    for v1_part, v2_part in zip(v1_parts, v2_parts):
        if v1_part < v2_part:
            return -1
        elif v1_part > v2_part:
            return 1
    
    return 0


def check_security_compatibility(
    *,
    erp_system_config: dict,
    infrastructure_config: dict,
    dataset_version_id: str,
) -> dict[str, Any]:
    """
    Check if ERP system security requirements are compatible with infrastructure.
    
    Args:
        erp_system_config: ERP system configuration dictionary
        infrastructure_config: Infrastructure configuration dictionary
        dataset_version_id: Dataset version ID for traceability
        
    Returns:
        Dictionary with check result:
        - compatible: bool indicating if security requirements are compatible
        - issues: list of security compatibility issues found
        - evidence: evidence data for traceability
    """
    issues: list[dict[str, Any]] = []
    evidence_data: dict[str, Any] = {
        "check_type": "security_compatibility",
        "dataset_version_id": dataset_version_id,
        "erp_system_id": erp_system_config.get("system_id", "unknown"),
    }
    
    # Check encryption requirements
    erp_encryption = erp_system_config.get("security", {}).get("encryption", {})
    infrastructure_encryption = infrastructure_config.get("security", {}).get("encryption", {})
    
    erp_required_encryption = erp_encryption.get("required", "").lower()
    infrastructure_supported = infrastructure_encryption.get("supported", [])
    
    if erp_required_encryption and infrastructure_supported:
        if erp_required_encryption not in [e.lower() for e in infrastructure_supported]:
            issues.append({
                "field": "security.encryption.required",
                "issue": f"Required encryption '{erp_required_encryption}' not supported. Supported: {infrastructure_supported}",
                "severity": "high",
            })
    
    # Check TLS/SSL version requirements
    erp_tls_version = erp_system_config.get("security", {}).get("tls_version", "")
    infrastructure_tls_versions = infrastructure_config.get("security", {}).get("supported_tls_versions", [])
    
    if erp_tls_version and infrastructure_tls_versions:
        if erp_tls_version not in infrastructure_tls_versions:
            issues.append({
                "field": "security.tls_version",
                "issue": f"Required TLS version '{erp_tls_version}' not supported. Supported: {infrastructure_tls_versions}",
                "severity": "high",
            })
    
    # Check certificate requirements
    erp_cert_requirements = erp_system_config.get("security", {}).get("certificate_requirements", {})
    if erp_cert_requirements.get("required", False):
        infrastructure_cert_support = infrastructure_config.get("security", {}).get("certificate_support", {})
        if not infrastructure_cert_support.get("enabled", False):
            issues.append({
                "field": "security.certificate_requirements",
                "issue": "Certificate requirements not supported by infrastructure",
                "severity": "high",
            })
    
    evidence_data["issues"] = issues
    evidence_data["compatible"] = len([i for i in issues if i["severity"] == "high"]) == 0
    
    return {
        "compatible": len([i for i in issues if i["severity"] == "high"]) == 0,
        "issues": issues,
        "evidence": evidence_data,
    }


