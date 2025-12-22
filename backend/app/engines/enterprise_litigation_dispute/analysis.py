"""Core legal and financial dispute analysis algorithms."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _assumption_record(*, assumption_id: str, description: str, source: str, impact: str, sensitivity: str) -> dict[str, str]:
    return {
        "id": assumption_id,
        "description": description,
        "source": source,
        "impact": impact,
        "sensitivity": sensitivity,
    }


@dataclass(frozen=True)
class DamageAssessment:
    dataset_version_id: str
    total_claim_value: float
    gross_damages: float
    mitigation: float
    net_damage: float
    severity: str
    severity_score: float
    confidence: str
    assumptions: list[dict[str, str]]


@dataclass(frozen=True)
class LiabilityAssessment:
    dataset_version_id: str
    responsible_party: str
    responsibility_pct: float
    evidence_strength: float
    liability_strength: str
    confidence: str
    indicators: list[str]
    assumptions: list[dict[str, str]]


@dataclass(frozen=True)
class ScenarioComparison:
    dataset_version_id: str
    scenarios: list[dict[str, Any]]
    best_case: dict[str, Any] | None
    worst_case: dict[str, Any] | None
    total_probability: float
    assumptions: list[dict[str, str]]


@dataclass(frozen=True)
class LegalConsistencyCheck:
    dataset_version_id: str
    consistent: bool
    issues: list[str]
    confidence: str
    assumptions: list[dict[str, str]]


def quantify_damages(*, dataset_version_id: str, dispute_payload: dict[str, Any], assumptions: dict[str, Any]) -> DamageAssessment:
    damage_cfg = assumptions.get("damage") if isinstance(assumptions.get("damage"), dict) else {}
    recovery_rate = max(0.0, min(1.0, _safe_float(damage_cfg.get("recovery_rate"), 1.0)))
    thresholds_cfg = damage_cfg.get("severity_thresholds") if isinstance(damage_cfg.get("severity_thresholds"), dict) else {}
    high_threshold = max(1.0, _safe_float(thresholds_cfg.get("high"), 1_000_000.0))
    medium_threshold = max(0.0, _safe_float(thresholds_cfg.get("medium"), 250_000.0))

    claims = dispute_payload.get("claims") if isinstance(dispute_payload.get("claims"), list) else []
    total_claim_value = sum(_safe_float(claim.get("amount")) for claim in claims if isinstance(claim, dict))

    damages = dispute_payload.get("damages") if isinstance(dispute_payload.get("damages"), dict) else {}
    gross_compensatory = _safe_float(damages.get("compensatory"), 0.0)
    gross_punitive = _safe_float(damages.get("punitive"), 0.0)
    gross_damages = gross_compensatory + gross_punitive
    mitigation = _safe_float(damages.get("mitigation"), 0.0)
    net_damage = max(0.0, gross_damages - mitigation * recovery_rate)

    if net_damage >= high_threshold:
        severity = "high"
    elif net_damage >= medium_threshold:
        severity = "medium"
    else:
        severity = "low"

    severity_score = min(1.0, net_damage / max(1.0, high_threshold))
    confidence = "high" if net_damage > 0 and total_claim_value > 0 else "medium"

    assumptions_list = [
        _assumption_record(
            assumption_id="assumption_damage_recovery_rate",
            description="Mitigation offsets are scaled by an assumed recovery rate.",
            source=f"parameters.assumptions.damage.recovery_rate (default 1.0, provided {recovery_rate})",
            impact="Reduces net damage when mitigation actions are supported.",
            sensitivity="Medium - linear with mitigation activity.",
        ),
        _assumption_record(
            assumption_id="assumption_damage_severity_thresholds",
            description="Severity bands categorize urgency for litigation exposure.",
            source=f"parameters.assumptions.damage.severity_thresholds {thresholds_cfg}",
            impact="Guides whether the dispute is classified as low, medium, or high damage.",
            sensitivity="Low - only impacts labels, not numeric exposure.",
        ),
    ]

    return DamageAssessment(
        dataset_version_id=dataset_version_id,
        total_claim_value=total_claim_value,
        gross_damages=gross_damages,
        mitigation=mitigation,
        net_damage=net_damage,
        severity=severity,
        severity_score=severity_score,
        confidence=confidence,
        assumptions=assumptions_list,
    )


def assess_liability(*, dataset_version_id: str, dispute_payload: dict[str, Any], assumptions: dict[str, Any]) -> LiabilityAssessment:
    liability_cfg = assumptions.get("liability") if isinstance(assumptions.get("liability"), dict) else {}
    thresholds_cfg = liability_cfg.get("evidence_strength_thresholds") if isinstance(liability_cfg.get("evidence_strength_thresholds"), dict) else {}
    strong_threshold = _safe_float(thresholds_cfg.get("strong"), 0.75)
    weak_threshold = _safe_float(thresholds_cfg.get("weak"), 0.4)

    liability_section = dispute_payload.get("liability") if isinstance(dispute_payload.get("liability"), dict) else {}
    parties = liability_section.get("parties") if isinstance(liability_section.get("parties"), list) else []

    dominant_party = None
    highest_pct = -1.0
    for party in parties:
        if not isinstance(party, dict):
            continue
        pct = _safe_float(party.get("percent"), 0.0)
        if pct > highest_pct:
            highest_pct = pct
            dominant_party = party

    responsible_party = dominant_party.get("party") if dominant_party and isinstance(dominant_party.get("party"), str) else "undetermined"
    responsibility_pct = max(0.0, min(100.0, highest_pct if highest_pct >= 0 else 0.0))
    evidence_strength = _safe_float(dominant_party.get("evidence_strength")) if dominant_party else 0.0

    if evidence_strength >= strong_threshold:
        liability_strength = "strong"
    elif evidence_strength >= weak_threshold:
        liability_strength = "moderate"
    else:
        liability_strength = "weak"

    confidence = "high" if evidence_strength >= weak_threshold else "medium"
    indicators: list[str] = []
    if responsible_party != "undetermined":
        indicators.append(f"Dominant responsibility assigned to {responsible_party}")
    if liability_section.get("admissions"):
        indicators.append("Admissions recorded")
    if liability_section.get("regulations"):
        indicators.append("Regulatory references present")

    assumptions_list = [
        _assumption_record(
            assumption_id="assumption_liability_strength_threshold",
            description="Evidence strength thresholds determine liability classification.",
            source=f"parameters.assumptions.liability.evidence_strength_thresholds (defaults strong={strong_threshold}, weak={weak_threshold})",
            impact="Impacts the reported liability strength label.",
            sensitivity="Low - only affects wording, not numeric exposure.",
        ),
    ]

    return LiabilityAssessment(
        dataset_version_id=dataset_version_id,
        responsible_party=responsible_party,
        responsibility_pct=responsibility_pct,
        evidence_strength=evidence_strength,
        liability_strength=liability_strength,
        confidence=confidence,
        indicators=indicators,
        assumptions=assumptions_list,
    )


def compare_scenarios(*, dataset_version_id: str, dispute_payload: dict[str, Any], assumptions: dict[str, Any]) -> ScenarioComparison:
    scenario_cfg = assumptions.get("scenario") if isinstance(assumptions.get("scenario"), dict) else {}
    scenarios = dispute_payload.get("scenarios") if isinstance(dispute_payload.get("scenarios"), list) else []

    compiled: list[dict[str, Any]] = []
    total_probability = 0.0
    for scenario in scenarios:
        if not isinstance(scenario, dict):
            continue
        probability = max(0.0, min(1.0, _safe_float(scenario.get("probability"), 0.0)))
        expected_damages = max(0.0, _safe_float(scenario.get("expected_damages")))
        liability_multiplier = max(0.0, _safe_float(scenario.get("liability_multiplier"), 1.0))
        expected_loss = probability * expected_damages
        liability_exposure = expected_damages * liability_multiplier
        compiled.append(
            {
                "name": scenario.get("name", "unnamed"),
                "description": scenario.get("description"),
                "probability": probability,
                "expected_damages": expected_damages,
                "liability_multiplier": liability_multiplier,
                "expected_loss": expected_loss,
                "liability_exposure": liability_exposure,
            }
        )
        total_probability += probability

    best_case = min(compiled, key=lambda s: s["expected_loss"], default=None)
    worst_case = max(compiled, key=lambda s: s["expected_loss"], default=None)

    assumptions_list = [
        _assumption_record(
            assumption_id="assumption_scenario_probabilities",
            description="Scenario probabilities are treated as independent estimates of likelihood.",
            source=f"parameters.assumptions.scenario.probabilities (sum={total_probability:.3f})",
            impact="Drives expectation-weighted comparisons among scenarios.",
            sensitivity="Medium - probabilities directly weight the exposure metrics.",
        ),
        _assumption_record(
            assumption_id="assumption_liability_multipliers",
            description="Scenario-specific liability multipliers shape exposure estimates.",
            source="parameters.assumptions.scenario.liability_multiplier (defaults to 1.0 per scenario)",
            impact="Scales legal exposure relative to expected damages.",
            sensitivity="Low - heuristics only affect relative ranking.",
        ),
    ]

    return ScenarioComparison(
        dataset_version_id=dataset_version_id,
        scenarios=compiled,
        best_case=best_case,
        worst_case=worst_case,
        total_probability=total_probability,
        assumptions=assumptions_list,
    )


def evaluate_legal_consistency(*, dataset_version_id: str, dispute_payload: dict[str, Any], assumptions: dict[str, Any]) -> LegalConsistencyCheck:
    consistency_cfg = assumptions.get("legal_consistency") if isinstance(assumptions.get("legal_consistency"), dict) else {}
    completeness_requirements = consistency_cfg.get("completeness_requirements", ["statutes", "evidence"])

    legal_consistency = dispute_payload.get("legal_consistency") if isinstance(dispute_payload.get("legal_consistency"), dict) else {}
    conflicts = legal_consistency.get("conflicts") if isinstance(legal_consistency.get("conflicts"), list) else []
    missing_support = legal_consistency.get("missing_support") if isinstance(legal_consistency.get("missing_support"), list) else []

    issues: list[str] = []
    for conflict in conflicts:
        issues.append(f"Conflict: {conflict}")
    for missing in missing_support:
        issues.append(f"Lacking support: {missing}")

    consistent = len(issues) == 0
    confidence = "high" if consistent else "low"

    assumptions_list = [
        _assumption_record(
            assumption_id="assumption_legal_framework_completeness",
            description="Assumes the provided legal framework captures all relevant statutes and policies.",
            source=f"parameters.assumptions.legal_consistency.completeness_requirements {completeness_requirements}",
            impact="Missing statutes or policies may hide unresolved conflicts.",
            sensitivity="High - missing requirements degrade trust in the consistency check.",
        )
    ]

    return LegalConsistencyCheck(
        dataset_version_id=dataset_version_id,
        consistent=consistent,
        issues=issues,
        confidence=confidence,
        assumptions=assumptions_list,
    )


def damage_payload(assessment: DamageAssessment) -> dict[str, Any]:
    return {
        "dataset_version_id": assessment.dataset_version_id,
        "total_claim_value": assessment.total_claim_value,
        "gross_damages": assessment.gross_damages,
        "mitigation": assessment.mitigation,
        "net_damage": assessment.net_damage,
        "severity": assessment.severity,
        "severity_score": assessment.severity_score,
        "confidence": assessment.confidence,
        "assumptions": assessment.assumptions,
    }


def liability_payload(assessment: LiabilityAssessment) -> dict[str, Any]:
    return {
        "dataset_version_id": assessment.dataset_version_id,
        "responsible_party": assessment.responsible_party,
        "responsibility_pct": assessment.responsibility_pct,
        "evidence_strength": assessment.evidence_strength,
        "liability_strength": assessment.liability_strength,
        "confidence": assessment.confidence,
        "indicators": assessment.indicators,
        "assumptions": assessment.assumptions,
    }


def scenario_payload(assessment: ScenarioComparison) -> dict[str, Any]:
    return {
        "dataset_version_id": assessment.dataset_version_id,
        "scenarios": assessment.scenarios,
        "best_case": assessment.best_case,
        "worst_case": assessment.worst_case,
        "total_probability": assessment.total_probability,
        "assumptions": assessment.assumptions,
    }


def legal_consistency_payload(assessment: LegalConsistencyCheck) -> dict[str, Any]:
    return {
        "dataset_version_id": assessment.dataset_version_id,
        "consistent": assessment.consistent,
        "issues": assessment.issues,
        "confidence": assessment.confidence,
        "assumptions": assessment.assumptions,
    }
