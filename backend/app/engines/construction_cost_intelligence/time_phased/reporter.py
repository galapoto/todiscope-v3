"""
Time-Phased Cost Reporting

Generates time-phased cost intelligence reports from CostLine models.
All reports are deterministic and DatasetVersion-bound.
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from backend.app.engines.construction_cost_intelligence.models import CostLine


# TimePeriod is represented as a string (e.g., '2024-Q1', '2024-01', '2024-W01')
TimePeriod = str


@dataclass
class TimePhasedCostReport:
    """
    Time-phased cost report for a construction project.
    
    All fields are deterministic and bound to DatasetVersion.
    """
    
    dataset_version_id: str
    """DatasetVersion identifier."""
    
    period_type: str
    """Type of time period (e.g., 'monthly', 'quarterly', 'weekly', 'daily')."""
    
    periods: list[dict[str, Any]]
    """
    List of period cost summaries.
    Each period dict contains:
        - period: str (period identifier)
        - start_date: str (ISO format)
        - end_date: str (ISO format)
        - estimated_cost: Decimal (as string)
        - actual_cost: Decimal (as string)
        - variance_amount: Decimal (as string)
        - variance_percentage: Decimal (as string)
        - item_count: int
        - items: list[dict] (optional, detailed items for the period)
    """
    
    total_estimated_cost: Decimal
    """Total estimated cost across all periods."""
    
    total_actual_cost: Decimal
    """Total actual cost across all periods."""
    
    total_variance_amount: Decimal
    """Total variance amount."""
    
    total_variance_percentage: Decimal
    """Total variance as percentage of total estimated cost."""
    
    report_start_date: str
    """Report start date (ISO format)."""
    
    report_end_date: str
    """Report end date (ISO format)."""


def _parse_date(date_str: str) -> datetime:
    """Parse ISO format date string to datetime."""
    try:
        # Try ISO format with time
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except ValueError:
        # Try date-only format
        return datetime.fromisoformat(date_str + "T00:00:00")


def _format_date(dt: datetime) -> str:
    """Format datetime to ISO format string."""
    return dt.isoformat()


def _get_period_identifier(
    date: datetime,
    period_type: str,
) -> str:
    """
    Generate period identifier from date based on period type.
    
    Args:
        date: Date to generate period for
        period_type: Type of period ('daily', 'weekly', 'monthly', 'quarterly', 'yearly')
    
    Returns:
        Period identifier string
    """
    if period_type == "daily":
        return date.strftime("%Y-%m-%d")
    elif period_type == "weekly":
        year, week, _ = date.isocalendar()
        return f"{year}-W{week:02d}"
    elif period_type == "monthly":
        return date.strftime("%Y-%m")
    elif period_type == "quarterly":
        quarter = (date.month - 1) // 3 + 1
        return f"{date.year}-Q{quarter}"
    elif period_type == "yearly":
        return str(date.year)
    else:
        raise ValueError(f"Unsupported period_type: {period_type}")


def _get_period_bounds(
    date: datetime,
    period_type: str,
) -> tuple[datetime, datetime]:
    """
    Get start and end datetime for a period containing the given date.
    
    Args:
        date: Date within the period
        period_type: Type of period
    
    Returns:
        Tuple of (start_datetime, end_datetime)
    """
    if period_type == "daily":
        start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = date.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif period_type == "weekly":
        # ISO week starts on Monday
        days_since_monday = date.weekday()
        start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        # Use timedelta for robust date arithmetic (handles month/year boundaries)
        start = start - timedelta(days=days_since_monday)
        end = start + timedelta(days=6, hours=23, minutes=59, seconds=59, microseconds=999999)
    elif period_type == "monthly":
        start = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # Use calendar.monthrange() to get the last day of the month correctly
        _, last_day = calendar.monthrange(date.year, date.month)
        end = date.replace(day=last_day, hour=23, minute=59, second=59, microsecond=999999)
    elif period_type == "quarterly":
        quarter = (date.month - 1) // 3
        start_month = quarter * 3 + 1
        start = date.replace(month=start_month, day=1, hour=0, minute=0, second=0, microsecond=0)
        end_month = start_month + 2
        # Use calendar.monthrange() to get the last day of the quarter-end month correctly
        _, last_day = calendar.monthrange(date.year, end_month)
        end = date.replace(month=end_month, day=last_day, hour=23, minute=59, second=59, microsecond=999999)
    elif period_type == "yearly":
        start = date.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end = date.replace(month=12, day=31, hour=23, minute=59, second=59, microsecond=999999)
    else:
        raise ValueError(f"Unsupported period_type: {period_type}")
    
    return start, end


def _extract_date_from_cost_line(
    line: CostLine,
    date_field: str = "date_recorded",
) -> datetime | None:
    """
    Extract date from CostLine attributes or return None.
    
    Args:
        line: CostLine to extract date from
        date_field: Field name to look for in attributes
    
    Returns:
        Parsed datetime or None if not found
    """
    if not line.attributes:
        return None
    
    date_value = line.attributes.get(date_field)
    if date_value is None:
        return None
    
    if isinstance(date_value, datetime):
        return date_value
    
    if isinstance(date_value, str):
        try:
            return _parse_date(date_value)
        except (ValueError, TypeError):
            return None
    
    return None


def _get_effective_cost(line: CostLine, *, prefer_total: bool = True) -> Decimal | None:
    """
    Get effective cost from CostLine, preferring total_cost when prefer_total is True.
    
    Args:
        line: CostLine to extract cost from
        prefer_total: If True, prefer total_cost over quantity * unit_cost
    
    Returns:
        Effective cost as Decimal or None if not calculable
    """
    if prefer_total and line.total_cost is not None:
        return line.total_cost
    
    if line.quantity is not None and line.unit_cost is not None:
        return line.quantity * line.unit_cost
    
    if not prefer_total and line.total_cost is not None:
        return line.total_cost
    
    return None


def generate_time_phased_report(
    *,
    dataset_version_id: str,
    cost_lines: list[CostLine],
    period_type: str = "monthly",
    date_field: str = "date_recorded",
    include_item_details: bool = False,
    start_date: str | None = None,
    end_date: str | None = None,
    prefer_total_cost: bool = True,
) -> TimePhasedCostReport:
    """
    Generate time-phased cost intelligence report from CostLine models.
    
    Aggregates cost data by time periods to provide time-phased visibility
    into project costs. Dates are extracted from CostLine attributes.
    
    Args:
        dataset_version_id: DatasetVersion identifier (must match all cost_lines)
        cost_lines: List of CostLine objects (mix of 'boq' and 'actual' kinds)
        period_type: Type of time period aggregation ('daily', 'weekly', 'monthly', 'quarterly', 'yearly')
        date_field: Field name in attributes to use for date extraction (default: 'date_recorded')
        include_item_details: Whether to include detailed item-level data in each period
        start_date: Optional start date filter (ISO format). If not provided, uses earliest date in records.
        end_date: Optional end date filter (ISO format). If not provided, uses latest date in records.
        prefer_total_cost: Whether to prefer total_cost over quantity * unit_cost
    
    Returns:
        TimePhasedCostReport with aggregated cost data by period
    
    Raises:
        ValueError: If required fields are missing or invalid
        DatasetVersionMismatchError: If cost_lines have mismatched dataset_version_id
    """
    from backend.app.engines.construction_cost_intelligence.errors import DatasetVersionMismatchError
    
    if not cost_lines:
        raise ValueError("cost_lines cannot be empty")
    
    if period_type not in ("daily", "weekly", "monthly", "quarterly", "yearly"):
        raise ValueError(f"Unsupported period_type: {period_type}")
    
    # Validate DatasetVersion consistency
    for line in cost_lines:
        if line.dataset_version_id != dataset_version_id:
            raise DatasetVersionMismatchError("DATASET_VERSION_MISMATCH")
    
    # Extract dates and build records with dates
    dated_records: list[tuple[datetime, CostLine]] = []
    for line in cost_lines:
        date = _extract_date_from_cost_line(line, date_field=date_field)
        if date is not None:
            dated_records.append((date, line))
    
    if not dated_records:
        raise ValueError(f"No cost_lines have valid date in field '{date_field}'")
    
    # Determine report bounds
    parsed_dates = [d for d, _ in dated_records]
    report_start = min(parsed_dates)
    report_end = max(parsed_dates)
    
    if start_date:
        start_filter = _parse_date(start_date)
        if start_filter > report_end:
            raise ValueError(f"start_date {start_date} is after latest record date")
        report_start = max(report_start, start_filter)
    
    if end_date:
        end_filter = _parse_date(end_date)
        if end_filter < report_start:
            raise ValueError(f"end_date {end_date} is before earliest record date")
        report_end = min(report_end, end_filter)
    
    # Group records by period
    periods_data: dict[str, list[tuple[datetime, CostLine]]] = {}
    
    for date, line in dated_records:
        # Skip records outside report bounds
        if date < report_start or date > report_end:
            continue
        
        period_id = _get_period_identifier(date, period_type)
        if period_id not in periods_data:
            periods_data[period_id] = []
        periods_data[period_id].append((date, line))
    
    # Build period summaries
    periods: list[dict[str, Any]] = []
    total_estimated = Decimal("0")
    total_actual = Decimal("0")
    
    # Sort periods for deterministic output
    sorted_period_ids = sorted(periods_data.keys())
    
    for period_id in sorted_period_ids:
        records = periods_data[period_id]
        
        # Get period bounds from first record's date
        first_date = records[0][0]
        period_start, period_end = _get_period_bounds(first_date, period_type)
        
        # Aggregate costs for period
        period_estimated = Decimal("0")
        period_actual = Decimal("0")
        items: list[dict[str, Any]] = []
        
        for date, line in records:
            cost = _get_effective_cost(line, prefer_total=prefer_total_cost)
            
            if cost is None:
                continue
            
            if line.kind == "boq":
                period_estimated += cost
            elif line.kind == "actual":
                period_actual += cost
            
            if include_item_details:
                items.append({
                    "line_id": line.line_id,
                    "kind": line.kind,
                    "identity": dict(line.identity),
                    "cost": str(cost),
                    "date_recorded": _format_date(date),
                })
        
        period_variance = period_actual - period_estimated
        period_variance_pct = Decimal("0")
        if period_estimated != Decimal("0"):
            period_variance_pct = ((period_actual - period_estimated) / period_estimated) * Decimal("100")
            period_variance_pct = period_variance_pct.quantize(Decimal("0.01"))
        
        period_summary: dict[str, Any] = {
            "period": period_id,
            "start_date": _format_date(period_start),
            "end_date": _format_date(period_end),
            "estimated_cost": str(period_estimated),
            "actual_cost": str(period_actual),
            "variance_amount": str(period_variance),
            "variance_percentage": str(period_variance_pct),
            "item_count": len(records),
        }
        
        if include_item_details:
            period_summary["items"] = items
        
        periods.append(period_summary)
        
        total_estimated += period_estimated
        total_actual += period_actual
    
    # Calculate totals
    total_variance = total_actual - total_estimated
    total_variance_pct = Decimal("0")
    if total_estimated != Decimal("0"):
        total_variance_pct = ((total_actual - total_estimated) / total_estimated) * Decimal("100")
        total_variance_pct = total_variance_pct.quantize(Decimal("0.01"))
    
    return TimePhasedCostReport(
        dataset_version_id=dataset_version_id,
        period_type=period_type,
        periods=periods,
        total_estimated_cost=total_estimated,
        total_actual_cost=total_actual,
        total_variance_amount=total_variance,
        total_variance_percentage=total_variance_pct,
        report_start_date=_format_date(report_start),
        report_end_date=_format_date(report_end),
    )
