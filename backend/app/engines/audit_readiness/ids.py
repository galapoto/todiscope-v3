"""
Deterministic ID generation for Audit Readiness Engine
"""
from __future__ import annotations

import uuid


def deterministic_id(dataset_version_id: str, *parts: str) -> str:
    """
    Generate a deterministic ID from stable parts.
    
    Uses UUIDv5 with a fixed namespace to ensure deterministic IDs.
    """
    namespace = uuid.UUID("00000000-0000-0000-0000-0000000000a1")  # Audit Readiness namespace
    stable_key = "|".join([dataset_version_id] + list(parts))
    return str(uuid.uuid5(namespace, stable_key))

