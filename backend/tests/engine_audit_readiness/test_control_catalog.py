"""
Test Control Catalog Creation

Tests to validate control catalog functionality, ensuring all control
attributes are correctly linked and managed.
"""
from __future__ import annotations

import pytest

from backend.app.engines.audit_readiness.control_catalog import (
    ControlCatalog,
    load_control_catalog,
)
from backend.app.engines.audit_readiness.errors import ControlCatalogError
from backend.app.engines.audit_readiness.errors import RegulatoryFrameworkNotFoundError


class TestControlCatalogValidation:
    """Test control catalog validation."""

    def test_validate_empty_catalog(self):
        """Test validation of empty catalog."""
        catalog = ControlCatalog({})
        # Empty catalog should be valid (no frameworks)
        assert catalog.validate_catalog() is True

    def test_validate_valid_catalog(self):
        """Test validation of valid catalog structure."""
        catalog_data = {
            "frameworks": {
                "framework_1": {
                    "metadata": {"name": "Test Framework", "version": "v1"},
                    "controls": [
                        {
                            "control_id": "ctrl_001",
                            "control_name": "Access Control",
                            "critical": True,
                            "required_evidence_types": ["evidence_type_1"],
                        }
                    ],
                }
            }
        }
        catalog = ControlCatalog(catalog_data)
        assert catalog.validate_catalog() is True

    def test_validate_invalid_catalog_not_dict(self):
        """Test validation fails when catalog is not a dictionary."""
        catalog = ControlCatalog("not a dict")
        with pytest.raises(ControlCatalogError, match="CONTROL_CATALOG_INVALID"):
            catalog.validate_catalog()

    def test_validate_invalid_frameworks_not_dict(self):
        """Test validation fails when frameworks is not a dictionary."""
        catalog_data = {"frameworks": "not a dict"}
        catalog = ControlCatalog(catalog_data)
        with pytest.raises(ControlCatalogError, match="CONTROL_CATALOG_INVALID"):
            catalog.validate_catalog()

    def test_validate_invalid_framework_not_dict(self):
        """Test validation fails when framework data is not a dictionary."""
        catalog_data = {"frameworks": {"framework_1": "not a dict"}}
        catalog = ControlCatalog(catalog_data)
        with pytest.raises(ControlCatalogError, match="CONTROL_CATALOG_INVALID"):
            catalog.validate_catalog()

    def test_validate_invalid_controls_not_list(self):
        """Test validation fails when controls is not a list."""
        catalog_data = {
            "frameworks": {
                "framework_1": {
                    "controls": "not a list"
                }
            }
        }
        catalog = ControlCatalog(catalog_data)
        with pytest.raises(ControlCatalogError, match="CONTROL_CATALOG_INVALID"):
            catalog.validate_catalog()

    def test_validate_invalid_control_not_dict(self):
        """Test validation fails when control is not a dictionary."""
        catalog_data = {
            "frameworks": {
                "framework_1": {
                    "controls": ["not a dict"]
                }
            }
        }
        catalog = ControlCatalog(catalog_data)
        with pytest.raises(ControlCatalogError, match="CONTROL_CATALOG_INVALID"):
            catalog.validate_catalog()

    def test_validate_missing_control_id(self):
        """Test validation fails when control_id is missing."""
        catalog_data = {
            "frameworks": {
                "framework_1": {
                    "controls": [
                        {
                            "control_name": "Access Control",
                        }
                    ]
                }
            }
        }
        catalog = ControlCatalog(catalog_data)
        with pytest.raises(ControlCatalogError, match="CONTROL_CATALOG_INVALID"):
            catalog.validate_catalog()


class TestControlCatalogRetrieval:
    """Test control catalog retrieval methods."""

    def test_get_framework_catalog_success(self):
        """Test successful framework catalog retrieval."""
        catalog_data = {
            "frameworks": {
                "framework_1": {
                    "metadata": {"name": "Test Framework", "version": "v1"},
                    "controls": [
                        {
                            "control_id": "ctrl_001",
                            "control_name": "Access Control",
                        }
                    ],
                }
            }
        }
        catalog = ControlCatalog(catalog_data)
        framework_catalog = catalog.get_framework_catalog("framework_1")
        assert framework_catalog["metadata"]["name"] == "Test Framework"
        assert len(framework_catalog["controls"]) == 1

    def test_get_framework_catalog_not_found(self):
        """Test framework catalog retrieval when framework doesn't exist."""
        catalog = ControlCatalog({})
        with pytest.raises(RegulatoryFrameworkNotFoundError):
            catalog.get_framework_catalog("nonexistent_framework")

    def test_get_controls_for_framework(self):
        """Test getting controls for a framework."""
        catalog_data = {
            "frameworks": {
                "framework_1": {
                    "controls": [
                        {
                            "control_id": "ctrl_001",
                            "control_name": "Access Control",
                        },
                        {
                            "control_id": "ctrl_002",
                            "control_name": "Data Encryption",
                        }
                    ],
                }
            }
        }
        catalog = ControlCatalog(catalog_data)
        controls = catalog.get_controls_for_framework("framework_1")
        assert len(controls) == 2
        assert controls[0]["control_id"] == "ctrl_001"
        assert controls[1]["control_id"] == "ctrl_002"

    def test_get_required_evidence_types(self):
        """Test getting required evidence types for controls."""
        catalog_data = {
            "frameworks": {
                "framework_1": {
                    "controls": [
                        {
                            "control_id": "ctrl_001",
                            "required_evidence_types": ["ev_type_1", "ev_type_2"],
                        },
                        {
                            "control_id": "ctrl_002",
                            "required_evidence_types": ["ev_type_3"],
                        }
                    ],
                }
            }
        }
        catalog = ControlCatalog(catalog_data)
        evidence_map = catalog.get_required_evidence_types("framework_1")
        assert evidence_map["ctrl_001"] == ["ev_type_1", "ev_type_2"]
        assert evidence_map["ctrl_002"] == ["ev_type_3"]

    def test_get_framework_metadata(self):
        """Test getting framework metadata."""
        catalog_data = {
            "frameworks": {
                "framework_1": {
                    "metadata": {
                        "name": "Test Framework",
                        "version": "v1",
                        "description": "A test framework",
                    },
                    "controls": [],
                }
            }
        }
        catalog = ControlCatalog(catalog_data)
        metadata = catalog.get_framework_metadata("framework_1")
        assert metadata["name"] == "Test Framework"
        assert metadata["version"] == "v1"
        assert metadata["description"] == "A test framework"


class TestLoadControlCatalog:
    """Test control catalog loading function."""

    def test_load_valid_catalog(self):
        """Test loading a valid catalog."""
        catalog_data = {
            "frameworks": {
                "framework_1": {
                    "metadata": {"name": "Test Framework", "version": "v1"},
                    "controls": [
                        {
                            "control_id": "ctrl_001",
                            "control_name": "Access Control",
                        }
                    ],
                }
            }
        }
        catalog = load_control_catalog(catalog_data)
        assert isinstance(catalog, ControlCatalog)
        assert catalog.validate_catalog() is True

    def test_load_invalid_catalog(self):
        """Test loading an invalid catalog raises error."""
        catalog_data = {
            "frameworks": {
                "framework_1": {
                    "controls": [
                        {
                            # Missing control_id
                            "control_name": "Access Control",
                        }
                    ],
                }
            }
        }
        with pytest.raises(ControlCatalogError):
            load_control_catalog(catalog_data)


class TestControlCatalogAttributes:
    """Test control attribute management."""

    def test_control_attributes_preserved(self):
        """Test that all control attributes are preserved."""
        catalog_data = {
            "frameworks": {
                "framework_1": {
                    "controls": [
                        {
                            "control_id": "ctrl_001",
                            "control_name": "Access Control",
                            "critical": True,
                            "ownership": "IT Security",
                            "status": "active",
                            "risk_type": "security",
                            "required_evidence_types": ["evidence_type_1"],
                            "remediation_guidance": "Implement access controls",
                        }
                    ],
                }
            }
        }
        catalog = ControlCatalog(catalog_data)
        controls = catalog.get_controls_for_framework("framework_1")
        control = controls[0]
        
        assert control["control_id"] == "ctrl_001"
        assert control["control_name"] == "Access Control"
        assert control["critical"] is True
        assert control["ownership"] == "IT Security"
        assert control["status"] == "active"
        assert control["risk_type"] == "security"
        assert control["required_evidence_types"] == ["evidence_type_1"]
        assert control["remediation_guidance"] == "Implement access controls"

    def test_multiple_frameworks(self):
        """Test catalog with multiple frameworks."""
        catalog_data = {
            "frameworks": {
                "framework_1": {
                    "metadata": {"name": "Framework 1", "version": "v1"},
                    "controls": [
                        {"control_id": "ctrl_001", "control_name": "Control 1"}
                    ],
                },
                "framework_2": {
                    "metadata": {"name": "Framework 2", "version": "v1"},
                    "controls": [
                        {"control_id": "ctrl_002", "control_name": "Control 2"}
                    ],
                }
            }
        }
        catalog = ControlCatalog(catalog_data)
        
        controls_1 = catalog.get_controls_for_framework("framework_1")
        controls_2 = catalog.get_controls_for_framework("framework_2")
        
        assert len(controls_1) == 1
        assert len(controls_2) == 1
        assert controls_1[0]["control_id"] == "ctrl_001"
        assert controls_2[0]["control_id"] == "ctrl_002"

