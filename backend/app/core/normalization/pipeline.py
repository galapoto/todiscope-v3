from __future__ import annotations

import re
from base64 import b64encode
from collections.abc import Mapping


_NON_ALNUM = re.compile(r"[^a-zA-Z0-9]+")


def _normalize_key(key: object) -> str:
    s = str(key).strip()
    if not s:
        return "_"
    s = _NON_ALNUM.sub("_", s)
    s = s.strip("_").lower()
    return s or "_"


def normalize_payload(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, bytes):
        return {"type": "bytes", "base64": b64encode(value).decode("ascii")}
    if isinstance(value, (list, tuple)):
        return [normalize_payload(v) for v in value]
    if isinstance(value, Mapping):
        out: dict[str, object] = {}
        for k in sorted(value.keys(), key=lambda x: str(x)):
            out[_normalize_key(k)] = normalize_payload(value[k])
        return out
    return str(value)

