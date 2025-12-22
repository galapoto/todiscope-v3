from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol


CONFIDENCE_EXACT = "exact"
CONFIDENCE_WITHIN_TOLERANCE = "within_tolerance"
CONFIDENCE_PARTIAL = "partial"
CONFIDENCE_AMBIGUOUS = "ambiguous"

ALLOWED_CONFIDENCE = {
    CONFIDENCE_EXACT,
    CONFIDENCE_WITHIN_TOLERANCE,
    CONFIDENCE_PARTIAL,
    CONFIDENCE_AMBIGUOUS,
}


@dataclass(frozen=True)
class ConvertedAmounts:
    base_currency: str
    amount_converted: Decimal
    fx_rate_used: Decimal


@dataclass(frozen=True)
class CanonicalInput:
    record_id: str
    record_type: str
    source_system: str
    source_record_id: str
    posted_at_iso: str
    counterparty_id: str
    amount_original: Decimal
    currency_original: str
    direction: str
    reference_ids: tuple[str, ...]
    converted: ConvertedAmounts

    @property
    def signed_converted_amount(self) -> Decimal:
        # Deterministic signed amount: debit=+ , credit=-
        sign = Decimal("1") if self.direction == "debit" else Decimal("-1")
        return sign * self.converted.amount_converted


@dataclass(frozen=True)
class RuleParameters:
    rounding_mode: str
    rounding_quantum: str
    tolerance_amount: str | None = None
    tolerance_percent: str | None = None
    max_posted_days_diff: int | None = None


@dataclass(frozen=True)
class RuleContext:
    dataset_version_id: str
    fx_artifact_id: str
    started_at_iso: str
    parameters: RuleParameters


@dataclass(frozen=True)
class MatchOutcome:
    rule_id: str
    rule_version: str
    confidence: str
    matched_record_ids: tuple[str, ...]
    unmatched_amount: Decimal | None
    selection_rationale: str
    evidence_payload: dict


class MatchingRule(Protocol):
    rule_id: str
    rule_version: str

    def apply(
        self,
        *,
        context: RuleContext,
        records: tuple[CanonicalInput, ...],
        used_record_ids: set[str],
    ) -> list[MatchOutcome]: ...


def deterministic_rule_order(rules: tuple[MatchingRule, ...]) -> tuple[MatchingRule, ...]:
    # Enforce explicit fixed order: rules are applied in the tuple order provided.
    return rules


def require_confidence(confidence: str) -> str:
    if confidence not in ALLOWED_CONFIDENCE:
        raise ValueError(f"CONFIDENCE_NOT_ALLOWED: {confidence}")
    return confidence
