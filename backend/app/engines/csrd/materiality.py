from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Assumption:
    assumption_id: str
    description: str
    source: str
    impact: str
    sensitivity: str


@dataclass(frozen=True)
class MaterialFinding:
    stable_key: str
    category: str
    metric: str
    description: str
    value: float
    threshold: float
    is_material: bool
    financial_impact_eur: float
    impact_score: float
    confidence: str
    raw_record_hint: str | None = None


def _f(value: object, default: float = 0.0) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    return default


def assess_double_materiality(
    *,
    dataset_version_id: str,
    esg: dict,
    financial: dict,
    total_emissions_tco2e: float,
    parameters: dict,
) -> tuple[list[MaterialFinding], list[Assumption]]:
    revenue = _f(financial.get("revenue"))
    carbon_price = _f(parameters.get("carbon_price_eur_per_tco2e"), 100.0)
    financial_threshold_pct = _f(parameters.get("financial_materiality_threshold_pct"), 1.0) / 100.0
    board_diversity_min = _f(parameters.get("board_diversity_min"), 0.3)
    emissions_impact_threshold = _f(parameters.get("emissions_impact_threshold_tco2e"), 5000.0)

    assumptions: list[Assumption] = [
        Assumption(
            assumption_id="assumption_carbon_price",
            description="Carbon price used to translate emissions into financial exposure.",
            source="Config parameter carbon_price_eur_per_tco2e (default 100 EUR/tCO2e)",
            impact="Directly affects estimated financial exposure for emissions.",
            sensitivity="High - linear with carbon price.",
        )
    ]

    findings: list[MaterialFinding] = []

    estimated_exposure = total_emissions_tco2e * carbon_price
    financial_threshold = revenue * financial_threshold_pct
    is_financially_material = revenue > 0 and estimated_exposure >= financial_threshold
    impact_score = min(1.0, total_emissions_tco2e / max(1.0, emissions_impact_threshold))
    is_impact_material = total_emissions_tco2e >= emissions_impact_threshold
    is_material = bool(is_financially_material or is_impact_material)

    if total_emissions_tco2e > 0:
        findings.append(
            MaterialFinding(
                stable_key="materiality:emissions:total",
                category="emissions",
                metric="total_emissions_tco2e",
                description="Total operational and value chain emissions.",
                value=total_emissions_tco2e,
                threshold=emissions_impact_threshold,
                is_material=is_material,
                financial_impact_eur=estimated_exposure,
                impact_score=impact_score,
                confidence="medium",
                raw_record_hint="emissions",
            )
        )

    governance = esg.get("governance") if isinstance(esg.get("governance"), dict) else {}
    board_diversity = _f(governance.get("board_diversity"), default=1.0)
    if board_diversity < board_diversity_min:
        findings.append(
            MaterialFinding(
                stable_key="materiality:governance:board_diversity",
                category="governance",
                metric="board_diversity",
                description="Board diversity below governance threshold.",
                value=board_diversity,
                threshold=board_diversity_min,
                is_material=True,
                financial_impact_eur=_f(parameters.get("governance_risk_cost_eur"), 0.0),
                impact_score=1.0,
                confidence="medium",
                raw_record_hint="governance",
            )
        )

    esg_committee = governance.get("esg_committee")
    if esg_committee is not True:
        findings.append(
            MaterialFinding(
                stable_key="materiality:governance:esg_committee",
                category="governance",
                metric="esg_governance",
                description="Missing ESG governance committee.",
                value=0.0,
                threshold=1.0,
                is_material=True,
                financial_impact_eur=_f(parameters.get("governance_risk_cost_eur"), 0.0),
                impact_score=1.0,
                confidence="low",
                raw_record_hint="governance",
            )
        )

    opportunities: list[MaterialFinding] = []
    energy = esg.get("energy_consumption") if isinstance(esg.get("energy_consumption"), dict) else {}
    renewable_pct = _f(energy.get("renewable"), 0.0) / 100.0 if _f(energy.get("renewable"), 0.0) > 1.0 else _f(energy.get("renewable"), 0.0)
    renewable_target = _f(parameters.get("renewable_target_pct"), 0.5)
    if renewable_pct >= renewable_target and renewable_pct > 0:
        opportunities.append(
            MaterialFinding(
                stable_key="materiality:opportunity:renewables",
                category="opportunity",
                metric="renewable_share",
                description="High renewable energy share reduces transition risk.",
                value=renewable_pct,
                threshold=renewable_target,
                is_material=True,
                financial_impact_eur=_f(parameters.get("renewable_benefit_eur"), 0.0),
                impact_score=renewable_pct,
                confidence="low",
                raw_record_hint="energy_consumption",
            )
        )

    return findings + opportunities, assumptions
