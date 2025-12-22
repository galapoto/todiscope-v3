"""
Leakage Evidence Emission Engine for Engine #2

FF-4: One evidence bundle per leakage instance, immutable, dataset-bound, replayable.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.evidence import create_evidence, deterministic_evidence_id
from backend.app.engines.financial_forensics.engine import ENGINE_ID
from backend.app.engines.financial_forensics.leakage.evidence_schema_v1 import (
    LeakageEvidenceSchemaV1,
    validate_leakage_evidence_schema_v1,
)


async def emit_leakage_evidence(
    db: AsyncSession,
    *,
    dataset_version_id: str,
    run_id: str,
    leakage_id: str,
    evidence_schema: LeakageEvidenceSchemaV1,
    created_at: datetime,
) -> str:
    """
    Emit leakage evidence bundle (one per leakage instance, immutable, dataset-bound).
    
    Args:
        db: Database session
        dataset_version_id: Dataset version ID
        run_id: Run ID that produced this leakage
        leakage_id: Leakage instance ID
        evidence_schema: Complete leakage evidence schema v1
        created_at: Deterministic timestamp
    
    Returns:
        Evidence ID
    
    Raises:
        LeakageEvidenceSchemaViolationError: If evidence schema is incomplete
    """
    # Validate evidence schema completeness
    validate_leakage_evidence_schema_v1(evidence_schema)
    
    # Convert evidence schema to payload dict
    payload = {
        "typology_assignment": {
            "leakage_type": evidence_schema.typology_assignment.leakage_type,
            "assignment_rule_id": evidence_schema.typology_assignment.assignment_rule_id,
            "assignment_rule_version": evidence_schema.typology_assignment.assignment_rule_version,
            "assignment_criteria": evidence_schema.typology_assignment.assignment_criteria,
            "assignment_confidence": evidence_schema.typology_assignment.assignment_confidence,
            "direction_convention": evidence_schema.typology_assignment.direction_convention,
            "direction_source": evidence_schema.typology_assignment.direction_source,
        },
        "exposure_derivation": {
            "exposure_amount": str(evidence_schema.exposure_derivation.exposure_amount) if evidence_schema.exposure_derivation.exposure_amount else None,
            "exposure_min": str(evidence_schema.exposure_derivation.exposure_min) if evidence_schema.exposure_derivation.exposure_min else None,
            "exposure_max": str(evidence_schema.exposure_derivation.exposure_max) if evidence_schema.exposure_derivation.exposure_max else None,
            "exposure_currency": evidence_schema.exposure_derivation.exposure_currency,
            "exposure_basis": evidence_schema.exposure_derivation.exposure_basis,
            "exposure_currency_mode": evidence_schema.exposure_derivation.exposure_currency_mode,
            "fx_artifact_id": evidence_schema.exposure_derivation.fx_artifact_id,
            "fx_artifact_sha256": evidence_schema.exposure_derivation.fx_artifact_sha256,
            "rounding_mode": evidence_schema.exposure_derivation.rounding_mode,
            "base_currency": evidence_schema.exposure_derivation.base_currency,
            "derivation_method": evidence_schema.exposure_derivation.derivation_method,
            "derivation_inputs": evidence_schema.exposure_derivation.derivation_inputs,
            "derivation_confidence": evidence_schema.exposure_derivation.derivation_confidence,
        },
        "finding_references": {
            "related_finding_ids": evidence_schema.finding_references.related_finding_ids,
            "finding_rule_ids": evidence_schema.finding_references.finding_rule_ids,
            "finding_rule_versions": evidence_schema.finding_references.finding_rule_versions,
            "finding_confidences": evidence_schema.finding_references.finding_confidences,
            "finding_evidence_ids": evidence_schema.finding_references.finding_evidence_ids,
            "match_outcome": evidence_schema.finding_references.match_outcome,
            "match_search_scope": evidence_schema.finding_references.match_search_scope,
        },
        "primary_records": {
            "invoice_record_id": evidence_schema.primary_records.invoice_record_id,
            "invoice_source_system": evidence_schema.primary_records.invoice_source_system,
            "invoice_source_record_id": evidence_schema.primary_records.invoice_source_record_id,
            "invoice_canonical_record_id": evidence_schema.primary_records.invoice_canonical_record_id,
            "counterpart_record_ids": evidence_schema.primary_records.counterpart_record_ids,
            "counterpart_source_systems": evidence_schema.primary_records.counterpart_source_systems,
            "counterpart_source_record_ids": evidence_schema.primary_records.counterpart_source_record_ids,
            "counterpart_canonical_record_ids": evidence_schema.primary_records.counterpart_canonical_record_ids,
            "is_intercompany": evidence_schema.primary_records.is_intercompany,
            "intercompany_counterparty_ids": evidence_schema.primary_records.intercompany_counterparty_ids,
            "intercompany_detection_method": evidence_schema.primary_records.intercompany_detection_method,
        },
        "run_id": run_id,  # Link to run that produced this leakage
        "leakage_id": leakage_id,  # Link to leakage instance
    }
    
    # Generate deterministic evidence ID
    evidence_id = deterministic_evidence_id(
        dataset_version_id=dataset_version_id,
        engine_id=ENGINE_ID,
        kind="leakage_evidence",
        stable_key=f"{run_id}|{leakage_id}",
    )
    
    # Create evidence record (immutable, dataset-bound)
    await create_evidence(
        db,
        evidence_id=evidence_id,
        dataset_version_id=dataset_version_id,
        engine_id=ENGINE_ID,
        kind="leakage_evidence",
        payload=payload,
        created_at=created_at,
    )
    
    return evidence_id


