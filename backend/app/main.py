from fastapi import FastAPI

from backend.app.health.routes import router as health_router
from backend.app.core.dataset.api import router as ingest_router
from backend.app.core.engine_registry.api import router as engine_registry_router
from backend.app.core.artifacts.api import router as artifacts_router
from backend.app.core.artifacts.fx_api import router as fx_artifacts_router
from backend.app.core.engine_registry.mount import mount_enabled_engine_routers
from backend.app.core.metrics import metrics_middleware, router as metrics_router
from backend.app.core.dataset.immutability import install_immutability_guards
from backend.app.engines import register_all_engines


def create_app() -> FastAPI:
    app = FastAPI(title="TodiScope v3 (bootstrap)")
    install_immutability_guards()
    app.middleware("http")(metrics_middleware())
    app.include_router(health_router)
    app.include_router(ingest_router)
    app.include_router(engine_registry_router)
    app.include_router(artifacts_router)
    app.include_router(fx_artifacts_router)
    app.include_router(metrics_router)
    register_all_engines()
    mount_enabled_engine_routers(app)
    return app


app = create_app()
