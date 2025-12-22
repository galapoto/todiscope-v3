# TodiScope v3 — Platform State

## Platform
- Name: TodiScope
- Version: v3

## Engines
- Engine #2 — Enterprise Financial Forensics & Leakage — CLOSED (Reference)
- Engine #4 — Enterprise Audit Readiness & Data Quality — CLOSED

## Laws and Requirements
- DatasetVersion immutability law: `docs/NON_NEGOTIABLE_PLATFORM_LAWS.md`
- Kill-switch requirement: all engines must be gated by a kill-switch that prevents route mounting and prevents writes when disabled.
- Rule: No refactors or engine changes without explicit approval.
