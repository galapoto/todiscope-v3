"""
Assumption & Limitation Registry for Construction Cost Intelligence Engine

Machine-readable registry of assumptions, exclusions, and validity scope for reporting and analysis.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class Assumption:
    """A single assumption used in the engine."""
    assumption_id: str
    category: str  # e.g., "variance_threshold", "period_type", "cost_basis", "categorization"
    description: str
    source: str  # e.g., "run_parameters", "comparison_config", "default"
    value: Any | None = None  # Optional value (e.g., threshold, period type)


@dataclass(frozen=True)
class Exclusion:
    """An explicit exclusion (what the engine does not do)."""
    exclusion_id: str
    category: str  # e.g., "causality", "decisions", "budget_approval"
    description: str
    rationale: str  # Why this exclusion exists


@dataclass(frozen=True)
class ValidityScope:
    """Validity scope for engine outputs."""
    dataset_version_id: str
    run_id: str | None = None
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
                    "value": str(a.value) if isinstance(a.value, Decimal) else a.value,
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
        exclusion_id="no_causality",
        category="causality",
        description="Engine does not determine causes of cost variances",
        rationale="Variance analysis is descriptive only; root cause analysis requires domain expertise",
    ))
    
    registry.add_exclusion(Exclusion(
        exclusion_id="no_decisions",
        category="decisions",
        description="Engine does not make budget approval or project management decisions",
        rationale="Engine provides analytical signals only; decisions are human responsibility",
    ))
    
    registry.add_exclusion(Exclusion(
        exclusion_id="no_budget_revision",
        category="budget_approval",
        description="Engine does not revise or approve budgets",
        rationale="Budget approval is a management decision; engine only reports variance signals",
    ))
    
    registry.add_exclusion(Exclusion(
        exclusion_id="no_cost_control",
        category="cost_control",
        description="Engine does not implement cost control measures",
        rationale="Engine is analytical only; cost control actions are operational responsibility",
    ))
    
    return registry


def add_variance_threshold_assumptions(
    registry: AssumptionRegistry,
    *,
    tolerance_threshold: Decimal,
    minor_threshold: Decimal,
    moderate_threshold: Decimal,
    major_threshold: Decimal,
) -> None:
    """Add variance threshold assumptions to registry."""
    registry.add_assumption(Assumption(
        assumption_id="variance_tolerance_threshold",
        category="variance_threshold",
        description=f"Variance tolerance threshold: {tolerance_threshold}%",
        source="run_parameters",
        value=str(tolerance_threshold),
    ))
    
    registry.add_assumption(Assumption(
        assumption_id="variance_minor_threshold",
        category="variance_threshold",
        description=f"Minor variance threshold: {minor_threshold}%",
        source="run_parameters",
        value=str(minor_threshold),
    ))
    
    registry.add_assumption(Assumption(
        assumption_id="variance_moderate_threshold",
        category="variance_threshold",
        description=f"Moderate variance threshold: {moderate_threshold}%",
        source="run_parameters",
        value=str(moderate_threshold),
    ))
    
    registry.add_assumption(Assumption(
        assumption_id="variance_major_threshold",
        category="variance_threshold",
        description=f"Major variance threshold: {major_threshold}%",
        source="run_parameters",
        value=str(major_threshold),
    ))


def add_category_field_assumption(
    registry: AssumptionRegistry,
    *,
    category_field: str | None,
) -> None:
    """Add category field assumption to registry."""
    if category_field:
        registry.add_assumption(Assumption(
            assumption_id="variance_category_field",
            category="categorization",
            description=f"Variance categorization uses field: {category_field}",
            source="run_parameters",
            value=category_field,
        ))
    else:
        registry.add_assumption(Assumption(
            assumption_id="variance_category_field",
            category="categorization",
            description="No variance categorization field specified",
            source="run_parameters",
            value=None,
        ))


def add_scope_creep_assumption(registry: AssumptionRegistry) -> None:
    """
    Add scope creep definition assumption.

    Scope creep is treated as unmatched actual lines under the configured identity_fields.
    """
    registry.add_assumption(
        Assumption(
            assumption_id="scope_creep_definition",
            category="scope_creep",
            description="Scope creep is defined as unmatched actual cost lines (no BOQ match under identity_fields).",
            source="engine_definition",
            value=True,
        )
    )


def add_time_phased_assumptions(
    registry: AssumptionRegistry,
    *,
    period_type: str,
    date_field: str,
    prefer_total_cost: bool,
    start_date: str | None = None,
    end_date: str | None = None,
) -> None:
    """Add time-phased reporting assumptions to registry."""
    registry.add_assumption(Assumption(
        assumption_id="period_type",
        category="period_type",
        description=f"Time period aggregation type: {period_type}",
        source="run_parameters",
        value=period_type,
    ))
    
    registry.add_assumption(Assumption(
        assumption_id="date_field",
        category="date_extraction",
        description=f"Date extraction uses field: {date_field} from CostLine attributes",
        source="run_parameters",
        value=date_field,
    ))
    
    registry.add_assumption(Assumption(
        assumption_id="cost_preference",
        category="cost_basis",
        description=f"Cost calculation preference: {'total_cost' if prefer_total_cost else 'quantity * unit_cost'}",
        source="run_parameters",
        value="prefer_total_cost" if prefer_total_cost else "prefer_quantity_unit_cost",
    ))
    
    if start_date:
        registry.add_assumption(Assumption(
            assumption_id="report_start_date_filter",
            category="date_filter",
            description=f"Report start date filter: {start_date}",
            source="run_parameters",
            value=start_date,
        ))
    
    if end_date:
        registry.add_assumption(Assumption(
            assumption_id="report_end_date_filter",
            category="date_filter",
            description=f"Report end date filter: {end_date}",
            source="run_parameters",
            value=end_date,
        ))





