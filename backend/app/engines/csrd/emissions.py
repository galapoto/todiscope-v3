from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EmissionFactor:
    scope: str
    value: float
    unit: str
    source: str
    methodology: str


@dataclass(frozen=True)
class EmissionsResult:
    totals_tco2e: dict[str, float]
    factors: dict[str, EmissionFactor]
    assumptions: list[dict]


def _f(value: object, default: float = 0.0) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    return default


def calculate_emissions(*, dataset_version_id: str, esg: dict, parameters: dict) -> EmissionsResult:
    emissions = esg.get("emissions") if isinstance(esg.get("emissions"), dict) else {}
    activity = esg.get("activity") if isinstance(esg.get("activity"), dict) else {}

    totals = {
        "scope1": _f(emissions.get("scope1")),
        "scope2": _f(emissions.get("scope2")),
        "scope3": _f(emissions.get("scope3")),
    }

    assumptions: list[dict] = [
        {
            "id": "assumption_units",
            "description": "Emissions are expressed as metric tons CO2e (tCO2e).",
            "source": "Engine convention",
            "impact": "Ensures consistent aggregation across scopes.",
            "sensitivity": "Low - unit conversion is deterministic.",
        }
    ]

    if all(v == 0.0 for v in totals.values()) and activity:
        scope1 = activity.get("scope1") if isinstance(activity.get("scope1"), dict) else {}
        fuel_liters = _f(scope1.get("fuel_liters"))
        ef_kg_per_liter = _f(scope1.get("emission_factor_kgco2e_per_liter"), 2.68)
        totals["scope1"] = (fuel_liters * ef_kg_per_liter) / 1000.0

        scope2 = activity.get("scope2") if isinstance(activity.get("scope2"), dict) else {}
        electricity_kwh = _f(scope2.get("electricity_kwh"))
        ef_kg_per_kwh = _f(scope2.get("emission_factor_kgco2e_per_kwh"), 0.25)
        totals["scope2"] = (electricity_kwh * ef_kg_per_kwh) / 1000.0

        scope3 = activity.get("scope3") if isinstance(activity.get("scope3"), dict) else {}
        totals["scope3"] = _f(scope3.get("total_tco2e"))

        assumptions.append(
            {
                "id": "assumption_default_factors",
                "description": "Default emission factors used when not provided.",
                "source": "Config defaults (2.68 kgCO2e/L fuel; 0.25 kgCO2e/kWh electricity)",
                "impact": "Affects calculated emissions when activity data is used.",
                "sensitivity": "High - linear with factor selection.",
            }
        )

    scope2_method = str(parameters.get("scope2_method", "market-based"))
    factors: dict[str, EmissionFactor] = {
        "scope1": EmissionFactor(
            scope="scope1",
            value=totals["scope1"],
            unit="tCO2e",
            source=str(parameters.get("scope1_source", "reported_or_default")),
            methodology="direct",
        ),
        "scope2": EmissionFactor(
            scope="scope2",
            value=totals["scope2"],
            unit="tCO2e",
            source=str(parameters.get("scope2_source", "reported_or_default")),
            methodology=scope2_method,
        ),
        "scope3": EmissionFactor(
            scope="scope3",
            value=totals["scope3"],
            unit="tCO2e",
            source=str(parameters.get("scope3_source", "reported_or_default")),
            methodology="value_chain",
        ),
    }

    return EmissionsResult(totals_tco2e=totals, factors=factors, assumptions=assumptions)
