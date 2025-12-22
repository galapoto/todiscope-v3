from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from backend.app.engines.financial_forensics.matching.framework import (
    CONFIDENCE_PARTIAL,
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


def _same_counterparty(a: CanonicalInput, b: CanonicalInput) -> bool:
    return a.counterparty_id == b.counterparty_id


def _opposite_direction(a: CanonicalInput, b: CanonicalInput) -> bool:
    return a.direction != b.direction


@dataclass(frozen=True)
class PartialInvoicePaymentRule:
    rule_id: str = "ff.match.invoice_payment.partial"
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

        # Deterministic ordering of candidate lists.
        payments_sorted = sorted(payments, key=lambda r: (r.posted_at_iso, r.record_id))

        outcomes: list[MatchOutcome] = []
        for inv in sorted(invoices, key=lambda r: r.record_id):
            # Gather eligible payments for this invoice.
            candidates = [
                p
                for p in payments_sorted
                if p.record_id not in used_record_ids
                and _same_counterparty(inv, p)
                and _opposite_direction(inv, p)
                and _eligible_by_date(context, inv, p)
            ]
            if not candidates:
                continue

            invoice_abs = abs(inv.signed_converted_amount)
            total_applied = Decimal("0")
            chosen: list[CanonicalInput] = []
            for p in candidates:
                if total_applied >= invoice_abs:
                    break
                pay_abs = abs(p.signed_converted_amount)
                if pay_abs == Decimal("0"):
                    continue
                chosen.append(p)
                total_applied += pay_abs

            if not chosen:
                continue

            # If it balances exactly, this should have been caught by earlier rules; skip to avoid confidence drift.
            if total_applied == invoice_abs:
                continue

            # Remaining amount is bounded and explicit (no accusation).
            remaining = invoice_abs - min(invoice_abs, total_applied)
            confidence = require_confidence(CONFIDENCE_PARTIAL)

            matched_ids = tuple([inv.record_id] + [p.record_id for p in chosen])
            evidence_payload = {
                "rule_id": self.rule_id,
                "rule_version": self.rule_version,
                "confidence": confidence,
                "tolerance": None,
                "amount_comparisons": [
                    {
                        "record_id": inv.record_id,
                        "amount_original": str(inv.amount_original),
                        "currency_original": inv.currency_original,
                        "amount_converted": str(inv.converted.amount_converted),
                        "fx_rate_used": str(inv.converted.fx_rate_used),
                        "direction": inv.direction,
                    },
                    *[
                        {
                            "record_id": p.record_id,
                            "amount_original": str(p.amount_original),
                            "currency_original": p.currency_original,
                            "amount_converted": str(p.converted.amount_converted),
                            "fx_rate_used": str(p.converted.fx_rate_used),
                            "direction": p.direction,
                        }
                        for p in chosen
                    ],
                ],
                "date_comparison": {
                    "invoice_posted_at": inv.posted_at_iso,
                    "other_posted_at_min": min(p.posted_at_iso for p in chosen),
                    "other_posted_at_max": max(p.posted_at_iso for p in chosen),
                    "max_posted_days_diff": context.parameters.max_posted_days_diff,
                },
                "reference_id_comparison": {
                    "invoice_reference_ids": list(inv.reference_ids),
                    "other_reference_ids_union": sorted({rid for p in chosen for rid in p.reference_ids}),
                },
                "counterparty_comparison": {
                    "invoice_counterparty_id": inv.counterparty_id,
                    "other_counterparty_ids": sorted({p.counterparty_id for p in chosen}),
                    "matched": True,
                },
                "match_selection": {
                    "conflict_handling": "first_match_wins",
                    "candidate_order": "posted_at_iso asc, record_id asc",
                    "selected_other_record_ids": [p.record_id for p in chosen],
                    "total_applied_in_base": str(total_applied),
                    "invoice_amount_in_base": str(invoice_abs),
                    "remaining_in_base": str(remaining),
                },
                "primary_links": list(matched_ids),
            }

            outcomes.append(
                MatchOutcome(
                    rule_id=self.rule_id,
                    rule_version=self.rule_version,
                    confidence=confidence,
                    matched_record_ids=matched_ids,
                    unmatched_amount=remaining,
                    selection_rationale="Partial settlement group selected deterministically; remaining amount computed explicitly.",
                    evidence_payload=evidence_payload,
                )
            )
        return outcomes


@dataclass(frozen=True)
class PartialManyInvoicesOnePaymentRule:
    """
    Many-to-one partial settlement:
    one payment applied across multiple invoices deterministically.
    """

    rule_id: str = "ff.match.invoice_payment.partial_many_to_one"
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

        invoices_sorted = sorted(invoices, key=lambda r: (r.posted_at_iso, r.record_id))
        payments_sorted = sorted(payments, key=lambda r: (r.posted_at_iso, r.record_id))

        outcomes: list[MatchOutcome] = []
        for pay in payments_sorted:
            candidates = [
                inv
                for inv in invoices_sorted
                if inv.record_id not in used_record_ids
                and _same_counterparty(inv, pay)
                and _opposite_direction(inv, pay)
                and _eligible_by_date(context, inv, pay)
            ]
            if not candidates:
                continue

            payment_abs = abs(pay.signed_converted_amount)
            total_invoices = Decimal("0")
            chosen_invoices: list[CanonicalInput] = []
            for inv in candidates:
                if total_invoices >= payment_abs:
                    break
                inv_abs = abs(inv.signed_converted_amount)
                if inv_abs == Decimal("0"):
                    continue
                chosen_invoices.append(inv)
                total_invoices += inv_abs

            if not chosen_invoices:
                continue
            if len(chosen_invoices) < 2:
                # This rule is explicitly many-to-one; one-to-many is handled by PartialInvoicePaymentRule.
                continue

            # If it balances exactly for the selected invoices, skip (exact group matching is out of scope here).
            if total_invoices == payment_abs:
                continue

            remaining = abs(total_invoices - payment_abs)
            confidence = require_confidence(CONFIDENCE_PARTIAL)

            # Keep invoice first for evidence schema compatibility.
            matched_ids = tuple([chosen_invoices[0].record_id] + [inv.record_id for inv in chosen_invoices[1:]] + [pay.record_id])

            evidence_payload = {
                "rule_id": self.rule_id,
                "rule_version": self.rule_version,
                "confidence": confidence,
                "tolerance": None,
                "amount_comparisons": [
                    *[
                        {
                            "record_id": inv.record_id,
                            "amount_original": str(inv.amount_original),
                            "currency_original": inv.currency_original,
                            "amount_converted": str(inv.converted.amount_converted),
                            "fx_rate_used": str(inv.converted.fx_rate_used),
                            "direction": inv.direction,
                        }
                        for inv in chosen_invoices
                    ],
                    {
                        "record_id": pay.record_id,
                        "amount_original": str(pay.amount_original),
                        "currency_original": pay.currency_original,
                        "amount_converted": str(pay.converted.amount_converted),
                        "fx_rate_used": str(pay.converted.fx_rate_used),
                        "direction": pay.direction,
                    },
                ],
                "date_comparison": {
                    "invoice_posted_at": min(inv.posted_at_iso for inv in chosen_invoices),
                    "counterpart_posted_at": [inv.posted_at_iso for inv in chosen_invoices[1:]] + [pay.posted_at_iso],
                    "max_posted_days_diff": context.parameters.max_posted_days_diff,
                },
                "reference_id_comparison": {
                    "invoice_reference_ids": list(chosen_invoices[0].reference_ids),
                    "other_reference_ids_union": sorted({rid for inv in chosen_invoices for rid in inv.reference_ids}.union(pay.reference_ids)),
                },
                "counterparty_comparison": {
                    "invoice_counterparty_id": chosen_invoices[0].counterparty_id,
                    "other_counterparty_ids": sorted({inv.counterparty_id for inv in chosen_invoices}.union({pay.counterparty_id})),
                    "matched": True,
                },
                "match_selection": {
                    "conflict_handling": "first_match_wins",
                    "candidate_order": "posted_at_iso asc, record_id asc",
                    "selected_invoice_record_ids": [inv.record_id for inv in chosen_invoices],
                    "selected_payment_record_id": pay.record_id,
                    "sum_invoices_in_base": str(total_invoices),
                    "payment_amount_in_base": str(payment_abs),
                    "remaining_in_base": str(remaining),
                },
                "primary_links": list(matched_ids),
            }

            outcomes.append(
                MatchOutcome(
                    rule_id=self.rule_id,
                    rule_version=self.rule_version,
                    confidence=confidence,
                    matched_record_ids=matched_ids,
                    unmatched_amount=remaining,
                    selection_rationale="Many-to-one partial group selected deterministically; remaining amount computed explicitly.",
                    evidence_payload=evidence_payload,
                )
            )
        return outcomes
