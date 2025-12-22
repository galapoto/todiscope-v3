from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import resource
import time
import tracemalloc

from backend.app.engines.enterprise_distressed_asset_debt_stress.models import (
    DEFAULT_STRESS_SCENARIOS,
    StressTestScenario,
    apply_stress_scenario,
    calculate_debt_exposure,
)


@dataclass(frozen=True)
class ModelingResult:
    instruments: int
    distressed_assets: int
    scenarios: int
    iterations: int
    duration_ms: float
    cpu_ms: float
    max_rss_kb: int
    peak_alloc_kb: int


def _build_payload(*, instruments: int, distressed_assets: int) -> dict:
    instrument_rows = []
    for idx in range(instruments):
        base = 50000 + idx * 250
        instrument_rows.append(
            {
                "principal": base,
                "interest_rate_pct": 3.75 + (idx % 5) * 0.2,
                "collateral_value": base * 0.65,
                "currency": "USD",
            }
        )

    distressed_rows = []
    for idx in range(distressed_assets):
        value = 15000 + idx * 200
        distressed_rows.append(
            {"name": f"asset-{idx}", "value": value, "recovery_rate_pct": 40 + (idx % 4) * 5}
        )

    return {
        "financial": {
            "debt": {
                "instruments": instrument_rows,
                "interest_rate_pct": 4.1,
            },
            "assets": {"total": instruments * 250000},
        },
        "distressed_assets": distressed_rows,
        "currency": "USD",
    }


def _expand_scenarios(count: int) -> list[StressTestScenario]:
    scenarios = list(DEFAULT_STRESS_SCENARIOS)
    if count <= len(scenarios):
        return scenarios[:count]
    while len(scenarios) < count:
        base = scenarios[len(scenarios) % len(DEFAULT_STRESS_SCENARIOS)]
        suffix = len(scenarios) + 1
        scenarios.append(
            StressTestScenario(
                scenario_id=f"{base.scenario_id}_x{suffix}",
                description=f"{base.description} (variant {suffix})",
                interest_rate_delta_pct=base.interest_rate_delta_pct + 0.1,
                collateral_market_impact_pct=base.collateral_market_impact_pct - 0.01,
                recovery_degradation_pct=base.recovery_degradation_pct - 0.01,
                default_risk_increment_pct=base.default_risk_increment_pct + 0.002,
            )
        )
    return scenarios


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark stress test modeling performance.")
    parser.add_argument("--instruments", type=int, default=2500)
    parser.add_argument("--distressed-assets", type=int, default=500)
    parser.add_argument("--scenarios", type=int, default=6)
    parser.add_argument("--iterations", type=int, default=10)
    parser.add_argument("--output", default="", help="Optional path to write JSON output.")
    args = parser.parse_args()

    payload = _build_payload(instruments=args.instruments, distressed_assets=args.distressed_assets)
    scenarios = _expand_scenarios(args.scenarios)

    tracemalloc.start()
    start_wall = time.perf_counter()
    start_cpu = time.process_time()
    for _ in range(args.iterations):
        exposure = calculate_debt_exposure(normalized_payload=payload)
        base_net = exposure.net_exposure_after_recovery
        for scenario in scenarios:
            apply_stress_scenario(exposure=exposure, base_net_exposure=base_net, scenario=scenario)
    cpu_ms = (time.process_time() - start_cpu) * 1000
    duration_ms = (time.perf_counter() - start_wall) * 1000
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    result = ModelingResult(
        instruments=args.instruments,
        distressed_assets=args.distressed_assets,
        scenarios=len(scenarios),
        iterations=args.iterations,
        duration_ms=duration_ms,
        cpu_ms=cpu_ms,
        max_rss_kb=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        peak_alloc_kb=int(peak / 1024),
    )
    payload_out = json.dumps(asdict(result), indent=2, sort_keys=True)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(payload_out)
    else:
        print(payload_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
