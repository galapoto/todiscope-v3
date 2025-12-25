# TODISCOPE V3 — FULL OPERATIONAL & VISIBILITY AUDIT

Audit date: 2025-12-24  
Repo: `/home/vitus-idi/Documents/todiscope-v3`  
Revision: `6cd51c7`  
Frontend: Next.js (`frontend/web`) on `http://localhost:3400`  
Backend: FastAPI (`backend`) on `http://localhost:8400`  

## Executive Summary (Verdict)
**VERDICT: FAIL (operational parity not yet proven end-to-end)**  

The platform is **visible and navigable** end-to-end (engines → lifecycle → pages), and key wiring exists for Import/Normalize/Calculate/Report/Audit. However, several **audit-gate requirements** are not satisfied yet:

- **Stage enforcement is not guaranteed**: Calculate can run without Normalize; Report can be attempted without a verified “completed calculation” state (beyond presence of `run_id`).
- **Audit stage does not yet prove replay/diff**: No UI for selecting historical runs, replaying, or comparing runs.
- **Dataset metadata is limited**: Import stage displays `dataset_version_id` but does not consistently surface source/timestamp/lineage metadata.
- **Per-engine semantics are still generic**: Engine landing pages explain lifecycle and inputs/outputs, but do not yet show engine-specific data contract (assumptions/rules/scenarios) in a verifiable, inspectable way.

This audit strictly evaluates **visible + clickable + runnable + inspectable** behavior; anything that cannot be proven in the UI is treated as failing.

## Evidence / How This Audit Was Verified
- Build + typecheck: `npm -C frontend/web run build` (PASS)
- Lint: `npm -C frontend/web run lint` (PASS with warnings)
- Engine endpoint availability probe (when backend started with engines enabled):
  - `npm -C frontend/web run check:engines -- --base http://localhost:8400 --all`
  - Note: Some engines legitimately do not implement `/report`; the checker treats those as “not required”.
- Frontend↔backend parity assertion (engine registry vs backend enabled engines + non-404 run endpoints):
  - `npm -C frontend/web run check:parity -- --base http://localhost:8400`
  - PASS output confirms **12/12** backend engines are represented in the frontend registry and expose non-404 `/run` endpoints (405 indicates POST-only).
  - Example output (abridged):
    - `Frontend engines (registry): 12`
    - `Backend engines (enabled): 12`
    - `OK: backend-enabled engines are represented in frontend registry and have non-404 run endpoints.`

---

## 1. GLOBAL PLATFORM AUDIT

### 1.1 Application Entry & Routing
- [⚠️] Application loads without console or network errors  
  - Verified: build/typecheck passes. Dev-server filesystem cache flakiness mitigated by forcing webpack dev cache to memory (`frontend/web/next.config.ts`) and avoiding unconditional `.next` deletion (`start_frontend.sh`).
- [✅] No dead routes or placeholder pages  
  - Verified via Next build route list (includes `/engines/[engineId]`, `/workflow/*`, `/reports`, `/ocr`, `/coverage`).
- [✅] All navigation links resolve to real pages  
  - Verified: sidebar links exist for `/dashboard`, `/reports`, `/workflow/import`, `/ocr`, `/settings`, `/coverage`.
- [✅] No engine is accessible only via direct URL hacking  
  - Verified: engines are listed in sidebar and route to `/engines/{engineId}`.
- [✅] Unauthorized routes are properly blocked (not hidden)  
  - Verified: `frontend/web/middleware.ts` redirects all non-public routes to `/login` if `todiscope_session` cookie missing.

### 1.2 Sidebar & Navigation Integrity
- [✅] Sidebar lists all available engines  
  - Verified: `frontend/web/src/engines/registry.ts` includes 12 engine slugs.
- [✅] Each engine entry is clickable  
  - Verified: sidebar links route to `/engines/{engineId}`.
- [✅] Clicking an engine loads an engine-specific view  
  - Verified: `frontend/web/src/app/engines/[engineId]/page.tsx` renders `EnginePage(engineId)`.
- [✅] Each engine has a backend action surface  
  - Verified: `npm -C frontend/web run check:parity -- --base http://localhost:8400` asserts `/api/v3/engines/{engine}/run` is non-404 for all 12 engines.
- [✅] No sidebar item links to an empty or generic page  
  - Verified: engine route is per-engine; workflow + OCR pages exist.
- [✅] No missing icons, labels, or broken navigation states  
  - Verified by code inspection; icons mapped for known engine IDs.

---

## 2. ENGINE DISCOVERY & LANDING PAGE AUDIT (PER ENGINE)

**Engines (12)**
- `/engines/csrd`
- `/engines/financial-forensics`
- `/engines/cost-intelligence`
- `/engines/audit-readiness`
- `/engines/enterprise-capital-debt-readiness`
- `/engines/data-migration-readiness`
- `/engines/erp-integration-readiness`
- `/engines/enterprise-deal-transaction-readiness`
- `/engines/litigation-analysis`
- `/engines/regulatory-readiness`
- `/engines/enterprise-insurance-claim-forensics`
- `/engines/distressed-asset-debt-stress`

For each engine:
- [✅] Engine has a dedicated landing page  
  - Implemented by `/engines/[engineId]`.
- [⚠️] Landing page explains what the engine does / consumes / produces  
  - Implemented generically in `EnginePage` (“Inputs & outputs” + capabilities).  
  - **Missing**: engine-specific data contract (scenarios/assumptions/rules) surfaced in UI.
- [✅] Engine lifecycle is visible on entry  
  - Import → Normalize → Calculate → Report → Audit.
- [✅] Lifecycle stages are ordered and labeled  
- [✅] Empty-state messaging exists (no data yet)  
  - Dataset required messaging shown; stages show blocked/available/completed.
- [✅] No engine opens into a blank canvas or reused generic layout  
  - Engine route renders an engine-scoped page with dataset requirement and actions.

---

## 3. ENGINE LIFECYCLE VISIBILITY AUDIT (CRITICAL)

Each engine exposes lifecycle navigation:
- [✅] Import stage visible and clickable  
- [✅] Normalize stage visible and gated by dataset  
- [✅] Calculate stage visible and gated by dataset + run endpoint  
- [✅] Report stage visible and gated by dataset + run_id + report endpoint  
- [✅] Audit stage visible and gated by dataset  

**Important correction applied:** engines without `/report` are now blocked at Report stage (no broken click-through).

---

## 4. IMPORT STAGE AUDIT

### Visibility & Access
- [✅] Import stage visible in lifecycle navigation  
- [✅] Import stage clickable  
- [✅] Import page renders without errors (build-time)

### Functionality
- [✅] User can initiate a new import (file upload)  
  - UI: `frontend/web/src/app/workflow/import/page.tsx`
- [✅] At least one data source type is usable (file upload)  
- [✅] Validation errors are shown in UI  
- [⚠️] Successful import creates a DatasetVersion  
  - UI expects `dataset_version_id` from backend; verified by wiring, not by executing against a populated backend.
- [✅] DatasetVersion ID is visible in UI  
- [⚠️] Import metadata (source, timestamp) is displayed  
  - Currently shows `dataset_version_id` and optionally `raw_records_written`.  
  - **Missing**: source system / timestamp surfaced consistently.

### Wiring
- [✅] Import triggers backend processing  
  - Uses `/api/v3/ingest-file` (`api.ingestFile()`).
- [⚠️] Import completion updates UI state  
  - UI updates local state; cross-page dataset selection depends on broader dataset discovery.
- [⚠️] Failed imports do not create ghost datasets  
  - Requires runtime verification against backend persistence (not provable from UI alone).

---

## 5. NORMALIZE STAGE AUDIT

### Visibility & Access
- [✅] Normalize stage visible in lifecycle  
- [✅] Normalize stage clickable  
- [✅] Normalize page is distinct from Import

### Functionality
- [⚠️] Raw vs normalized data distinction is visible  
  - Preview shows raw response payload; normalized dataset ID shown after commit.
- [⚠️] Mapping or transformation rules are displayed  
  - Only indirectly (backend response). No explicit rules view.
- [✅] Normalization can be executed  
  - Preview/Validate/Commit wired to `/api/v3/normalize/*`.
- [✅] Errors are shown explicitly  
- [⚠️] Normalized data persisted to DatasetVersion  
  - UI expects `normalized_dataset_version_id`; persistence must be verified with backend.

### Wiring
- [✅] Normalize cannot run without an imported dataset  
  - Blocked unless `dataset_version_id` present.
- [⚠️] UI reflects completion or failure  
  - UI reflects local state; persistence + downstream effects need runtime verification.
- [⚠️] No silent auto-normalization occurs  
  - UI does not auto-normalize, but backend may normalize on ingest if configured; needs runtime confirmation.

---

## 6. CALCULATE STAGE AUDIT

### Visibility & Access
- [✅] Calculate stage visible  
- [✅] Calculate stage clickable  
- [⚠️] Calculate page is engine-specific  
  - Engine is passed via query param; UI is generic with engine selection.

### Functionality
- [✅] User can trigger a calculation run  
  - Calls `/api/v3/engines/{engine}/run`.
- [❌] Scenario or rule selection is visible  
- [✅] DatasetVersion used for calculation is shown  
- [❌] Assumptions used are listed  
- [✅] Execution status is shown (running/success/fail)

### Wiring
- [⚠️] Calculation triggers backend execution  
  - Wired; runtime confirmation required.
- [⚠️] Results are stored and retrievable  
  - Results are stored client-side in `EngineResultsProvider`; backend persistence is not shown in UI.
- [❌] Re-running with same inputs yields same results  
  - Determinism is not provable from UI.
- [⚠️] Failed runs leave an explicit trace  
  - UI shows error; audit trail persistence requires backend confirmation.

---

## 7. REPORT STAGE AUDIT

### Visibility & Access
- [✅] Report stage visible  
- [✅] Report stage clickable (only when supported by backend + run_id present)  
- [⚠️] Report page loads structured content  
  - Currently renders JSON preview + success state; enterprise narrative sections not guaranteed.

### Functionality
- [✅] Reports reference DatasetVersion and Run ID (query params shown)  
- [❌] Assumptions are disclosed in report  
- [⚠️] Results are shown as ranges, not assertions  
  - Depends on engine payload; UI does not enforce.
- [⚠️] Narrative sections exist (not raw tables only)  
  - Not guaranteed; current view is primarily JSON preview.
- [✅] Export options exist (PDF/structured output)  
  - Platform exports exist in report builder; per-engine report export varies by engine.

### Wiring
- [⚠️] Report content updates after calculation  
  - UI builds report from API response; not proven across engines.
- [✅] Report cannot be generated without dataset/run/engine params in workflow page  
- [❌] Reports are immutable per run  
  - UI does not enforce immutability or version pinning beyond passing `run_id`.

---

## 8. AUDIT STAGE AUDIT (STOP-SHIP IF FAILS)

### Visibility & Access
- [✅] Audit stage visible  
- [✅] Audit stage clickable  
- [✅] Audit page distinct from Report

### Traceability
- [⚠️] Full data lineage visible (Import → Normalize → Calculate → Report)  
  - Audit page requests `/api/v3/audit/logs` for the dataset.  
  - Actual lineage completeness depends on backend emitting audit events (runtime verification required).
- [⚠️] DatasetVersion history inspectable  
  - UI shows logs; no dedicated dataset version history timeline.
- [❌] Rule execution trace visible  
- [❌] Scenario definitions frozen and shown  
- [❌] Assumptions listed in one place

### Replay & Verification
- [❌] Past runs can be selected  
- [❌] Replays are possible  
- [❌] Differences between runs are inspectable  
- [❌] No hidden logic exists outside audit view  
  - Cannot be proven from UI.

**STOP-SHIP NOTE:** The audit surface exists and is reachable, but the “replay/diff/assumptions/rules” requirements are not met, so this section fails the prompt’s criteria.

---

## 9. CROSS-ENGINE CONSISTENCY AUDIT
- [✅] All engines expose the same lifecycle stages  
- [⚠️] Lifecycle behavior is consistent across engines  
  - Report support varies by backend; UI gates accordingly.
- [⚠️] Shared datasets behave consistently  
  - Depends on backend emitting consistent dataset/audit data.
- [❌] Audit posture is uniform platform-wide  
  - Replay/diff/assumptions view is not implemented.

---

## 10. NEGATIVE TESTS (MUST FAIL SAFELY)
- [❌] Attempting Calculate without Normalize fails clearly  
  - UI currently allows Calculate with any dataset version ID.
- [✅] Attempting Report without Calculate is blocked (requires `run_id`)  
- [✅] Attempting Audit without a run shows empty state (no logs)  
- [✅] Broken inputs produce explicit errors (UI error panels)  
- [⚠️] No silent success paths exist  
  - Some flows rely on backend persistence and may fail silently if backend returns partials; needs runtime confirmation.

---

## Required Follow-ups (to reach PASS under this audit rubric)
This is not an implementation plan; it is a strict audit gap list.

1. **Enforce lifecycle ordering in UI** (Normalize → Calculate → Report) using backend-backed state, not just query params.
2. **Audit stage must support historical selection + replay + diff** (or explicitly state unsupported if backend does not provide it).
3. **Expose assumptions/scenario/rule sets** used for Calculate/Report in the UI.
4. **Surface import metadata** (source + timestamp) and make dataset version lineage obvious.

---

## Issue Log (Severity / Location / Repro / Notes)

### Critical
1. **Missing audit replay/diff and rule trace**
   - Location: `/workflow/audit`
   - Repro: Open Audit stage for any engine/dataset; no run selector, replay, diff, scenario freeze, or rule trace is available.
   - Impact: Fails “auditable end-to-end” requirement; blocks production audit sign-off.

2. **Lifecycle ordering not enforced**
   - Location: `/workflow/calculate`, `/workflow/report`
   - Repro: Navigate directly to Calculate with `dataset_version_id` without completing Normalize; UI allows running.
   - Impact: Fails negative tests; risk of inconsistent pipeline states.

### High
3. **Backend DB missing env causes dataset discovery failures**
   - Location: dataset listing (header `DatasetSelector`) + `/workflow/audit` log fetch
   - Repro: Start backend without `TODISCOPE_DATABASE_URL`; `GET /api/v3/audit/logs` returns 500 and dataset list becomes unavailable.
   - Mitigation present: `./start_backend.sh` defaults to sqlite dev DB; manual `uvicorn` runs still fail unless env is set.

4. **Engine semantics are generic (no inspectable scenarios/assumptions UI)**
   - Location: `/engines/[engineId]`, `/workflow/calculate`, `/workflow/report`
   - Repro: Open any engine and look for engine-specific inputs/assumptions/rule sets; only generic metadata is shown.
   - Impact: Fails “inspectable” requirement for enterprise audit.

### Medium
5. **Dev-server stability (historical ENOENT .next artifacts)**
   - Location: Next dev server output
   - Repro: Rapidly restart dev server and hard-delete `.next` while it’s running; manifests may error with ENOENT.
   - Mitigation present: memory cache in dev (`frontend/web/next.config.ts`) and optional cache wipe (`CLEAN_NEXT=1 ./start_frontend.sh`).

---

## Explicit Recommendation
**NOT READY FOR PRODUCTION** under the “operational + visibility + auditability” rubric.

Proceed only after:
- Audit replay/diff + rule/assumption visibility exists (or backend declares these unsupported and UI gates accordingly).
- Lifecycle ordering is enforced in the UI with backend-backed state.
