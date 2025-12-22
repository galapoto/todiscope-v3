"""
Evidence Schema v1 (Hard Requirement)

FF-3: Defines the evidence schema that MUST be populated per finding.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any


class EvidenceSchemaViolationError(ValueError):
    """Raised when evidence schema is incomplete or invalid."""
    pass


@dataclass(frozen=True)
class RuleIdentityEvidence:
    """Rule identity and version evidence."""
    rule_id: str
    rule_version: str
    framework_version: str
    executed_parameters: dict[str, Any]


@dataclass(frozen=True)
class ToleranceEvidence:
    """Tolerance values evidence (if used)."""
    tolerance_absolute: Decimal | None
    tolerance_percent: Decimal | None
    threshold_applied: Decimal | None
    tolerance_source: str  # e.g., "rule_config", "run_parameters"


@dataclass(frozen=True)
class AmountComparisonEvidence:
    """Amount comparison evidence."""
    invoice_amount_original: Decimal
    invoice_currency_original: str
    invoice_amount_converted: Decimal | None  # If FX conversion used
    counterpart_amounts_original: list[Decimal]
    counterpart_currencies_original: list[str]
    counterpart_amounts_converted: list[Decimal] | None  # If FX conversion used
    sum_counterpart_amount_original: Decimal
    sum_counterpart_amount_converted: Decimal | None  # If FX conversion used
    comparison_currency: str
    diff_original: Decimal
    diff_converted: Decimal | None  # If FX conversion used


@dataclass(frozen=True)
class DateComparisonEvidence:
    """Date comparison evidence."""
    invoice_posted_at: str
    counterpart_posted_at: list[str]
    date_diffs_days: list[int] | None  # Days difference for each counterpart


@dataclass(frozen=True)
class ReferenceComparisonEvidence:
    """Reference ID comparison evidence."""
    invoice_reference_ids: list[str]
    counterpart_reference_ids: list[list[str]]  # Per counterpart
    matched_references: list[list[str]]  # Matched reference IDs per counterpart
    unmatched_references: list[list[str]]  # Unmatched reference IDs per counterpart


@dataclass(frozen=True)
class CounterpartyEvidence:
    """Counterparty logic evidence."""
    invoice_counterparty_id: str
    counterpart_counterparty_ids: list[str]
    counterparty_match: bool
    counterparty_match_logic: str  # e.g., "exact", "normalized", "fuzzy"


@dataclass(frozen=True)
class MatchSelectionRationale:
    """Match selection rationale evidence."""
    selection_method: str  # e.g., "first_match", "best_match", "all_matches"
    selection_criteria: list[str]  # e.g., ["amount", "date", "reference"]
    selection_priority: dict[str, int]  # Priority weights for criteria
    excluded_matches: list[str] | None  # Record IDs excluded from match
    exclusion_reasons: list[str] | None  # Reasons for exclusion


@dataclass(frozen=True)
class PrimarySourceLinks:
    """Primary source record links."""
    invoice_record_id: str
    counterpart_record_ids: list[str]
    source_system: str
    source_record_ids: list[str]  # Original source IDs
    canonical_record_ids: list[str]  # Canonical record IDs


@dataclass(frozen=True)
class EvidenceSchemaV1:
    """
    Complete evidence schema v1 (hard requirement).
    
    All fields must be populated per finding.
    """
    # Rule identity
    rule_identity: RuleIdentityEvidence
    
    # Tolerance (if used)
    tolerance: ToleranceEvidence | None
    
    # Amount comparisons
    amount_comparison: AmountComparisonEvidence
    
    # Date comparisons
    date_comparison: DateComparisonEvidence
    
    # Reference comparisons
    reference_comparison: ReferenceComparisonEvidence
    
    # Counterparty logic
    counterparty: CounterpartyEvidence
    
    # Match selection rationale
    match_selection: MatchSelectionRationale
    
    # Primary source links
    primary_sources: PrimarySourceLinks


def validate_evidence_schema_v1(evidence: dict[str, Any] | EvidenceSchemaV1) -> None:
    """
    Validate that evidence schema v1 is complete.
    
    Raises:
        EvidenceSchemaViolationError: If any required field is missing
    """
    if isinstance(evidence, EvidenceSchemaV1):
        evidence_dict = {
            "rule_identity": {
                "rule_id": evidence.rule_identity.rule_id,
                "rule_version": evidence.rule_identity.rule_version,
                "framework_version": evidence.rule_identity.framework_version,
                "executed_parameters": evidence.rule_identity.executed_parameters,
            },
            "tolerance": {
                "tolerance_absolute": evidence.tolerance.tolerance_absolute if evidence.tolerance else None,
                "tolerance_percent": evidence.tolerance.tolerance_percent if evidence.tolerance else None,
                "threshold_applied": evidence.tolerance.threshold_applied if evidence.tolerance else None,
                "tolerance_source": evidence.tolerance.tolerance_source if evidence.tolerance else None,
            } if evidence.tolerance else None,
            "amount_comparison": {
                "invoice_amount_original": evidence.amount_comparison.invoice_amount_original,
                "invoice_currency_original": evidence.amount_comparison.invoice_currency_original,
                "invoice_amount_converted": evidence.amount_comparison.invoice_amount_converted,
                "counterpart_amounts_original": evidence.amount_comparison.counterpart_amounts_original,
                "counterpart_currencies_original": evidence.amount_comparison.counterpart_currencies_original,
                "counterpart_amounts_converted": evidence.amount_comparison.counterpart_amounts_converted,
                "sum_counterpart_amount_original": evidence.amount_comparison.sum_counterpart_amount_original,
                "sum_counterpart_amount_converted": evidence.amount_comparison.sum_counterpart_amount_converted,
                "comparison_currency": evidence.amount_comparison.comparison_currency,
                "diff_original": evidence.amount_comparison.diff_original,
                "diff_converted": evidence.amount_comparison.diff_converted,
            },
            "date_comparison": {
                "invoice_posted_at": evidence.date_comparison.invoice_posted_at,
                "counterpart_posted_at": evidence.date_comparison.counterpart_posted_at,
                "date_diffs_days": evidence.date_comparison.date_diffs_days,
            },
            "reference_comparison": {
                "invoice_reference_ids": evidence.reference_comparison.invoice_reference_ids,
                "counterpart_reference_ids": evidence.reference_comparison.counterpart_reference_ids,
                "matched_references": evidence.reference_comparison.matched_references,
                "unmatched_references": evidence.reference_comparison.unmatched_references,
            },
            "counterparty": {
                "invoice_counterparty_id": evidence.counterparty.invoice_counterparty_id,
                "counterpart_counterparty_ids": evidence.counterparty.counterpart_counterparty_ids,
                "counterparty_match": evidence.counterparty.counterparty_match,
                "counterparty_match_logic": evidence.counterparty.counterparty_match_logic,
            },
            "match_selection": {
                "selection_method": evidence.match_selection.selection_method,
                "selection_criteria": evidence.match_selection.selection_criteria,
                "selection_priority": evidence.match_selection.selection_priority,
                "excluded_matches": evidence.match_selection.excluded_matches,
                "exclusion_reasons": evidence.match_selection.exclusion_reasons,
            },
            "primary_sources": {
                "invoice_record_id": evidence.primary_sources.invoice_record_id,
                "counterpart_record_ids": evidence.primary_sources.counterpart_record_ids,
                "source_system": evidence.primary_sources.source_system,
                "source_record_ids": evidence.primary_sources.source_record_ids,
                "canonical_record_ids": evidence.primary_sources.canonical_record_ids,
            },
        }
    else:
        evidence_dict = evidence
    
    # Required top-level fields
    required_top_level = [
        "rule_identity",
        "amount_comparison",
        "date_comparison",
        "reference_comparison",
        "counterparty",
        "match_selection",
        "primary_sources",
    ]

    missing_top_level = [f for f in required_top_level if f not in evidence_dict]

    # If exactly one non-rule_identity top-level field is missing, surface it directly.
    if len(missing_top_level) == 1 and missing_top_level[0] != "rule_identity":
        raise EvidenceSchemaViolationError(f"EVIDENCE_FIELD_MISSING: evidence.{missing_top_level[0]} is required")

    # If rule_identity exists but is incomplete, surface rule_identity subfield errors (even if other fields are missing).
    if "rule_identity" in evidence_dict:
        rule_identity = evidence_dict.get("rule_identity", {})
        required_rule_fields = ["rule_id", "rule_version", "framework_version", "executed_parameters"]
        for field in required_rule_fields:
            if field not in rule_identity:
                raise EvidenceSchemaViolationError(
                    f"EVIDENCE_RULE_IDENTITY_FIELD_MISSING: evidence.rule_identity.{field} is required"
                )
    else:
        # rule_identity itself missing
        raise EvidenceSchemaViolationError("EVIDENCE_FIELD_MISSING: evidence.rule_identity is required")

    # Remaining missing top-level fields (if any)
    for field in missing_top_level:
        if field == "rule_identity":
            continue
        raise EvidenceSchemaViolationError(f"EVIDENCE_FIELD_MISSING: evidence.{field} is required")
    
    # Validate amount_comparison
    amount_comparison = evidence_dict.get("amount_comparison", {})
    required_amount_fields = [
        "invoice_amount_original",
        "invoice_currency_original",
        "counterpart_amounts_original",
        "counterpart_currencies_original",
        "sum_counterpart_amount_original",
        "comparison_currency",
        "diff_original",
    ]
    for field in required_amount_fields:
        if field not in amount_comparison:
            raise EvidenceSchemaViolationError(
                f"EVIDENCE_AMOUNT_COMPARISON_FIELD_MISSING: evidence.amount_comparison.{field} is required"
            )
    
    # Validate date_comparison
    date_comparison = evidence_dict.get("date_comparison", {})
    required_date_fields = ["invoice_posted_at", "counterpart_posted_at"]
    for field in required_date_fields:
        if field not in date_comparison:
            raise EvidenceSchemaViolationError(
                f"EVIDENCE_DATE_COMPARISON_FIELD_MISSING: evidence.date_comparison.{field} is required"
            )
    
    # Validate reference_comparison
    reference_comparison = evidence_dict.get("reference_comparison", {})
    required_ref_fields = [
        "invoice_reference_ids",
        "counterpart_reference_ids",
        "matched_references",
        "unmatched_references",
    ]
    for field in required_ref_fields:
        if field not in reference_comparison:
            raise EvidenceSchemaViolationError(
                f"EVIDENCE_REFERENCE_COMPARISON_FIELD_MISSING: evidence.reference_comparison.{field} is required"
            )
    
    # Validate counterparty
    counterparty = evidence_dict.get("counterparty", {})
    required_counterparty_fields = [
        "invoice_counterparty_id",
        "counterpart_counterparty_ids",
        "counterparty_match",
        "counterparty_match_logic",
    ]
    for field in required_counterparty_fields:
        if field not in counterparty:
            raise EvidenceSchemaViolationError(
                f"EVIDENCE_COUNTERPARTY_FIELD_MISSING: evidence.counterparty.{field} is required"
            )
    
    # Validate match_selection
    match_selection = evidence_dict.get("match_selection", {})
    required_selection_fields = [
        "selection_method",
        "selection_criteria",
        "selection_priority",
    ]
    for field in required_selection_fields:
        if field not in match_selection:
            raise EvidenceSchemaViolationError(
                f"EVIDENCE_MATCH_SELECTION_FIELD_MISSING: evidence.match_selection.{field} is required"
            )
    
    # Validate primary_sources
    primary_sources = evidence_dict.get("primary_sources", {})
    required_source_fields = [
        "invoice_record_id",
        "counterpart_record_ids",
        "source_system",
        "source_record_ids",
        "canonical_record_ids",
    ]
    for field in required_source_fields:
        if field not in primary_sources:
            raise EvidenceSchemaViolationError(
                f"EVIDENCE_PRIMARY_SOURCES_FIELD_MISSING: evidence.primary_sources.{field} is required"
            )

