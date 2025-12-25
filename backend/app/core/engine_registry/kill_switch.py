from backend.app.core.config import get_settings


def is_engine_enabled(engine_id: str) -> bool:
    return engine_id in get_settings().enabled_engines


async def log_disabled_engine_attempt(
    *,
    engine_id: str,
    actor_id: str | None = None,
    attempted_action: str = "run",
    dataset_version_id: str | None = None,
) -> None:
    """
    Log an attempt to execute a disabled engine to the audit log.
    
    Creates its own database session to ensure logging happens even if
    the calling endpoint doesn't have a session available.
    
    Args:
        engine_id: Engine identifier
        actor_id: ID of the actor attempting execution (optional)
        attempted_action: Action attempted ("run", "report", etc.)
        dataset_version_id: Optional dataset version ID from request
    """
    from backend.app.core.audit.service import log_action
    from backend.app.core.db import get_sessionmaker
    
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        try:
            await log_action(
                db,
                actor_id=actor_id or "system",
                actor_type="system",
                action_type="integrity",
                action_label=f"Disabled engine execution attempt ({attempted_action})",
                dataset_version_id=dataset_version_id,
                reason=f"Engine {engine_id} is disabled. Enable via TODISCOPE_ENABLED_ENGINES environment variable.",
                context={
                    "engine_id": engine_id,
                    "attempted_action": attempted_action,
                },
                metadata={
                    "engine_id": engine_id,
                    "enabled_engines": list(get_settings().enabled_engines),
                },
                status="failure",
                error_message=f"ENGINE_DISABLED: Engine {engine_id} is disabled",
            )
            await db.commit()
        except Exception:
            # Don't fail the request if audit logging fails
            await db.rollback()

