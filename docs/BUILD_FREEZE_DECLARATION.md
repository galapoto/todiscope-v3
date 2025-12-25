# TodiScope v3 — BUILD FREEZE Declaration

Date: 2025-12-24  
Scope: Frontend build freeze (UI/UX/integration surface)

This repository is now in **BUILD FROZEN** mode for the frontend:

- No new features
- No redesigns
- No refactors
- Only **audits** and **targeted fixes** for user-visible blockers and parity gaps

The canonical parity surface for this freeze is:

- Parity matrix page: `/coverage` (internal-only)
- Engine landing pages: `/engines/[engineId]`
- Lifecycle pages: `/workflow/import`, `/workflow/normalize`, `/workflow/calculate`, `/workflow/report`, `/workflow/audit`
- Reports: `/reports`
- OCR: `/ocr`

Audit artifacts:

- `TODISCOPE_V3_FULL_OPERATIONAL_VISIBILITY_AUDIT.md`

