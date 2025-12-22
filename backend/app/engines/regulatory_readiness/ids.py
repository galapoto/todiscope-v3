from __future__ import annotations

import uuid


_NAMESPACE = uuid.UUID("00000000-0000-0000-0000-000000000244")


def deterministic_id(*parts: str) -> str:
    key = "|".join(parts)
    return str(uuid.uuid5(_NAMESPACE, key))
