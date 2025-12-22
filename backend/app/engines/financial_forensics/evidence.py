"""
Evidence Emission Engine for Engine #2

FF-3: One evidence bundle per finding, immutable, dataset-bound, replayable.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.evidence import create_evidence, deterministic_evidence_id
from backend.app.engines.financial_forensics.engine import ENGINE_ID
from backend.app.engines.financial_forensics.evidence_schema_v1 import (
    EvidenceSchemaV1,
    validate_evidence_schema_v1,
)


def deterministic_finding_id(*, dataset_version_id: str, rule_id: str, rule_version: str, matched_record_ids: tuple[str, ...]) -> str:
    namespace = uuid.UUID("00000000-0000-0000-0000-000000000045")
    stable = "|".join(matched_record_ids)
    return str(uuid.uuid5(namespace, f"{dataset_version_id}|{rule_id}|{rule_version}|{stable}"))


async def emit_finding_evidence(
    db: AsyncSession,
    *,
    dataset_version_id: str,
    finding_id: str,
    evidence_schema: EvidenceSchemaV1,
    created_at: datetime,
) -> str:
    """
    Emit finding evidence bundle (one per finding, immutable, dataset-bound).
    
    Args:
        db: Database session
        dataset_version_id: Dataset version ID
        finding_id: Finding ID
        evidence_schema: Complete evidence schema v1
        created_at: Deterministic timestamp
    
    Returns:
        Evidence ID
    
    Raises:
        EvidenceSchemaViolationError: If evidence schema is incomplete
    """
    # Validate evidence schema completeness
    validate_evidence_schema_v1(evidence_schema)
    
    # Convert evidence schema to payload dict
    payload = {
        "rule_identity": {
            "rule_id": evidence_schema.rule_identity.rule_id,
            "rule_version": evidence_schema.rule_identity.rule_version,
            "framework_version": evidence_schema.rule_identity.framework_version,
            "executed_parameters": evidence_schema.rule_identity.executed_parameters,
        },
        "tolerance": {
            "tolerance_absolute": str(evidence_schema.tolerance.tolerance_absolute)
            if evidence_schema.tolerance and evidence_schema.tolerance.tolerance_absolute is not None
            else None,
            "tolerance_percent": str(evidence_schema.tolerance.tolerance_percent)
            if evidence_schema.tolerance and evidence_schema.tolerance.tolerance_percent is not None
            else None,
            "threshold_applied": str(evidence_schema.tolerance.threshold_applied)
            if evidence_schema.tolerance and evidence_schema.tolerance.threshold_applied is not None
            else None,
            "tolerance_source": evidence_schema.tolerance.tolerance_source if evidence_schema.tolerance else None,
        } if evidence_schema.tolerance else None,
        "amount_comparison": {
            "invoice_amount_original": str(evidence_schema.amount_comparison.invoice_amount_original),
            "invoice_currency_original": evidence_schema.amount_comparison.invoice_currency_original,
            "invoice_amount_converted": str(evidence_schema.amount_comparison.invoice_amount_converted)
            if evidence_schema.amount_comparison.invoice_amount_converted is not None
            else None,
            "counterpart_amounts_original": [str(a) for a in evidence_schema.amount_comparison.counterpart_amounts_original],
            "counterpart_currencies_original": evidence_schema.amount_comparison.counterpart_currencies_original,
            "counterpart_amounts_converted": [str(a) for a in evidence_schema.amount_comparison.counterpart_amounts_converted]
            if evidence_schema.amount_comparison.counterpart_amounts_converted is not None
            else None,
            "sum_counterpart_amount_original": str(evidence_schema.amount_comparison.sum_counterpart_amount_original),
            "sum_counterpart_amount_converted": str(evidence_schema.amount_comparison.sum_counterpart_amount_converted)
            if evidence_schema.amount_comparison.sum_counterpart_amount_converted is not None
            else None,
            "comparison_currency": evidence_schema.amount_comparison.comparison_currency,
            "diff_original": str(evidence_schema.amount_comparison.diff_original),
            "diff_converted": str(evidence_schema.amount_comparison.diff_converted)
            if evidence_schema.amount_comparison.diff_converted is not None
            else None,
        },
        "date_comparison": {
            "invoice_posted_at": evidence_schema.date_comparison.invoice_posted_at,
            "counterpart_posted_at": evidence_schema.date_comparison.counterpart_posted_at,
            "date_diffs_days": evidence_schema.date_comparison.date_diffs_days,
        },
        "reference_comparison": {
            "invoice_reference_ids": evidence_schema.reference_comparison.invoice_reference_ids,
            "counterpart_reference_ids": evidence_schema.reference_comparison.counterpart_reference_ids,
            "matched_references": evidence_schema.reference_comparison.matched_references,
            "unmatched_references": evidence_schema.reference_comparison.unmatched_references,
        },
        "counterparty": {
            "invoice_counterparty_id": evidence_schema.counterparty.invoice_counterparty_id,
            "counterpart_counterparty_ids": evidence_schema.counterparty.counterpart_counterparty_ids,
            "counterparty_match": evidence_schema.counterparty.counterparty_match,
            "counterparty_match_logic": evidence_schema.counterparty.counterparty_match_logic,
        },
        "match_selection": {
            "selection_method": evidence_schema.match_selection.selection_method,
            "selection_criteria": evidence_schema.match_selection.selection_criteria,
            "selection_priority": evidence_schema.match_selection.selection_priority,
            "excluded_matches": evidence_schema.match_selection.excluded_matches,
            "exclusion_reasons": evidence_schema.match_selection.exclusion_reasons,
        },
        "primary_sources": {
            "invoice_record_id": evidence_schema.primary_sources.invoice_record_id,
            "counterpart_record_ids": evidence_schema.primary_sources.counterpart_record_ids,
            "source_system": evidence_schema.primary_sources.source_system,
            "source_record_ids": evidence_schema.primary_sources.source_record_ids,
            "canonical_record_ids": evidence_schema.primary_sources.canonical_record_ids,
        },
    }
    
    # Generate deterministic evidence ID
    evidence_id = deterministic_evidence_id(
        dataset_version_id=dataset_version_id,
        engine_id=ENGINE_ID,
        kind="finding_evidence",
        stable_key=finding_id,
    )
    
    # Create evidence record (immutable, dataset-bound)
    await create_evidence(
        db,
        evidence_id=evidence_id,
        dataset_version_id=dataset_version_id,
        engine_id=ENGINE_ID,
        kind="finding_evidence",
        payload=payload,
        created_at=created_at,
    )
    
    return evidence_id
