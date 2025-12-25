from __future__ import annotations

import importlib
import pkgutil

from sqlalchemy.ext.asyncio import AsyncEngine

from backend.db.models.base import Base


def _import_model_modules() -> None:
    """
    Import all `*.models` and `*.raw_models` modules under `backend.app`.

    This is used to populate `Base.metadata` for environments without a formal
    migration system (e.g., local SQLite dev). It is intentionally broad to
    cover engine-owned tables as well as core tables.
    """
    import backend.app  # imported locally to avoid import-time side effects

    for module_info in pkgutil.walk_packages(backend.app.__path__, backend.app.__name__ + "."):
        name = module_info.name
        if not (name.endswith(".models") or name.endswith(".raw_models")):
            continue
        importlib.import_module(name)


async def ensure_sqlite_schema(engine: AsyncEngine) -> None:
    """
    Create all SQLAlchemy tables for SQLite dev environments.

    This does not replace production migrations. It exists to keep local dev and
    audits operational when using a local SQLite database.
    """
    _import_model_modules()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

