# Financial Forensics Engine Guarantees

**Engine:** Engine #2 — Financial Forensics & Leakage  
**Version:** v1  
**Last Updated:** 2025-01-XX

---

## What the Engine Does

### Core Functionality

1. **Matching Analysis**
   - Invoice ↔ payment matching with explicit rule sets (exact, tolerance, partial)
   - Duplicate detection (invoice duplicates, payment duplicates)
   - Matching confidence labeling (exact, within_tolerance, partial, ambiguous)

2. **Leakage Typology Classification**
   - Unmatched payable/receivable exposure identification
   - Partial settlement residual detection
   - Timing mismatch detection (matched amounts but date delta beyond threshold)
   - Overpayment/underpayment signal detection

3. **Exposure Quantification**
   - Exposure estimation (point estimates or bounded ranges)
   - Multi-currency support with deterministic FX conversion
   - Exposure aggregation (per document, counterparty, currency, typology)

4. **Evidence & Traceability**
   - Complete evidence linking per finding and leakage instance
   - Rule identity and parameter tracking
   - Primary record references
   - Replayability guarantees

5. **Review Workflow Integration**
   - Human review state management
   - Immutable findings and review actions
   - Audit-safe invalidation

---

## What the Engine Explicitly Does Not Do

### Legal & Operational Exclusions

1. **No Fraud Declarations**
   - Engine does not declare fraud or infer intent
   - Engine does not assign blame or responsibility
   - Engine reports signals and patterns only

2. **No Decision-Making**
   - Engine does not make decisions or recommendations
   - Engine does not prescribe actions
   - Engine provides advisory signals only

3. **No Accounting Policy Logic**
   - Engine does not eliminate or net intercompany transactions
   - Engine does not apply consolidation rules
   - Engine flags intercompany for visibility only

4. **No Recovery Claims**
   - Engine does not claim recoverable amounts
   - Engine does not assert damages
   - Engine reports exposure estimates only

5. **No Intent Inference**
   - Engine does not infer intent or motivation
   - Engine does not assign fault
   - Engine reports observable patterns only

---

## Replay and Determinism Guarantees

### Replayability

**Guarantee:** Same inputs (DatasetVersion, parameters, FX artifact) produce identical outputs.

**Enforcement:**
- All findings are deterministic (same inputs → same finding IDs)
- All leakage classifications are deterministic (same finding + evidence → same typology)
- All exposure calculations are deterministic (same inputs → same exposure values/ranges)
- Evidence IDs are deterministic (same inputs → same evidence IDs)

**Validation:**
- Replay tests verify bitwise-identical outputs
- Artifact hash comparison for deterministic verification
- Semantic finding/leakage/aggregation set equality checks

### Determinism Requirements

1. **No Time-Dependent Logic**
   - No `datetime.now()`, `date.today()`, or `time.time()` usage
   - All timestamps are injected or derived from stable sources
   - FX artifacts use deterministic timestamps

2. **No Environment-Dependent Behavior**
   - No environment variable dependencies (except engine enable/disable)
   - No system time dependencies
   - No random number generation

3. **No Hidden Defaults**
   - All parameters must be explicit
   - No implicit thresholds or tolerances
   - No fallback values that affect results

4. **Explicit Rule Ordering**
   - Classification rules are applied in explicit, documented order
   - No dict/set iteration that could produce non-deterministic ordering
   - Rule priority is locked and tested

---

## Validity Scope

### Dataset/Run Binding

**Guarantee:** All outputs are bound to a specific DatasetVersion and Run.

**Enforcement:**
- Every finding requires `dataset_version_id` and `run_id`
- Every leakage instance requires `dataset_version_id` and `run_id`
- Every evidence record requires `dataset_version_id`
- FX artifacts are bound to `dataset_version_id`

**Scope:**
- Outputs are valid only for the specific DatasetVersion and Run
- Replay requires identical DatasetVersion and Run parameters
- Cross-dataset aggregation is forbidden

### FX Artifact Binding

**Guarantee:** FX conversions use fixed, immutable FX artifacts per run.

**Enforcement:**
- FX artifacts are immutable (content-addressed, checksum-verified)
- FX artifacts are bound to runs (no live FX fetching)
- FX artifact references are included in all findings and leakage instances

---

## Evidence Completeness Guarantees

### Finding Evidence

**Guarantee:** Every finding has complete, defensible evidence.

**Required Evidence:**
- Rule identity (rule_id, rule_version, framework_version)
- Tolerance values (if used)
- Amount comparisons (original + converted)
- Date comparisons
- Reference comparisons
- Counterparty logic
- Match selection rationale
- Primary source links

### Leakage Evidence

**Guarantee:** Every leakage instance has complete, defensible evidence.

**Required Evidence:**
- Typology assignment rationale
- Numeric exposure derivation steps
- Source FF-3 finding references
- Primary records involved
- Intercompany flags (if applicable)

---

## External Sharing Guarantees

### External View Safety

**Guarantee:** External views are safe for third-party sharing.

**Enforcement:**
- Internal-only sections are omitted
- Sensitive fields are redacted or anonymized
- No fraud/blame language
- No decisioning language
- Numbers are not transformed (only omitted/redacted)

**Shareable Sections:**
- Findings overview
- Exposure estimates
- Control signals
- Limitations & uncertainty
- Assumptions
- Evidence index

**Internal-Only Sections:**
- Internal notes
- Counterparty details
- Source system IDs
- Run parameters

---

## Assumptions & Limitations

### Standard Assumptions

1. **FX Assumptions**
   - FX rates are provided via FX artifacts (not live)
   - FX conversions use deterministic rounding
   - Base currency is explicit per run

2. **Data Completeness**
   - Data completeness level is declared
   - Missing fields are documented
   - Evidence completeness affects confidence levels

3. **Tolerance Settings**
   - Tolerance values are explicit per rule
   - Tolerance source is documented (rule_config, run_parameters)

### Standard Limitations

1. **Scope Limitations**
   - Analysis is limited to provided DatasetVersion
   - Analysis is limited to executed matching rules
   - Analysis does not include enrichment data unless provided

2. **Confidence Limitations**
   - Confidence levels reflect evidence completeness
   - Ambiguous findings require human review
   - Exposure ranges reflect uncertainty

3. **Validity Limitations**
   - Outputs are valid only for specific DatasetVersion and Run
   - Replay requires identical inputs
   - Cross-dataset comparisons are not supported

---

## Version Lock

**FF-4 v1 is permanently locked:**
- Typology enum cannot be changed
- Timing mismatch rule cannot be removed
- Partial exposure binding cannot be changed
- Exposure source must use `diff_converted` from evidence
- Classification rule order is locked

**Enforcement:**
- Structural tests fail if locked behaviors are changed
- Functional tests verify locked behaviors work correctly

---

## Contact & Support

For questions about these guarantees or engine behavior, refer to:
- Engine documentation: `docs/engine_financial_forensics/`
- Contracts: `docs/contracts/`
- Assumption registry: Generated per run

---

**END OF FINANCIAL FORENSICS ENGINE GUARANTEES**


