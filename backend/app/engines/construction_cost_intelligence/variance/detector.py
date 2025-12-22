"""
Cost Variance Detection Logic

Detects and analyzes variances from ComparisonResult (Agent 1's comparison model).
All calculations are deterministic and DatasetVersion-bound.
"""
from __future__ import annotations

from decimal import Decimal
from enum import Enum

from dataclasses import dataclass

from backend.app.engines.construction_cost_intelligence.models import ComparisonMatch, ComparisonResult


class VarianceSeverity(str, Enum):
    """Severity classification for cost variances."""
    
    WITHIN_TOLERANCE = "within_tolerance"
    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"
    CRITICAL = "critical"
    SCOPE_CREEP = "scope_creep"


class VarianceDirection(str, Enum):
    """Direction of variance (over or under budget)."""
    
    OVER_BUDGET = "over_budget"
    UNDER_BUDGET = "under_budget"
    ON_BUDGET = "on_budget"


@dataclass
class CostVariance:
    """
    Represents a detected cost variance from a ComparisonMatch.
    
    All fields are deterministic and bound to DatasetVersion.
    """
    
    match_key: str
    """Identity key for the matched lines."""
    
    estimated_cost: Decimal
    """Estimated cost from BOQ."""
    
    actual_cost: Decimal
    """Actual cost incurred."""
    
    variance_amount: Decimal
    """Variance amount (actual - estimated)."""
    
    variance_percentage: Decimal
    """Variance as percentage of estimated cost."""
    
    severity: VarianceSeverity
    """Severity classification of the variance."""
    
    direction: VarianceDirection
    """Direction of variance (over/under budget)."""
    
    category: str | None = None
    """Category/classification extracted from identity or attributes."""
    
    line_ids_boq: tuple[str, ...] = ()
    """BOQ line IDs involved in this variance."""
    
    line_ids_actual: tuple[str, ...] = ()
    """Actual line IDs involved in this variance."""
    
    identity: dict[str, str] | None = None
    """Identity fields for this variance."""
    
    attributes: dict | None = None
    """Additional attributes from the cost lines."""

    scope_creep: bool = False
    """True when this entry represents scope creep (unmatched actual)."""

    core_finding_ids: tuple[str, ...] = ()
    """Optional core FindingRecord IDs associated with this entry."""

    evidence_ids: tuple[str, ...] = ()
    """Optional evidence IDs associated with this entry (from core finding links)."""


def _effective_cost_from_line(line, *, cost_basis: str) -> Decimal | None:  # noqa: ANN001
    if cost_basis == "total_cost":
        return line.total_cost
    if cost_basis == "quantity_unit_cost":
        if line.quantity is None or line.unit_cost is None:
            return None
        return line.quantity * line.unit_cost
    # prefer_total_cost
    if line.total_cost is not None:
        return line.total_cost
    if line.quantity is None or line.unit_cost is None:
        return None
    return line.quantity * line.unit_cost


def detect_scope_creep(
    *,
    comparison_result: ComparisonResult,
    category_field: str | None = None,
    core_traceability_index: dict[str, dict] | None = None,
) -> list[CostVariance]:
    """
    Detect scope creep by labeling unmatched actual lines as scope creep.

    Scope creep is defined here as: actual cost lines that have no matched BOQ group under the configured identity_fields.
    This is intentionally distinct from variance thresholds and severity classification.
    """
    variances: list[CostVariance] = []

    for line in comparison_result.unmatched_actual:
        actual_cost = _effective_cost_from_line(line, cost_basis=comparison_result.cost_basis)
        if actual_cost is None:
            actual_cost = Decimal("0")

        category: str | None = None
        if category_field:
            if category_field in line.identity:
                category = line.identity.get(category_field)
            elif line.attributes and category_field in line.attributes and isinstance(line.attributes.get(category_field), str):
                category = line.attributes.get(category_field)

        core_finding_ids: tuple[str, ...] = ()
        evidence_ids: tuple[str, ...] = ()
        if core_traceability_index is not None:
            idx = core_traceability_index.get(line.line_id)
            if isinstance(idx, dict):
                core_finding_ids = tuple(idx.get("core_finding_ids") or ())
                evidence_ids = tuple(idx.get("evidence_ids") or ())

        variances.append(
            CostVariance(
                match_key=f"scope_creep|line_id={line.line_id}",
                estimated_cost=Decimal("0"),
                actual_cost=actual_cost,
                variance_amount=actual_cost,
                variance_percentage=Decimal("0"),
                severity=VarianceSeverity.SCOPE_CREEP,
                direction=VarianceDirection.OVER_BUDGET,
                category=category,
                line_ids_boq=(),
                line_ids_actual=(line.line_id,),
                identity=dict(line.identity),
                attributes=dict(line.attributes or {}),
                scope_creep=True,
                core_finding_ids=core_finding_ids,
                evidence_ids=evidence_ids,
            )
        )

    variances.sort(key=lambda v: v.match_key)
    return variances


def _calculate_variance_percentage(estimated: Decimal, actual: Decimal) -> Decimal:
    """
    Calculate variance percentage.
    
    Returns 0 if estimated is 0 to avoid division by zero.
    """
    if estimated == Decimal("0"):
        return Decimal("0")
    
    variance = ((actual - estimated) / estimated) * Decimal("100")
    return variance.quantize(Decimal("0.01"))


def _classify_severity(
    variance_percentage: Decimal,
    tolerance_threshold: Decimal = Decimal("5.0"),
    minor_threshold: Decimal = Decimal("10.0"),
    moderate_threshold: Decimal = Decimal("25.0"),
    major_threshold: Decimal = Decimal("50.0"),
) -> VarianceSeverity:
    """
    Classify variance severity based on percentage thresholds.
    
    Args:
        variance_percentage: Absolute variance as percentage of estimated cost
        tolerance_threshold: Percentage threshold for within tolerance (default 5%)
        minor_threshold: Percentage threshold for minor variance (default 10%)
        moderate_threshold: Percentage threshold for moderate variance (default 25%)
        major_threshold: Percentage threshold for major variance (default 50%)
    
    Returns:
        VarianceSeverity classification
    """
    abs_percentage = abs(variance_percentage)
    
    if abs_percentage <= tolerance_threshold:
        return VarianceSeverity.WITHIN_TOLERANCE
    elif abs_percentage <= minor_threshold:
        return VarianceSeverity.MINOR
    elif abs_percentage <= moderate_threshold:
        return VarianceSeverity.MODERATE
    elif abs_percentage <= major_threshold:
        return VarianceSeverity.MAJOR
    else:
        return VarianceSeverity.CRITICAL


def _determine_direction(variance_amount: Decimal) -> VarianceDirection:
    """Determine variance direction based on variance amount."""
    if variance_amount > Decimal("0"):
        return VarianceDirection.OVER_BUDGET
    elif variance_amount < Decimal("0"):
        return VarianceDirection.UNDER_BUDGET
    else:
        return VarianceDirection.ON_BUDGET


def _extract_category(match: ComparisonMatch, category_field: str | None = None) -> str | None:
    """
    Extract category from match identity or attributes.
    
    Args:
        match: ComparisonMatch to extract category from
        category_field: Optional field name to use as category (from identity or attributes)
    
    Returns:
        Category string or None
    """
    if not category_field:
        return None
    
    # Try to get from first BOQ line's identity
    if match.boq_lines:
        first_boq = match.boq_lines[0]
        if category_field in first_boq.identity:
            return first_boq.identity[category_field]
        # Try attributes
        if first_boq.attributes and category_field in first_boq.attributes:
            val = first_boq.attributes[category_field]
            if isinstance(val, str):
                return val
    
    # Try actual lines as fallback
    if match.actual_lines:
        first_actual = match.actual_lines[0]
        if category_field in first_actual.identity:
            return first_actual.identity[category_field]
        if first_actual.attributes and category_field in first_actual.attributes:
            val = first_actual.attributes[category_field]
            if isinstance(val, str):
                return val
    
    return None


def _extract_identity(match: ComparisonMatch) -> dict[str, str]:
    """Extract identity fields from first BOQ line."""
    if match.boq_lines:
        return dict(match.boq_lines[0].identity)
    elif match.actual_lines:
        return dict(match.actual_lines[0].identity)
    return {}


def _extract_attributes(match: ComparisonMatch) -> dict | None:
    """Extract merged attributes from cost lines."""
    attrs: dict = {}
    
    if match.boq_lines:
        for line in match.boq_lines:
            if line.attributes:
                attrs.update(line.attributes)
    
    if match.actual_lines:
        for line in match.actual_lines:
            if line.attributes:
                attrs.update(line.attributes)
    
    return attrs if attrs else None


def detect_cost_variances(
    *,
    comparison_result: ComparisonResult,
    tolerance_threshold: Decimal = Decimal("5.0"),
    minor_threshold: Decimal = Decimal("10.0"),
    moderate_threshold: Decimal = Decimal("25.0"),
    major_threshold: Decimal = Decimal("50.0"),
    category_field: str | None = None,
) -> list[CostVariance]:
    """
    Detect and calculate cost variances from a ComparisonResult.
    
    This function takes Agent 1's ComparisonResult and extracts variance
    information with severity classification and categorization.
    
    Args:
        comparison_result: ComparisonResult from Agent 1's comparison logic
        tolerance_threshold: Percentage threshold for within tolerance
        minor_threshold: Percentage threshold for minor variance
        moderate_threshold: Percentage threshold for moderate variance
        major_threshold: Percentage threshold for major variance
        category_field: Optional field name to use for categorization (from identity or attributes)
    
    Returns:
        List of CostVariance objects sorted by match_key
    
    Raises:
        ValueError: If comparison_result is invalid or missing required data
    """
    variances: list[CostVariance] = []
    
    # Process matched lines
    for match in comparison_result.matched:
        # Skip if costs are not available
        if match.boq_total_cost is None or match.actual_total_cost is None:
            continue
        
        estimated_cost = match.boq_total_cost
        actual_cost = match.actual_total_cost
        variance_amount = match.cost_delta if match.cost_delta is not None else (actual_cost - estimated_cost)
        
        # Calculate variance percentage
        variance_percentage = _calculate_variance_percentage(estimated_cost, actual_cost)
        
        # Classify severity
        severity = _classify_severity(
            abs(variance_percentage),
            tolerance_threshold=tolerance_threshold,
            minor_threshold=minor_threshold,
            moderate_threshold=moderate_threshold,
            major_threshold=major_threshold,
        )
        
        # Determine direction
        direction = _determine_direction(variance_amount)
        
        # Extract category
        category = _extract_category(match, category_field=category_field)
        
        # Extract line IDs
        line_ids_boq = tuple(line.line_id for line in match.boq_lines)
        line_ids_actual = tuple(line.line_id for line in match.actual_lines)
        
        # Extract identity and attributes
        identity = _extract_identity(match)
        attributes = _extract_attributes(match)
        
        variance = CostVariance(
            match_key=match.match_key,
            estimated_cost=estimated_cost,
            actual_cost=actual_cost,
            variance_amount=variance_amount,
            variance_percentage=variance_percentage,
            severity=severity,
            direction=direction,
            category=category,
            line_ids_boq=line_ids_boq,
            line_ids_actual=line_ids_actual,
            identity=identity,
            attributes=attributes,
            scope_creep=False,
        )
        
        variances.append(variance)
    
    # Sort by match_key for deterministic output
    variances.sort(key=lambda v: v.match_key)
    
    return variances
