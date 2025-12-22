DatasetVersion: 1.1.0
ReleaseDate: 2025-01-XX
Author: Documentation Team (Agent 3)
Last Updated: 2025-01-XX (Remediation: Multi-Currency & RBAC)

# Enterprise Distressed Asset & Debt Stress Engine — Documentation

## 1. Purpose & Overview

The **Enterprise Distressed Asset & Debt Stress Engine** quantifies net debt exposure and simulates stress scenarios over a portfolio of assets and liabilities. It is designed as a **modular monolith component** inside TodiScope and integrates tightly with:

- **DatasetVersioning** — every run is bound to a specific `DatasetVersion`.
- **Normalization** — inputs come from normalized financial records.
- **Core evidence & findings services** — exposure and stress results are persisted immutably and linked as findings.

High-level goals:
- Model **current debt exposure** including collateral and distressed asset recovery.
- Apply **stress test scenarios** (interest rate shocks, collateral devaluation, recovery degradation, default risk increments).
- Produce **material findings** and evidence for auditability and reporting.
- Support **scenario creation, execution, storage, and replay** with full immutability.

Code location:
- Engine package: `backend/app/engines/enterprise_distressed_asset_debt_stress/`
- HTTP router: `engine.py`
- Run entrypoint: `run.py`
- Core modeling logic: `models.py`
- Scenario creation: `scenario_creation.py`
- Scenario execution: `scenario_execution.py`
- Scenario storage & replay: `scenario_storage.py`
- Reporting helpers: `reporting.py`

---

## 2. Core Debt Exposure Modeling

**File:** `models.py`

### 2.1 Distressed assets

```python
@dataclass(frozen=True)
class DistressedAsset:
    name: str | None
    value: float
    recovery_rate_pct: float

    @property
    def recovery_value(self) -> float:
        return self.value * (self.recovery_rate_pct / 100.0)
```

Distressed assets are modeled as immutable dataclasses with a `value` and a percentage recovery rate. The helper `_extract_distressed_assets()` collects them from either the normalized payload or the `financial` block, handling field variants and non-dict entries gracefully.

### 2.2 Debt exposure

The main exposure type is `DebtExposure`:

```python
@dataclass(frozen=True)
class DebtExposure:
    total_outstanding: float
    interest_rate_pct: float
    interest_payment: float
    collateral_value: float
    collateral_shortfall: float
    collateral_coverage_ratio: float
    assets_value: float
    leverage_ratio: float
    distressed_asset_value: float
    distressed_asset_recovery: float
    distressed_asset_recovery_ratio: float
    distressed_asset_count: int
    net_exposure_after_recovery: float

    def to_payload(self) -> dict[str, float | int]:
        ...
```

Key derived metrics:
- `total_outstanding` — aggregate principal across all debt.
- `interest_rate_pct` — possibly weighted average across instruments.
- `interest_payment` — annual interest = `total_outstanding * rate/100`.
- `collateral_value` and `collateral_shortfall` — coverage vs outstanding.
- `collateral_coverage_ratio` — `collateral_value / total_outstanding`.
- `assets_value` and `leverage_ratio` — debt-to-assets ratio.
- `distressed_asset_value`, `distressed_asset_recovery`, `distressed_asset_recovery_ratio`.
- `net_exposure_after_recovery` — debt net of collateral and distressed asset recoveries.

### 2.3 Aggregating debt instruments

`calculate_debt_exposure()` handles both simple and complex capital structures:

```python
def calculate_debt_exposure(*, normalized_payload: dict) -> DebtExposure:
    financial = normalized_payload.get("financial") or {}
    debt = financial.get("debt") or {}

    instruments = debt.get("instruments") if isinstance(debt.get("instruments"), list) else []

    if instruments:
        total_outstanding, interest_rate_pct, collateral_from_instruments = _aggregate_debt_instruments(instruments)
        collateral_value = _as_float(
            debt.get("collateral_value") or debt.get("collateral") or debt.get("security_value"),
            collateral_from_instruments,
        )
    else:
        total_outstanding = _as_float(
            debt.get("total_outstanding") or debt.get("outstanding") or debt.get("principal")
        )
        interest_rate_pct = _as_float(
            debt.get("interest_rate_pct") or debt.get("interest_rate") or debt.get("rate_pct"),
            0.0,
        )
        collateral_value = _as_float(
            debt.get("collateral_value") or debt.get("collateral") or debt.get("security_value"),
            0.0,
        )

    assets_value = _normalize_assets_value(
        financial.get("assets") or financial.get("asset_value") or normalized_payload.get("assets")
    )
    distressed_assets = _extract_distressed_assets(normalized_payload, financial)
    ...
    return DebtExposure(...)
```

`_aggregate_debt_instruments()` calculates:
- `total_outstanding` — sum of valid principals.
- `interest_rate_pct` — weighted average by principal.
- `collateral_value` — sum of collateral fields per instrument.

Invalid instruments (non-dict, non-positive principal, negative rates) are skipped or normalized to safe defaults.

**Edge cases tested** in `backend/tests/engine_distressed_asset_debt_stress/test_debt_exposure_edge_cases.py` and `test_models.py`:
- No debt instruments, or zero outstanding.
- Debt only in `financial["debt"]` vs multiple instruments.
- Missing/negative collateral.
- Assets from `financial["assets"]`, `asset_value`, or top-level `assets`.
- Presence/absence of distressed assets.

---

## 3. Stress Test Simulation Logic

### 3.1 Scenario definitions

```python
@dataclass(frozen=True)
class StressTestScenario:
    scenario_id: str
    description: str
    interest_rate_delta_pct: float
    collateral_market_impact_pct: float
    recovery_degradation_pct: float
    default_risk_increment_pct: float
```

`DEFAULT_STRESS_SCENARIOS` defines three canonical scenarios:
- `interest_rate_spike`
- `market_crash`
- `default_wave`

Each encodes different combinations of interest rate shocks, collateral markdowns, recovery degradation, and default risk increments.

### 3.2 Applying a scenario

```python
def apply_stress_scenario(
    *,
    exposure: DebtExposure,
    base_net_exposure: float,
    scenario: StressTestScenario,
) -> StressTestResult:
    adjusted_interest_rate_pct = exposure.interest_rate_pct + scenario.interest_rate_delta_pct
    interest_payment = exposure.total_outstanding * (adjusted_interest_rate_pct / 100.0)
    adjusted_collateral_value = max(0.0, exposure.collateral_value * (1.0 + scenario.collateral_market_impact_pct))
    adjusted_distressed_asset_value = max(0.0, exposure.distressed_asset_value * (1.0 + scenario.collateral_market_impact_pct))
    adjusted_distressed_asset_recovery = max(
        0.0, exposure.distressed_asset_recovery * (1.0 + scenario.recovery_degradation_pct)
    )
    ...
    default_risk_buffer = max(0.0, exposure.total_outstanding * scenario.default_risk_increment_pct)
    net_exposure = scenario_net_exposure + default_risk_buffer
    loss_estimate = max(0.0, net_exposure - base_net_exposure)
    impact_score = min(1.0, loss_estimate / max(1.0, exposure.total_outstanding))
    return StressTestResult(...)
```

The resulting `StressTestResult` is immutable and exposes a `.to_payload()` method for serialization.

**Unit tests** (see `test_models.py` and `test_debt_exposure_edge_cases.py`) validate:
- Correct sensitivity of interest payment to rate shocks.
- Collateral and distressed asset losses under different scenario parameters.
- Non‑negative adjusted values and loss estimates under extreme stress.

---

## 4. Scenario Management & Execution

### 4.1 Scenario creation (`scenario_creation.py`)

Key entry point:

```python
def create_scenario(
    *,
    dataset_version_id: str,
    scenario_name: str,
    description: str,
    time_horizon_months: int,
    assumptions: dict[str, Any],
    created_by: str | None = None,
) -> Scenario:
    ...
```

Validation rules:
- `dataset_version_id` — **required**, non-empty string. On failure: `ScenarioInvalidError("DATASET_VERSION_ID_REQUIRED")`.
- `scenario_name` — **required**, non-empty.
- `time_horizon_months` — integer in `[6, 24]`. Otherwise: `TIME_HORIZON_MUST_BE_6_TO_24_MONTHS`.

Assumptions are parsed into an immutable `StressAssumptions` dataclass by `_parse_assumptions()`, enforcing ranges:
- `revenue_change_factor ∈ [0, 2]`
- `cost_change_factor ∈ [0, 3]`
- `interest_rate_change_factor ∈ [0, 5]`
- `liquidity_shock_factor ∈ [0, 1]`
- `market_value_depreciation_factor ∈ [0, 1]`

A deterministic `scenario_id` is generated via `deterministic_id(dataset_version_id, "scenario", scenario_name, ...)`, ensuring idempotent recreation given the same inputs.

`create_default_stress_scenarios()` builds a standard set of `mild_stress`, `moderate_stress`, and `severe_stress` scenarios for a DatasetVersion.

### 4.2 Scenario execution (`scenario_execution.py`)

Main orchestration function:

```python
def execute_scenario(
    *,
    scenario: Scenario,
    financial_data: dict[str, Any],
    analysis_date: date,
    executed_by: str | None = None,
) -> ScenarioExecution:
    ...
```

Execution steps per period:
1. Extract base metrics:
   - `base_exposure` from balance sheet (`total_assets`/`current_assets`).
   - `base_cash` from `cash_and_equivalents`.
   - `base_revenue` and `base_costs` from income statement.
   - `debt_instruments` from `financial_data["debt"]["instruments"]`.
2. For each month from `1` to `scenario.time_horizon_months`:
   - Compute `period_date` relative to `analysis_date`.
   - Compute `ExposureChange` via `_calculate_exposure_changes` (applying compounding market depreciation).
   - Compute `CashShortfall` entries via `_calculate_cash_shortfalls` (operating and debt service shortfalls).
   - Compute `DebtServiceCoverage` metrics via `_calculate_debt_service_coverage` (DSCR, interest, principal coverage).
   - Accumulate `cumulative_exposure_change` and `cumulative_cash_shortfall`.
3. Aggregate summary via `_generate_summary()`:
   - Total exposure change and total cash shortfall.
   - Count of periods with shortfalls.
   - Count of periods with insufficient coverage.
   - Average and minimum DSCR.

The result is a `ScenarioExecution` dataclass:
- `execution_id` is deterministic via `deterministic_id(scenario_id, "execution", analysis_date.isoformat())`.
- `dataset_version_id` equals the scenario’s DatasetVersion.
- `assumptions_used` stores the exact `StressAssumptions` used.
- `period_results` holds per‑month results.
- `summary` captures aggregated metrics.

Errors during execution are wrapped in `ScenarioExecutionError("SCENARIO_EXECUTION_FAILED: ...")`.

### 4.3 Scenario storage & replay (`scenario_storage.py`)

Scenarios and executions are stored immutably as `EvidenceRecord`s using deterministic evidence IDs:

```python
evidence_id = deterministic_evidence_id(
    dataset_version_id=scenario.dataset_version_id,
    engine_id="engine_enterprise_distressed_asset_debt_stress",
    kind="scenario",
    stable_key=scenario.scenario_id,
)
```

- `store_scenario()` / `store_scenario_execution()` enforce immutability:
  - On existing evidence, they compare `dataset_version_id`, `engine_id`, `kind`, and payload.
  - On any mismatch, they raise `ImmutableConflictError` (`SCENARIO_*` or `EXECUTION_*` codes).

Retrieval APIs:
- `retrieve_scenario(db, scenario_id, dataset_version_id)`
- `retrieve_scenario_execution(db, execution_id, dataset_version_id)`

Both:
- Compute the same deterministic evidence ID.
- Enforce dataset_version_id equality.
- Convert payloads back into immutable dataclasses via `_payload_to_scenario()` / `_payload_to_execution()`.

Replay API:

```python
async def replay_scenario(
    db: AsyncSession,
    *,
    scenario_id: str,
    dataset_version_id: str,
    financial_data: dict[str, Any],
    analysis_date: str,
    executed_by: str | None = None,
) -> ScenarioExecution:
    scenario = await retrieve_scenario(...)
    analysis_date_obj = parsed_or_today(analysis_date)
    execution = execute_scenario(...)
    return execution
```

This guarantees that replays use the **same stored assumptions** while allowing new financial data.

---

## 5. Engine Run & Platform Integration

### 5.1 DatasetVersion & normalization

**File:** `run.py`

Entry point:

```python
async def run_engine(*, dataset_version_id: object, started_at: object, parameters: dict | None = None) -> dict:
    install_immutability_guards()
    dv_id = _validate_dataset_version_id(dataset_version_id)
    started = _parse_started_at(started_at)
    params = dict(parameters) if isinstance(parameters, dict) else {}

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        dv = await db.scalar(select(DatasetVersion).where(DatasetVersion.id == dv_id))
        if dv is None:
            raise DatasetVersionNotFoundError("DATASET_VERSION_NOT_FOUND")

        normalized_records = (
            await db.scalars(
                select(NormalizedRecord)
                .where(NormalizedRecord.dataset_version_id == dv_id)
                .order_by(NormalizedRecord.normalized_at.asc())
            )
        ).all()
        if not normalized_records:
            raise NormalizedRecordMissingError("NORMALIZED_RECORD_REQUIRED")
        normalized_record = normalized_records[0]
        raw_id = normalized_record.raw_record_id
        ...
```

Rules enforced:
- `DatasetVersionMissingError` and `DatasetVersionInvalidError` for missing/invalid IDs.
- `DatasetVersionNotFoundError` if the DV is not in the database.
- `NormalizedRecordMissingError` if there are no normalized records for the DV.
- Only **normalized** payloads are used to derive exposure (`calculate_debt_exposure`).

### 5.2 Evidence & findings (immutability + linkage)

The engine uses strict wrappers around core evidence/finding services:

```python
async def _strict_create_evidence(...)
async def _strict_create_finding(...)
async def _strict_link(...)
```

Behaviors:
- If an evidence/finding/link with the same ID already exists:
  - Validates `dataset_version_id`, `engine_id` (for evidence), `kind`, and payload.
  - On mismatch → logs a `DISTRESSED_DEBT_IMMUTABLE_CONFLICT` and raises `ImmutableConflictError`.
  - On exact match → returns the existing record (idempotency).

During a run, the engine:
1. Computes `DebtExposure` from the first normalized record.
2. Resolves stress scenarios via `_resolve_scenarios(params)` (default + overrides).
3. Applies each scenario using `apply_stress_scenario(...)` to get `StressTestResult` objects.
4. Builds **material findings** via `_build_material_findings(...)` (for net exposure and each stress scenario).
5. Persists:
   - Base exposure evidence (`kind="debt_exposure"`).
   - Per-scenario stress evidence (`kind="stress_test"`).
6. For each finding:
   - Creates a core `FindingRecord` via `_strict_create_finding` with `raw_record_id` from the normalized record.
   - Links it to the appropriate `EvidenceRecord` via `_strict_link` and `FindingEvidenceLink`.

The returned response includes:

```jsonc
{
  "dataset_version_id": "...",
  "started_at": "...",
  "debt_exposure_evidence_id": "...",
  "stress_test_evidence_ids": { "scenario_id": "evidence_id", ... },
  "material_findings": [ ... ],
  "report": { ... },
  "assumptions": [ ... ]
}
```

### 5.3 HTTP endpoint

**File:** `engine.py`

```python
router = APIRouter(prefix="/api/v3/engines/distressed-asset-debt-stress", tags=[ENGINE_ID])

@router.post("/run")
async def run_endpoint(payload: dict) -> dict:
    if not is_engine_enabled(ENGINE_ID):
        raise HTTPException(status_code=503, detail="ENGINE_DISABLED: ...")

    from backend.app.engines.enterprise_distressed_asset_debt_stress.run import run_engine
    ...
    try:
        return await run_engine(...)
    except DatasetVersionMissingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    ...
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"ENGINE_RUN_FAILED: {type(exc).__name__}: {exc}") from exc
```

Error mapping:
- 400 — missing/invalid dataset version or started_at.
- 404 — DatasetVersion not found.
- 409 — normalized record missing or immutability conflicts.
- 503 — engine disabled via kill switch.
- 500 — unexpected internal errors.

---

## 6. How to Run Stress Tests & Interpret Results

### 6.1 Via HTTP API

1. Ensure engine is enabled:
   - Set `TODISCOPE_ENABLED_ENGINES` to include `engine_distressed_asset_debt_stress`.
2. Ingest and normalize financial data for a `DatasetVersion`.
3. Call the endpoint:

```http
POST /api/v3/engines/distressed-asset-debt-stress/run
Content-Type: application/json

{
  "dataset_version_id": "dv-example-1",
  "started_at": "2025-01-01T00:00:00Z",
  "parameters": {
    "net_exposure_materiality_threshold_pct": 0.2,
    "stress_loss_materiality_threshold_pct": 0.05,
    "stress_scenarios": [
      {
        "scenario_id": "interest_rate_spike",
        "interest_rate_delta_pct": 3.0
      }
    ]
  }
}
```

4. Inspect the response for:
   - `debt_exposure_evidence_id` — pointer to the base exposure evidence.
   - `stress_test_evidence_ids` — map from scenario IDs to evidence IDs.
   - `material_findings` — net exposure and per-scenario loss findings with thresholds, materiality flags, and impact scores.
   - `report` — contains `metadata`, `debt_exposure`, `stress_tests`, `assumptions`.

### 6.2 Via Python (direct)

For analytical workflows or unit tests, you can call modeling functions directly:

```python
from backend.app.engines.enterprise_distressed_asset_debt_stress.models import (
    calculate_debt_exposure,
    apply_stress_scenario,
    DEFAULT_STRESS_SCENARIOS,
)

exposure = calculate_debt_exposure(normalized_payload=normalized_record.payload)

scenario = DEFAULT_STRESS_SCENARIOS[0]
result = apply_stress_scenario(
    exposure=exposure,
    base_net_exposure=exposure.net_exposure_after_recovery,
    scenario=scenario,
)

print(result.to_payload())
```

For scenario management and execution:

```python
from datetime import date
from backend.app.engines.enterprise_distressed_asset_debt_stress.scenario_creation import create_scenario
from backend.app.engines.enterprise_distressed_asset_debt_stress.scenario_execution import execute_scenario

scenario = create_scenario(
    dataset_version_id="dv_123",
    scenario_name="moderate_stress",
    description="Moderate stress scenario",
    time_horizon_months=12,
    assumptions={
        "revenue_change_factor": 0.8,
        "cost_change_factor": 1.15,
        "interest_rate_change_factor": 1.3,
        "liquidity_shock_factor": 0.85,
        "market_value_depreciation_factor": 0.85,
    },
)

execution = execute_scenario(
    scenario=scenario,
    financial_data={"balance_sheet": {...}, "income_statement": {...}, "debt": {...}},
    analysis_date=date(2025, 1, 1),
)
```

### 6.3 Interpreting outputs

- **Net exposure after recovery** (`debt_exposure.net_exposure_after_recovery`):
  - High values relative to total outstanding indicate insufficient collateral/recovery.
- **Stress test loss estimates** (`StressTestResult.loss_estimate`):
  - Compare against `stress_loss_materiality_threshold_pct * total_outstanding` to judge materiality.
- **Impact scores** (`StressTestResult.impact_score`):
  - Normalized [0,1] metric; values near 1.0 indicate severe stress impact.
- **Findings**:
  - `category == "debt_exposure"` — baseline risk.
  - `category == "stress_test"` — scenario‑specific tail risk.
- **Assumptions**:
  - The `assumptions` list in the response documents modeling assumptions and any scenario overrides; these are also persisted into evidence.

---

## 7. Unit Tests & Coverage (Summary)

Existing tests for this engine live in `backend/tests/engine_distressed_asset_debt_stress/` and (for enterprise scenario tooling) `backend/tests/engine_enterprise_distressed_asset_debt_stress/`. They cover:

- **Debt exposure modeling**: `test_models.py`, `test_debt_exposure_edge_cases.py`.
- **Engine run & HTTP integration**: `test_engine.py`.
- **DatasetVersion & immutability**: `test_dataset_version_immutability.py`.
- **Scenario management, execution, storage, replay, reporting**: scenario‑focused tests under the enterprise test package (scenario creation, execution, replay, reporting) validate:
  - Scenario validation and deterministic IDs.
  - Period‑by‑period execution and summary metrics.
  - Storage/replay idempotency and immutability.
  - Reporting output structure and numerical consistency.

All tests respect:
- **DatasetVersioning** — each test creates or uses an explicit `DatasetVersion` ID, often via the shared `sqlite_db` fixture.
- **Immutability** — tests assert that conflicting writes raise `ImmutableConflictError` and that evidence/finding records are reused when payloads match.

To run just this engine’s tests:

```bash
cd backend
pytest tests/engine_distressed_asset_debt_stress -q
```

This documentation should be updated whenever the engine’s debt exposure model, stress logic, or scenario lifecycle semantics change, ensuring it remains aligned with code and tests.
