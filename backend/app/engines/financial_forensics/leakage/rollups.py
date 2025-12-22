from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from backend.app.engines.financial_forensics.leakage.typology import LeakageTypology


@dataclass(frozen=True)
class RollupRow:
    typology: LeakageTypology
    finding_count: int
    total_exposure_abs: Decimal


@dataclass(frozen=True)
class Rollups:
    by_typology: tuple[RollupRow, ...]
    total_findings: int
    total_exposure_abs: Decimal


def roll_up(
    *,
    classified: list[dict[str, Any]],
) -> Rollups:
    """
    Deterministic rollups derived only from finding-level computed exposure.
    `classified` items must include: typology (str), exposure_abs (Decimal-compatible).
    """
    buckets: dict[LeakageTypology, tuple[int, Decimal]] = {}
    total_findings = 0
    total_exposure = Decimal("0")

    for row in classified:
        typology = LeakageTypology(str(row["typology"]))
        exposure_abs = Decimal(str(row["exposure_abs"]))
        count, tot = buckets.get(typology, (0, Decimal("0")))
        buckets[typology] = (count + 1, tot + exposure_abs)
        total_findings += 1
        total_exposure += exposure_abs

    by_typology = tuple(
        RollupRow(typology=t, finding_count=buckets[t][0], total_exposure_abs=buckets[t][1])
        for t in sorted(buckets.keys(), key=lambda x: x.value)
    )
    return Rollups(by_typology=by_typology, total_findings=total_findings, total_exposure_abs=total_exposure)


__all__ = ["RollupRow", "Rollups", "roll_up"]

