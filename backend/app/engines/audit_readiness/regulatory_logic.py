"""
Regulatory check logic for Audit Readiness Engine

Framework-agnostic implementation of regulatory readiness evaluation.
"""
from __future__ import annotations

from typing import Any

from backend.app.engines.audit_readiness.models.regulatory_checks import ControlGap, RegulatoryCheckResult


# Risk threshold definitions (framework-agnostic)
RISK_THRESHOLDS = {
    "critical": 0.8,  # 80%+ risk score
    "high": 0.6,      # 60-80% risk score
    "medium": 0.4,    # 40-60% risk score
    "low": 0.2,       # 20-40% risk score
    "none": 0.0,      # <20% risk score
}


def calculate_risk_score(controls_passing: int, controls_total: int, gap_severities: list[str]) -> float:
    """
    Calculate risk score based on control coverage and gap severities.
    
    Args:
        controls_passing: Number of controls passing
        controls_total: Total number of controls assessed
        gap_severities: List of gap severity levels ("critical", "high", "medium", "low")
    
    Returns:
        Risk score between 0.0 (lowest risk) and 1.0 (highest risk)
    """
    if controls_total == 0:
        return 1.0  # No controls assessed = maximum risk
    
    # Base score from control coverage
    coverage_score = 1.0 - (controls_passing / controls_total)
    
    # Severity multipliers
    severity_weights = {
        "critical": 1.0,
        "high": 0.75,
        "medium": 0.5,
        "low": 0.25,
    }
    
    # Calculate severity impact
    severity_impact = 0.0
    if gap_severities:
        total_weight = sum(severity_weights.get(s, 0.0) for s in gap_severities)
        max_possible_weight = len(gap_severities) * severity_weights["critical"]
        if max_possible_weight > 0:
            severity_impact = total_weight / max_possible_weight
    
    # Combine coverage and severity (weighted average)
    risk_score = (coverage_score * 0.6) + (severity_impact * 0.4)
    
    return min(1.0, max(0.0, risk_score))


def determine_risk_level(risk_score: float) -> str:
    """
    Determine risk level from risk score.
    
    Args:
        risk_score: Risk score between 0.0 and 1.0
    
    Returns:
        Risk level string
    """
    if risk_score >= RISK_THRESHOLDS["critical"]:
        return "critical"
    elif risk_score >= RISK_THRESHOLDS["high"]:
        return "high"
    elif risk_score >= RISK_THRESHOLDS["medium"]:
        return "medium"
    elif risk_score >= RISK_THRESHOLDS["low"]:
        return "low"
    else:
        return "none"


def determine_check_status(controls_passing: int, controls_total: int, risk_level: str) -> str:
    """
    Determine overall check status from control assessment and risk level.
    
    Args:
        controls_passing: Number of controls passing
        controls_total: Total number of controls assessed
        risk_level: Risk level string
    
    Returns:
        Check status: "ready", "not_ready", "partial", "unknown"
    """
    if controls_total == 0:
        return "unknown"
    
    pass_rate = controls_passing / controls_total
    
    if risk_level in ("critical", "high"):
        return "not_ready"
    elif risk_level == "medium" and pass_rate < 0.7:
        return "not_ready"
    elif risk_level == "medium" and pass_rate >= 0.7:
        return "partial"
    elif risk_level in ("low", "none") and pass_rate >= 0.9:
        return "ready"
    elif risk_level in ("low", "none") and pass_rate >= 0.7:
        return "partial"
    else:
        return "not_ready"


def evaluate_control_gaps(
    framework_id: str,
    control_catalog: dict[str, Any],
    evidence_map: dict[str, list[str]],
) -> list[ControlGap]:
    """
    Evaluate control gaps based on control catalog and available evidence.
    
    Args:
        framework_id: Regulatory framework identifier
        control_catalog: Control catalog structure (framework-agnostic)
        evidence_map: Map of control IDs to evidence IDs
    
    Returns:
        List of control gaps identified
    """
    gaps: list[ControlGap] = []
    
    # Extract controls from catalog (framework-agnostic structure)
    controls = control_catalog.get("controls", [])
    required_evidence_types = control_catalog.get("required_evidence_types", {})
    
    for control in controls:
        control_id = control.get("control_id", "")
        control_name = control.get("control_name", "")
        required_evidence = required_evidence_types.get(control_id, [])
        available_evidence = evidence_map.get(control_id, [])
        
        # Check for missing evidence
        missing_evidence = [ev for ev in required_evidence if ev not in available_evidence]
        
        # If no evidence available at all
        if not available_evidence and required_evidence:
            # For critical controls, use "missing" with critical severity
            # For non-critical controls, use "insufficient" with low severity
            if control.get("critical", False):
                gap_type = "missing"
                severity = "critical"
            else:
                gap_type = "insufficient"
                severity = "low"
            
            gaps.append(
                ControlGap(
                    control_id=control_id,
                    control_name=control_name,
                    gap_type=gap_type,
                    severity=severity,
                    description=f"Control {control_name} has no supporting evidence",
                    evidence_required=required_evidence,
                    remediation_guidance=control.get("remediation_guidance"),
                )
            )
        elif missing_evidence:
            # Determine gap type and severity
            if len(missing_evidence) == len(required_evidence):
                gap_type = "missing"
                severity = "critical" if control.get("critical", False) else "high"
            elif len(missing_evidence) > len(required_evidence) / 2:
                gap_type = "incomplete"
                severity = "high" if control.get("critical", False) else "medium"
            else:
                gap_type = "incomplete"
                severity = "medium" if control.get("critical", False) else "low"
            
            gaps.append(
                ControlGap(
                    control_id=control_id,
                    control_name=control_name,
                    gap_type=gap_type,
                    severity=severity,
                    description=f"Control {control_name} is missing required evidence: {', '.join(missing_evidence)}",
                    evidence_required=missing_evidence,
                    remediation_guidance=control.get("remediation_guidance"),
                )
            )
    
    return gaps


def assess_regulatory_readiness(
    framework_id: str,
    framework_name: str,
    framework_version: str,
    dataset_version_id: str,
    control_catalog: dict[str, Any],
    evidence_map: dict[str, list[str]],
    assessment_timestamp: str,
    metadata: dict[str, Any] | None = None,
) -> RegulatoryCheckResult:
    """
    Assess regulatory readiness for a framework.
    
    Args:
        framework_id: Regulatory framework identifier
        framework_name: Human-readable framework name
        framework_version: Framework version
        dataset_version_id: Dataset version ID
        control_catalog: Control catalog structure
        evidence_map: Map of control IDs to evidence IDs
        assessment_timestamp: ISO timestamp of assessment
        metadata: Additional metadata
    
    Returns:
        RegulatoryCheckResult with assessment details
    """
    # Evaluate control gaps
    gaps = evaluate_control_gaps(framework_id, control_catalog, evidence_map)
    
    # Count controls
    controls = control_catalog.get("controls", [])
    controls_total = len(controls)
    controls_failing = len(gaps)
    controls_passing = controls_total - controls_failing
    
    # Calculate risk metrics
    gap_severities = [gap.severity for gap in gaps]
    risk_score = calculate_risk_score(controls_passing, controls_total, gap_severities)
    risk_level = determine_risk_level(risk_score)
    check_status = determine_check_status(controls_passing, controls_total, risk_level)
    
    # Collect evidence IDs
    evidence_ids = []
    for evidence_list in evidence_map.values():
        evidence_ids.extend(evidence_list)
    evidence_ids = list(set(evidence_ids))  # Deduplicate
    
    return RegulatoryCheckResult(
        framework_id=framework_id,
        framework_name=framework_name,
        framework_version=framework_version,
        dataset_version_id=dataset_version_id,
        check_status=check_status,
        risk_level=risk_level,
        control_gaps=gaps,
        controls_assessed=controls_total,
        controls_passing=controls_passing,
        controls_failing=controls_failing,
        risk_score=risk_score,
        evidence_ids=evidence_ids,
        assessment_timestamp=assessment_timestamp,
        metadata=metadata or {},
    )

