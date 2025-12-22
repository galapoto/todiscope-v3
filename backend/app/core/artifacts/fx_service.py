from __future__ import annotations

import json
import uuid
from datetime import datetime
from decimal import Decimal
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.artifacts.checksums import sha256_hex, verify_sha256
from backend.app.core.artifacts.fx_models import FxArtifact
from backend.app.core.artifacts.store import get_artifact_store


class FxArtifactError(ValueError):
    pass


def _canonical_fx_payload_bytes(*, base_currency: str, effective_date: str, rates: dict) -> bytes:
    if not isinstance(base_currency, str) or not base_currency.strip():
        raise FxArtifactError("BASE_CURRENCY_REQUIRED")
    base = base_currency.strip().upper()
    if len(base) != 3:
        raise FxArtifactError("BASE_CURRENCY_INVALID")

    if not isinstance(effective_date, str) or not effective_date.strip():
        raise FxArtifactError("EFFECTIVE_DATE_REQUIRED")

    if not isinstance(rates, dict) or not rates:
        raise FxArtifactError("RATES_REQUIRED")

    normalized_rates: dict[str, str] = {}
    for currency, rate in rates.items():
        if not isinstance(currency, str) or len(currency.strip()) != 3:
            raise FxArtifactError("RATE_CURRENCY_INVALID")
        cur = currency.strip().upper()
        try:
            dec = Decimal(str(rate))
        except Exception as exc:
            raise FxArtifactError("RATE_DECIMAL_INVALID") from exc
        if dec <= 0:
            raise FxArtifactError("RATE_NON_POSITIVE")
        normalized_rates[cur] = format(dec, "f")

    payload = {
        "base_currency": base,
        "effective_date": effective_date.strip(),
        "rates": {k: normalized_rates[k] for k in sorted(normalized_rates.keys())},
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


async def create_fx_artifact(
    db: AsyncSession,
    *,
    dataset_version_id: str,
    base_currency: str,
    effective_date: str,
    rates: dict,
    created_at: datetime,
) -> FxArtifact:
    """
    Create FX artifact with deterministic timestamp.
    
    Args:
        created_at: Deterministic timestamp (typically from dataset_version or provided explicitly).
                    Must be timezone-aware.
    """
    if created_at.tzinfo is None:
        raise FxArtifactError("CREATED_AT_TIMEZONE_REQUIRED: created_at must be timezone-aware")
    
    payload_bytes = _canonical_fx_payload_bytes(
        base_currency=base_currency, effective_date=effective_date, rates=rates
    )
    checksum = sha256_hex(payload_bytes)

    existing = await db.scalar(
        select(FxArtifact).where(
            FxArtifact.dataset_version_id == dataset_version_id,
            FxArtifact.checksum == checksum,
        )
    )
    if existing is not None:
        return existing

    fx_artifact_id = str(uuid.uuid4())
    store = get_artifact_store()
    stored = await store.put_bytes(
        key=f"core/fx/{dataset_version_id}/{checksum}.json",
        data=payload_bytes,
        content_type="application/json",
    )

    row = FxArtifact(
        fx_artifact_id=fx_artifact_id,
        dataset_version_id=dataset_version_id,
        base_currency=base_currency.strip().upper(),
        effective_date=effective_date.strip(),
        checksum=checksum,
        artifact_uri=stored.uri,
        created_at=created_at,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def load_fx_artifact(db: AsyncSession, *, fx_artifact_id: str) -> tuple[FxArtifact, dict]:
    row = await db.scalar(select(FxArtifact).where(FxArtifact.fx_artifact_id == fx_artifact_id))
    if row is None:
        raise FxArtifactError("FX_ARTIFACT_NOT_FOUND")

    store = get_artifact_store()
    parsed = urlparse(row.artifact_uri)
    if parsed.scheme == "memory":
        key = parsed.netloc + parsed.path
        if key.startswith("/"):
            key = key[1:]
    elif parsed.scheme == "s3":
        # s3://bucket/key -> path is /key
        key = parsed.path[1:] if parsed.path.startswith("/") else parsed.path
    else:
        raise FxArtifactError("FX_ARTIFACT_URI_INVALID")
    raw = await store.get_bytes(key=key)
    verify_sha256(raw, row.checksum)
    payload = json.loads(raw.decode("utf-8"))
    return row, payload


async def load_fx_artifact_for_dataset(
    db: AsyncSession, *, fx_artifact_id: str, dataset_version_id: str
) -> tuple[FxArtifact, dict]:
    row, payload = await load_fx_artifact(db, fx_artifact_id=fx_artifact_id)
    if row.dataset_version_id != dataset_version_id:
        raise FxArtifactError("FX_ARTIFACT_DATASET_MISMATCH")
    return row, payload
