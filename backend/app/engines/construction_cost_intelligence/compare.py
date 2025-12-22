from __future__ import annotations

from decimal import Decimal
from types import MappingProxyType
from typing import Any, Iterable

from backend.app.engines.construction_cost_intelligence.errors import DatasetVersionMismatchError, IdentityInvalidError
from backend.app.engines.construction_cost_intelligence.models import (
    ComparisonConfig,
    ComparisonBreakdown,
    ComparisonMatch,
    ComparisonResult,
    CostBasis,
    CostLine,
    validate_dataset_version_id,
)


def _ensure_dataset_version_consistent(dv_id: str, lines: Iterable[CostLine]) -> None:
    for line in lines:
        if line.dataset_version_id != dv_id:
            raise DatasetVersionMismatchError("DATASET_VERSION_MISMATCH")


def _match_key(*, line: CostLine, identity_fields: tuple[str, ...]) -> str:
    missing: list[str] = []
    parts: list[str] = []
    for field in identity_fields:
        val = line.identity.get(field)
        if val is None or not str(val).strip():
            missing.append(field)
            continue
        parts.append(f"{field}={val}")
    if missing:
        raise IdentityInvalidError(f"IDENTITY_MISSING_FIELDS:{','.join(missing)}")
    return "|".join(parts)


def _effective_cost(line: CostLine, *, cost_basis: CostBasis) -> Decimal | None:
    if cost_basis == "total_cost":
        return line.total_cost
    if cost_basis == "quantity_unit_cost":
        if line.quantity is None or line.unit_cost is None:
            return None
        return line.quantity * line.unit_cost
    # prefer_total_cost
    if line.total_cost is not None:
        return line.total_cost
    if line.quantity is None or line.unit_cost is None:
        return None
    return line.quantity * line.unit_cost


def _sum_cost_with_incomplete(lines: tuple[CostLine, ...], *, cost_basis: CostBasis) -> tuple[Decimal, int]:
    total = Decimal("0")
    incomplete = 0
    for ln in lines:
        c = _effective_cost(ln, cost_basis=cost_basis)
        if c is None:
            incomplete += 1
            continue
        total += c
    return total, incomplete


def _field_value(line: CostLine, field: str) -> str | None:
    val = line.identity.get(field)
    if isinstance(val, str) and val.strip():
        return val.strip()
    attrs: dict[str, Any] = dict(line.attributes or {})
    val2 = attrs.get(field)
    if isinstance(val2, str) and val2.strip():
        return val2.strip()
    return None


def _breakdown_key(*, line: CostLine, breakdown_fields: tuple[str, ...]) -> tuple[str, MappingProxyType]:
    dims: dict[str, str] = {}
    missing: list[str] = []
    for field in breakdown_fields:
        v = _field_value(line, field)
        if v is None:
            missing.append(field)
            continue
        dims[field] = v
    if missing:
        raise IdentityInvalidError(f"BREAKDOWN_MISSING_FIELDS:{','.join(missing)}")
    key = "|".join(f"{k}={dims[k]}" for k in sorted(dims.keys()))
    return key, MappingProxyType(dims)


def compare_boq_to_actuals(
    *,
    dataset_version_id: str,
    boq_lines: list[CostLine],
    actual_lines: list[CostLine],
    config: ComparisonConfig,
) -> ComparisonResult:
    """
    Align BOQ and Actual lines by identity fields and return an immutable comparison model.

    This function is intentionally domain-agnostic:
    - No variance categorization (e.g., "over/under") is performed
    - No reporting or narrative generation
    - Only alignment and arithmetic where inputs are present
    """
    dv_id = validate_dataset_version_id(dataset_version_id)
    if not isinstance(boq_lines, list) or not isinstance(actual_lines, list):
        raise TypeError("boq_lines and actual_lines must be lists")

    _ensure_dataset_version_consistent(dv_id, boq_lines)
    _ensure_dataset_version_consistent(dv_id, actual_lines)

    boq_by_key: dict[str, list[CostLine]] = {}
    for ln in boq_lines:
        if ln.kind != "boq":
            raise ValueError("boq_lines must contain kind='boq'")
        key = _match_key(line=ln, identity_fields=config.identity_fields)
        boq_by_key.setdefault(key, []).append(ln)

    actual_by_key: dict[str, list[CostLine]] = {}
    for ln in actual_lines:
        if ln.kind != "actual":
            raise ValueError("actual_lines must contain kind='actual'")
        key = _match_key(line=ln, identity_fields=config.identity_fields)
        actual_by_key.setdefault(key, []).append(ln)

    all_keys = sorted(set(boq_by_key.keys()) | set(actual_by_key.keys()))
    matched: list[ComparisonMatch] = []
    unmatched_boq: list[CostLine] = []
    unmatched_actual: list[CostLine] = []

    for key in all_keys:
        boq_tuple = tuple(boq_by_key.get(key, []))
        actual_tuple = tuple(actual_by_key.get(key, []))
        if boq_tuple and actual_tuple:
            boq_total, boq_incomplete = _sum_cost_with_incomplete(boq_tuple, cost_basis=config.cost_basis)
            actual_total, actual_incomplete = _sum_cost_with_incomplete(actual_tuple, cost_basis=config.cost_basis)
            delta = actual_total - boq_total
            matched.append(
                ComparisonMatch(
                    match_key=key,
                    boq_lines=boq_tuple,
                    actual_lines=actual_tuple,
                    boq_total_cost=boq_total,
                    actual_total_cost=actual_total,
                    cost_delta=delta,
                    boq_incomplete_cost_count=boq_incomplete,
                    actual_incomplete_cost_count=actual_incomplete,
                )
            )
        elif boq_tuple:
            unmatched_boq.extend(list(boq_tuple))
        else:
            unmatched_actual.extend(list(actual_tuple))

    breakdowns: tuple[ComparisonBreakdown, ...] = ()
    if config.breakdown_fields:
        buckets: dict[str, dict[str, Any]] = {}
        for ln in list(boq_lines) + list(actual_lines):
            key, dims = _breakdown_key(line=ln, breakdown_fields=config.breakdown_fields)
            if key not in buckets:
                buckets[key] = {
                    "dimensions": dims,
                    "boq_total": Decimal("0"),
                    "actual_total": Decimal("0"),
                    "boq_count": 0,
                    "actual_count": 0,
                    "boq_incomplete": 0,
                    "actual_incomplete": 0,
                }
            bucket = buckets[key]
            cost = _effective_cost(ln, cost_basis=config.cost_basis)
            if ln.kind == "boq":
                bucket["boq_count"] += 1
                if cost is None:
                    bucket["boq_incomplete"] += 1
                else:
                    bucket["boq_total"] += cost
            else:
                bucket["actual_count"] += 1
                if cost is None:
                    bucket["actual_incomplete"] += 1
                else:
                    bucket["actual_total"] += cost

        breakdowns_list: list[ComparisonBreakdown] = []
        for k in sorted(buckets.keys()):
            b = buckets[k]
            boq_total = b["boq_total"]
            actual_total = b["actual_total"]
            breakdowns_list.append(
                ComparisonBreakdown(
                    breakdown_key=k,
                    dimensions=b["dimensions"],
                    boq_total_cost=boq_total,
                    actual_total_cost=actual_total,
                    cost_delta=actual_total - boq_total,
                    boq_lines_count=b["boq_count"],
                    actual_lines_count=b["actual_count"],
                    boq_incomplete_cost_count=b["boq_incomplete"],
                    actual_incomplete_cost_count=b["actual_incomplete"],
                )
            )
        breakdowns = tuple(breakdowns_list)

    return ComparisonResult(
        dataset_version_id=dv_id,
        identity_fields=config.identity_fields,
        breakdown_fields=config.breakdown_fields,
        cost_basis=config.cost_basis,
        matched=tuple(matched),
        unmatched_boq=tuple(unmatched_boq),
        unmatched_actual=tuple(unmatched_actual),
        breakdowns=breakdowns,
    )
