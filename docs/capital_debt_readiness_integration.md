# Capital & Debt Readiness Integration Notes

## Immutability guard hardening
- `_strict_create_evidence()` now normalizes `created_at` timestamps and enforces matching `(dataset_version_id, engine_id, kind)` to avoid evidence collisions; any deviation raises `ImmutableConflictError` variants (`backend/app/engines/csrd/run.py:61-100`, `backend/app/engines/enterprise_capital_debt_readiness/run.py:60-92`).
- Payload differences still raise `IMMUTABLE_EVIDENCE_MISMATCH`, and created-at drift now triggers `IMMUTABLE_EVIDENCE_CREATED_AT_MISMATCH`, keeping reruns deterministic and append-only.
- Tests covering payload and timestamp conflicts live in `backend/tests/engine_csrd/test_csrd_strict_immutability.py:11-74`.

## Time-horizon scaling for DSCR/interest coverage
- Debt-service analyses now annualize the scheduled payments before applying the horizon scale factor, ensuring DSCR and interest coverage compare like-for-like time horizons (`backend/app/engines/enterprise_capital_debt_readiness/debt_service.py:214-339`).
- Annual cash/EBITDA inputs are multiplied by `horizon_months / 12`, the same factor applied to annualized debt and interest totals, with the assumption recorded (`backend/app/engines/enterprise_capital_debt_readiness/debt_service.py:254-329`).
- Horizon-scaling assumptions are documented alongside the payload so future readers understand why these metrics are proportional to the horizon.

## Executive reporting
- Executive-level reports now generated via `backend/app/engines/enterprise_capital_debt_readiness/reporting.py`, combining readiness scores, risk assessment components, and scenario insights with linked findings and evidence for traceability.
- Reports surface scenario-based insights for base/best/worst cases, quantify cross-engine exposure, and document the data sources and evidence IDs for enterprise review.

## Configuration & assumptions
- Default skip for horizon scaling and other controls are centralized in `backend/app/engines/enterprise_capital_debt_readiness/config/default_assumptions.json` and consumed through `resolved_assumptions()` so parameter overrides remain straightforward (`backend/app/engines/enterprise_capital_debt_readiness/assumptions.py:1-31`).
- Configurable keys include `assumptions.debt_service.horizon_months`, `assumptions.capital_adequacy.*`, and `assumptions.cash_available`, all of which show up in the evidence payload for traceability.

## Production readiness
- The hardened guards and horizon scaling changes are already covered by the existing `pytest -q` run, ensuring no regressions before deployment (see `backend/tests/engine_csrd/test_csrd_strict_immutability.py` and the debt service horizon scaling suite).
