"""
Control Catalog Integration for Audit Readiness Engine

Framework-agnostic control catalog interface that integrates with Agent 1's control catalog.
"""
from __future__ import annotations

from typing import Any

from backend.app.engines.audit_readiness.errors import ControlCatalogError, RegulatoryFrameworkNotFoundError


class ControlCatalog:
    """
    Framework-agnostic control catalog interface.
    
    This integrates with Agent 1's control catalog implementation while
    remaining framework-agnostic.
    """
    
    def __init__(self, catalog_data: dict[str, Any] | None = None):
        """
        Initialize control catalog.
        
        Args:
            catalog_data: Control catalog data structure (from Agent 1)
        """
        self._catalog = catalog_data or {}
    
    def get_framework_catalog(self, framework_id: str) -> dict[str, Any]:
        """
        Get control catalog for a specific regulatory framework.
        
        Args:
            framework_id: Regulatory framework identifier
        
        Returns:
            Framework-specific control catalog structure
        
        Raises:
            RegulatoryFrameworkNotFoundError: If framework not found
        """
        frameworks = self._catalog.get("frameworks", {})
        if framework_id not in frameworks:
            raise RegulatoryFrameworkNotFoundError(
                f"REGULATORY_FRAMEWORK_NOT_FOUND: Framework {framework_id} not found in catalog"
            )
        
        return frameworks[framework_id]
    
    def get_controls_for_framework(self, framework_id: str) -> list[dict[str, Any]]:
        """
        Get list of controls for a framework.
        
        Args:
            framework_id: Regulatory framework identifier
        
        Returns:
            List of control definitions
        """
        framework_catalog = self.get_framework_catalog(framework_id)
        return framework_catalog.get("controls", [])
    
    def get_required_evidence_types(self, framework_id: str) -> dict[str, list[str]]:
        """
        Get required evidence types for each control in a framework.
        
        Args:
            framework_id: Regulatory framework identifier
        
        Returns:
            Map of control_id to list of required evidence type identifiers
        """
        framework_catalog = self.get_framework_catalog(framework_id)
        controls = framework_catalog.get("controls", [])
        
        evidence_map: dict[str, list[str]] = {}
        for control in controls:
            control_id = control.get("control_id", "")
            evidence_types = control.get("required_evidence_types", [])
            evidence_map[control_id] = evidence_types
        
        return evidence_map
    
    def get_framework_metadata(self, framework_id: str) -> dict[str, Any]:
        """
        Get metadata for a regulatory framework.
        
        Args:
            framework_id: Regulatory framework identifier
        
        Returns:
            Framework metadata dictionary
        """
        framework_catalog = self.get_framework_catalog(framework_id)
        return framework_catalog.get("metadata", {})
    
    def validate_catalog(self) -> bool:
        """
        Validate control catalog structure.
        
        Returns:
            True if catalog is valid
        
        Raises:
            ControlCatalogError: If catalog structure is invalid
        """
        if not isinstance(self._catalog, dict):
            raise ControlCatalogError("CONTROL_CATALOG_INVALID: Catalog must be a dictionary")
        
        frameworks = self._catalog.get("frameworks", {})
        if not isinstance(frameworks, dict):
            raise ControlCatalogError("CONTROL_CATALOG_INVALID: Frameworks must be a dictionary")
        
        for framework_id, framework_data in frameworks.items():
            if not isinstance(framework_data, dict):
                raise ControlCatalogError(
                    f"CONTROL_CATALOG_INVALID: Framework {framework_id} must be a dictionary"
                )
            
            controls = framework_data.get("controls", [])
            if not isinstance(controls, list):
                raise ControlCatalogError(
                    f"CONTROL_CATALOG_INVALID: Controls for {framework_id} must be a list"
                )
            
            for control in controls:
                if not isinstance(control, dict):
                    raise ControlCatalogError(
                        f"CONTROL_CATALOG_INVALID: Control in {framework_id} must be a dictionary"
                    )
                if "control_id" not in control:
                    raise ControlCatalogError(
                        f"CONTROL_CATALOG_INVALID: Control in {framework_id} missing control_id"
                    )
        
        return True


def load_control_catalog(catalog_data: dict[str, Any]) -> ControlCatalog:
    """
    Load and validate control catalog.
    
    Args:
        catalog_data: Control catalog data structure
    
    Returns:
        Validated ControlCatalog instance
    
    Raises:
        ControlCatalogError: If catalog is invalid
    """
    catalog = ControlCatalog(catalog_data)
    catalog.validate_catalog()
    return catalog

