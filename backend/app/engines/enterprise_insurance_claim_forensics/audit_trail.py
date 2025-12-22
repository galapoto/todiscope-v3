"""Audit trail functionality for forensic analysis of claim transactions."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.evidence.models import EvidenceRecord
from backend.app.core.evidence.service import (
    create_evidence,
    deterministic_evidence_id,
)
from backend.app.engines.enterprise_insurance_claim_forensics.constants import ENGINE_ID
from backend.app.engines.enterprise_insurance_claim_forensics.claims_management import (
    ClaimRecord,
    ClaimTransaction,
)
from backend.app.engines.enterprise_insurance_claim_forensics.errors import ImmutableConflictError

logger = logging.getLogger(__name__)


async def _strict_create_evidence(
    db: AsyncSession,
    *,
    evidence_id: str,
    dataset_version_id: str,
    engine_id: str,
    kind: str,
    payload: dict[str, Any],
    created_at: datetime,
) -> EvidenceRecord:
    """
    Create evidence with immutability conflict detection.

    Follows the pattern from other engines for consistency.
    """
    existing = await db.scalar(select(EvidenceRecord).where(EvidenceRecord.evidence_id == evidence_id))
    if existing is not None:
        if existing.dataset_version_id != dataset_version_id or existing.engine_id != engine_id or existing.kind != kind:
            logger.warning(
                "INSURANCE_CLAIM_IMMUTABLE_CONFLICT evidence_id_collision evidence_id=%s dataset_version_id=%s",
                evidence_id,
                dataset_version_id,
            )
            raise ImmutableConflictError("EVIDENCE_ID_COLLISION")
        existing_created_at = existing.created_at
        if existing_created_at.tzinfo is None:
            existing_created_at = existing_created_at.replace(tzinfo=timezone.utc)
        normalized_created_at = created_at if created_at.tzinfo is not None else created_at.replace(tzinfo=timezone.utc)
        if existing_created_at != normalized_created_at:
            logger.warning(
                "INSURANCE_CLAIM_IMMUTABLE_CONFLICT evidence_created_at_mismatch evidence_id=%s dataset_version_id=%s",
                evidence_id,
                dataset_version_id,
            )
            raise ImmutableConflictError("IMMUTABLE_EVIDENCE_CREATED_AT_MISMATCH")
        if existing.payload != payload:
            logger.warning(
                "INSURANCE_CLAIM_IMMUTABLE_CONFLICT evidence_payload_mismatch evidence_id=%s dataset_version_id=%s",
                evidence_id,
                dataset_version_id,
            )
            raise ImmutableConflictError("IMMUTABLE_EVIDENCE_MISMATCH")
        return existing
    return await create_evidence(
        db,
        evidence_id=evidence_id,
        dataset_version_id=dataset_version_id,
        engine_id=engine_id,
        kind=kind,
        payload=payload,
        created_at=created_at,
    )


class AuditTrail:
    """Audit trail manager for claim transactions and interactions."""

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

    async def log_claim_creation(
        self,
        claim: ClaimRecord,
        created_at: datetime,
    ) -> str:
        """
        Log a claim creation event.

        Args:
            claim: The claim record
            created_at: Timestamp of creation

        Returns:
            Evidence ID of audit trail entry
        """
        action_details = {
            "action_type": "claim_creation",
            "claim_id": claim.claim_id,
            "policy_number": claim.policy_number,
            "claim_number": claim.claim_number,
            "claim_type": claim.claim_type,
            "claim_status": claim.claim_status,
            "claim_amount": claim.claim_amount,
            "currency": claim.currency,
            "claimant_name": claim.claimant_name,
            "claimant_type": claim.claimant_type,
            "reported_date": claim.reported_date.isoformat(),
            "incident_date": claim.incident_date.isoformat() if claim.incident_date else None,
            "description": claim.description,
            "metadata": claim.metadata,
        }

        evidence_id = deterministic_evidence_id(
            dataset_version_id=self.dataset_version_id,
            engine_id=ENGINE_ID,
            kind="audit_trail",
            stable_key=f"claim_creation_{claim.claim_id}",
        )

        evidence = await _strict_create_evidence(
            self.db,
            evidence_id=evidence_id,
            dataset_version_id=self.dataset_version_id,
            engine_id=ENGINE_ID,
            kind="audit_trail",
            payload={
                "action": "claim_creation",
                "timestamp": created_at.isoformat(),
                "details": action_details,
            },
            created_at=created_at,
        )

        self._entries.append({
            "evidence_id": evidence_id,
            "action_type": "claim_creation",
            "claim_id": claim.claim_id,
            "timestamp": created_at.isoformat(),
        })

        return evidence_id

    async def log_claim_update(
        self,
        claim_id: str,
        update_details: dict[str, Any],
        updated_at: datetime,
    ) -> str:
        """
        Log a claim update event.

        Args:
            claim_id: The claim ID
            update_details: Details of what was updated
            updated_at: Timestamp of update

        Returns:
            Evidence ID of audit trail entry
        """
        action_details = {
            "action_type": "claim_update",
            "claim_id": claim_id,
            "update_details": update_details,
        }

        evidence_id = deterministic_evidence_id(
            dataset_version_id=self.dataset_version_id,
            engine_id=ENGINE_ID,
            kind="audit_trail",
            stable_key=f"claim_update_{claim_id}_{updated_at.isoformat()}",
        )

        evidence = await _strict_create_evidence(
            self.db,
            evidence_id=evidence_id,
            dataset_version_id=self.dataset_version_id,
            engine_id=ENGINE_ID,
            kind="audit_trail",
            payload={
                "action": "claim_update",
                "timestamp": updated_at.isoformat(),
                "details": action_details,
            },
            created_at=updated_at,
        )

        self._entries.append({
            "evidence_id": evidence_id,
            "action_type": "claim_update",
            "claim_id": claim_id,
            "timestamp": updated_at.isoformat(),
        })

        return evidence_id

    async def log_transaction(
        self,
        transaction: ClaimTransaction,
        created_at: datetime,
    ) -> str:
        """
        Log a claim transaction event.

        Args:
            transaction: The transaction record
            created_at: Timestamp of transaction

        Returns:
            Evidence ID of audit trail entry
        """
        action_details = {
            "action_type": "transaction",
            "transaction_id": transaction.transaction_id,
            "claim_id": transaction.claim_id,
            "transaction_type": transaction.transaction_type,
            "amount": transaction.amount,
            "currency": transaction.currency,
            "transaction_date": transaction.transaction_date.isoformat(),
            "description": transaction.description,
            "metadata": transaction.metadata,
        }

        evidence_id = deterministic_evidence_id(
            dataset_version_id=self.dataset_version_id,
            engine_id=ENGINE_ID,
            kind="audit_trail",
            stable_key=f"transaction_{transaction.transaction_id}",
        )

        evidence = await _strict_create_evidence(
            self.db,
            evidence_id=evidence_id,
            dataset_version_id=self.dataset_version_id,
            engine_id=ENGINE_ID,
            kind="audit_trail",
            payload={
                "action": "transaction",
                "timestamp": created_at.isoformat(),
                "details": action_details,
            },
            created_at=created_at,
        )

        self._entries.append({
            "evidence_id": evidence_id,
            "action_type": "transaction",
            "transaction_id": transaction.transaction_id,
            "claim_id": transaction.claim_id,
            "timestamp": created_at.isoformat(),
        })

        return evidence_id

    async def log_validation_result(
        self,
        claim_id: str,
        validation_result: dict[str, Any],
        validated_at: datetime,
    ) -> str:
        """
        Log a validation result.

        Args:
            claim_id: The claim ID
            validation_result: The validation result
            validated_at: Timestamp of validation

        Returns:
            Evidence ID of audit trail entry
        """
        action_details = {
            "action_type": "validation",
            "claim_id": claim_id,
            "validation_result": validation_result,
        }

        evidence_id = deterministic_evidence_id(
            dataset_version_id=self.dataset_version_id,
            engine_id=ENGINE_ID,
            kind="audit_trail",
            stable_key=f"validation_{claim_id}_{validated_at.isoformat()}",
        )

        evidence = await _strict_create_evidence(
            self.db,
            evidence_id=evidence_id,
            dataset_version_id=self.dataset_version_id,
            engine_id=ENGINE_ID,
            kind="audit_trail",
            payload={
                "action": "validation",
                "timestamp": validated_at.isoformat(),
                "details": action_details,
            },
            created_at=validated_at,
        )

        self._entries.append({
            "evidence_id": evidence_id,
            "action_type": "validation",
            "claim_id": claim_id,
            "timestamp": validated_at.isoformat(),
        })

        return evidence_id

    async def log_forensic_analysis(
        self,
        claim_id: str,
        analysis_type: str,
        analysis_result: dict[str, Any],
        analyzed_at: datetime,
    ) -> str:
        """
        Log a forensic analysis event.

        Args:
            claim_id: The claim ID
            analysis_type: Type of analysis performed
            analysis_result: Results of the analysis
            analyzed_at: Timestamp of analysis

        Returns:
            Evidence ID of audit trail entry
        """
        action_details = {
            "action_type": "forensic_analysis",
            "claim_id": claim_id,
            "analysis_type": analysis_type,
            "analysis_result": analysis_result,
        }

        evidence_id = deterministic_evidence_id(
            dataset_version_id=self.dataset_version_id,
            engine_id=ENGINE_ID,
            kind="audit_trail",
            stable_key=f"forensic_analysis_{claim_id}_{analysis_type}_{analyzed_at.isoformat()}",
        )

        evidence = await _strict_create_evidence(
            self.db,
            evidence_id=evidence_id,
            dataset_version_id=self.dataset_version_id,
            engine_id=ENGINE_ID,
            kind="audit_trail",
            payload={
                "action": "forensic_analysis",
                "timestamp": analyzed_at.isoformat(),
                "details": action_details,
            },
            created_at=analyzed_at,
        )

        self._entries.append({
            "evidence_id": evidence_id,
            "action_type": "forensic_analysis",
            "claim_id": claim_id,
            "analysis_type": analysis_type,
            "timestamp": analyzed_at.isoformat(),
        })

        return evidence_id

    def get_entries(self) -> list[dict[str, Any]]:
        """Get all audit trail entries logged in this session."""
        return self._entries.copy()

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of audit trail entries."""
        action_counts = {}
        for entry in self._entries:
            action_type = entry.get("action_type", "unknown")
            action_counts[action_type] = action_counts.get(action_type, 0) + 1

        return {
            "total_entries": len(self._entries),
            "action_counts": action_counts,
            "dataset_version_id": self.dataset_version_id,
        }

