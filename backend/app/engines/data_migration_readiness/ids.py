"""Deterministic identifier helpers for data migration readiness artifacts."""

from __future__ import annotations

import uuid

_NAMESPACE = uuid.UUID("00000000-0000-0000-0000-000000000244")


def deterministic_id(*parts: str) -> str:
    """Generate a deterministic UUIDv5 based on ordered parts."""

    key = "|".join(parts)
    return str(uuid.uuid5(_NAMESPACE, key))
