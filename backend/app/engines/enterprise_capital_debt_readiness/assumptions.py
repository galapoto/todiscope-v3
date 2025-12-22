from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = dict(base)
    for key, override_value in override.items():
        base_value = merged.get(key)
        if isinstance(base_value, dict) and isinstance(override_value, dict):
            merged[key] = _deep_merge(base_value, override_value)
        else:
            merged[key] = override_value
    return merged


def load_default_assumptions() -> dict[str, Any]:
    path = Path(__file__).with_name("config") / "default_assumptions.json"
    return json.loads(path.read_text(encoding="utf-8"))


def resolved_assumptions(parameters: dict | None) -> dict[str, Any]:
    params = parameters or {}
    if isinstance(params.get("assumptions"), dict):
        overrides = params["assumptions"]
    else:
        # Allow callers (e.g., unit tests / internal tools) to pass an assumptions-shaped
        # dict directly without wrapping it in {"assumptions": ...}.
        known_roots = {"capital_adequacy", "debt_service", "cash_available"}
        overrides = params if any(k in params for k in known_roots) else {}
    return _deep_merge(load_default_assumptions(), overrides)
