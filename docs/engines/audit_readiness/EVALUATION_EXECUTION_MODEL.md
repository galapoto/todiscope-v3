# Evaluation Run Lifecycle (States and Transitions)
- CREATED → VALIDATING_INPUTS: run identifier allocated; requested DatasetVersion identifier received.
- VALIDATING_INPUTS → CHECKING_EVIDENCE_PRESENCE: DatasetVersion binding requirements satisfied for the run request.
- VALIDATING_INPUTS → INVALID: DatasetVersion binding requirements not satisfied for the run request.
- CHECKING_EVIDENCE_PRESENCE → VALID: all contract-required evidence artifact identifiers are present and bound as required.
- CHECKING_EVIDENCE_PRESENCE → INVALID: one or more contract-required evidence artifact identifiers are missing or not bound as required.
- VALID → FINALIZED: run record sealed as presence-only valid evaluation.
- INVALID → FINALIZED: run record sealed as presence-only invalid evaluation with contract-referenced reasons.

# How Required Evidence Artifacts Are Checked for Presence
- For each dimension contract, the run enumerates the required evidence artifact names defined by the contract.
- Presence is satisfied only when an evidence artifact identifier exists for each required artifact name.
- Presence checks operate on artifact identifiers and declared names only.

# How DatasetVersion Binding Is Enforced During Execution
- The run has a single required DatasetVersion identifier.
- Each required evidence artifact identifier must declare a binding to the same DatasetVersion identifier.
- Any missing DatasetVersion binding or any mismatch between an artifact binding and the run DatasetVersion identifier makes the evaluation invalid.

# How Invalidity Reasons Are Produced (Contract-Referenced, Not Data-Derived)
- Invalidity reasons are produced only from contract rules and binding requirements.
- Each reason references the dimension name and the contract clause category: missing required evidence artifact; missing required binding; inconsistent binding across artifacts.
- Reasons identify the missing or mismatched evidence artifact names and bindings by identifiers only.

# What Is Recorded Per Run (Identifiers Only)
- Evaluation run identifier.
- DatasetVersion identifier.
- Source Reference identifier.
- Dimension identifiers evaluated.
- Contract identifier for each dimension evaluation.
- Required evidence artifact identifiers observed per dimension.
- Validity state per dimension evaluation.
- Invalidity reason identifiers per dimension evaluation.
