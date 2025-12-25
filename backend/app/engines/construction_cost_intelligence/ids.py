"""
Deterministic ID Generation for Construction Cost Intelligence Engine

All replay-stable IDs must be deterministic and derived from stable keys.
"""
from __future__ import annotations

import uuid


# Namespace UUID for deterministic ID generation
_VARIANCE_ANALYSIS_NAMESPACE = uuid.UUID("00000000-0000-0000-0000-000000000060")
_TIME_PHASED_REPORT_NAMESPACE = uuid.UUID("00000000-0000-0000-0000-000000000061")


def deterministic_comparison_result_stable_key(
    *,
    dataset_version_id: str,
    identity_fields: tuple[str, ...],
    matched_count: int,
    unmatched_boq_count: int,
    unmatched_actual_count: int,
) -> str:
    """
    Generate deterministic stable key for a ComparisonResult.
    
    Used as stable_key for evidence emission.
    
    Args:
        dataset_version_id: DatasetVersion identifier
        identity_fields: Identity fields used in comparison
        matched_count: Number of matched items
        unmatched_boq_count: Number of unmatched BOQ items
        unmatched_actual_count: Number of unmatched actual items
    
    Returns:
        Stable key string
    """
    identity_fields_str = "|".join(sorted(identity_fields))
    return f"{dataset_version_id}|{identity_fields_str}|matched={matched_count}|unmatched_boq={unmatched_boq_count}|unmatched_actual={unmatched_actual_count}"


def deterministic_time_phased_report_stable_key(
    *,
    dataset_version_id: str,
    period_type: str,
    date_field: str,
    prefer_total_cost: bool,
    start_date: str | None = None,
    end_date: str | None = None,
) -> str:
    """
    Generate deterministic stable key for a time-phased report.
    
    Used as stable_key for evidence emission.
    
    Args:
        dataset_version_id: DatasetVersion identifier
        period_type: Type of time period aggregation
        date_field: Field name used for date extraction
        prefer_total_cost: Whether total_cost is preferred
        start_date: Optional start date filter
        end_date: Optional end date filter
    
    Returns:
        Stable key string
    """
    parts = [
        dataset_version_id,
        period_type,
        date_field,
        "prefer_total" if prefer_total_cost else "prefer_quantity_unit",
    ]
    if start_date:
        parts.append(f"start={start_date}")
    if end_date:
        parts.append(f"end={end_date}")
    return "|".join(parts)






