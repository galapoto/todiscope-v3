"""
Reporting Service

Provides functions to format findings and evidence into structured reports for legal teams.
Reports present findings as ranges/scenarios, not definitive conclusions.
All assumptions and evidence are explicitly documented.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.calculation.service import get_calculation_run, get_evidence_for_calculation_run
from backend.app.core.evidence.aggregation import (
    get_evidence_for_findings,
    get_findings_by_dataset_version,
    verify_evidence_traceability,
)
from backend.app.core.evidence.models import EvidenceRecord, FindingRecord
from backend.app.core.reporting.models import ReportArtifact
from backend.app.core.audit.service import log_reporting_action


class ReportingError(Exception):
    """Base exception for reporting errors."""


class InvalidFindingError(ReportingError):
    """Raised when a finding cannot be formatted for reporting."""


def deterministic_report_id(*, calculation_run_id: str, report_kind: str) -> str:
    namespace = uuid.UUID("00000000-0000-0000-0000-000000000046")
    return str(uuid.uuid5(namespace, f"{calculation_run_id}|{report_kind}"))


def format_finding_as_scenario(
    finding: FindingRecord,
    *,
    evidence_records: list[EvidenceRecord] | None = None,
) -> dict[str, Any]:
    """
    Format a finding as a scenario/range rather than a definitive conclusion.
    
    Args:
        finding: The FindingRecord to format
        evidence_records: Optional list of evidence records linked to this finding
        
    Returns:
        Dictionary with scenario-formatted finding:
        - finding_id: str
        - dataset_version_id: str
        - kind: str
        - scenario_description: str (describes the finding as a scenario)
        - evidence_references: list of evidence IDs
        - assumptions: list of assumptions extracted from payload
        - created_at: ISO datetime string
    """
    evidence_ids = [e.evidence_id for e in (evidence_records or [])]
    
    # Extract assumptions from payload if present
    assumptions: list[str] = []
    if isinstance(finding.payload, dict):
        payload_assumptions = finding.payload.get("assumptions", [])
        if isinstance(payload_assumptions, list):
            assumptions = [str(a) for a in payload_assumptions]
        elif payload_assumptions:
            assumptions = [str(payload_assumptions)]
    
    # Build scenario description from finding kind and payload
    scenario_description = _build_scenario_description(finding)
    
    return {
        "finding_id": finding.finding_id,
        "dataset_version_id": finding.dataset_version_id,
        "kind": finding.kind,
        "scenario_description": scenario_description,
        "evidence_references": evidence_ids,
        "assumptions": assumptions,
        "created_at": finding.created_at.isoformat(),
    }


def format_finding_as_range(
    finding: FindingRecord,
    *,
    evidence_records: list[EvidenceRecord] | None = None,
    range_fields: list[str] | None = None,
) -> dict[str, Any]:
    """
    Format a finding with numeric ranges when applicable.
    
    Args:
        finding: The FindingRecord to format
        evidence_records: Optional list of evidence records linked to this finding
        range_fields: Optional list of field names in payload that represent ranges
        
    Returns:
        Dictionary with range-formatted finding:
        - finding_id: str
        - dataset_version_id: str
        - kind: str
        - ranges: dict mapping field names to range values (min, max, or value)
        - evidence_references: list of evidence IDs
        - assumptions: list of assumptions
        - created_at: ISO datetime string
    """
    evidence_ids = [e.evidence_id for e in (evidence_records or [])]
    
    # Extract assumptions from payload
    assumptions: list[str] = []
    ranges: dict[str, Any] = {}
    
    if isinstance(finding.payload, dict):
        # Extract assumptions
        payload_assumptions = finding.payload.get("assumptions", [])
        if isinstance(payload_assumptions, list):
            assumptions = [str(a) for a in payload_assumptions]
        elif payload_assumptions:
            assumptions = [str(payload_assumptions)]
        
        # Extract ranges
        if range_fields:
            for field in range_fields:
                if field in finding.payload:
                    ranges[field] = finding.payload[field]
        else:
            # Try to detect common range fields
            for key, value in finding.payload.items():
                if key in ("min_value", "max_value", "min", "max", "range_min", "range_max", "value"):
                    ranges[key] = value
                elif isinstance(value, (int, float, Decimal)) or (isinstance(value, str) and _is_numeric_string(value)):
                    ranges[key] = value
    
    return {
        "finding_id": finding.finding_id,
        "dataset_version_id": finding.dataset_version_id,
        "kind": finding.kind,
        "ranges": ranges,
        "evidence_references": evidence_ids,
        "assumptions": assumptions,
        "created_at": finding.created_at.isoformat(),
    }


def _build_scenario_description(finding: FindingRecord) -> str:
    """Build a scenario description from finding kind and payload."""
    kind = finding.kind or "unknown"
    
    if isinstance(finding.payload, dict):
        # Try to extract a description or summary
        description = finding.payload.get("description") or finding.payload.get("summary") or finding.payload.get("scenario")
        if description:
            return str(description)
        
        # Build from kind and key fields
        key_fields = []
        for key in ("type", "category", "severity", "status"):
            if key in finding.payload:
                key_fields.append(f"{key}={finding.payload[key]}")
        
        if key_fields:
            return f"{kind}: {', '.join(key_fields)}"
    
    return f"{kind} scenario"


def _is_numeric_string(value: str) -> bool:
    """Check if a string represents a number."""
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False


async def generate_litigation_report(
    db: AsyncSession,
    *,
    dataset_version_id: str,
    calculation_run_id: str,
    actor_id: str | None = None,
    report_title: str | None = None,
    include_assumptions: bool = True,
    include_evidence_index: bool = True,
    format_as_ranges: bool = False,
) -> dict[str, Any]:
    """
    Generate a structured litigation support report.
    
    Args:
        db: Database session
        dataset_version_id: The dataset version ID
        calculation_run_id: The calculation run ID (required)
        report_title: Optional title for the report
        include_assumptions: Whether to include assumptions section
        include_evidence_index: Whether to include evidence index
        format_as_ranges: Whether to format findings as ranges (default: scenarios)
        
    Returns:
        Dictionary with report structure:
        - metadata: dict with report identifiers and timestamps
        - scope: dict with dataset_version_id and traceability info
        - findings: list of formatted findings
        - assumptions: list of all assumptions (if include_assumptions=True)
        - evidence_index: list of evidence references (if include_evidence_index=True)
        - limitations: list of limitations and disclaimers
    """
    run = await get_calculation_run(db, run_id=calculation_run_id)
    if run is None:
        raise ReportingError("CALCULATION_RUN_NOT_FOUND")
    if run.dataset_version_id != dataset_version_id:
        raise ReportingError("CALCULATION_RUN_DATASET_VERSION_MISMATCH")

    evidence_records = await get_evidence_for_calculation_run(db, calculation_run_id=calculation_run_id)
    if not evidence_records:
        raise ReportingError("CALCULATION_RUN_EVIDENCE_REQUIRED")

    evidence_ids = [e.evidence_id for e in evidence_records]
    evidence_id_set = set(evidence_ids)
    traceability_result = await verify_evidence_traceability(
        db, dataset_version_id=dataset_version_id, evidence_ids=evidence_ids
    )
    if not traceability_result["valid"]:
        raise ReportingError(
            f"Evidence traceability verification failed: {traceability_result['mismatches']}"
        )
    
    # Get all findings for this dataset version
    findings = await get_findings_by_dataset_version(db, dataset_version_id=dataset_version_id)
    
    # Get evidence for all findings
    finding_ids = [f.finding_id for f in findings]
    evidence_by_finding = await get_evidence_for_findings(
        db, finding_ids=finding_ids, dataset_version_id=dataset_version_id
    )
    
    # Format findings
    formatted_findings: list[dict[str, Any]] = []
    all_assumptions: set[str] = set()
    all_evidence_ids: set[str] = set()
    
    for finding in findings:
        finding_evidence = [
            e for e in evidence_by_finding.get(finding.finding_id, []) if e.evidence_id in evidence_id_set
        ]
        finding_evidence_ids = [e.evidence_id for e in finding_evidence]
        all_evidence_ids.update(finding_evidence_ids)
        
        if format_as_ranges:
            formatted = format_finding_as_range(finding, evidence_records=finding_evidence)
        else:
            formatted = format_finding_as_scenario(finding, evidence_records=finding_evidence)
        
        formatted_findings.append(formatted)
        
        # Collect assumptions
        if include_assumptions and formatted.get("assumptions"):
            all_assumptions.update(formatted["assumptions"])
    
    # Get evidence index if requested
    evidence_index: list[dict[str, Any]] = []
    if include_evidence_index and all_evidence_ids:
        evidence_by_id = {e.evidence_id: e for e in evidence_records}
        
        for evidence_id in sorted(all_evidence_ids):
            if evidence_id in evidence_by_id:
                evidence = evidence_by_id[evidence_id]
                evidence_index.append({
                    "evidence_id": evidence.evidence_id,
                    "kind": evidence.kind,
                    "engine_id": evidence.engine_id,
                    "dataset_version_id": evidence.dataset_version_id,
                    "created_at": evidence.created_at.isoformat(),
                })
    
    # Build limitations section
    limitations = [
        "Findings are presented as scenarios or ranges, not definitive conclusions.",
        "All findings are bound to DatasetVersion and are immutable once created.",
        "Evidence traceability is verified for all findings.",
        "Assumptions are explicitly documented and may affect findings.",
        "This report is for litigation support purposes and does not constitute legal advice.",
    ]
    
    # Build report
    report_id = deterministic_report_id(calculation_run_id=calculation_run_id, report_kind="litigation")
    report: dict[str, Any] = {
        "metadata": {
            "report_id": report_id,
            "report_title": report_title or "Litigation Support Report",
            "dataset_version_id": dataset_version_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_findings": len(formatted_findings),
            "format_type": "ranges" if format_as_ranges else "scenarios",
        },
        "scope": {
            "dataset_version_id": dataset_version_id,
            "calculation_run_id": calculation_run_id,
            "traceability_verified": traceability_result["valid"],
            "total_evidence_checked": traceability_result["total_checked"],
        },
        "findings": formatted_findings,
        "limitations": limitations,
    }
    
    if include_assumptions:
        report["assumptions"] = sorted(list(all_assumptions)) if all_assumptions else []
    
    if include_evidence_index:
        report["evidence_index"] = evidence_index
    
    artifact = ReportArtifact(
        report_id=report_id,
        dataset_version_id=dataset_version_id,
        calculation_run_id=calculation_run_id,
        engine_id=run.engine_id,
        report_kind="litigation",
        payload=report,
        created_at=datetime.now(timezone.utc),
    )
    db.add(artifact)
    await db.flush()
    await log_reporting_action(
        db,
        actor_id=actor_id or "system",
        dataset_version_id=dataset_version_id,
        calculation_run_id=calculation_run_id,
        artifact_id=report_id,
        report_type="litigation",
        metadata={"report_id": report_id},
    )
    return report


async def generate_evidence_summary_report(
    db: AsyncSession,
    *,
    dataset_version_id: str,
    calculation_run_id: str,
    actor_id: str | None = None,
) -> dict[str, Any]:
    """
    Generate a summary report of all evidence for a dataset version.
    
    Args:
        db: Database session
        dataset_version_id: The dataset version ID
        calculation_run_id: The calculation run ID (required)
        
    Returns:
        Dictionary with evidence summary:
        - dataset_version_id: str
        - summary: dict with counts and statistics
        - evidence_by_kind: list of evidence grouped by kind
        - evidence_by_engine: list of evidence grouped by engine
        - traceability: traceability verification results
    """
    run = await get_calculation_run(db, run_id=calculation_run_id)
    if run is None:
        raise ReportingError("CALCULATION_RUN_NOT_FOUND")
    if run.dataset_version_id != dataset_version_id:
        raise ReportingError("CALCULATION_RUN_DATASET_VERSION_MISMATCH")

    evidence_records = await get_evidence_for_calculation_run(db, calculation_run_id=calculation_run_id)
    if not evidence_records:
        raise ReportingError("CALCULATION_RUN_EVIDENCE_REQUIRED")

    evidence_ids = [record.evidence_id for record in evidence_records]
    traceability = await verify_evidence_traceability(
        db, dataset_version_id=dataset_version_id, evidence_ids=evidence_ids
    )

    summary = {
        "total_evidence": len(evidence_records),
        "engine_ids": sorted({record.engine_id for record in evidence_records}),
        "kinds": sorted({record.kind for record in evidence_records}),
    }

    evidence_by_kind: dict[str, list[EvidenceRecord]] = {}
    evidence_by_engine: dict[str, list[EvidenceRecord]] = {}
    for record in evidence_records:
        evidence_by_kind.setdefault(record.kind, []).append(record)
        evidence_by_engine.setdefault(record.engine_id, []).append(record)

    kind_summary = [
        {
            "kind": kind,
            "count": len(records),
            "evidence_ids": sorted([r.evidence_id for r in records]),
        }
        for kind, records in sorted(evidence_by_kind.items())
    ]

    engine_summary = [
        {
            "engine_id": engine_id,
            "count": len(records),
            "evidence_ids": sorted([r.evidence_id for r in records]),
        }
        for engine_id, records in sorted(evidence_by_engine.items())
    ]

    report_id = deterministic_report_id(calculation_run_id=calculation_run_id, report_kind="evidence_summary")
    artifact = ReportArtifact(
        report_id=report_id,
        dataset_version_id=dataset_version_id,
        calculation_run_id=calculation_run_id,
        engine_id=run.engine_id,
        report_kind="evidence_summary",
        payload={
            "dataset_version_id": dataset_version_id,
            "calculation_run_id": calculation_run_id,
            "summary": summary,
            "evidence_by_kind": kind_summary,
            "evidence_by_engine": engine_summary,
            "traceability": traceability,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        created_at=datetime.now(timezone.utc),
    )
    db.add(artifact)
    await db.flush()
    await log_reporting_action(
        db,
        actor_id=actor_id or "system",
        dataset_version_id=dataset_version_id,
        calculation_run_id=calculation_run_id,
        artifact_id=report_id,
        report_type="evidence_summary",
        metadata={"report_id": report_id},
    )

    return {
        "dataset_version_id": dataset_version_id,
        "calculation_run_id": calculation_run_id,
        "summary": summary,
        "evidence_by_kind": kind_summary,
        "evidence_by_engine": engine_summary,
        "traceability": traceability,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
