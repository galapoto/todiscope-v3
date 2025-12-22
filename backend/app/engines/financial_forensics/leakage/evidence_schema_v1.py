"""
Leakage Evidence Schema v1 (Hard Requirement)

FF-4: Defines the evidence schema that MUST be populated per leakage instance.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any


class LeakageEvidenceSchemaViolationError(ValueError):
    """Raised when leakage evidence schema is incomplete or invalid."""
    pass


@dataclass(frozen=True)
class TypologyAssignmentRationale:
    """Typology assignment rationale evidence."""
    leakage_type: str  # e.g., "unmatched_payable_exposure", "unmatched_receivable_exposure", "duplicate_settlement_risk"
    assignment_rule_id: str  # Rule or rule set that triggered this typology
    assignment_rule_version: str
    assignment_criteria: list[str]  # Criteria that were met (e.g., ["no_match_found", "invoice_direction=payable"])
    assignment_confidence: str  # Confidence level of typology assignment (exact/within_tolerance/partial/ambiguous)
    direction_convention: str  # Explicit direction convention used (e.g., "debit=payable", "credit=receivable")
    direction_source: str  # Source of direction convention (e.g., "run_parameters", "canonical_field")


@dataclass(frozen=True)
class NumericExposureDerivation:
    """Numeric exposure derivation steps evidence."""
    exposure_amount: Decimal | None  # Point estimate (if deterministic)
    exposure_min: Decimal | None  # Lower bound (if range)
    exposure_max: Decimal | None  # Upper bound (if range)
    exposure_currency: str  # ISO 4217 currency code
    exposure_basis: str  # Description of what exposure represents (e.g., "remaining unmatched amount under declared constraints")
    exposure_currency_mode: str  # "original_only" or "fx_to_base"
    
    # FX conversion details (if fx_to_base)
    fx_artifact_id: str | None
    fx_artifact_sha256: str | None
    rounding_mode: str | None
    base_currency: str | None
    
    # Derivation steps
    derivation_method: str  # e.g., "direct_amount", "sum_differences", "range_estimation"
    derivation_inputs: dict[str, Any]  # Inputs used in derivation (e.g., invoice_amount, matched_amounts)
    derivation_confidence: str  # Confidence level of exposure calculation


@dataclass(frozen=True)
class FindingReferences:
    """Source FF-3 finding references evidence."""
    related_finding_ids: list[str]  # Finding IDs that contributed to this leakage
    finding_rule_ids: list[str]  # Rule IDs from related findings
    finding_rule_versions: list[str]  # Rule versions from related findings
    finding_confidences: list[str]  # Confidence levels from related findings
    finding_evidence_ids: list[str]  # Evidence IDs from related findings
    match_outcome: str  # Overall match outcome (e.g., "no_match", "partial_match", "ambiguous_match")
    match_search_scope: dict[str, Any]  # Constraints used in matching search (date windows, reference overlap, etc.)


@dataclass(frozen=True)
class PrimaryRecordsInvolved:
    """Primary records involved in leakage evidence."""
    invoice_record_id: str  # Primary invoice record
    invoice_source_system: str
    invoice_source_record_id: str
    invoice_canonical_record_id: str | None
    
    # Counterpart records (if any matches found)
    counterpart_record_ids: list[str]  # Payment/credit_note record IDs
    counterpart_source_systems: list[str]
    counterpart_source_record_ids: list[str]
    counterpart_canonical_record_ids: list[str | None]
    
    # Intercompany flags
    is_intercompany: bool
    intercompany_counterparty_ids: list[str] | None  # If intercompany, which counterparties
    intercompany_detection_method: str | None  # How intercompany was detected (e.g., "counterparty_master", "account_pattern")


@dataclass(frozen=True)
class LeakageEvidenceSchemaV1:
    """
    Complete leakage evidence schema v1 (hard requirement).
    
    All fields must be populated per leakage instance.
    """
    # Typology assignment
    typology_assignment: TypologyAssignmentRationale
    
    # Numeric exposure derivation
    exposure_derivation: NumericExposureDerivation
    
    # Source finding references
    finding_references: FindingReferences
    
    # Primary records involved
    primary_records: PrimaryRecordsInvolved


def validate_leakage_evidence_schema_v1(evidence: dict[str, Any] | LeakageEvidenceSchemaV1) -> None:
    """
    Validate that leakage evidence schema v1 is complete.
    
    Raises:
        LeakageEvidenceSchemaViolationError: If any required field is missing
    """
    if isinstance(evidence, LeakageEvidenceSchemaV1):
        evidence_dict = {
            "typology_assignment": {
                "leakage_type": evidence.typology_assignment.leakage_type,
                "assignment_rule_id": evidence.typology_assignment.assignment_rule_id,
                "assignment_rule_version": evidence.typology_assignment.assignment_rule_version,
                "assignment_criteria": evidence.typology_assignment.assignment_criteria,
                "assignment_confidence": evidence.typology_assignment.assignment_confidence,
                "direction_convention": evidence.typology_assignment.direction_convention,
                "direction_source": evidence.typology_assignment.direction_source,
            },
            "exposure_derivation": {
                "exposure_amount": str(evidence.exposure_derivation.exposure_amount) if evidence.exposure_derivation.exposure_amount else None,
                "exposure_min": str(evidence.exposure_derivation.exposure_min) if evidence.exposure_derivation.exposure_min else None,
                "exposure_max": str(evidence.exposure_derivation.exposure_max) if evidence.exposure_derivation.exposure_max else None,
                "exposure_currency": evidence.exposure_derivation.exposure_currency,
                "exposure_basis": evidence.exposure_derivation.exposure_basis,
                "exposure_currency_mode": evidence.exposure_derivation.exposure_currency_mode,
                "fx_artifact_id": evidence.exposure_derivation.fx_artifact_id,
                "fx_artifact_sha256": evidence.exposure_derivation.fx_artifact_sha256,
                "rounding_mode": evidence.exposure_derivation.rounding_mode,
                "base_currency": evidence.exposure_derivation.base_currency,
                "derivation_method": evidence.exposure_derivation.derivation_method,
                "derivation_inputs": evidence.exposure_derivation.derivation_inputs,
                "derivation_confidence": evidence.exposure_derivation.derivation_confidence,
            },
            "finding_references": {
                "related_finding_ids": evidence.finding_references.related_finding_ids,
                "finding_rule_ids": evidence.finding_references.finding_rule_ids,
                "finding_rule_versions": evidence.finding_references.finding_rule_versions,
                "finding_confidences": evidence.finding_references.finding_confidences,
                "finding_evidence_ids": evidence.finding_references.finding_evidence_ids,
                "match_outcome": evidence.finding_references.match_outcome,
                "match_search_scope": evidence.finding_references.match_search_scope,
            },
            "primary_records": {
                "invoice_record_id": evidence.primary_records.invoice_record_id,
                "invoice_source_system": evidence.primary_records.invoice_source_system,
                "invoice_source_record_id": evidence.primary_records.invoice_source_record_id,
                "invoice_canonical_record_id": evidence.primary_records.invoice_canonical_record_id,
                "counterpart_record_ids": evidence.primary_records.counterpart_record_ids,
                "counterpart_source_systems": evidence.primary_records.counterpart_source_systems,
                "counterpart_source_record_ids": evidence.primary_records.counterpart_source_record_ids,
                "counterpart_canonical_record_ids": evidence.primary_records.counterpart_canonical_record_ids,
                "is_intercompany": evidence.primary_records.is_intercompany,
                "intercompany_counterparty_ids": evidence.primary_records.intercompany_counterparty_ids,
                "intercompany_detection_method": evidence.primary_records.intercompany_detection_method,
            },
        }
    else:
        evidence_dict = evidence
    
    # Required top-level fields
    required_fields = [
        "typology_assignment",
        "exposure_derivation",
        "finding_references",
        "primary_records",
    ]
    
    for field in required_fields:
        if field not in evidence_dict:
            raise LeakageEvidenceSchemaViolationError(
                f"LEAKAGE_EVIDENCE_FIELD_MISSING: evidence.{field} is required"
            )
    
    # Validate typology_assignment
    typology = evidence_dict.get("typology_assignment", {})
    required_typology_fields = [
        "leakage_type",
        "assignment_rule_id",
        "assignment_rule_version",
        "assignment_criteria",
        "assignment_confidence",
        "direction_convention",
        "direction_source",
    ]
    for field in required_typology_fields:
        if field not in typology:
            raise LeakageEvidenceSchemaViolationError(
                f"LEAKAGE_EVIDENCE_TYPOLOGY_FIELD_MISSING: evidence.typology_assignment.{field} is required"
            )
    
    # Validate exposure_derivation
    exposure = evidence_dict.get("exposure_derivation", {})
    required_exposure_fields = [
        "exposure_currency",
        "exposure_basis",
        "exposure_currency_mode",
        "derivation_method",
        "derivation_inputs",
        "derivation_confidence",
    ]
    for field in required_exposure_fields:
        if field not in exposure:
            raise LeakageEvidenceSchemaViolationError(
                f"LEAKAGE_EVIDENCE_EXPOSURE_FIELD_MISSING: evidence.exposure_derivation.{field} is required"
            )
    
    # Validate finding_references
    findings = evidence_dict.get("finding_references", {})
    required_finding_fields = [
        "related_finding_ids",
        "finding_rule_ids",
        "finding_rule_versions",
        "finding_confidences",
        "finding_evidence_ids",
        "match_outcome",
        "match_search_scope",
    ]
    for field in required_finding_fields:
        if field not in findings:
            raise LeakageEvidenceSchemaViolationError(
                f"LEAKAGE_EVIDENCE_FINDING_FIELD_MISSING: evidence.finding_references.{field} is required"
            )
    
    # Validate primary_records
    records = evidence_dict.get("primary_records", {})
    required_record_fields = [
        "invoice_record_id",
        "invoice_source_system",
        "invoice_source_record_id",
        "counterpart_record_ids",
        "counterpart_source_systems",
        "counterpart_source_record_ids",
        "is_intercompany",
    ]
    for field in required_record_fields:
        if field not in records:
            raise LeakageEvidenceSchemaViolationError(
                f"LEAKAGE_EVIDENCE_RECORD_FIELD_MISSING: evidence.primary_records.{field} is required"
            )


