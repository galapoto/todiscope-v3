"""
Enterprise Construction & Infrastructure Cost Intelligence Engine (Core)

This package intentionally contains only core, domain-agnostic primitives:
- DatasetVersion binding/enforcement helpers
- BOQ vs Actuals comparison model (alignment + arithmetic only)

Reporting, variance interpretation, and domain rules belong in higher layers.
"""

from backend.app.engines.construction_cost_intelligence.compare import compare_boq_to_actuals
from backend.app.engines.construction_cost_intelligence.models import (
    ComparisonConfig,
    ComparisonBreakdown,
    ComparisonMatch,
    ComparisonResult,
    CostLine,
    NormalizationMapping,
    normalize_cost_lines,
)
from backend.app.engines.construction_cost_intelligence.run import run_engine
from backend.app.engines.construction_cost_intelligence.traceability import (
    CoreMaterializationResult,
    build_core_assumptions,
    materialize_core_traceability,
)
from backend.app.engines.construction_cost_intelligence.engine import register_engine

__all__ = [
    "ComparisonConfig",
    "ComparisonBreakdown",
    "ComparisonMatch",
    "ComparisonResult",
    "CostLine",
    "NormalizationMapping",
    "compare_boq_to_actuals",
    "normalize_cost_lines",
    "CoreMaterializationResult",
    "build_core_assumptions",
    "materialize_core_traceability",
    "run_engine",
    "register_engine",
]





