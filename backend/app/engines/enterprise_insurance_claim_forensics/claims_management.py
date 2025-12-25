"""Core structure for claims management within the Enterprise Insurance Claim Forensics Engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True, slots=True)
class ClaimRecord:
    """Immutable claim record structure."""

    claim_id: str
    dataset_version_id: str
    policy_number: str
    claim_number: str
    claim_type: str
    claim_status: str
    reported_date: datetime
    incident_date: datetime | None
    claim_amount: float
    currency: str
    claimant_name: str
    claimant_type: str
    description: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate claim record structure."""
        if not self.claim_id or not isinstance(self.claim_id, str):
            raise ValueError("CLAIM_ID_REQUIRED")
        if not self.dataset_version_id or not isinstance(self.dataset_version_id, str):
            raise ValueError("DATASET_VERSION_ID_REQUIRED")
        if not self.policy_number or not isinstance(self.policy_number, str):
            raise ValueError("POLICY_NUMBER_REQUIRED")
        if not self.claim_number or not isinstance(self.claim_number, str):
            raise ValueError("CLAIM_NUMBER_REQUIRED")
        if not self.claim_type or not isinstance(self.claim_type, str):
            raise ValueError("CLAIM_TYPE_REQUIRED")
        if not self.claim_status or not isinstance(self.claim_status, str):
            raise ValueError("CLAIM_STATUS_REQUIRED")
        if not isinstance(self.claim_amount, (int, float)) or self.claim_amount < 0:
            raise ValueError("CLAIM_AMOUNT_INVALID")
        if not self.currency or not isinstance(self.currency, str):
            raise ValueError("CURRENCY_REQUIRED")
        if not self.claimant_name or not isinstance(self.claimant_name, str):
            raise ValueError("CLAIMANT_NAME_REQUIRED")
        if not self.claimant_type or not isinstance(self.claimant_type, str):
            raise ValueError("CLAIMANT_TYPE_REQUIRED")


@dataclass(frozen=True, slots=True)
class ClaimTransaction:
    """Immutable claim transaction record."""

    transaction_id: str
    claim_id: str
    dataset_version_id: str
    transaction_type: str
    transaction_date: datetime
    amount: float
    currency: str
    description: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate transaction record structure."""
        if not self.transaction_id or not isinstance(self.transaction_id, str):
            raise ValueError("TRANSACTION_ID_REQUIRED")
        if not self.claim_id or not isinstance(self.claim_id, str):
            raise ValueError("CLAIM_ID_REQUIRED")
        if not self.dataset_version_id or not isinstance(self.dataset_version_id, str):
            raise ValueError("DATASET_VERSION_ID_REQUIRED")
        if not self.transaction_type or not isinstance(self.transaction_type, str):
            raise ValueError("TRANSACTION_TYPE_REQUIRED")
        if not isinstance(self.amount, (int, float)):
            raise ValueError("TRANSACTION_AMOUNT_INVALID")
        if not self.currency or not isinstance(self.currency, str):
            raise ValueError("CURRENCY_REQUIRED")


def _extract_claim_data(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize the claim dict out of a normalized record payload."""
    if isinstance(payload.get("data"), dict):
        nested = payload["data"]
        nested_claim = nested.get("insurance_claim") or nested.get("claim")
        if isinstance(nested_claim, dict):
            return nested_claim
        if isinstance(nested, dict) and ("claim_id" in nested or "claim_number" in nested):
            return nested
    direct = payload.get("insurance_claim") or payload.get("claim") or payload
    if not isinstance(direct, dict):
        raise ValueError("CLAIM_PAYLOAD_INVALID")
    return direct


def _parse_iso_datetime(value: object | None, default: datetime | None = None) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return default
    else:
        return default
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _coerce_float(value: object | None, fallback: float = 0.0) -> float:
    if value is None:
        return fallback
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return fallback


def extract_transactions_from_claim_payload(
    payload: dict[str, Any],
    dataset_version_id: str,
    claim_id: str,
    default_date: datetime,
) -> list[ClaimTransaction]:
    claim_data = _extract_claim_data(payload)
    collections: list[list[dict[str, Any]]] = []
    for key in ("transactions", "claim_transactions", "transaction_history", "activities"):
        candidate = claim_data.get(key)
        if isinstance(candidate, dict):
            collections.append([candidate])
        elif isinstance(candidate, list):
            collections.append(candidate)

    transactions: list[ClaimTransaction] = []
    for collection in collections:
        for item in collection:
            if not isinstance(item, dict):
                continue
            transaction_id = item.get("transaction_id") or item.get("id")
            if not transaction_id:
                continue
            tx_type = item.get("transaction_type") or item.get("type") or "unknown"
            tx_amount = _coerce_float(item.get("amount") or item.get("value"))
            currency = item.get("currency") or item.get("currency_code") or "USD"
            tx_date = _parse_iso_datetime(item.get("transaction_date"), default_date)
            if tx_date is None:
                tx_date = default_date
            description = item.get("description") or item.get("notes") or ""
            metadata = item.get("metadata") or {}
            if not isinstance(metadata, dict):
                metadata = {}
            transactions.append(
                ClaimTransaction(
                    transaction_id=str(transaction_id),
                    claim_id=claim_id,
                    dataset_version_id=dataset_version_id,
                    transaction_type=str(tx_type),
                    transaction_date=tx_date,
                    amount=tx_amount,
                    currency=str(currency),
                    description=str(description),
                    metadata=metadata,
                )
            )
    return transactions


def parse_claim_from_payload(payload: dict[str, Any], dataset_version_id: str) -> ClaimRecord:
    """Parse a claim record from a normalized payload."""
    claim_data = _extract_claim_data(payload)

    claim_id = claim_data.get("claim_id") or claim_data.get("id")
    if not claim_id:
        raise ValueError("CLAIM_ID_MISSING_IN_PAYLOAD")

    policy_number = claim_data.get("policy_number") or claim_data.get("policy_id")
    if not policy_number:
        raise ValueError("POLICY_NUMBER_MISSING_IN_PAYLOAD")

    claim_number = claim_data.get("claim_number") or claim_data.get("claim_ref")
    if not claim_number:
        raise ValueError("CLAIM_NUMBER_MISSING_IN_PAYLOAD")

    claim_type = claim_data.get("claim_type") or claim_data.get("type") or "unknown"
    claim_status = claim_data.get("claim_status") or claim_data.get("status") or "unknown"

    reported_date_value = claim_data.get("reported_date") or claim_data.get("reported_at")
    reported_date = _parse_iso_datetime(reported_date_value)
    if reported_date is None:
        raise ValueError("REPORTED_DATE_MISSING_IN_PAYLOAD")

    incident_date = None
    incident_date_value = claim_data.get("incident_date") or claim_data.get("incident_at")
    incident_date = _parse_iso_datetime(incident_date_value)

    claim_amount = _coerce_float(claim_data.get("claim_amount") or claim_data.get("amount"))

    currency = claim_data.get("currency") or claim_data.get("currency_code") or "USD"
    claimant_name = claim_data.get("claimant_name") or claim_data.get("claimant") or "Unknown"
    claimant_type = claim_data.get("claimant_type") or claim_data.get("claimant_category") or "individual"
    description = claim_data.get("description") or claim_data.get("claim_description") or ""

    metadata = claim_data.get("metadata") or {}
    if not isinstance(metadata, dict):
        metadata = {}

    return ClaimRecord(
        claim_id=str(claim_id),
        dataset_version_id=dataset_version_id,
        policy_number=str(policy_number),
        claim_number=str(claim_number),
        claim_type=str(claim_type),
        claim_status=str(claim_status),
        reported_date=reported_date,
        incident_date=incident_date,
        claim_amount=claim_amount,
        currency=str(currency),
        claimant_name=str(claimant_name),
        claimant_type=str(claimant_type),
        description=str(description),
        metadata=metadata,
    )





