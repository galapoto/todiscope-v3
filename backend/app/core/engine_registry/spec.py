from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from fastapi import APIRouter


@dataclass(frozen=True)
class EngineSpec:
    engine_id: str
    engine_version: str
    enabled_by_default: bool
    owned_tables: tuple[str, ...]
    report_sections: tuple[str, ...]
    routers: tuple[APIRouter, ...]
    run_entrypoint: Callable[..., object] | None = None
