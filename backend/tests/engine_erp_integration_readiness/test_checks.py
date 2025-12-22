"""Tests for ERP integration readiness checks."""
from __future__ import annotations

import pytest

from backend.app.engines.erp_integration_readiness.readiness import (
    check_erp_system_availability,
    check_data_integrity_requirements,
    check_operational_readiness,
)
from backend.app.engines.erp_integration_readiness.compatibility import (
    check_infrastructure_compatibility,
    check_version_compatibility,
    check_security_compatibility,
)
from backend.app.engines.erp_integration_readiness.risk_assessment import (
    assess_downtime_risk,
    assess_data_integrity_risk,
    assess_compatibility_risk,
)


@pytest.fixture
def sample_erp_config():
    """Return a sample ERP system configuration for testing."""
    return {
        "system_id": "erp_system_001",
        "connection_type": "api",
        "api_endpoint": "https://erp.example.com/api",
        "version": "2.1.0",
        "api_version": "v2",
        "high_availability": {
            "enabled": True,
        },
        "backup_config": {
            "enabled": True,
        },
        "transaction_support": {
            "enabled": True,
        },
        "maintenance_window": {
            "scheduled": True,
        },
        "monitoring": {
            "enabled": True,
        },
        "data_validation": {
            "schema_validation": True,
            "data_type_validation": True,
        },
        "security": {
            "encryption": {
                "required": "TLS 1.2",
            },
            "tls_version": "1.2",
            "certificate_requirements": {
                "required": True,
            },
        },
    }


@pytest.fixture
def sample_infrastructure_config():
    """Return a sample infrastructure configuration for testing."""
    return {
        "supported_protocols": ["REST", "SOAP", "JDBC"],
        "supported_data_formats": ["JSON", "XML", "CSV"],
        "supported_auth_methods": ["OAuth2", "API Key", "Basic Auth"],
        "network": {
            "available_bandwidth_mbps": 100,
        },
        "required_erp_versions": {
            "min_version": "1.0.0",
            "max_version": "3.0.0",
        },
        "required_api_versions": ["v1", "v2"],
        "security": {
            "encryption": {
                "supported": ["TLS 1.2", "TLS 1.3"],
            },
            "supported_tls_versions": ["1.2", "1.3"],
            "certificate_support": {
                "enabled": True,
            },
        },
    }


def test_check_erp_system_availability_valid(sample_erp_config):
    """Test ERP system availability check with valid configuration."""
    result = check_erp_system_availability(
        erp_system_config=sample_erp_config,
        dataset_version_id="test-dv-1",
    )
    
    assert result["ready"] is True
    assert len(result["issues"]) == 0
    assert result["evidence"]["check_type"] == "erp_system_availability"
    assert result["evidence"]["erp_system_id"] == "erp_system_001"


def test_check_erp_system_availability_missing_fields():
    """Test ERP system availability check with missing required fields."""
    invalid_config = {
        "system_id": "erp_system_001",
        # Missing connection_type and api_endpoint
    }
    
    result = check_erp_system_availability(
        erp_system_config=invalid_config,
        dataset_version_id="test-dv-1",
    )
    
    assert result["ready"] is False
    assert len(result["issues"]) > 0
    assert any(issue["field"] == "connection_type" for issue in result["issues"])


def test_check_erp_system_availability_invalid_connection_type():
    """Test ERP system availability check with invalid connection type."""
    invalid_config = {
        "system_id": "erp_system_001",
        "connection_type": "invalid_type",
        "api_endpoint": "https://example.com/api",
    }
    
    result = check_erp_system_availability(
        erp_system_config=invalid_config,
        dataset_version_id="test-dv-1",
    )
    
    assert result["ready"] is False
    assert any("invalid connection type" in issue["issue"].lower() for issue in result["issues"])


def test_check_data_integrity_requirements_valid(sample_erp_config):
    """Test data integrity requirements check with valid configuration."""
    result = check_data_integrity_requirements(
        erp_system_config=sample_erp_config,
        dataset_version_id="test-dv-1",
    )
    
    assert result["ready"] is True
    assert len([i for i in result["issues"] if i["severity"] == "high"]) == 0


def test_check_data_integrity_requirements_missing_backup():
    """Test data integrity requirements check with missing backup configuration."""
    config_without_backup = {
        "system_id": "erp_system_001",
        "connection_type": "api",
        # Missing backup_config
    }
    
    result = check_data_integrity_requirements(
        erp_system_config=config_without_backup,
        dataset_version_id="test-dv-1",
    )
    
    assert result["ready"] is False
    assert any("backup" in issue["field"].lower() for issue in result["issues"])


def test_check_operational_readiness_valid(sample_erp_config):
    """Test operational readiness check with valid configuration."""
    result = check_operational_readiness(
        erp_system_config=sample_erp_config,
        dataset_version_id="test-dv-1",
    )
    
    assert result["ready"] is True
    assert len([i for i in result["issues"] if i["severity"] == "high"]) == 0


def test_check_operational_readiness_missing_ha():
    """Test operational readiness check with high availability disabled."""
    config_without_ha = {
        "system_id": "erp_system_001",
        "connection_type": "api",
        "high_availability": {
            "enabled": False,
        },
    }
    
    result = check_operational_readiness(
        erp_system_config=config_without_ha,
        dataset_version_id="test-dv-1",
    )
    
    assert result["ready"] is False
    assert any("high_availability" in issue["field"] for issue in result["issues"])


def test_check_infrastructure_compatibility_valid(sample_erp_config, sample_infrastructure_config):
    """Test infrastructure compatibility check with compatible configurations."""
    result = check_infrastructure_compatibility(
        erp_system_config=sample_erp_config,
        infrastructure_config=sample_infrastructure_config,
        dataset_version_id="test-dv-1",
    )
    
    assert result["compatible"] is True
    assert len([i for i in result["issues"] if i["severity"] == "high"]) == 0


def test_check_infrastructure_compatibility_incompatible_protocol():
    """Test infrastructure compatibility check with incompatible protocol."""
    erp_config = {
        "system_id": "erp_system_001",
        "connection_type": "api",
        "protocol": "FTP",  # Not in supported protocols
    }
    infra_config = {
        "supported_protocols": ["REST", "SOAP"],
    }
    
    result = check_infrastructure_compatibility(
        erp_system_config=erp_config,
        infrastructure_config=infra_config,
        dataset_version_id="test-dv-1",
    )
    
    assert result["compatible"] is False
    assert any("protocol" in issue["field"].lower() for issue in result["issues"])


def test_check_version_compatibility_valid(sample_erp_config, sample_infrastructure_config):
    """Test version compatibility check with compatible versions."""
    result = check_version_compatibility(
        erp_system_config=sample_erp_config,
        infrastructure_config=sample_infrastructure_config,
        dataset_version_id="test-dv-1",
    )
    
    assert result["compatible"] is True
    assert len([i for i in result["issues"] if i["severity"] == "high"]) == 0


def test_check_version_compatibility_incompatible_version():
    """Test version compatibility check with incompatible version."""
    erp_config = {
        "system_id": "erp_system_001",
        "connection_type": "api",
        "version": "4.0.0",  # Above max version
    }
    infra_config = {
        "required_erp_versions": {
            "min_version": "1.0.0",
            "max_version": "3.0.0",
        },
    }
    
    result = check_version_compatibility(
        erp_system_config=erp_config,
        infrastructure_config=infra_config,
        dataset_version_id="test-dv-1",
    )
    
    assert result["compatible"] is False
    assert any("version" in issue["field"].lower() for issue in result["issues"])


def test_check_security_compatibility_valid(sample_erp_config, sample_infrastructure_config):
    """Test security compatibility check with compatible security settings."""
    result = check_security_compatibility(
        erp_system_config=sample_erp_config,
        infrastructure_config=sample_infrastructure_config,
        dataset_version_id="test-dv-1",
    )
    
    assert result["compatible"] is True
    assert len([i for i in result["issues"] if i["severity"] == "high"]) == 0


def test_check_security_compatibility_incompatible_encryption():
    """Test security compatibility check with incompatible encryption."""
    erp_config = {
        "system_id": "erp_system_001",
        "connection_type": "api",
        "security": {
            "encryption": {
                "required": "AES-128",  # Not in supported list
            },
        },
    }
    infra_config = {
        "security": {
            "encryption": {
                "supported": ["TLS 1.2", "TLS 1.3"],
            },
        },
    }
    
    result = check_security_compatibility(
        erp_system_config=erp_config,
        infrastructure_config=infra_config,
        dataset_version_id="test-dv-1",
    )
    
    assert result["compatible"] is False
    assert any("encryption" in issue["field"].lower() for issue in result["issues"])


def test_assess_downtime_risk_low(sample_erp_config):
    """Test downtime risk assessment with low risk configuration."""
    readiness_results = {
        "operational_readiness": {
            "ready": True,
            "issues": [],
        },
    }
    compatibility_results = {
        "infrastructure_compatibility": {
            "compatible": True,
            "issues": [],
        },
    }
    
    result = assess_downtime_risk(
        erp_system_config=sample_erp_config,
        readiness_results=readiness_results,
        compatibility_results=compatibility_results,
        dataset_version_id="test-dv-1",
    )
    
    assert result["risk_level"] in ("low", "medium")
    assert result["risk_score"] < 0.5


def test_assess_downtime_risk_high():
    """Test downtime risk assessment with high risk configuration."""
    erp_config = {
        "system_id": "erp_system_001",
        "connection_type": "api",
        "high_availability": {
            "enabled": False,
        },
    }
    readiness_results = {
        "operational_readiness": {
            "ready": False,
            "issues": [
                {"field": "high_availability.enabled", "severity": "high"},
            ],
        },
    }
    compatibility_results = {}
    
    result = assess_downtime_risk(
        erp_system_config=erp_config,
        readiness_results=readiness_results,
        compatibility_results=compatibility_results,
        dataset_version_id="test-dv-1",
    )
    
    assert result["risk_level"] in ("high", "critical")
    assert result["risk_score"] >= 0.5


def test_assess_data_integrity_risk_low(sample_erp_config):
    """Test data integrity risk assessment with low risk configuration."""
    readiness_results = {
        "data_integrity_requirements": {
            "ready": True,
            "issues": [],
        },
    }
    
    result = assess_data_integrity_risk(
        erp_system_config=sample_erp_config,
        readiness_results=readiness_results,
        dataset_version_id="test-dv-1",
    )
    
    assert result["risk_level"] in ("low", "medium")
    assert result["risk_score"] < 0.5


def test_assess_data_integrity_risk_high():
    """Test data integrity risk assessment with high risk configuration."""
    erp_config = {
        "system_id": "erp_system_001",
        "connection_type": "api",
        "backup_config": {
            "enabled": False,
        },
    }
    readiness_results = {
        "data_integrity_requirements": {
            "ready": False,
            "issues": [
                {"field": "backup_config.enabled", "severity": "high"},
            ],
        },
    }
    
    result = assess_data_integrity_risk(
        erp_system_config=erp_config,
        readiness_results=readiness_results,
        dataset_version_id="test-dv-1",
    )
    
    assert result["risk_level"] in ("high", "critical")
    assert result["risk_score"] >= 0.5


def test_assess_compatibility_risk_low():
    """Test compatibility risk assessment with low risk configuration."""
    compatibility_results = {
        "infrastructure_compatibility": {
            "compatible": True,
            "issues": [],
        },
        "version_compatibility": {
            "compatible": True,
            "issues": [],
        },
        "security_compatibility": {
            "compatible": True,
            "issues": [],
        },
    }
    
    result = assess_compatibility_risk(
        compatibility_results=compatibility_results,
        dataset_version_id="test-dv-1",
    )
    
    assert result["risk_level"] in ("low", "medium")
    assert result["risk_score"] < 0.5


def test_assess_compatibility_risk_high():
    """Test compatibility risk assessment with high risk configuration."""
    compatibility_results = {
        "infrastructure_compatibility": {
            "compatible": False,
            "issues": [
                {"field": "protocol", "severity": "high"},
            ],
        },
        "version_compatibility": {
            "compatible": True,
            "issues": [],
        },
        "security_compatibility": {
            "compatible": False,
            "issues": [
                {"field": "encryption", "severity": "high"},
            ],
        },
    }
    
    result = assess_compatibility_risk(
        compatibility_results=compatibility_results,
        dataset_version_id="test-dv-1",
    )
    
    assert result["risk_level"] in ("high", "critical")
    assert result["risk_score"] >= 0.5


