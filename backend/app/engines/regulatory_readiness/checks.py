from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from backend.app.engines.regulatory_readiness.controls import ControlDefinition, ControlStatus


@dataclass(frozen=True)
class ControlEvaluation:
    control_id: str
    status: ControlStatus
    confidence: float
    rationale: str
    evidence_refs: Sequence[str]

    def as_dict(self) -> dict:
        return {
            "control_id": self.control_id,
            "status": self.status.value,
            "confidence": self.confidence,
            "rationale": self.rationale,
            "evidence_refs": tuple(self.evidence_refs),
        }


def evaluate_controls(
    controls: Iterable[ControlDefinition],
    *,
    evidence_hints: dict[str, str] | None = None,
) -> Sequence[ControlEvaluation]:
    hints = evidence_hints or {}
    evaluations: list[ControlEvaluation] = []
    for control in controls:
        override = hints.get(control.control_id)
        status = control.status
        rationale = "Derived from declared status and metadata."
        if override and override in ControlStatus._value2member_map_:
            status = ControlStatus(override)
            rationale = "Evidence hint overrides declared status."
        confidence = 0.9 if status == ControlStatus.IMPLEMENTED else 0.55
        evaluations.append(
            ControlEvaluation(
                control_id=control.control_id,
                status=status,
                confidence=confidence,
                rationale=rationale,
                evidence_refs=tuple(control.ownership),
            )
        )
    return tuple(evaluations)
