from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, Header, HTTPException, status

from backend.app.core.auth.models import Principal
from backend.app.core.config import get_settings
from backend.app.core.rbac.roles import Role
from backend.app.core.rbac.service import has_roles


async def get_principal(x_api_key: str | None = Header(None, alias="X-API-Key")) -> Principal:
    settings = get_settings()
    if not settings.api_keys:
        return Principal(subject="dev", roles=tuple(r.value for r in Role))

    if not x_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="AUTH_REQUIRED")

    roles = settings.api_keys.get(x_api_key)
    if roles is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="AUTH_INVALID")

    return Principal(subject="api_key", roles=roles)


def require_principal(*required_roles: Role) -> Callable[[Principal], Principal]:
    async def _dep(principal: Principal = Depends(get_principal)) -> Principal:
        if not has_roles(principal.roles, required_roles):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="FORBIDDEN")
        return principal

    return _dep

