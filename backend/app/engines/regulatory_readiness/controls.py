from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, Tuple, Type


class ControlCategory(str, Enum):
    DATA_GOVERNANCE = "data_governance"
    REPORTING = "reporting"
    OPERATIONS = "operations"
    THIRD_PARTY = "third_party"
    RISK_MANAGEMENT = "risk_management"
    COMPLIANCE_MONITORING = "compliance_monitoring"

    @classmethod
    def default(cls) -> "ControlCategory":
        return cls.OPERATIONS


class RiskType(str, Enum):
    COMPLIANCE = "compliance"
    OPERATIONAL = "operational"
    FINANCIAL = "financial"
    STRATEGIC = "strategic"
    REPUTATIONAL = "reputational"

    @classmethod
    def default(cls) -> "RiskType":
        return cls.COMPLIANCE


class ControlStatus(str, Enum):
    IMPLEMENTED = "implemented"
    PARTIAL = "partial"
    NOT_IMPLEMENTED = "not_implemented"
    MONITORED = "monitored"
    UNKNOWN = "unknown"

    @classmethod
    def default(cls) -> "ControlStatus":
        return cls.UNKNOWN


def _as_tuple(value: Iterable[str] | str | None) -> Tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        trimmed = value.strip()
        return (trimmed,) if trimmed else ()
    result: list[str] = []
    for part in value:
        trimmed = str(part).strip()
        if trimmed:
            result.append(trimmed)
    return tuple(result)


def _resolve_enum(value: object, enum_cls: Type[Enum], default: Enum) -> Enum:
    if isinstance(value, enum_cls):
        return value
    if isinstance(value, str) and value in enum_cls._value2member_map_:
        return enum_cls(value)
    return default


@dataclass(frozen=True)
class ControlDefinition:
    control_id: str
    title: str
    description: str
    category: ControlCategory
    risk_type: RiskType
    ownership: Tuple[str, ...]
    status: ControlStatus
    frameworks: Tuple[str, ...]
    criticality: str | None = None
    tags: Tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict:
        return {
            "control_id": self.control_id,
            "title": self.title,
            "description": self.description,
            "category": self.category.value,
            "risk_type": self.risk_type.value,
            "ownership": self.ownership,
            "status": self.status.value,
            "frameworks": self.frameworks,
            "criticality": self.criticality,
            "tags": self.tags,
        }

    @staticmethod
    def from_payload(payload: dict) -> "ControlDefinition":
        if not isinstance(payload, dict):
            raise ValueError("control payload must be a mapping")
        control_id = str(payload.get("id") or payload.get("control_id") or "").strip()
        if not control_id:
            raise ValueError("control_id is required")
        title = str(payload.get("title") or payload.get("name") or control_id)
        description = str(payload.get("description") or payload.get("summary") or "").strip()
        category = _resolve_enum(payload.get("category"), ControlCategory, ControlCategory.default())
        risk_type = _resolve_enum(payload.get("risk_type"), RiskType, RiskType.default())
        status = _resolve_enum(payload.get("status"), ControlStatus, ControlStatus.default())
        ownership = _as_tuple(payload.get("ownership") or payload.get("owners"))
        if not ownership:
            ownership = ("unknown",)
        frameworks = _as_tuple(payload.get("frameworks") or payload.get("applicable_frameworks") or payload.get("framework_ids"))
        criticality = payload.get("criticality")
        raw_tags = _as_tuple(payload.get("tags"))
        base_tags = []
        for tag in (category.value, risk_type.value):
            if tag not in base_tags:
                base_tags.append(tag)
        tags = tuple(raw_tags) + tuple(x for x in base_tags if x not in raw_tags)
        return ControlDefinition(
            control_id=control_id,
            title=title,
            description=description,
            category=category,
            risk_type=risk_type,
            ownership=ownership,
            status=status,
            frameworks=frameworks,
            criticality=str(criticality) if criticality is not None else None,
            tags=tags,
        )
