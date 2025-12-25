# BUILD FREEZE — Frontend–Backend Parity Lock

Date: 2025-12-24

This repository is in **BUILD FREEZE** for the frontend parity-closure phase.

Scope is locked to functional parity only:
- No new features
- No redesigns
- No refactors
- No performance work
- No accessibility audit work

## Parity Surfaces

- Parity Matrix (internal): `frontend/web/src/app/coverage/page.tsx` (route: `/coverage`)
- Dashboard widgets + engine surface: `frontend/web/src/app/dashboard/page.tsx` (route: `/dashboard`)
- Reports + exports (PDF/XLSX/CSV) + gated AI/OCR: `frontend/web/src/app/reports/page.tsx` (route: `/reports`)
- Evidence viewer (runtime evidence IDs): `frontend/web/src/app/evidence/[evidenceId]/page.tsx` (route: `/evidence/:evidenceId`)

## Dataset Coverage

- Dataset versions are discovered via audit logs (`/api/v3/audit/logs?action_type=import…`).
- UI requirements implemented:
  - Discoverable in UI (dataset selector + dataset versions table)
  - Viewable in a table with filtering/search
  - Exportable to CSV/XLSX (exports reflect the filtered table state)
  - Version-aware with read-only indicator for historical datasets
  - Explicit states:
    - Empty dataset list → empty state
    - Restricted (401/403) → permission explanation
    - Backend error (5xx) → explicit “unavailable” explanation

## Capability Gating

Unsupported capabilities are not shown as broken UI:
- AI panels render only when backend AI endpoint is detected.
- OCR upload renders only when backend OCR endpoint is detected.
- Workflow actions are disabled (with explanation) when backend workflow endpoint is not detected.
- Engine run/report actions are enabled/disabled per-engine by probing run/report endpoints.

## Evidence Reachability

- Evidence is reachable in ≤ 1 click wherever evidence IDs are present:
  - Engine details modal links evidence IDs to `/evidence/:evidenceId`.
  - Existing evidence badges open an evidence viewer modal for UI-supplied evidence objects.

## Export Coverage

- Reports → PDF export includes:
  - Current language labels (i18n)
  - Current filter state (dataset, engines, date range, scope, region)
  - AI insights (when present)
- Datasets → CSV/XLSX export includes current filtered table state.
- Evidence bundle exports are treated as not applicable unless/until a backend endpoint exists.

## Freeze Rule

From this point:
- Only audits and audit-driven fixes are permitted.
- Any feature/UX/performance work must be deferred until after the audit phase.

