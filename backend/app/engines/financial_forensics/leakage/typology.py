from __future__ import annotations

from enum import Enum


class LeakageTypology(str, Enum):
    # Closed v1 set for FF-4 (no extras).
    UNMATCHED_INVOICE = "unmatched_invoice"
    UNMATCHED_PAYMENT = "unmatched_payment"
    OVERPAYMENT = "overpayment"
    UNDERPAYMENT = "underpayment"
    TIMING_MISMATCH = "timing_mismatch"
    PARTIAL_SETTLEMENT_RESIDUAL = "partial_settlement_residual"


__all__ = ["LeakageTypology"]
