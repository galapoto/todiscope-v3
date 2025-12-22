from __future__ import annotations
import inspect
import sys

from backend.app.core.engine_registry.spec import EngineSpec


class EngineSelfRegistrationError(RuntimeError):
    """Raised when an engine attempts to self-register directly."""


class EngineRegistry:
    def __init__(self) -> None:
        self._specs: dict[str, EngineSpec] = {}
        self._registration_allowed = True  # Only core can register

    def register(self, spec: EngineSpec) -> None:
        """Register an engine spec. Only callable from core registration code."""
        # Safety: Prevent engines from self-registering directly from their own modules.
        # Registration is permitted only when initiated from the explicit engine registration
        # aggregator (backend/app/engines/__init__.py), which is the single allowed wiring point.
        stack = inspect.stack()
        caller_files = [frame.filename for frame in stack]
        allowlist_marker = "/backend/app/engines/__init__.py"
        allowlisted = any(allowlist_marker in f for f in caller_files)
        if not allowlisted:
            # If any direct caller originates from an engine module, block it.
            for f in caller_files:
                if "/engines/" in f and "/core/" not in f:
                    raise EngineSelfRegistrationError(
                        f"Engine {spec.engine_id} cannot self-register. "
                        "Engines must be registered via backend/app/engines/__init__.py."
                    )
        
        if spec.engine_id in self._specs:
            raise ValueError(f"Duplicate engine_id: {spec.engine_id}")
        self._specs[spec.engine_id] = spec

    def get(self, engine_id: str) -> EngineSpec | None:
        return self._specs.get(engine_id)

    def all(self) -> list[EngineSpec]:
        return list(self._specs.values())

    def is_enabled(self, engine_id: str) -> bool:
        """Check if engine is enabled. Registry controls this centrally."""
        from backend.app.core.engine_registry.kill_switch import is_engine_enabled
        return is_engine_enabled(engine_id)

    def reset_for_tests(self) -> None:
        self._specs.clear()


REGISTRY = EngineRegistry()
