from __future__ import annotations

from typing import Iterable, Sequence

from backend.app.engines.regulatory_readiness.controls import ControlDefinition


class ControlCatalog:
    def __init__(self, *, initial_controls: Iterable[ControlDefinition] | None = None):
        self._controls: dict[str, ControlDefinition] = {}
        if initial_controls is not None:
            for control in initial_controls:
                self.register(control)

    def register(self, control: ControlDefinition) -> None:
        self._controls[control.control_id] = control

    def load_from_payloads(self, payloads: Iterable[dict] | None) -> None:
        if not payloads:
            return
        for payload in payloads:
            if not isinstance(payload, dict):
                continue
            try:
                control = ControlDefinition.from_payload(payload)
            except ValueError:
                continue
            self.register(control)

    def list_controls(self) -> Sequence[ControlDefinition]:
        return tuple(self._controls.values())

    def find(self, control_id: str) -> ControlDefinition | None:
        return self._controls.get(control_id)

    def status_distribution(self) -> dict[str, int]:
        distribution: dict[str, int] = {}
        for control in self._controls.values():
            distribution[control.status.value] = distribution.get(control.status.value, 0) + 1
        return distribution
