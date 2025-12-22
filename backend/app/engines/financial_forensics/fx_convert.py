from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


@dataclass(frozen=True)
class ConversionResult:
    amount_converted: Decimal
    fx_rate_used: Decimal


_ROUNDING = {
    "ROUND_HALF_UP": ROUND_HALF_UP,
}


def convert_amount(
    *,
    amount_original: Decimal,
    currency_original: str,
    base_currency: str,
    rates: dict[str, str],
    rounding_mode: str,
    rounding_quantum: str,
) -> ConversionResult:
    if rounding_mode not in _ROUNDING:
        raise ValueError("ROUNDING_MODE_REQUIRED")
    if not isinstance(rounding_quantum, str) or not rounding_quantum:
        raise ValueError("ROUNDING_QUANTUM_REQUIRED")

    cur = currency_original.upper()
    base = base_currency.upper()
    if cur == base:
        rate = Decimal("1")
    else:
        if cur not in rates:
            raise ValueError("FX_RATE_MISSING")
        rate = Decimal(rates[cur])

    converted = (amount_original * rate).quantize(Decimal(rounding_quantum), rounding=_ROUNDING[rounding_mode])
    return ConversionResult(amount_converted=converted, fx_rate_used=rate)

