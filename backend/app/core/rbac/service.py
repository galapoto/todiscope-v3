from __future__ import annotations

from collections.abc import Iterable

from backend.app.core.rbac.roles import Role


def has_roles(granted: Iterable[str], required: Iterable[Role]) -> bool:
    granted_set = {r for r in granted}
    for req in required:
        if req.value in granted_set:
            continue
        if Role.ADMIN.value in granted_set:
            continue
        return False
    return True


def require_roles(*roles: Role) -> tuple[Role, ...]:
    return roles

