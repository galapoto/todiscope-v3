from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Tuple

from backend.app.engines.regulatory_readiness.controls import ControlDefinition


@dataclass(frozen=True)
class RegulatoryFramework:
    framework_id: str
    name: str
    description: str
    version: str | None = None
    domains: Tuple[str, ...] = field(default_factory=tuple)
    explicit_controls: Tuple[str, ...] = field(default_factory=tuple)

    def matches_control(self, control: ControlDefinition) -> bool:
        if self.framework_id in control.frameworks:
            return True
        if control.control_id in self.explicit_controls:
            return True
        if self.domains and any(domain in control.tags for domain in self.domains):
            return True
        return False


class FrameworkCatalog:
    def __init__(self, frameworks: Iterable[RegulatoryFramework] | None = None):
        self._frameworks: dict[str, RegulatoryFramework] = {}
        if frameworks:
            for framework in frameworks:
                self.register(framework)

    def register(self, framework: RegulatoryFramework) -> None:
        self._frameworks[framework.framework_id] = framework

    def list_frameworks(self) -> Tuple[RegulatoryFramework, ...]:
        return tuple(self._frameworks.values())


def build_default_frameworks() -> Tuple[RegulatoryFramework, ...]:
    return (
        RegulatoryFramework(
            framework_id="iso27001",
            name="ISO 27001",
            description="Information security and risk management controls.",
            version="2013",
            domains=("data_governance", "compliance_monitoring"),
        ),
        RegulatoryFramework(
            framework_id="internal_controls",
            name="Internal Regulatory Controls",
            description="High level internal controls defined by the enterprise compliance office.",
            version="v1",
            domains=("operations", "risk_management"),
        ),
        RegulatoryFramework(
            framework_id="future_regulations",
            name="Future Regulations",
            description="Placeholder for upcoming regulatory expectations.",
            domains=("third_party", "risk_management"),
        ),
    )
