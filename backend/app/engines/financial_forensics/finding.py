from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any


class RuleIdentifierMissingError(ValueError):
    pass


class PrimaryEvidenceMissingError(ValueError):
    pass


class ComparisonDetailsMissingError(ValueError):
    pass


class ToleranceMissingError(ValueError):
    pass


@dataclass(frozen=True)
class FindingDetails:
    left_record_id: str
    right_record_ids: list[str]
    comparison_currency: str
    amounts: dict[str, Any]
    diff: Decimal
    tolerance: dict[str, Any] | None
    exposure: dict[str, Any]
    assumptions: dict[str, Any]
    timestamps: dict[str, Any]


def _details_to_dict(details: dict[str, Any] | FindingDetails) -> dict[str, Any]:
    if isinstance(details, FindingDetails):
        return asdict(details)
    return details


def validate_finding_completeness(
    *,
    rule_id: str | None,
    rule_version: str | None,
    framework_version: str | None,
    confidence: str,
    finding_type: str,
    primary_evidence_item_id: str | None,
    details: dict[str, Any] | FindingDetails | None,
    tolerance_required: bool = False,
) -> None:
    if not rule_id:
        raise RuleIdentifierMissingError("RULE_ID_MISSING")
    if not rule_version:
        raise RuleIdentifierMissingError("RULE_VERSION_MISSING")
    if not framework_version:
        raise RuleIdentifierMissingError("FRAMEWORK_VERSION_MISSING")
    if not primary_evidence_item_id:
        raise PrimaryEvidenceMissingError("PRIMARY_EVIDENCE_MISSING")
    if details is None:
        raise ComparisonDetailsMissingError("DETAILS_MISSING")

    details_dict = _details_to_dict(details)
    required_fields = [
        "left_record_id",
        "right_record_ids",
        "comparison_currency",
        "amounts",
        "diff",
        "exposure",
        "assumptions",
        "timestamps",
    ]
    for field in required_fields:
        if field not in details_dict:
            raise ComparisonDetailsMissingError(f"DETAILS_FIELD_MISSING: {field}")

    if tolerance_required:
        tolerance = details_dict.get("tolerance")
        if not isinstance(tolerance, dict):
            raise ToleranceMissingError("DETAILS_TOLERANCE_FIELD_MISSING")
        for k in ["tolerance_absolute", "tolerance_percent", "threshold_applied"]:
            if k not in tolerance:
                raise ToleranceMissingError("DETAILS_TOLERANCE_FIELD_MISSING")


