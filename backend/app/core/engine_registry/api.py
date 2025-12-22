from fastapi import APIRouter

from backend.app.core.config import get_settings


router = APIRouter(prefix="/api/v3/engine-registry", tags=["engine-registry"])


@router.get("/enabled")
async def enabled_engines() -> dict:
    return {"enabled_engines": list(get_settings().enabled_engines)}

