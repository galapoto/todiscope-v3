"""
Report Assembler for Construction Cost Intelligence Engine

Assembles cost variance and time-phased reports from ComparisonResult (Agent 1's model).
All reports are deterministic and bound to DatasetVersion.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.evidence.models import EvidenceRecord, FindingEvidenceLink, FindingRecord
from backend.app.engines.construction_cost_intelligence.assumptions import (
    AssumptionRegistry,
    ValidityScope,
    add_category_field_assumption,
    add_scope_creep_assumption,
    add_time_phased_assumptions,
    add_variance_threshold_assumptions,
    create_default_assumption_registry,
)
from backend.app.engines.construction_cost_intelligence.errors import (
    DatasetVersionMismatchError,
    MissingArtifactError,
)
from backend.app.engines.construction_cost_intelligence.evidence import (
    emit_time_phased_report_evidence,
    emit_variance_analysis_evidence,
)
from backend.app.engines.construction_cost_intelligence.findings import (
    persist_time_phased_findings,
    persist_variance_findings,
)
from backend.app.engines.construction_cost_intelligence.findings import (
    persist_scope_creep_finding,
    persist_time_phased_findings,
    persist_variance_findings,
)
from backend.app.engines.construction_cost_intelligence.ids import (
    deterministic_comparison_result_stable_key,
    deterministic_time_phased_report_stable_key,
)
from backend.app.engines.construction_cost_intelligence.models import (
    ComparisonResult,
    CostLine,
)
from backend.app.engines.construction_cost_intelligence.report.sections import (
    section_cost_variances,
    section_core_traceability,
    section_evidence_index,
    section_executive_summary,
    section_limitations_assumptions,
    section_time_phased_report,
    section_variance_summary_by_category,
    section_variance_summary_by_severity,
)
from backend.app.engines.construction_cost_intelligence.variance.detector import (
    CostVariance,
    VarianceSeverity,
    detect_cost_variances,
    detect_scope_creep,
)
from backend.app.engines.construction_cost_intelligence.time_phased.reporter import (
    generate_time_phased_report,
)
from backend.app.engines.construction_cost_intelligence.traceability import ENGINE_ID as CORE_ENGINE_ID


def _aggregate_variances_by_severity(variances: list[CostVariance]) -> list[dict]:
    """
    Aggregate variances by severity classification.
    
    Returns list of summary dicts, one per severity level.
    """
    severity_buckets: dict[VarianceSeverity, dict] = {}
    
    for variance in variances:
        severity = variance.severity
        if severity not in severity_buckets:
            severity_buckets[severity] = {
                "severity": severity.value,
                "count": 0,
                "total_variance_amount": Decimal("0"),
                "total_estimated_cost": Decimal("0"),
                "total_actual_cost": Decimal("0"),
            }
        
        bucket = severity_buckets[severity]
        bucket["count"] += 1
        bucket["total_variance_amount"] += abs(variance.variance_amount)
        bucket["total_estimated_cost"] += variance.estimated_cost
        bucket["total_actual_cost"] += variance.actual_cost
    
    # Convert to list and format
    summary = []
    for severity in sorted(severity_buckets.keys(), key=lambda s: s.value):
        bucket = severity_buckets[severity]
        total_variance_pct = Decimal("0")
        if bucket["total_estimated_cost"] != Decimal("0"):
            total_variance_pct = (
                (bucket["total_actual_cost"] - bucket["total_estimated_cost"])
                / bucket["total_estimated_cost"]
                * Decimal("100")
            )
            total_variance_pct = total_variance_pct.quantize(Decimal("0.01"))
        
        summary.append({
            "severity": bucket["severity"],
            "count": bucket["count"],
            "total_variance_amount": str(bucket["total_variance_amount"]),
            "total_estimated_cost": str(bucket["total_estimated_cost"]),
            "total_actual_cost": str(bucket["total_actual_cost"]),
            "total_variance_percentage": str(total_variance_pct),
        })
    
    return summary


def _aggregate_variances_by_category(variances: list[CostVariance]) -> list[dict]:
    """
    Aggregate variances by category.
    
    Returns list of summary dicts, one per category.
    """
    category_buckets: dict[str, dict] = {}
    
    for variance in variances:
        category = variance.category or "uncategorized"
        if category not in category_buckets:
            category_buckets[category] = {
                "category": category,
                "count": 0,
                "total_variance_amount": Decimal("0"),
                "total_estimated_cost": Decimal("0"),
                "total_actual_cost": Decimal("0"),
            }
        
        bucket = category_buckets[category]
        bucket["count"] += 1
        bucket["total_variance_amount"] += abs(variance.variance_amount)
        bucket["total_estimated_cost"] += variance.estimated_cost
        bucket["total_actual_cost"] += variance.actual_cost
    
    # Convert to list and format
    summary = []
    for category in sorted(category_buckets.keys()):
        bucket = category_buckets[category]
        total_variance_pct = Decimal("0")
        if bucket["total_estimated_cost"] != Decimal("0"):
            total_variance_pct = (
                (bucket["total_actual_cost"] - bucket["total_estimated_cost"])
                / bucket["total_estimated_cost"]
                * Decimal("100")
            )
            total_variance_pct = total_variance_pct.quantize(Decimal("0.01"))
        
        summary.append({
            "category": bucket["category"],
            "count": bucket["count"],
            "total_variance_amount": str(bucket["total_variance_amount"]),
            "total_estimated_cost": str(bucket["total_estimated_cost"]),
            "total_actual_cost": str(bucket["total_actual_cost"]),
            "total_variance_percentage": str(total_variance_pct),
        })
    
    return summary


def _variance_to_dict(variance: CostVariance) -> dict:
    """Convert CostVariance to dict for report."""
    return {
        "match_key": variance.match_key,
        "category": variance.category,
        "estimated_cost": str(variance.estimated_cost),
        "actual_cost": str(variance.actual_cost),
        "variance_amount": str(variance.variance_amount),
        "variance_percentage": str(variance.variance_percentage),
        "severity": variance.severity.value,
        "direction": variance.direction.value,
        "scope_creep": bool(getattr(variance, "scope_creep", False)),
        "line_ids_boq": list(variance.line_ids_boq),
        "line_ids_actual": list(variance.line_ids_actual),
        "identity": variance.identity or {},
        "attributes": variance.attributes or {},
        "core_finding_ids": list(getattr(variance, "core_finding_ids", ())),
        "evidence_ids": list(getattr(variance, "evidence_ids", ())),
    }


async def _load_core_traceability_bundle(
    db: AsyncSession,
    *,
    dataset_version_id: str,
    core_traceability: dict,
) -> tuple[list[dict], list[dict], list[str]]:
    """
    Load and validate core traceability artifacts for report integration.

    Returns:
      (core_assumptions, core_findings, core_evidence_ids)
    """
    assumptions_evidence_id = core_traceability.get("assumptions_evidence_id")
    inputs_evidence_ids = core_traceability.get("inputs_evidence_ids")
    finding_ids = core_traceability.get("finding_ids")

    if not isinstance(assumptions_evidence_id, str) or not assumptions_evidence_id.strip():
        raise MissingArtifactError("CORE_ASSUMPTIONS_EVIDENCE_ID_REQUIRED")
    if not isinstance(inputs_evidence_ids, list) or any(
        not isinstance(x, str) or not x.strip() for x in inputs_evidence_ids
    ):
        raise MissingArtifactError("CORE_INPUTS_EVIDENCE_IDS_REQUIRED")
    if not isinstance(finding_ids, list) or any(not isinstance(x, str) or not x.strip() for x in finding_ids):
        raise MissingArtifactError("CORE_FINDING_IDS_REQUIRED")

    assumptions_ev = await db.scalar(select(EvidenceRecord).where(EvidenceRecord.evidence_id == assumptions_evidence_id))
    if assumptions_ev is None:
        raise MissingArtifactError("CORE_ASSUMPTIONS_EVIDENCE_NOT_FOUND")
    if assumptions_ev.dataset_version_id != dataset_version_id:
        raise DatasetVersionMismatchError("CORE_ASSUMPTIONS_EVIDENCE_DATASET_MISMATCH")

    core_assumptions: list[dict] = []
    if isinstance(assumptions_ev.payload, dict):
        ass = assumptions_ev.payload.get("assumptions")
        if isinstance(ass, list) and all(isinstance(a, dict) for a in ass):
            core_assumptions = list(ass)

    evidence_ids_set: set[str] = {assumptions_evidence_id}
    for ev_id in inputs_evidence_ids:
        ev = await db.scalar(select(EvidenceRecord).where(EvidenceRecord.evidence_id == ev_id))
        if ev is None:
            raise MissingArtifactError("CORE_INPUT_EVIDENCE_NOT_FOUND")
        if ev.dataset_version_id != dataset_version_id:
            raise DatasetVersionMismatchError("CORE_INPUT_EVIDENCE_DATASET_MISMATCH")
        evidence_ids_set.add(ev_id)

    findings_rows = (
        await db.execute(select(FindingRecord).where(FindingRecord.finding_id.in_(finding_ids)))
    ).scalars().all()
    if len(findings_rows) != len(set(finding_ids)):
        raise MissingArtifactError("CORE_FINDING_NOT_FOUND")
    for fr in findings_rows:
        if fr.dataset_version_id != dataset_version_id:
            raise DatasetVersionMismatchError("CORE_FINDING_DATASET_MISMATCH")

    link_rows = (
        await db.execute(select(FindingEvidenceLink).where(FindingEvidenceLink.finding_id.in_(finding_ids)))
    ).scalars().all()
    evidence_by_finding: dict[str, set[str]] = {}
    for link in link_rows:
        evidence_by_finding.setdefault(link.finding_id, set()).add(link.evidence_id)
        evidence_ids_set.add(link.evidence_id)

    core_findings: list[dict] = []
    for fr in sorted(findings_rows, key=lambda f: f.finding_id):
        core_findings.append(
            {
                "finding_id": fr.finding_id,
                "kind": fr.kind,
                "raw_record_id": fr.raw_record_id,
                "payload": fr.payload,
                "evidence_ids": sorted(evidence_by_finding.get(fr.finding_id, set())),
            }
        )

    return core_assumptions, core_findings, sorted(evidence_ids_set)


async def assemble_cost_variance_report(
    db: AsyncSession,
    *,
    dataset_version_id: str,
    run_id: str,
    comparison_result: ComparisonResult,
    tolerance_threshold: Decimal = Decimal("5.0"),
    minor_threshold: Decimal = Decimal("10.0"),
    moderate_threshold: Decimal = Decimal("25.0"),
    major_threshold: Decimal = Decimal("50.0"),
    category_field: str | None = None,
    evidence_ids: list[str] | None = None,
    core_traceability: dict | None = None,
    boq_raw_record_id: str | None = None,
    actual_raw_record_id: str | None = None,
    created_at: datetime | None = None,
    emit_evidence: bool = True,
    persist_findings: bool = True,
) -> dict:
    """
    Assemble cost variance report from ComparisonResult.
    
    Args:
        db: Database session
        dataset_version_id: DatasetVersion identifier (must match comparison_result)
        run_id: Run identifier
        comparison_result: ComparisonResult from Agent 1's comparison logic
        tolerance_threshold: Percentage threshold for within tolerance
        minor_threshold: Percentage threshold for minor variance
        moderate_threshold: Percentage threshold for moderate variance
        major_threshold: Percentage threshold for major variance
        category_field: Optional field name to use for categorization
        evidence_ids: Optional list of evidence IDs to include in report
        boq_raw_record_id: Optional BOQ raw record ID for finding persistence
        actual_raw_record_id: Optional actual raw record ID for finding persistence
        persist_findings: Whether to persist findings as FindingRecords (default: True)
    
    Returns:
        Complete cost variance report dict
    
    Raises:
        MissingArtifactError: If required data is missing
        DatasetVersionMismatchError: If dataset_version_id mismatch
    """
    # Validate DatasetVersion match
    if comparison_result.dataset_version_id != dataset_version_id:
        raise DatasetVersionMismatchError("COMPARISON_RESULT_DATASET_VERSION_MISMATCH")
    
    # Build assumptions registry
    assumptions_registry = create_default_assumption_registry()
    add_variance_threshold_assumptions(
        assumptions_registry,
        tolerance_threshold=tolerance_threshold,
        minor_threshold=minor_threshold,
        moderate_threshold=moderate_threshold,
        major_threshold=major_threshold,
    )
    add_category_field_assumption(assumptions_registry, category_field=category_field)
    add_scope_creep_assumption(assumptions_registry)
    
    # Set validity scope
    validity_scope = ValidityScope(
        dataset_version_id=dataset_version_id,
        run_id=run_id,
        created_at=created_at,
    )
    assumptions_registry.set_validity_scope(validity_scope)
    
    # Detect cost variances (matched BOQ vs actual)
    variances = detect_cost_variances(
        comparison_result=comparison_result,
        tolerance_threshold=tolerance_threshold,
        minor_threshold=minor_threshold,
        moderate_threshold=moderate_threshold,
        major_threshold=major_threshold,
        category_field=category_field,
    )

    # Optional: integrate scope creep (unmatched actual) into variance output, with traceability if provided.
    core_assumptions: list[dict] = []
    core_findings: list[dict] = []
    core_traceability_index: dict[str, dict] | None = None
    if core_traceability is not None:
        core_assumptions, core_findings, _ = await _load_core_traceability_bundle(
            db, dataset_version_id=dataset_version_id, core_traceability=core_traceability
        )
        line_to_trace: dict[str, dict] = {}
        for f in core_findings:
            payload = f.get("payload")
            if not isinstance(payload, dict):
                continue
            line_ids = payload.get("line_ids")
            if not isinstance(line_ids, list):
                continue
            for line_id in line_ids:
                if not isinstance(line_id, str) or not line_id.strip():
                    continue
                bucket = line_to_trace.setdefault(line_id, {"core_finding_ids": [], "evidence_ids": []})
                bucket["core_finding_ids"].append(f.get("finding_id"))
                for ev_id in f.get("evidence_ids") or []:
                    bucket["evidence_ids"].append(ev_id)
        core_traceability_index = line_to_trace

    scope_creep_variances = detect_scope_creep(
        comparison_result=comparison_result,
        category_field=category_field,
        core_traceability_index=core_traceability_index,
    )
    variances.extend(scope_creep_variances)
    
    # Calculate totals
    total_estimated = sum(v.estimated_cost for v in variances)
    total_actual = sum(v.actual_cost for v in variances)
    total_variance = total_actual - total_estimated
    total_variance_pct = Decimal("0")
    if total_estimated != Decimal("0"):
        total_variance_pct = ((total_actual - total_estimated) / total_estimated) * Decimal("100")
        total_variance_pct = total_variance_pct.quantize(Decimal("0.01"))
    
    # Calculate severity breakdown
    severity_breakdown: dict[str, int] = {}
    for variance in variances:
        severity = variance.severity.value
        severity_breakdown[severity] = severity_breakdown.get(severity, 0) + 1
    
    # Build variance summaries
    severity_summary = _aggregate_variances_by_severity(variances)
    category_summary = _aggregate_variances_by_category(variances)
    
    # Emit evidence for variance analysis
    all_evidence_ids: list[str] = list(evidence_ids) if evidence_ids else []
    variance_evidence_id: str | None = None
    if emit_evidence and created_at:
        comparison_stable_key = deterministic_comparison_result_stable_key(
            dataset_version_id=dataset_version_id,
            identity_fields=comparison_result.identity_fields,
            matched_count=len(comparison_result.matched),
            unmatched_boq_count=len(comparison_result.unmatched_boq),
            unmatched_actual_count=len(comparison_result.unmatched_actual),
        )
        variance_evidence_id = await emit_variance_analysis_evidence(
            db,
            dataset_version_id=dataset_version_id,
            comparison_result_id=comparison_stable_key,
            variance_count=len(variances),
            scope_creep_count=len(scope_creep_variances),
            scope_creep_line_ids=[ln_id for v in scope_creep_variances for ln_id in v.line_ids_actual],
            assumptions=assumptions_registry,
            created_at=created_at,
        )
        all_evidence_ids.append(variance_evidence_id)
        
        # Persist variance findings as FindingRecords
        variance_finding_ids: list[str] = []
        if persist_findings and variance_evidence_id and created_at:
            # Persist matched variances (excluding scope creep which are handled separately)
            matched_variances = [v for v in variances if not getattr(v, "scope_creep", False)]
            if matched_variances and boq_raw_record_id:
                variance_finding_ids = await persist_variance_findings(
                    db,
                    dataset_version_id=dataset_version_id,
                    variances=matched_variances,
                    raw_record_id=boq_raw_record_id,
                    evidence_id=variance_evidence_id,
                    created_at=created_at,
                )
            
            # Persist scope creep findings
            if scope_creep_variances and actual_raw_record_id:
                scope_creep_finding_ids = await persist_variance_findings(
                    db,
                    dataset_version_id=dataset_version_id,
                    variances=scope_creep_variances,
                    raw_record_id=actual_raw_record_id,
                    evidence_id=variance_evidence_id,
                    created_at=created_at,
                )
                variance_finding_ids.extend(scope_creep_finding_ids)
    
    # Convert variances to dicts with evidence reference
    variance_dicts = [
        {
            **_variance_to_dict(v),
            "evidence_id": variance_evidence_id,  # Link each variance to report evidence
        }
        for v in variances
    ]
    
    # Build evidence index (including core traceability evidence if provided)
    evidence_index: list[dict] = []
    if core_traceability is not None:
        _, _, core_evidence_ids = await _load_core_traceability_bundle(
            db, dataset_version_id=dataset_version_id, core_traceability=core_traceability
        )
        all_evidence_ids.extend(core_evidence_ids)

    all_evidence_ids = sorted(set([e for e in all_evidence_ids if isinstance(e, str) and e.strip()]))
    if all_evidence_ids:
        evidences = (
            await db.execute(
                select(EvidenceRecord)
                .where(EvidenceRecord.evidence_id.in_(all_evidence_ids))
                .where(EvidenceRecord.dataset_version_id == dataset_version_id)
                .order_by(EvidenceRecord.evidence_id.asc())
            )
        ).scalars().all()
        
        evidence_index = [
            {
                "evidence_id": e.evidence_id,
                "kind": e.kind,
                "engine_id": e.engine_id,
                "created_at": e.created_at.isoformat(),
            }
            for e in evidences
        ]
    
    # Build limitations
    limitations = [
        "Variance analysis is limited to the provided DatasetVersion",
        "Variance analysis processes matched BOQ vs actual, plus scope creep (unmatched actual) entries when present",
        "Severity classification is based on percentage thresholds",
        "Variance analysis does not determine causes or recommend actions",
    ]
    
    # Assemble report sections
    sections = [
        section_executive_summary(
            dataset_version_id=dataset_version_id,
            run_id=run_id,
            total_estimated_cost=str(total_estimated),
            total_actual_cost=str(total_actual),
            total_variance_amount=str(total_variance),
            total_variance_percentage=str(total_variance_pct),
            variance_count=len(variances),
            severity_breakdown=severity_breakdown,
        ),
        section_variance_summary_by_severity(severity_summary=severity_summary),
        section_variance_summary_by_category(category_summary=category_summary),
        section_cost_variances(variances=variance_dicts),
        section_limitations_assumptions(
            limitations=limitations,
            assumptions=(
                {"core": {"assumptions": core_assumptions}, "report": assumptions_registry.to_dict()}
                if core_traceability is not None
                else assumptions_registry.to_dict()
            ),
        ),
    ]

    if core_traceability is not None:
        sections.append(
            section_core_traceability(
                dataset_version_id=dataset_version_id,
                core_engine_id=CORE_ENGINE_ID,
                assumptions_evidence_id=str(core_traceability.get("assumptions_evidence_id")),
                inputs_evidence_ids=list(core_traceability.get("inputs_evidence_ids") or []),
                findings=core_findings,
            )
        )

    if evidence_index:
        sections.append(section_evidence_index(evidence_index=evidence_index))
    
    return {
        "engine_id": "engine_construction_cost_intelligence",
        "engine_version": "v1",
        "report_type": "cost_variance",
        "dataset_version_id": dataset_version_id,
        "run_id": run_id,
        "sections": sections,
    }


async def assemble_time_phased_report(
    db: AsyncSession,
    *,
    dataset_version_id: str,
    run_id: str,
    cost_lines: list[CostLine],
    period_type: str = "monthly",
    date_field: str = "date_recorded",
    include_item_details: bool = False,
    start_date: str | None = None,
    end_date: str | None = None,
    prefer_total_cost: bool = True,
    evidence_ids: list[str] | None = None,
    core_traceability: dict | None = None,
    raw_record_id: str | None = None,
    created_at: datetime | None = None,
    emit_evidence: bool = True,
    persist_findings: bool = True,
) -> dict:
    """
    Assemble time-phased cost report from CostLine models.
    
    Args:
        db: Database session
        dataset_version_id: DatasetVersion identifier (must match cost_lines)
        run_id: Run identifier
        cost_lines: List of CostLine objects (mix of 'boq' and 'actual' kinds)
        period_type: Type of time period aggregation
        date_field: Field name in attributes to use for date extraction
        include_item_details: Whether to include detailed item-level data
        start_date: Optional start date filter (ISO format)
        end_date: Optional end date filter (ISO format)
        prefer_total_cost: Whether to prefer total_cost over quantity * unit_cost
        evidence_ids: Optional list of evidence IDs to include in report
        raw_record_id: Optional raw record ID for finding persistence
        persist_findings: Whether to persist findings as FindingRecords (default: True)
    
    Returns:
        Complete time-phased cost report dict
    
    Raises:
        MissingArtifactError: If required data is missing
        DatasetVersionMismatchError: If dataset_version_id mismatch
    """
    if not cost_lines:
        raise MissingArtifactError("COST_LINES_REQUIRED")
    
    # Build assumptions registry
    assumptions_registry = create_default_assumption_registry()
    add_time_phased_assumptions(
        assumptions_registry,
        period_type=period_type,
        date_field=date_field,
        prefer_total_cost=prefer_total_cost,
        start_date=start_date,
        end_date=end_date,
    )
    
    # Set validity scope
    validity_scope = ValidityScope(
        dataset_version_id=dataset_version_id,
        run_id=run_id,
        created_at=created_at,
    )
    assumptions_registry.set_validity_scope(validity_scope)
    
    # Generate time-phased report
    time_phased = generate_time_phased_report(
        dataset_version_id=dataset_version_id,
        cost_lines=cost_lines,
        period_type=period_type,
        date_field=date_field,
        include_item_details=include_item_details,
        start_date=start_date,
        end_date=end_date,
        prefer_total_cost=prefer_total_cost,
    )
    
    # Emit evidence for time-phased report
    all_evidence_ids: list[str] = list(evidence_ids) if evidence_ids else []
    time_phased_evidence_id: str | None = None
    time_phased_finding_ids: list[str] = []
    if emit_evidence and created_at:
        report_stable_key = deterministic_time_phased_report_stable_key(
            dataset_version_id=dataset_version_id,
            period_type=period_type,
            date_field=date_field,
            prefer_total_cost=prefer_total_cost,
            start_date=start_date,
            end_date=end_date,
        )
        time_phased_evidence_id = await emit_time_phased_report_evidence(
            db,
            dataset_version_id=dataset_version_id,
            report_id=report_stable_key,
            period_type=period_type,
            period_count=len(time_phased.periods),
            assumptions=assumptions_registry,
            created_at=created_at,
        )
        all_evidence_ids.append(time_phased_evidence_id)
        
        # Persist time-phased findings for periods with significant variance
        time_phased_finding_ids: list[str] = []
        if persist_findings and time_phased_evidence_id and raw_record_id and created_at:
            # Filter periods with significant variance (moderate, major, or critical)
            periods_with_variance = []
            for period in time_phased.periods:
                variance_pct_str = period.get("variance_percentage", "0")
                try:
                    variance_pct = Decimal(str(variance_pct_str))
                except (ValueError, TypeError):
                    variance_pct = Decimal("0")
                
                # Only persist findings for moderate or higher variances (>25%)
                if abs(variance_pct) > Decimal("25.0"):
                    period_with_meta = dict(period)
                    period_with_meta["period_type"] = period_type
                    periods_with_variance.append(period_with_meta)
            
            if periods_with_variance:
                time_phased_finding_ids = await persist_time_phased_findings(
                    db,
                    dataset_version_id=dataset_version_id,
                    periods_with_variance=periods_with_variance,
                    raw_record_id=raw_record_id,
                    evidence_id=time_phased_evidence_id,
                    created_at=created_at,
                )
    
    # Add evidence_id to time-phased report periods if evidence was emitted
    if time_phased_evidence_id:
        for period in time_phased.periods:
            period["evidence_id"] = time_phased_evidence_id
    
    # Build evidence index (including core traceability evidence if provided)
    evidence_index: list[dict] = []
    core_assumptions: list[dict] = []
    core_findings: list[dict] = []
    if core_traceability is not None:
        core_assumptions, core_findings, core_evidence_ids = await _load_core_traceability_bundle(
            db, dataset_version_id=dataset_version_id, core_traceability=core_traceability
        )
        all_evidence_ids.extend(core_evidence_ids)

    all_evidence_ids = sorted(set([e for e in all_evidence_ids if isinstance(e, str) and e.strip()]))
    if all_evidence_ids:
        evidences = (
            await db.execute(
                select(EvidenceRecord)
                .where(EvidenceRecord.evidence_id.in_(all_evidence_ids))
                .where(EvidenceRecord.dataset_version_id == dataset_version_id)
                .order_by(EvidenceRecord.evidence_id.asc())
            )
        ).scalars().all()
        
        evidence_index = [
            {
                "evidence_id": e.evidence_id,
                "kind": e.kind,
                "engine_id": e.engine_id,
                "created_at": e.created_at.isoformat(),
            }
            for e in evidences
        ]
    
    # Build limitations
    limitations = [
        "Time-phased report is limited to the provided DatasetVersion",
        "Time-phased report only includes CostLines with valid dates in the specified date_field",
        "Period boundaries are calculated deterministically based on period_type",
        "Cost aggregation separates BOQ (estimated) and actual costs by kind field",
    ]
    
    # Assemble report sections
    sections = [
        section_time_phased_report(
            period_type=time_phased.period_type,
            periods=time_phased.periods,
            total_estimated_cost=str(time_phased.total_estimated_cost),
            total_actual_cost=str(time_phased.total_actual_cost),
            total_variance_amount=str(time_phased.total_variance_amount),
            total_variance_percentage=str(time_phased.total_variance_percentage),
            report_start_date=time_phased.report_start_date,
            report_end_date=time_phased.report_end_date,
        ),
        section_limitations_assumptions(
            limitations=limitations,
            assumptions=(
                {"core": {"assumptions": core_assumptions}, "report": assumptions_registry.to_dict()}
                if core_traceability is not None
                else assumptions_registry.to_dict()
            ),
        ),
    ]

    if core_traceability is not None:
        sections.append(
            section_core_traceability(
                dataset_version_id=dataset_version_id,
                core_engine_id=CORE_ENGINE_ID,
                assumptions_evidence_id=str(core_traceability.get("assumptions_evidence_id")),
                inputs_evidence_ids=list(core_traceability.get("inputs_evidence_ids") or []),
                findings=core_findings,
            )
        )

    if evidence_index:
        sections.append(section_evidence_index(evidence_index=evidence_index))
    
    return {
        "engine_id": "engine_construction_cost_intelligence",
        "engine_version": "v1",
        "report_type": "time_phased",
        "dataset_version_id": dataset_version_id,
        "run_id": run_id,
        "sections": sections,
    }


async def assemble_report(
    db: AsyncSession,
    *,
    dataset_version_id: str,
    run_id: str,
    report_type: str,
    parameters: dict,
    created_at: datetime | None = None,
    emit_evidence: bool = True,
) -> dict:
    """
    Main report assembly function.
    
    Routes to appropriate report assembler based on report_type.
    
    Args:
        db: Database session
        dataset_version_id: DatasetVersion identifier
        run_id: Run identifier
        report_type: Type of report ('cost_variance' or 'time_phased')
        parameters: Report parameters containing data and configuration
    
    Returns:
        Complete report dict
    
    Raises:
        MissingArtifactError: If required data is missing
        DatasetVersionMismatchError: If dataset_version_id mismatch
        ValueError: If report_type is invalid
    """
    if report_type == "cost_variance":
        # ComparisonResult should be passed as a dict that can be reconstructed,
        # or the comparison should be done before calling this function.
        # For now, we expect comparison_result to be a ComparisonResult object
        comparison_result = parameters.get("comparison_result")
        
        if comparison_result is None:
            raise MissingArtifactError("COMPARISON_RESULT_REQUIRED")
        
        if not isinstance(comparison_result, ComparisonResult):
            raise ValueError("comparison_result must be a ComparisonResult instance")
        
        tolerance_threshold = Decimal(str(parameters.get("tolerance_threshold", "5.0")))
        minor_threshold = Decimal(str(parameters.get("minor_threshold", "10.0")))
        moderate_threshold = Decimal(str(parameters.get("moderate_threshold", "25.0")))
        major_threshold = Decimal(str(parameters.get("major_threshold", "50.0")))
        category_field = parameters.get("category_field")
        evidence_ids = parameters.get("evidence_ids")
        core_traceability = parameters.get("core_traceability")
        boq_raw_record_id = parameters.get("boq_raw_record_id")
        actual_raw_record_id = parameters.get("actual_raw_record_id")
        persist_findings = parameters.get("persist_findings", True)
        
        return await assemble_cost_variance_report(
            db=db,
            dataset_version_id=dataset_version_id,
            run_id=run_id,
            comparison_result=comparison_result,
            tolerance_threshold=tolerance_threshold,
            minor_threshold=minor_threshold,
            moderate_threshold=moderate_threshold,
            major_threshold=major_threshold,
            category_field=category_field,
            evidence_ids=evidence_ids,
            core_traceability=core_traceability,
            boq_raw_record_id=boq_raw_record_id,
            actual_raw_record_id=actual_raw_record_id,
            created_at=created_at,
            emit_evidence=emit_evidence,
            persist_findings=persist_findings,
        )
    
    elif report_type == "time_phased":
        cost_lines = parameters.get("cost_lines")
        
        if cost_lines is None:
            raise MissingArtifactError("COST_LINES_REQUIRED")
        
        if not isinstance(cost_lines, list):
            raise ValueError("cost_lines must be a list")
        
        # Validate all are CostLine instances
        if not all(isinstance(line, CostLine) for line in cost_lines):
            raise ValueError("All items in cost_lines must be CostLine instances")
        
        period_type = parameters.get("period_type", "monthly")
        date_field = parameters.get("date_field", "date_recorded")
        include_item_details = parameters.get("include_item_details", False)
        start_date = parameters.get("start_date")
        end_date = parameters.get("end_date")
        prefer_total_cost = parameters.get("prefer_total_cost", True)
        evidence_ids = parameters.get("evidence_ids")
        core_traceability = parameters.get("core_traceability")
        raw_record_id = parameters.get("raw_record_id")
        persist_findings = parameters.get("persist_findings", True)
        
        return await assemble_time_phased_report(
            db=db,
            dataset_version_id=dataset_version_id,
            run_id=run_id,
            cost_lines=cost_lines,
            period_type=period_type,
            date_field=date_field,
            include_item_details=include_item_details,
            start_date=start_date,
            end_date=end_date,
            prefer_total_cost=prefer_total_cost,
            evidence_ids=evidence_ids,
            core_traceability=core_traceability,
            raw_record_id=raw_record_id,
            created_at=created_at,
            emit_evidence=emit_evidence,
            persist_findings=persist_findings,
        )
    
    else:
        raise ValueError(f"Invalid report_type: {report_type}. Must be 'cost_variance' or 'time_phased'")
