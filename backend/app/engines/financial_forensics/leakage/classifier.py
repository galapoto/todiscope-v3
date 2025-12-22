"""
Deterministic Classifier for Leakage Typology

FF-4: Every FF-3 finding maps to exactly one typology.
Mapping rules are explicit and ordered.
No category exists without a rule.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from backend.app.engines.financial_forensics.leakage.typology import LeakageTypology


@dataclass(frozen=True)
class ClassificationResult:
    """Result of deterministic classification."""
    typology: LeakageTypology
    rationale: str


class ClassificationError(ValueError):
    """Raised when classification fails or produces invalid results."""
    pass


# Explicit mapping rules (ordered by priority)
# Rule 1: Partial match findings always map to partial_settlement_residual
# Rule 2: Timing mismatch (matched amounts but date delta beyond threshold)
# Rule 3: Unmatched invoice/payment detection (based on evidence amount structure)
# Rule 4: Amount-based classification (overpayment/underpayment)
# Rule 5: Balanced amounts fall back to unmatched_payment (no neutral category in v1 set)


def classify_finding(
    *,
    finding: dict[str, Any],
    evidence_payload: dict[str, Any],
    timing_inconsistency_days_threshold: int | None = None,
) -> ClassificationResult:
    """
    Deterministic classification from FF-3 finding + stored evidence payload.
    
    Every finding maps to exactly one typology.
    Rules are applied in explicit order.
    
    Args:
        finding: FF-3 finding dict with finding_type, confidence, etc.
        evidence_payload: Evidence payload from evidence_records
        timing_inconsistency_days_threshold: Optional threshold for timing mismatch (days)
    
    Returns:
        ClassificationResult with typology and rationale
    
    Raises:
        ClassificationError: If finding cannot be classified or produces invalid result
    """
    finding_type = finding.get("finding_type")
    if not finding_type:
        raise ClassificationError(
            "CLASSIFICATION_ERROR: finding_type is required for classification"
        )
    
    # Rule 1: Partial match findings always map to partial_settlement_residual
    if finding_type == "partial_match":
        return ClassificationResult(
            typology=LeakageTypology.PARTIAL_SETTLEMENT_RESIDUAL,
            rationale="finding_type=partial_match implies remaining balance without allegation.",
        )
    
    # Rule 2: Timing mismatch (matched amounts but date delta beyond threshold)
    # Only applies to exact_match and tolerance_match (not partial_match, already handled)
    if finding_type in ("exact_match", "tolerance_match"):
        timing_result = _check_timing_mismatch(
            evidence_payload=evidence_payload,
            timing_inconsistency_days_threshold=timing_inconsistency_days_threshold,
        )
        if timing_result is not None:
            return timing_result
    
    # Rule 3: Unmatched invoice/payment detection (v1 typologies)
    amount_comparison = evidence_payload.get("amount_comparison")
    if isinstance(amount_comparison, dict):
        inv_conv = amount_comparison.get("invoice_amount_converted")
        sum_conv = amount_comparison.get("sum_counterpart_amount_converted")
        if inv_conv is not None and sum_conv is not None:
            inv = Decimal(str(inv_conv))
            summ = Decimal(str(sum_conv))
            if inv > 0 and summ == 0:
                return ClassificationResult(
                    typology=LeakageTypology.UNMATCHED_INVOICE,
                    rationale="invoice_amount_converted > 0 and sum_counterpart_amount_converted == 0 indicates unmatched_invoice.",
                )
            if inv == 0 and summ > 0:
                return ClassificationResult(
                    typology=LeakageTypology.UNMATCHED_PAYMENT,
                    rationale="invoice_amount_converted == 0 and sum_counterpart_amount_converted > 0 indicates unmatched_payment.",
                )

    # Rule 4: Amount-based classification (overpayment/underpayment)
    diff = _extract_diff_converted(evidence_payload)
    if diff is None:
        # If diff_converted is missing, cannot determine amount-based classification
        # This should not happen for valid findings, but we need a deterministic fallback
        raise ClassificationError(
            "CLASSIFICATION_ERROR: diff_converted missing in evidence_payload; cannot classify finding"
        )
    
    if diff < 0:
        return ClassificationResult(
            typology=LeakageTypology.OVERPAYMENT,
            rationale="diff_converted < 0 indicates counterparts exceed invoice (overpayment signal).",
        )
    if diff > 0:
        return ClassificationResult(
            typology=LeakageTypology.UNDERPAYMENT,
            rationale="diff_converted > 0 indicates invoice exceeds counterparts (underpayment signal).",
        )
    
    # Rule 5: diff == 0
    return ClassificationResult(
        typology=LeakageTypology.UNMATCHED_PAYMENT,
        rationale="diff_converted == 0 indicates balanced amounts; v1 typology set has no neutral category.",
    )


def _check_timing_mismatch(
    *,
    evidence_payload: dict[str, Any],
    timing_inconsistency_days_threshold: int | None,
) -> ClassificationResult | None:
    """
    Check if finding represents a timing mismatch.
    
    Timing mismatch: matched amounts but date delta beyond threshold.
    
    Args:
        evidence_payload: Evidence payload from evidence_records
        timing_inconsistency_days_threshold: Threshold for timing inconsistency (days)
    
    Returns:
        ClassificationResult if timing mismatch detected, None otherwise
    """
    if timing_inconsistency_days_threshold is None:
        # No threshold provided, cannot detect timing mismatch
        return None
    
    date_comparison = evidence_payload.get("date_comparison")
    if not isinstance(date_comparison, dict):
        return None
    
    invoice_posted_at = date_comparison.get("invoice_posted_at")
    counterpart_posted_at = date_comparison.get("counterpart_posted_at")
    
    if not invoice_posted_at or not counterpart_posted_at:
        return None
    
    # Calculate date differences
    date_diffs_days = date_comparison.get("date_diffs_days")
    if date_diffs_days is None:
        # Calculate if not provided
        try:
            invoice_date = datetime.fromisoformat(invoice_posted_at.replace("Z", "+00:00"))
            # For multiple counterparts, use the first one or calculate max difference
            if isinstance(counterpart_posted_at, list) and len(counterpart_posted_at) > 0:
                counterpart_date = datetime.fromisoformat(counterpart_posted_at[0].replace("Z", "+00:00"))
            elif isinstance(counterpart_posted_at, str):
                counterpart_date = datetime.fromisoformat(counterpart_posted_at.replace("Z", "+00:00"))
            else:
                return None
            
            diff_days = abs((invoice_date - counterpart_date).days)
        except (ValueError, AttributeError):
            return None
    else:
        # Use provided date differences
        if isinstance(date_diffs_days, list) and len(date_diffs_days) > 0:
            diff_days = abs(date_diffs_days[0])
        elif isinstance(date_diffs_days, int):
            diff_days = abs(date_diffs_days)
        else:
            return None
    
    # Check if difference exceeds threshold
    if diff_days > timing_inconsistency_days_threshold:
        return ClassificationResult(
            typology=LeakageTypology.TIMING_MISMATCH,
            rationale=f"Matched amounts but date delta ({diff_days} days) exceeds threshold ({timing_inconsistency_days_threshold} days).",
        )
    
    return None


def _extract_diff_converted(evidence_payload: dict[str, Any]) -> Decimal | None:
    """Extract diff_converted from evidence payload."""
    amount_comparison = evidence_payload.get("amount_comparison")
    if not isinstance(amount_comparison, dict):
        return None
    diff = amount_comparison.get("diff_converted")
    if diff is None:
        return None
    return Decimal(str(diff))


def _extract_rounding(evidence_payload: dict[str, Any]) -> tuple[str, str]:
    """Extract rounding mode and quantum from evidence payload."""
    rule_identity = evidence_payload.get("rule_identity", {})
    executed = rule_identity.get("executed_parameters", {}) if isinstance(rule_identity, dict) else {}
    rounding_mode = executed.get("rounding_mode") or "ROUND_HALF_UP"
    rounding_quantum = executed.get("rounding_quantum") or "0.01"
    return str(rounding_mode), str(rounding_quantum)


def _extract_started_at(evidence_payload: dict[str, Any]) -> str | None:
    """Extract started_at from evidence payload (optional)."""
    started_at = evidence_payload.get("started_at")
    if isinstance(started_at, str):
        # Validate parsable format but do not depend on system time.
        _ = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        return started_at
    return None


__all__ = ["ClassificationResult", "classify_finding", "ClassificationError"]
