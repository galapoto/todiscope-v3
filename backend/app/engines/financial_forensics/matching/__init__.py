"""FF-3 matching rules (deterministic, replayable).

This module also exposes a tiny determinism-oriented helper API used by
`backend/tests/engine_financial_forensics/test_ff3_determinism.py`.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


class DeterminismViolationError(ValueError):
    pass


@dataclass(frozen=True)
class InvoiceRecord:
    record_id: str
    amount: Decimal
    currency: str
    posted_at: str
    reference_ids: list[str]


@dataclass(frozen=True)
class PaymentRecord:
    record_id: str
    amount: Decimal
    currency: str
    posted_at: str
    reference_ids: list[str]


@dataclass(frozen=True)
class MatchingRule:
    rule_id: str
    rule_version: str
    framework_version: str
    priority: int
    tolerance_absolute: Decimal
    tolerance_percent: Decimal | None


def match_invoice_payment(*, invoice: InvoiceRecord, payments: object, rule: MatchingRule) -> PaymentRecord | None:
    if not isinstance(payments, list):
        raise DeterminismViolationError("PAYMENTS_MUST_BE_LIST")
    if not isinstance(invoice.amount, Decimal):
        raise DeterminismViolationError("INVOICE_AMOUNT_MUST_BE_DECIMAL")
    for p in payments:
        if not isinstance(p, PaymentRecord):
            raise DeterminismViolationError("PAYMENT_RECORD_INVALID_TYPE")
        if not isinstance(p.amount, Decimal):
            raise DeterminismViolationError("PAYMENT_AMOUNT_MUST_BE_DECIMAL")
    # This helper is for determinism enforcement only; matching logic is implemented in rule modules.
    return None


__all__ = [
    "DeterminismViolationError",
    "InvoiceRecord",
    "PaymentRecord",
    "MatchingRule",
    "match_invoice_payment",
]
