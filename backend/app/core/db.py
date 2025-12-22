from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from backend.app.core.config import get_settings


_ENGINE: AsyncEngine | None = None
_SESSIONMAKER: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _ENGINE, _SESSIONMAKER
    if _ENGINE is not None:
        return _ENGINE

    settings = get_settings()
    if not settings.database_url:
        raise RuntimeError("Database not configured (TODISCOPE_DATABASE_URL missing)")

    _ENGINE = create_async_engine(settings.database_url, pool_pre_ping=True)
    _SESSIONMAKER = async_sessionmaker(_ENGINE, expire_on_commit=False)
    return _ENGINE


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    if _SESSIONMAKER is None:
        get_engine()
    assert _SESSIONMAKER is not None
    return _SESSIONMAKER


async def session_scope() -> AsyncIterator[AsyncSession]:
    session = get_sessionmaker()()
    try:
        yield session
        await session.commit()
    finally:
        await session.close()


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async for s in session_scope():
        yield s


def reset_db_state_for_tests() -> None:
    global _ENGINE, _SESSIONMAKER
    _ENGINE = None
    _SESSIONMAKER = None
