"""
Canonical Finance Normalization for Engine #2

FF-2: Deterministic mapping from raw to canonical records.
No enrichment, no accounting assumptions, no aggregation.
"""
from __future__ import annotations

from decimal import Decimal
from datetime import datetime
from typing import Any

import uuid

from sqlalchemy import DateTime, ForeignKey, JSON, Numeric, String, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.dataset.raw_models import RawRecord
from backend.db.models.base import Base


class CanonicalTypeInvalidError(ValueError):
    """Raised when record_type cannot be mapped to canonical enum."""
    pass


class CanonicalCurrencyInvalidError(ValueError):
    """Raised when currency_original is not valid ISO 4217."""
    pass


class CanonicalDirectionInvalidError(ValueError):
    """Raised when direction cannot be mapped to debit/credit."""
    pass


class EnrichmentImportError(RuntimeError):
    """Raised when normalization attempts to import enrichment data."""
    pass


class AccountingAssumptionError(RuntimeError):
    """Raised when normalization makes accounting policy assumptions."""
    pass


# Valid ISO 4217 currency codes (subset for FF-2)
VALID_CURRENCIES = {
    "USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD",
    "SEK", "NOK", "DKK", "PLN", "CZK", "HUF", "RUB", "CNY",
}


def normalize_record_type(raw_type: str) -> str:
    """
    Normalize record_type to canonical enum.
    
    Allowed values: invoice, payment, credit_note, journal_line
    
    Raises:
        CanonicalTypeInvalidError: If type cannot be mapped
    """
    type_map = {
        "invoice": "invoice",
        "inv": "invoice",
        "payment": "payment",
        "pay": "payment",
        "credit_note": "credit_note",
        "credit": "credit_note",
        "cn": "credit_note",
        "journal_line": "journal_line",
        "journal": "journal_line",
        "jl": "journal_line",
    }
    
    normalized = type_map.get(raw_type.lower().strip())
    if normalized is None:
        raise CanonicalTypeInvalidError(
            f"CANONICAL_TYPE_INVALID: Cannot map record_type '{raw_type}' to canonical enum. "
            f"Allowed: invoice, payment, credit_note, journal_line"
        )
    
    return normalized


def normalize_currency(raw_currency: str) -> str:
    """
    Normalize currency to uppercase ISO 4217.
    
    Raises:
        CanonicalCurrencyInvalidError: If currency is not valid ISO 4217
    """
    normalized = raw_currency.strip().upper()
    
    if len(normalized) != 3 or not normalized.isalpha():
        raise CanonicalCurrencyInvalidError(
            f"CANONICAL_CURRENCY_INVALID: Currency '{raw_currency}' is not valid ISO 4217 format"
        )
    
    # For FF-2, we validate against known subset
    # In production, would validate against full ISO 4217 list
    if normalized not in VALID_CURRENCIES:
        raise CanonicalCurrencyInvalidError(
            f"CANONICAL_CURRENCY_INVALID: Currency '{normalized}' not in supported set: {sorted(VALID_CURRENCIES)}"
        )
    
    return normalized


def normalize_direction(raw_direction: str) -> str:
    """
    Normalize direction to debit or credit.
    
    Raises:
        CanonicalDirectionInvalidError: If direction cannot be mapped
    """
    direction_map = {
        "debit": "debit",
        "dr": "debit",
        "d": "debit",
        "credit": "credit",
        "cr": "credit",
        "c": "credit",
    }
    
    normalized = direction_map.get(raw_direction.lower().strip())
    if normalized is None:
        raise CanonicalDirectionInvalidError(
            f"CANONICAL_DIRECTION_INVALID: Cannot map direction '{raw_direction}' to debit/credit"
        )
    
    return normalized


def normalize_amount(raw_amount: str | Decimal | float) -> Decimal:
    """
    Normalize amount to Decimal (no float).
    
    Raises:
        ValueError: If amount cannot be parsed as Decimal
    """
    if isinstance(raw_amount, Decimal):
        return raw_amount
    if isinstance(raw_amount, float):
        # Convert float to string first to avoid precision issues
        return Decimal(str(raw_amount))
    if isinstance(raw_amount, str):
        return Decimal(raw_amount.strip())
    raise ValueError(f"CANONICAL_AMOUNT_INVALID: Cannot parse amount: {raw_amount} (type: {type(raw_amount)})")


def normalize_reference_ids(raw_refs: str | list[str] | None) -> list[str]:
    """
    Normalize reference_ids to list of strings.
    
    Deterministic: empty string or None → []
    """
    if raw_refs is None:
        return []
    if isinstance(raw_refs, list):
        return [str(r).strip() for r in raw_refs if str(r).strip()]
    if isinstance(raw_refs, str):
        if not raw_refs.strip():
            return []
        # Split by comma (deterministic delimiter)
        return [r.strip() for r in raw_refs.split(",") if r.strip()]
    return []


def normalize_canonical_record(
    *,
    raw_record: dict[str, Any],
    dataset_version_id: str,
    ingested_at: datetime,
) -> dict[str, Any]:
    """
    Normalize raw record to canonical finance record.
    
    Deterministic mapping with no enrichment or accounting assumptions.
    
    Raises:
        CanonicalTypeInvalidError: If record_type invalid
        CanonicalCurrencyInvalidError: If currency invalid
        CanonicalDirectionInvalidError: If direction invalid
        ValueError: If required fields missing or invalid
    """
    # Guard: No enrichment imports
    # (This is a structural check - enrichment would require imports that don't exist)
    
    # Guard: No accounting assumptions
    # (Direction is normalized, not computed from accounting rules)
    
    # Required fields validation
    required_fields = ["source_system", "source_record_id", "record_type", "posted_at", "counterparty_id", "amount_original", "currency_original", "direction"]
    for field in required_fields:
        if field not in raw_record:
            raise ValueError(f"CANONICAL_FIELD_MISSING: Required field '{field}' is missing")
    
    # Normalize fields
    record_type = normalize_record_type(raw_record["record_type"])
    currency_original = normalize_currency(raw_record["currency_original"])
    direction = normalize_direction(raw_record["direction"])
    amount_original = normalize_amount(raw_record["amount_original"])
    reference_ids = normalize_reference_ids(raw_record.get("reference_ids"))
    
    # Parse posted_at (deterministic - assume UTC if no timezone)
    posted_at_str = str(raw_record["posted_at"])
    try:
        posted_at = datetime.fromisoformat(posted_at_str.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(f"CANONICAL_DATE_INVALID: Cannot parse posted_at: {posted_at_str}")
    
    return {
        "record_id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"{dataset_version_id}:{raw_record['source_system']}:{raw_record['source_record_id']}")),
        "dataset_version_id": dataset_version_id,
        "source_system": str(raw_record["source_system"]).strip(),
        "source_record_id": str(raw_record["source_record_id"]).strip(),
        "record_type": record_type,
        "posted_at": posted_at,
        "counterparty_id": str(raw_record["counterparty_id"]).strip(),
        "amount_original": amount_original,
        "currency_original": currency_original,
        "direction": direction,
        "reference_ids": reference_ids,
        "ingested_at": ingested_at,
    }


class CanonicalRecord(Base):
    __tablename__ = "engine_financial_forensics_canonical_records"

    record_id: Mapped[str] = mapped_column(String, primary_key=True)
    dataset_version_id: Mapped[str] = mapped_column(String, ForeignKey("dataset_version.id"), nullable=False, index=True)
    source_system: Mapped[str] = mapped_column(String, nullable=False)
    source_record_id: Mapped[str] = mapped_column(String, nullable=False)
    record_type: Mapped[str] = mapped_column(String, nullable=False)
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    counterparty_id: Mapped[str] = mapped_column(String, nullable=False)
    amount_original: Mapped[Decimal] = mapped_column(Numeric(38, 12), nullable=False)
    currency_original: Mapped[str] = mapped_column(String, nullable=False)
    direction: Mapped[str] = mapped_column(String, nullable=False)
    reference_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


async def normalize_dataset(db: AsyncSession, *, dataset_version_id: str) -> int:
    raw_rows = (
        await db.execute(
            select(RawRecord)
            .where(RawRecord.dataset_version_id == dataset_version_id)
            .order_by(RawRecord.ingested_at.asc(), RawRecord.raw_record_id.asc())
        )
    ).scalars().all()

    created = 0
    for raw in raw_rows:
        canonical = normalize_canonical_record(raw_record=raw.payload, dataset_version_id=dataset_version_id, ingested_at=raw.ingested_at)
        existing = await db.scalar(select(CanonicalRecord).where(CanonicalRecord.record_id == canonical["record_id"]))
        if existing is not None:
            continue
        db.add(CanonicalRecord(**canonical))
        created += 1

    await db.commit()
    return created

