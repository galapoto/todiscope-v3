from fastapi import FastAPI

from backend.app.core.engine_registry.kill_switch import is_engine_enabled
from backend.app.core.engine_registry.registry import REGISTRY


def mount_enabled_engine_routers(app: FastAPI) -> None:
    for spec in REGISTRY.all():
        if is_engine_enabled(spec.engine_id):
            for r in spec.routers:
                app.include_router(r)

