from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from types import MappingProxyType
from typing import Any, Literal, Mapping

from backend.app.engines.construction_cost_intelligence.errors import (
    CostLineInvalidError,
    DatasetVersionInvalidError,
    DatasetVersionMissingError,
    IdentityInvalidError,
)


def _require_non_empty_str(value: object, *, code_missing: str, code_invalid: str) -> str:
    if value is None:
        raise DatasetVersionMissingError(code_missing)
    if not isinstance(value, str) or not value.strip():
        raise DatasetVersionInvalidError(code_invalid)
    return value.strip()


def validate_dataset_version_id(value: object) -> str:
    dv = _require_non_empty_str(
        value,
        code_missing="DATASET_VERSION_ID_REQUIRED",
        code_invalid="DATASET_VERSION_ID_INVALID",
    )
    try:
        parsed = uuid.UUID(dv)
    except ValueError as exc:
        raise DatasetVersionInvalidError("DATASET_VERSION_ID_INVALID_UUID") from exc
    if parsed.version != 7:
        raise DatasetVersionInvalidError("DATASET_VERSION_ID_UUIDV7_REQUIRED") from None
    return dv


def _coerce_optional_decimal(value: object, *, field_name: str) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, str):
        if not value.strip():
            return None
        try:
            return Decimal(value.strip())
        except InvalidOperation as exc:
            raise CostLineInvalidError(f"{field_name.upper()}_INVALID") from exc
    raise CostLineInvalidError(f"{field_name.upper()}_INVALID_TYPE")


def _freeze_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return MappingProxyType(dict(value or {}))


def _freeze_str_mapping(value: Mapping[str, Any] | None, *, field_name: str) -> Mapping[str, str]:
    frozen: dict[str, str] = {}
    for k, v in dict(value or {}).items():
        if not isinstance(k, str) or not k.strip():
            raise IdentityInvalidError(f"{field_name.upper()}_KEY_INVALID")
        if not isinstance(v, str) or not v.strip():
            raise IdentityInvalidError(f"{field_name.upper()}_VALUE_INVALID")
        frozen[k.strip()] = v.strip()
    return MappingProxyType(frozen)


CostKind = Literal["boq", "actual"]
CostBasis = Literal["total_cost", "quantity_unit_cost", "prefer_total_cost"]


@dataclass(frozen=True, slots=True)
class CostLine:
    dataset_version_id: str
    kind: CostKind
    line_id: str
    identity: Mapping[str, str]
    quantity: Decimal | None = None
    unit_cost: Decimal | None = None
    total_cost: Decimal | None = None
    currency: str | None = None
    attributes: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "dataset_version_id", validate_dataset_version_id(self.dataset_version_id))

        if self.kind not in ("boq", "actual"):
            raise CostLineInvalidError("KIND_INVALID")
        if not isinstance(self.line_id, str) or not self.line_id.strip():
            raise CostLineInvalidError("LINE_ID_INVALID")
        object.__setattr__(self, "line_id", self.line_id.strip())

        object.__setattr__(self, "identity", _freeze_str_mapping(self.identity, field_name="identity"))

        object.__setattr__(self, "quantity", _coerce_optional_decimal(self.quantity, field_name="quantity"))
        object.__setattr__(self, "unit_cost", _coerce_optional_decimal(self.unit_cost, field_name="unit_cost"))
        object.__setattr__(self, "total_cost", _coerce_optional_decimal(self.total_cost, field_name="total_cost"))

        if self.currency is not None:
            if not isinstance(self.currency, str) or not self.currency.strip():
                raise CostLineInvalidError("CURRENCY_INVALID")
            object.__setattr__(self, "currency", self.currency.strip())

        object.__setattr__(self, "attributes", _freeze_mapping(self.attributes))


@dataclass(frozen=True, slots=True)
class NormalizationMapping:
    """
    Field mapping for normalizing source dicts into CostLine.

    This is intentionally domain-agnostic: it only maps keys and preserves extras.
    """

    line_id: str
    identity: Mapping[str, str]
    quantity: str | None = None
    unit_cost: str | None = None
    total_cost: str | None = None
    currency: str | None = None
    extras: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.line_id, str) or not self.line_id.strip():
            raise CostLineInvalidError("MAPPING_LINE_ID_REQUIRED")
        object.__setattr__(self, "line_id", self.line_id.strip())

        if not isinstance(self.identity, Mapping) or not dict(self.identity):
            raise IdentityInvalidError("MAPPING_IDENTITY_REQUIRED")
        object.__setattr__(self, "identity", _freeze_str_mapping(self.identity, field_name="mapping_identity"))

        for key in (self.quantity, self.unit_cost, self.total_cost, self.currency):
            if key is not None and (not isinstance(key, str) or not key.strip()):
                raise CostLineInvalidError("MAPPING_KEY_INVALID")

        if not isinstance(self.extras, tuple) or any(not isinstance(x, str) or not x.strip() for x in self.extras):
            raise CostLineInvalidError("MAPPING_EXTRAS_INVALID")


def normalize_cost_lines(
    *,
    dataset_version_id: str,
    kind: CostKind,
    raw_lines: list[Mapping[str, Any]],
    mapping: NormalizationMapping,
) -> list[CostLine]:
    dv_id = validate_dataset_version_id(dataset_version_id)
    if not isinstance(raw_lines, list):
        raise CostLineInvalidError("RAW_LINES_INVALID")

    normalized: list[CostLine] = []
    for idx, raw in enumerate(raw_lines):
        if not isinstance(raw, Mapping):
            raise CostLineInvalidError("RAW_LINE_INVALID")

        raw_dict = dict(raw)
        line_id_val = raw_dict.get(mapping.line_id)
        if not isinstance(line_id_val, str) or not line_id_val.strip():
            raise CostLineInvalidError(f"LINE_ID_REQUIRED_AT_INDEX_{idx}")

        identity: dict[str, str] = {}
        for out_key, in_key in dict(mapping.identity).items():
            val = raw_dict.get(in_key)
            if not isinstance(val, str) or not val.strip():
                raise IdentityInvalidError(f"IDENTITY_REQUIRED_{out_key.upper()}_AT_INDEX_{idx}")
            identity[out_key] = val.strip()

        attrs: dict[str, Any] = {}
        for k in mapping.extras:
            if k in raw_dict:
                attrs[k] = raw_dict.get(k)

        normalized.append(
            CostLine(
                dataset_version_id=dv_id,
                kind=kind,
                line_id=line_id_val.strip(),
                identity=identity,
                quantity=raw_dict.get(mapping.quantity) if mapping.quantity else None,
                unit_cost=raw_dict.get(mapping.unit_cost) if mapping.unit_cost else None,
                total_cost=raw_dict.get(mapping.total_cost) if mapping.total_cost else None,
                currency=raw_dict.get(mapping.currency) if mapping.currency else None,
                attributes=attrs,
            )
        )

    return normalized


@dataclass(frozen=True, slots=True)
class ComparisonConfig:
    identity_fields: tuple[str, ...]
    cost_basis: CostBasis = "prefer_total_cost"
    breakdown_fields: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if (
            not isinstance(self.identity_fields, tuple)
            or not self.identity_fields
            or any(not isinstance(f, str) or not f.strip() for f in self.identity_fields)
        ):
            raise IdentityInvalidError("IDENTITY_FIELDS_REQUIRED")
        object.__setattr__(self, "identity_fields", tuple(f.strip() for f in self.identity_fields))
        if self.cost_basis not in ("total_cost", "quantity_unit_cost", "prefer_total_cost"):
            raise CostLineInvalidError("COST_BASIS_INVALID")
        if not isinstance(self.breakdown_fields, tuple) or any(
            not isinstance(f, str) or not f.strip() for f in self.breakdown_fields
        ):
            raise IdentityInvalidError("BREAKDOWN_FIELDS_INVALID")
        object.__setattr__(self, "breakdown_fields", tuple(f.strip() for f in self.breakdown_fields))


@dataclass(frozen=True, slots=True)
class ComparisonMatch:
    match_key: str
    boq_lines: tuple[CostLine, ...]
    actual_lines: tuple[CostLine, ...]
    boq_total_cost: Decimal
    actual_total_cost: Decimal
    cost_delta: Decimal
    boq_incomplete_cost_count: int
    actual_incomplete_cost_count: int


@dataclass(frozen=True, slots=True)
class ComparisonBreakdown:
    breakdown_key: str
    dimensions: Mapping[str, str]
    boq_total_cost: Decimal
    actual_total_cost: Decimal
    cost_delta: Decimal
    boq_lines_count: int
    actual_lines_count: int
    boq_incomplete_cost_count: int
    actual_incomplete_cost_count: int


@dataclass(frozen=True, slots=True)
class ComparisonResult:
    dataset_version_id: str
    identity_fields: tuple[str, ...]
    breakdown_fields: tuple[str, ...]
    cost_basis: CostBasis
    matched: tuple[ComparisonMatch, ...]
    unmatched_boq: tuple[CostLine, ...]
    unmatched_actual: tuple[CostLine, ...]
    breakdowns: tuple[ComparisonBreakdown, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "dataset_version_id", validate_dataset_version_id(self.dataset_version_id))
