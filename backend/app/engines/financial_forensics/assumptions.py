"""
Assumption & Limitation Registry for Engine #2

FF-5: Machine-readable registry of assumptions, exclusions, and validity scope.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class Assumption:
    """A single assumption used in the engine."""
    assumption_id: str
    category: str  # e.g., "fx", "data_completeness", "tolerance", "matching"
    description: str
    source: str  # e.g., "run_parameters", "fx_artifact", "canonical_field"
    value: Any | None = None  # Optional value (e.g., tolerance threshold, FX rate)


@dataclass(frozen=True)
class Exclusion:
    """An explicit exclusion (what the engine does not do)."""
    exclusion_id: str
    category: str  # e.g., "fraud", "decisions", "eliminations", "intent"
    description: str
    rationale: str  # Why this exclusion exists


@dataclass(frozen=True)
class ValidityScope:
    """Validity scope for engine outputs."""
    dataset_version_id: str
    run_id: str
    fx_artifact_id: str | None = None
    fx_artifact_sha256: str | None = None
    created_at: datetime | None = None


@dataclass
class AssumptionRegistry:
    """
    Machine-readable registry of assumptions, exclusions, and validity scope.
    """
    # Assumptions
    assumptions: list[Assumption] = field(default_factory=list)
    
    # Explicit exclusions
    exclusions: list[Exclusion] = field(default_factory=list)
    
    # Validity scope
    validity_scope: ValidityScope | None = None
    
    def add_assumption(self, assumption: Assumption) -> None:
        """Add an assumption to the registry."""
        self.assumptions.append(assumption)
    
    def add_exclusion(self, exclusion: Exclusion) -> None:
        """Add an exclusion to the registry."""
        self.exclusions.append(exclusion)
    
    def set_validity_scope(self, scope: ValidityScope) -> None:
        """Set validity scope for the registry."""
        self.validity_scope = scope
    
    def to_dict(self) -> dict[str, Any]:
        """Convert registry to dictionary for serialization."""
        return {
            "assumptions": [
                {
                    "assumption_id": a.assumption_id,
                    "category": a.category,
                    "description": a.description,
                    "source": a.source,
                    "value": a.value,
                }
                for a in self.assumptions
            ],
            "exclusions": [
                {
                    "exclusion_id": e.exclusion_id,
                    "category": e.category,
                    "description": e.description,
                    "rationale": e.rationale,
                }
                for e in self.exclusions
            ],
            "validity_scope": {
                "dataset_version_id": self.validity_scope.dataset_version_id if self.validity_scope else None,
                "run_id": self.validity_scope.run_id if self.validity_scope else None,
                "fx_artifact_id": self.validity_scope.fx_artifact_id if self.validity_scope else None,
                "fx_artifact_sha256": self.validity_scope.fx_artifact_sha256 if self.validity_scope else None,
                "created_at": self.validity_scope.created_at.isoformat() if self.validity_scope and self.validity_scope.created_at else None,
            } if self.validity_scope else None,
        }


def create_default_assumption_registry() -> AssumptionRegistry:
    """
    Create default assumption registry with standard assumptions and exclusions.
    
    Returns:
        AssumptionRegistry with default assumptions and exclusions
    """
    registry = AssumptionRegistry()
    
    # Standard exclusions (what the engine does not do)
    registry.add_exclusion(Exclusion(
        exclusion_id="no_fraud",
        category="fraud",
        description="Engine does not declare fraud or infer intent",
        rationale="Fraud determination requires legal/judicial process; engine only reports signals",
    ))
    
    registry.add_exclusion(Exclusion(
        exclusion_id="no_decisions",
        category="decisions",
        description="Engine does not make decisions or recommendations",
        rationale="Engine provides advisory signals only; decisions are human responsibility",
    ))
    
    registry.add_exclusion(Exclusion(
        exclusion_id="no_eliminations",
        category="eliminations",
        description="Engine does not eliminate or net intercompany transactions",
        rationale="Intercompany transactions are flagged for visibility only; no accounting policy logic",
    ))
    
    registry.add_exclusion(Exclusion(
        exclusion_id="no_intent",
        category="intent",
        description="Engine does not infer intent or assign blame",
        rationale="Engine reports patterns and signals only; intent inference is out of scope",
    ))
    
    registry.add_exclusion(Exclusion(
        exclusion_id="no_recovery",
        category="recovery",
        description="Engine does not claim recoverable amounts or damages",
        rationale="Recovery claims require legal process; engine only reports exposure estimates",
    ))
    
    return registry


def add_fx_assumptions(
    registry: AssumptionRegistry,
    *,
    fx_artifact_id: str,
    fx_artifact_sha256: str,
    base_currency: str,
    effective_date: str,
) -> None:
    """Add FX-related assumptions to registry."""
    registry.add_assumption(Assumption(
        assumption_id="fx_artifact",
        category="fx",
        description=f"FX rates from artifact {fx_artifact_id}",
        source="fx_artifact",
        value={"fx_artifact_id": fx_artifact_id, "fx_artifact_sha256": fx_artifact_sha256},
    ))
    
    registry.add_assumption(Assumption(
        assumption_id="base_currency",
        category="fx",
        description=f"Base currency: {base_currency}",
        source="run_parameters",
        value=base_currency,
    ))
    
    registry.add_assumption(Assumption(
        assumption_id="fx_effective_date",
        category="fx",
        description=f"FX rates effective date: {effective_date}",
        source="fx_artifact",
        value=effective_date,
    ))


def add_tolerance_assumptions(
    registry: AssumptionRegistry,
    *,
    tolerance_absolute: float | None = None,
    tolerance_percent: float | None = None,
) -> None:
    """Add tolerance-related assumptions to registry."""
    if tolerance_absolute is not None:
        registry.add_assumption(Assumption(
            assumption_id="tolerance_absolute",
            category="tolerance",
            description=f"Absolute tolerance: {tolerance_absolute}",
            source="run_parameters",
            value=tolerance_absolute,
        ))
    
    if tolerance_percent is not None:
        registry.add_assumption(Assumption(
            assumption_id="tolerance_percent",
            category="tolerance",
            description=f"Percentage tolerance: {tolerance_percent}%",
            source="run_parameters",
            value=tolerance_percent,
        ))


def add_data_completeness_assumptions(
    registry: AssumptionRegistry,
    *,
    data_completeness_level: str,
    missing_fields: list[str] | None = None,
) -> None:
    """Add data completeness assumptions to registry."""
    registry.add_assumption(Assumption(
        assumption_id="data_completeness",
        category="data_completeness",
        description=f"Data completeness level: {data_completeness_level}",
        source="dataset_analysis",
        value={"completeness_level": data_completeness_level, "missing_fields": missing_fields or []},
    ))


