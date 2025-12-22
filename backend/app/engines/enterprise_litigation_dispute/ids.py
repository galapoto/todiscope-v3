"""Deterministic identifiers for the litigation/dispute engine."""

from __future__ import annotations

import uuid


_NAMESPACE = uuid.UUID("00000000-0000-0000-0000-000000000081")


def deterministic_id(*parts: str) -> str:
    """Generate a deterministic UUIDv5 from the provided components."""
    return str(uuid.uuid5(_NAMESPACE, "|".join(parts)))
