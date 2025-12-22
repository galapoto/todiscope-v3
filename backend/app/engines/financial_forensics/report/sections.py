from __future__ import annotations

from decimal import Decimal
from typing import Any


def section_executive_overview(*, dataset_version_id: str, run_id: str, totals: dict[str, Any]) -> dict:
    return {
        "title": "Executive Overview",
        "dataset_version_id": dataset_version_id,
        "run_id": run_id,
        "totals": totals,
    }


def section_leakage_breakdown(*, rows: list[dict[str, Any]]) -> dict:
    return {"title": "Leakage Breakdown", "by_typology": rows}


def section_exposure_summary(*, total_exposure_abs: str) -> dict:
    return {"title": "Exposure Summary", "total_exposure_abs": total_exposure_abs}


def section_findings_table(*, findings: list[dict[str, Any]]) -> dict:
    return {"title": "Detailed Findings (Appendix)", "rows": findings}


def section_evidence_index(*, evidence_index: list[dict[str, Any]]) -> dict:
    return {"title": "Evidence Index", "items": evidence_index}

