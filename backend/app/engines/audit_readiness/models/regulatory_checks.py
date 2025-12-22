"""
Regulatory check result models for Audit Readiness Engine
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ControlGap:
    """Represents a gap in control implementation."""
    control_id: str
    control_name: str
    gap_type: str  # "missing", "incomplete", "insufficient"
    severity: str  # "critical", "high", "medium", "low"
    description: str
    evidence_required: list[str]
    remediation_guidance: str | None = None


@dataclass
class RegulatoryCheckResult:
    """Result of a regulatory framework readiness check."""
    framework_id: str
    framework_name: str
    framework_version: str
    dataset_version_id: str
    check_status: str  # "ready", "not_ready", "partial", "unknown"
    risk_level: str  # "critical", "high", "medium", "low", "none"
    control_gaps: list[ControlGap]
    controls_assessed: int
    controls_passing: int
    controls_failing: int
    risk_score: float  # 0.0 to 1.0
    evidence_ids: list[str]
    assessment_timestamp: str
    metadata: dict[str, Any]

