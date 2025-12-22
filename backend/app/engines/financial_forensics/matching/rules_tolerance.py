from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from backend.app.engines.financial_forensics.matching.framework import (
    CONFIDENCE_WITHIN_TOLERANCE,
    CanonicalInput,
    MatchOutcome,
    RuleContext,
    require_confidence,
)


def _parse_iso(dt: str) -> datetime:
    return datetime.fromisoformat(dt.replace("Z", "+00:00"))


def _days_diff(a_iso: str, b_iso: str) -> int:
    a = _parse_iso(a_iso)
    b = _parse_iso(b_iso)
    return abs((a - b).days)


def _eligible_by_date(context: RuleContext, a: CanonicalInput, b: CanonicalInput) -> bool:
    if context.parameters.max_posted_days_diff is None:
        return True
    return _days_diff(a.posted_at_iso, b.posted_at_iso) <= context.parameters.max_posted_days_diff


def _tolerance_amount(context: RuleContext, base_amount: Decimal) -> Decimal:
    tol_amt = context.parameters.tolerance_amount
    tol_pct = context.parameters.tolerance_percent
    if tol_amt is None and tol_pct is None:
        raise ValueError("TOLERANCE_REQUIRED: tolerance_amount or tolerance_percent must be provided")

    computed = Decimal("0")
    if tol_amt is not None:
        computed = max(computed, Decimal(tol_amt))
    if tol_pct is not None:
        pct = Decimal(tol_pct)
        computed = max(computed, (abs(base_amount) * pct))
    return computed


def _within_tolerance(a: CanonicalInput, b: CanonicalInput, tolerance: Decimal) -> bool:
    # Compare absolute imbalance: invoice+other should be close to zero.
    imbalance = abs(a.signed_converted_amount + b.signed_converted_amount)
    return imbalance <= tolerance


@dataclass(frozen=True)
class ToleranceInvoicePaymentRule:
    rule_id: str = "ff.match.invoice_payment.tolerance"
    rule_version: str = "v1"

    def apply(
        self,
        *,
        context: RuleContext,
        records: tuple[CanonicalInput, ...],
        used_record_ids: set[str],
    ) -> list[MatchOutcome]:
        invoices = [r for r in records if r.record_type == "invoice" and r.record_id not in used_record_ids]
        payments = [r for r in records if r.record_type == "payment" and r.record_id not in used_record_ids]

        outcomes: list[MatchOutcome] = []
        for inv in sorted(invoices, key=lambda r: r.record_id):
            tolerance = _tolerance_amount(context, inv.converted.amount_converted)
            candidates = [
                p
                for p in payments
                if p.record_id not in used_record_ids
                and p.counterparty_id == inv.counterparty_id
                and _eligible_by_date(context, inv, p)
                and _within_tolerance(inv, p, tolerance)
            ]
            candidates_sorted = sorted(
                candidates,
                key=lambda p: (
                    abs(inv.signed_converted_amount + p.signed_converted_amount),
                    _days_diff(inv.posted_at_iso, p.posted_at_iso),
                    p.record_id,
                ),
            )
            if not candidates_sorted:
                continue
            chosen = candidates_sorted[0]

            imbalance = inv.signed_converted_amount + chosen.signed_converted_amount

            confidence = require_confidence(CONFIDENCE_WITHIN_TOLERANCE)
            evidence_payload = {
                "rule_id": self.rule_id,
                "rule_version": self.rule_version,
                "confidence": confidence,
                "tolerance": {
                    "tolerance_amount": context.parameters.tolerance_amount,
                    "tolerance_percent": context.parameters.tolerance_percent,
                    "computed_tolerance_in_base": str(tolerance),
                    "imbalance_in_base": str(imbalance),
                },
                "amount_comparisons": [
                    {
                        "record_id": inv.record_id,
                        "amount_original": str(inv.amount_original),
                        "currency_original": inv.currency_original,
                        "amount_converted": str(inv.converted.amount_converted),
                        "fx_rate_used": str(inv.converted.fx_rate_used),
                        "direction": inv.direction,
                    },
                    {
                        "record_id": chosen.record_id,
                        "amount_original": str(chosen.amount_original),
                        "currency_original": chosen.currency_original,
                        "amount_converted": str(chosen.converted.amount_converted),
                        "fx_rate_used": str(chosen.converted.fx_rate_used),
                        "direction": chosen.direction,
                    },
                ],
                "date_comparison": {
                    "invoice_posted_at": inv.posted_at_iso,
                    "other_posted_at": chosen.posted_at_iso,
                    "days_diff": _days_diff(inv.posted_at_iso, chosen.posted_at_iso),
                    "max_posted_days_diff": context.parameters.max_posted_days_diff,
                },
                "reference_id_comparison": {
                    "invoice_reference_ids": list(inv.reference_ids),
                    "other_reference_ids": list(chosen.reference_ids),
                    "intersection": sorted(set(inv.reference_ids).intersection(chosen.reference_ids)),
                },
                "counterparty_comparison": {
                    "invoice_counterparty_id": inv.counterparty_id,
                    "other_counterparty_id": chosen.counterparty_id,
                    "matched": inv.counterparty_id == chosen.counterparty_id,
                },
                "match_selection": {
                    "conflict_handling": "first_match_wins",
                    "candidates_considered": len(candidates_sorted),
                    "selected_other_record_id": chosen.record_id,
                    "preference_order": ["min_imbalance", "days_diff", "record_id"],
                },
                "primary_links": [inv.record_id, chosen.record_id],
            }

            outcomes.append(
                MatchOutcome(
                    rule_id=self.rule_id,
                    rule_version=self.rule_version,
                    confidence=confidence,
                    matched_record_ids=(inv.record_id, chosen.record_id),
                    unmatched_amount=None,
                    selection_rationale="Converted amounts balance within explicit tolerance; deterministic selection applied.",
                    evidence_payload=evidence_payload,
                )
            )
        return outcomes


@dataclass(frozen=True)
class ToleranceInvoiceCreditNoteRule:
    rule_id: str = "ff.match.invoice_credit_note.tolerance"
    rule_version: str = "v1"

    def apply(
        self,
        *,
        context: RuleContext,
        records: tuple[CanonicalInput, ...],
        used_record_ids: set[str],
    ) -> list[MatchOutcome]:
        invoices = [r for r in records if r.record_type == "invoice" and r.record_id not in used_record_ids]
        credit_notes = [r for r in records if r.record_type == "credit_note" and r.record_id not in used_record_ids]

        outcomes: list[MatchOutcome] = []
        for inv in sorted(invoices, key=lambda r: r.record_id):
            tolerance = _tolerance_amount(context, inv.converted.amount_converted)
            candidates = [
                cn
                for cn in credit_notes
                if cn.record_id not in used_record_ids
                and cn.counterparty_id == inv.counterparty_id
                and _eligible_by_date(context, inv, cn)
                and _within_tolerance(inv, cn, tolerance)
            ]
            candidates_sorted = sorted(
                candidates,
                key=lambda cn: (
                    abs(inv.signed_converted_amount + cn.signed_converted_amount),
                    _days_diff(inv.posted_at_iso, cn.posted_at_iso),
                    cn.record_id,
                ),
            )
            if not candidates_sorted:
                continue
            chosen = candidates_sorted[0]

            imbalance = inv.signed_converted_amount + chosen.signed_converted_amount

            confidence = require_confidence(CONFIDENCE_WITHIN_TOLERANCE)
            evidence_payload = {
                "rule_id": self.rule_id,
                "rule_version": self.rule_version,
                "confidence": confidence,
                "tolerance": {
                    "tolerance_amount": context.parameters.tolerance_amount,
                    "tolerance_percent": context.parameters.tolerance_percent,
                    "computed_tolerance_in_base": str(tolerance),
                    "imbalance_in_base": str(imbalance),
                },
                "amount_comparisons": [
                    {
                        "record_id": inv.record_id,
                        "amount_original": str(inv.amount_original),
                        "currency_original": inv.currency_original,
                        "amount_converted": str(inv.converted.amount_converted),
                        "fx_rate_used": str(inv.converted.fx_rate_used),
                        "direction": inv.direction,
                    },
                    {
                        "record_id": chosen.record_id,
                        "amount_original": str(chosen.amount_original),
                        "currency_original": chosen.currency_original,
                        "amount_converted": str(chosen.converted.amount_converted),
                        "fx_rate_used": str(chosen.converted.fx_rate_used),
                        "direction": chosen.direction,
                    },
                ],
                "date_comparison": {
                    "invoice_posted_at": inv.posted_at_iso,
                    "other_posted_at": chosen.posted_at_iso,
                    "days_diff": _days_diff(inv.posted_at_iso, chosen.posted_at_iso),
                    "max_posted_days_diff": context.parameters.max_posted_days_diff,
                },
                "reference_id_comparison": {
                    "invoice_reference_ids": list(inv.reference_ids),
                    "other_reference_ids": list(chosen.reference_ids),
                    "intersection": sorted(set(inv.reference_ids).intersection(chosen.reference_ids)),
                },
                "counterparty_comparison": {
                    "invoice_counterparty_id": inv.counterparty_id,
                    "other_counterparty_id": chosen.counterparty_id,
                    "matched": inv.counterparty_id == chosen.counterparty_id,
                },
                "match_selection": {
                    "conflict_handling": "first_match_wins",
                    "candidates_considered": len(candidates_sorted),
                    "selected_other_record_id": chosen.record_id,
                    "preference_order": ["min_imbalance", "days_diff", "record_id"],
                },
                "primary_links": [inv.record_id, chosen.record_id],
            }

            outcomes.append(
                MatchOutcome(
                    rule_id=self.rule_id,
                    rule_version=self.rule_version,
                    confidence=confidence,
                    matched_record_ids=(inv.record_id, chosen.record_id),
                    unmatched_amount=None,
                    selection_rationale="Converted amounts balance within explicit tolerance; deterministic selection applied.",
                    evidence_payload=evidence_payload,
                )
            )
        return outcomes
