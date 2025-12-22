from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RuntimeLimits:
    max_canonical_records: int
    max_findings: int
    max_report_findings: int


DEFAULT_LIMITS = RuntimeLimits(
    max_canonical_records=100_000,
    max_findings=50_000,
    max_report_findings=10_000,
)


def limits_from_parameters(parameters: dict) -> RuntimeLimits:
    """
    Optional explicit overrides for tests / controlled environments.
    No silent defaults: absence means DEFAULT_LIMITS.
    """
    def _maybe_int(key: str) -> int | None:
        v = parameters.get(key)
        if v is None:
            return None
        try:
            iv = int(v)
        except (TypeError, ValueError):
            raise ValueError(f"RUNTIME_LIMIT_INVALID: {key}")
        if iv <= 0:
            raise ValueError(f"RUNTIME_LIMIT_INVALID: {key}")
        return iv

    max_canonical_records = _maybe_int("max_canonical_records") or DEFAULT_LIMITS.max_canonical_records
    max_findings = _maybe_int("max_findings") or DEFAULT_LIMITS.max_findings
    max_report_findings = _maybe_int("max_report_findings") or DEFAULT_LIMITS.max_report_findings
    return RuntimeLimits(
        max_canonical_records=max_canonical_records,
        max_findings=max_findings,
        max_report_findings=max_report_findings,
    )


__all__ = ["RuntimeLimits", "DEFAULT_LIMITS", "limits_from_parameters"]
