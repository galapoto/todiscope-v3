from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from backend.app.engines.regulatory_readiness.controls import ControlDefinition, ControlStatus
from backend.app.engines.regulatory_readiness.frameworks import RegulatoryFramework


@dataclass(frozen=True)
class ComplianceMapping:
    control_id: str
    framework_id: str
    framework_name: str
    status: ControlStatus
    alignment_score: float
    notes: str

    def as_dict(self) -> dict:
        return {
            "control_id": self.control_id,
            "framework_id": self.framework_id,
            "framework_name": self.framework_name,
            "status": self.status.value,
            "alignment_score": self.alignment_score,
            "notes": self.notes,
        }


def _score_from_status(status: ControlStatus) -> float:
    if status == ControlStatus.IMPLEMENTED:
        return 1.0
    if status == ControlStatus.MONITORED or status == ControlStatus.PARTIAL:
        return 0.75
    if status == ControlStatus.NOT_IMPLEMENTED:
        return 0.2
    return 0.5


def map_controls_to_frameworks(
    controls: Sequence[ControlDefinition],
    frameworks: Sequence[RegulatoryFramework],
    *,
    evaluations: dict[str, ControlStatus] | None = None,
) -> Sequence[ComplianceMapping]:
    eval_map = evaluations or {}
    mappings: list[ComplianceMapping] = []
    for control in controls:
        control_status = eval_map.get(control.control_id, control.status)
        for framework in frameworks:
            if not framework.matches_control(control):
                continue
            alignment_score = _score_from_status(control_status)
            notes = "Control explicitly scoped to framework."
            if framework.framework_id not in control.frameworks:
                notes = "Framework derived from catalog domains."
            mappings.append(
                ComplianceMapping(
                    control_id=control.control_id,
                    framework_id=framework.framework_id,
                    framework_name=framework.name,
                    status=control_status,
                    alignment_score=alignment_score,
                    notes=notes,
                )
            )
    return tuple(mappings)
