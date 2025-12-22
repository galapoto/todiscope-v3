"""
Report Sections for Construction Cost Intelligence Engine

Deterministic report section generation for cost variance and time-phased reports.
All sections are deterministic and replay-stable, bound to DatasetVersion.
"""
from __future__ import annotations

from typing import Any


def section_executive_summary(
    *,
    dataset_version_id: str,
    run_id: str,
    total_estimated_cost: str,
    total_actual_cost: str,
    total_variance_amount: str,
    total_variance_percentage: str,
    variance_count: int,
    severity_breakdown: dict[str, int],
) -> dict[str, Any]:
    """
    Executive summary section.
    
    Contains high-level cost variance overview and summary metrics.
    """
    return {
        "section_id": "executive_summary",
        "section_type": "executive_summary",
        "dataset_version_id": dataset_version_id,
        "run_id": run_id,
        "total_estimated_cost": total_estimated_cost,
        "total_actual_cost": total_actual_cost,
        "total_variance_amount": total_variance_amount,
        "total_variance_percentage": total_variance_percentage,
        "variance_count": variance_count,
        "severity_breakdown": severity_breakdown,
    }


def section_cost_variances(
    *,
    variances: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Cost variances section.
    
    Contains detailed variance analysis between BOQ estimates and actual costs.
    """
    return {
        "section_id": "cost_variances",
        "section_type": "cost_variances",
        "variances": variances,
        "variance_count": len(variances),
    }


def section_variance_summary_by_severity(
    *,
    severity_summary: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Variance summary by severity section.
    
    Aggregated variance metrics grouped by severity classification.
    """
    return {
        "section_id": "variance_summary_by_severity",
        "section_type": "variance_summary_by_severity",
        "severity_summary": severity_summary,
    }


def section_variance_summary_by_category(
    *,
    category_summary: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Variance summary by category section.
    
    Aggregated variance metrics grouped by cost category.
    """
    return {
        "section_id": "variance_summary_by_category",
        "section_type": "variance_summary_by_category",
        "category_summary": category_summary,
    }


def section_time_phased_report(
    *,
    period_type: str,
    periods: list[dict[str, Any]],
    total_estimated_cost: str,
    total_actual_cost: str,
    total_variance_amount: str,
    total_variance_percentage: str,
    report_start_date: str,
    report_end_date: str,
) -> dict[str, Any]:
    """
    Time-phased cost report section.
    
    Contains time-phased cost intelligence aggregated by time periods.
    """
    return {
        "section_id": "time_phased_report",
        "section_type": "time_phased_report",
        "period_type": period_type,
        "periods": periods,
        "total_estimated_cost": total_estimated_cost,
        "total_actual_cost": total_actual_cost,
        "total_variance_amount": total_variance_amount,
        "total_variance_percentage": total_variance_percentage,
        "report_start_date": report_start_date,
        "report_end_date": report_end_date,
        "period_count": len(periods),
    }


def section_evidence_index(
    *,
    evidence_index: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Evidence index section.
    
    Contains references to all evidence bundles used in the report.
    """
    return {
        "section_id": "evidence_index",
        "section_type": "evidence_index",
        "evidence_index": evidence_index,
        "evidence_count": len(evidence_index),
    }


def section_limitations_assumptions(
    *,
    limitations: list[str],
    assumptions: dict[str, Any],
) -> dict[str, Any]:
    """
    Limitations and assumptions section.
    
    Contains explicit limitations and assumptions for the cost analysis.
    """
    return {
        "section_id": "limitations_assumptions",
        "section_type": "limitations_assumptions",
        "limitations": limitations,
        "assumptions": assumptions,
    }


def section_core_traceability(
    *,
    dataset_version_id: str,
    core_engine_id: str,
    assumptions_evidence_id: str,
    inputs_evidence_ids: list[str],
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Core traceability section.

    Provides explicit links from core findings to evidence records, and exposes the
    assumptions evidence anchor used for the core comparison run.
    """
    return {
        "section_id": "core_traceability",
        "section_type": "core_traceability",
        "dataset_version_id": dataset_version_id,
        "core_engine_id": core_engine_id,
        "assumptions_evidence_id": assumptions_evidence_id,
        "inputs_evidence_ids": inputs_evidence_ids,
        "findings": findings,
        "finding_count": len(findings),
    }
