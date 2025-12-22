from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


@dataclass(frozen=True)
class ExposureResult:
    exposure_abs: Decimal
    exposure_signed: Decimal
    rounding_mode: str
    rounding_quantum: str


def _to_rounding(rounding_mode: str) -> str:
    # Minimal supported set; extend only when required.
    if rounding_mode == "ROUND_HALF_UP":
        return ROUND_HALF_UP
    raise ValueError(f"ROUNDING_MODE_NOT_SUPPORTED: {rounding_mode}")


def _extract_rounding_from_evidence(evidence_payload: dict) -> tuple[str, str]:
    rule_identity = evidence_payload.get("rule_identity", {})
    executed = rule_identity.get("executed_parameters", {}) if isinstance(rule_identity, dict) else {}
    rounding_mode = executed.get("rounding_mode") or "ROUND_HALF_UP"
    rounding_quantum = executed.get("rounding_quantum") or "0.01"
    return str(rounding_mode), str(rounding_quantum)


def compute_finding_exposure(
    *,
    finding: dict,
    evidence_payload: dict,
) -> ExposureResult:
    """
    Deterministic exposure binding.

    - Partial findings: exposure is bound to FF-3 `unmatched_amount` (already computed by matching).
    - Non-partial findings: exposure is derived from FX-converted values (diff_converted) stored in evidence payload.
    """
    rounding_mode, rounding_quantum = _extract_rounding_from_evidence(evidence_payload)

    finding_type = finding.get("finding_type")
    if finding_type == "partial_match":
        raw = finding.get("unmatched_amount")
        if raw is None:
            raise ValueError("PARTIAL_EXPOSURE_REQUIRES_UNMATCHED_AMOUNT")
        return compute_exposure(
            diff_converted=Decimal(str(raw)),
            rounding_mode=rounding_mode,
            rounding_quantum=rounding_quantum,
        )

    amount_comparison = evidence_payload.get("amount_comparison")
    if not isinstance(amount_comparison, dict):
        raise ValueError("EXPOSURE_REQUIRES_AMOUNT_COMPARISON")
    diff_converted = amount_comparison.get("diff_converted")
    if diff_converted is None:
        raise ValueError("EXPOSURE_REQUIRES_DIFF_CONVERTED")

    return compute_exposure(
        diff_converted=Decimal(str(diff_converted)),
        rounding_mode=rounding_mode,
        rounding_quantum=rounding_quantum,
    )


def compute_exposure(
    *,
    diff_converted: Decimal,
    rounding_mode: str,
    rounding_quantum: str,
) -> ExposureResult:
    quantum = Decimal(rounding_quantum)
    mode = _to_rounding(rounding_mode)
    signed = diff_converted.quantize(quantum, rounding=mode)
    return ExposureResult(
        exposure_abs=abs(signed),
        exposure_signed=signed,
        rounding_mode=rounding_mode,
        rounding_quantum=rounding_quantum,
    )
