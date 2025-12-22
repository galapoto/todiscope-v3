from __future__ import annotations

import uuid


_NAMESPACE = uuid.UUID("00000000-0000-0000-0000-000000000711")


def deterministic_id(*parts: str) -> str:
    return str(uuid.uuid5(_NAMESPACE, "|".join(parts)))

