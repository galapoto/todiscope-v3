"""
Audit Trail Setup for Audit Readiness Engine

Provides traceability for compliance mapping and control assessments.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.engines.audit_readiness.evidence_integration import create_audit_trail_entry


class AuditTrail:
    """
    Audit trail manager for compliance mapping and control assessments.
    
    Ensures all actions are traceable and auditable.
    """
    
    def __init__(self, db: AsyncSession, dataset_version_id: str):
        """
        Initialize audit trail.
        
        Args:
            db: Database session
            dataset_version_id: Dataset version ID
        """
        self.db = db
        self.dataset_version_id = dataset_version_id
        self._entries: list[dict[str, Any]] = []
    
    async def log_compliance_mapping(
        self,
        framework_id: str,
        mapping_details: dict[str, Any],
        created_at: datetime,
    ) -> str:
        """
        Log a compliance mapping action.
        
        Args:
            framework_id: Regulatory framework ID
            mapping_details: Mapping details
            created_at: Timestamp
    
        Returns:
            Evidence ID of audit trail entry
        """
        action_details = {
            "framework_id": framework_id,
            "mapping_details": mapping_details,
        }
        
        evidence_id = await create_audit_trail_entry(
            self.db,
            self.dataset_version_id,
            "compliance_mapping",
            action_details,
            created_at,
        )
        
        self._entries.append({
            "evidence_id": evidence_id,
            "action_type": "compliance_mapping",
            "framework_id": framework_id,
            "timestamp": created_at.isoformat(),
        })
        
        return evidence_id
    
    async def log_control_assessment(
        self,
        framework_id: str,
        control_id: str,
        assessment_result: dict[str, Any],
        created_at: datetime,
    ) -> str:
        """
        Log a control assessment action.
        
        Args:
            framework_id: Regulatory framework ID
            control_id: Control ID
            assessment_result: Assessment result details
            created_at: Timestamp
    
        Returns:
            Evidence ID of audit trail entry
        """
        action_details = {
            "framework_id": framework_id,
            "control_id": control_id,
            "assessment_result": assessment_result,
        }
        
        evidence_id = await create_audit_trail_entry(
            self.db,
            self.dataset_version_id,
            "control_assessment",
            action_details,
            created_at,
        )
        
        self._entries.append({
            "evidence_id": evidence_id,
            "action_type": "control_assessment",
            "framework_id": framework_id,
            "control_id": control_id,
            "timestamp": created_at.isoformat(),
        })
        
        return evidence_id
    
    async def log_regulatory_check(
        self,
        framework_id: str,
        check_result: dict[str, Any],
        created_at: datetime,
    ) -> str:
        """
        Log a regulatory check execution.
        
        Args:
            framework_id: Regulatory framework ID
            check_result: Check result details
            created_at: Timestamp
    
        Returns:
            Evidence ID of audit trail entry
        """
        action_details = {
            "framework_id": framework_id,
            "check_result": check_result,
        }
        
        evidence_id = await create_audit_trail_entry(
            self.db,
            self.dataset_version_id,
            "regulatory_check",
            action_details,
            created_at,
        )
        
        self._entries.append({
            "evidence_id": evidence_id,
            "action_type": "regulatory_check",
            "framework_id": framework_id,
            "timestamp": created_at.isoformat(),
        })
        
        return evidence_id
    
    def get_entries(self) -> list[dict[str, Any]]:
        """
        Get all audit trail entries (in-memory cache).
        
        Returns:
            List of audit trail entries
        """
        return self._entries.copy()

