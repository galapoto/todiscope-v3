import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.health.routes import router as health_router
from backend.app.core.dataset.api import router as ingest_router
from backend.app.core.engine_registry.api import router as engine_registry_router
from backend.app.core.audit.api import router as audit_router
from backend.app.core.normalization.api import router as normalization_router
from backend.app.core.workflows.api import router as workflows_router
from backend.app.core.artifacts.api import router as artifacts_router
from backend.app.core.artifacts.fx_api import router as fx_artifacts_router
from backend.app.core.ocr.api import router as ocr_router
from backend.app.core.normalization.api import router as normalization_router
from backend.app.core.audit.api import router as audit_router
from backend.app.core.engine_registry.mount import mount_enabled_engine_routers
from backend.app.core.metrics import metrics_middleware, router as metrics_router
from backend.app.core.dataset.immutability import install_immutability_guards
from backend.app.core.config import get_settings
from backend.app.core.db import get_engine
from backend.app.core.db_bootstrap import ensure_sqlite_schema
from backend.app.engines import register_all_engines


def create_app() -> FastAPI:
    app = FastAPI(title="TodiScope v3 (bootstrap)")
    cors_origins = os.getenv(
        "TODISCOPE_CORS_ALLOW_ORIGINS",
        "http://localhost:3400,http://localhost:3000",
    ).strip()
    allow_origins = (
        ["*"]
        if cors_origins == "*"
        else [o.strip() for o in cors_origins.split(",") if o.strip()]
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
        max_age=86400,
    )
    install_immutability_guards()
    app.middleware("http")(metrics_middleware())
    app.include_router(health_router)
    app.include_router(ingest_router)
    app.include_router(engine_registry_router)
    app.include_router(audit_router)
    app.include_router(normalization_router)
    app.include_router(workflows_router)
    app.include_router(artifacts_router)
    app.include_router(fx_artifacts_router)
    app.include_router(ocr_router)
    app.include_router(normalization_router)
    app.include_router(audit_router)
    app.include_router(metrics_router)
    register_all_engines()
    mount_enabled_engine_routers(app)

    @app.on_event("startup")
    async def _bootstrap_db() -> None:
        settings = get_settings()
        if settings.database_url and settings.database_url.startswith("sqlite"):
            await ensure_sqlite_schema(get_engine())

    return app


app = create_app()
