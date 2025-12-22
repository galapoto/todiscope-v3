from backend.app.core.config import get_settings


def is_engine_enabled(engine_id: str) -> bool:
    return engine_id in get_settings().enabled_engines

