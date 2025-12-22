# Evaluation Contracts

## Completeness
- Required evidence artifacts: Dataset Contract Declaration; Required Field Inventory; Required Population Declaration; Missing Required Field Register; Missing Required Record Register.
- Mandatory bindings: DatasetVersion; Source Reference.
- Conditions under which evaluation is VALID: Dataset Contract Declaration is present; Required Field Inventory is present; Required Population Declaration is present; all required evidence artifacts are bound to the same DatasetVersion and the same Source Reference.
- Conditions under which evaluation is INVALID: Dataset Contract Declaration is missing; Required Field Inventory is missing; Required Population Declaration is missing; any required evidence artifact is missing; any required evidence artifact is not bound to DatasetVersion; any required evidence artifact is not bound to Source Reference; bindings are not consistent across artifacts.
- Required disclosures when INVALID: Which required evidence artifacts are missing; which bindings are missing; which artifacts have binding mismatches; scope statement that the completeness evaluation is not valid for the stated DatasetVersion and Source Reference.

## Validity
- Required evidence artifacts: Schema Declaration; Value Domain Declaration; Structural Format Declaration; Invalid Value Register; Invalid Structure Register.
- Mandatory bindings: DatasetVersion; Source Reference.
- Conditions under which evaluation is VALID: Schema Declaration is present; Value Domain Declaration is present; Structural Format Declaration is present; all required evidence artifacts are bound to the same DatasetVersion and the same Source Reference.
- Conditions under which evaluation is INVALID: Schema Declaration is missing; Value Domain Declaration is missing; Structural Format Declaration is missing; any required evidence artifact is missing; any required evidence artifact is not bound to DatasetVersion; any required evidence artifact is not bound to Source Reference; bindings are not consistent across artifacts.
- Required disclosures when INVALID: Which required evidence artifacts are missing; which bindings are missing; which artifacts have binding mismatches; scope statement that the validity evaluation is not valid for the stated DatasetVersion and Source Reference.

## Consistency
- Required evidence artifacts: Relationship Declaration; Invariant Declaration; Consistency Check Register; Contradiction Register; Identity Resolution Basis Declaration.
- Mandatory bindings: DatasetVersion; Source Reference.
- Conditions under which evaluation is VALID: Relationship Declaration is present; Invariant Declaration is present; Identity Resolution Basis Declaration is present; all required evidence artifacts are bound to the same DatasetVersion and the same Source Reference.
- Conditions under which evaluation is INVALID: Relationship Declaration is missing; Invariant Declaration is missing; Identity Resolution Basis Declaration is missing; any required evidence artifact is missing; any required evidence artifact is not bound to DatasetVersion; any required evidence artifact is not bound to Source Reference; bindings are not consistent across artifacts.
- Required disclosures when INVALID: Which required evidence artifacts are missing; which bindings are missing; which artifacts have binding mismatches; scope statement that the consistency evaluation is not valid for the stated DatasetVersion and Source Reference.

## Uniqueness
- Required evidence artifacts: Uniqueness Key Declaration; Identifier Field Declaration; Duplicate Detection Basis Declaration; Duplicate Key Register; Duplicate Identifier Register.
- Mandatory bindings: DatasetVersion; Source Reference.
- Conditions under which evaluation is VALID: Uniqueness Key Declaration is present; Identifier Field Declaration is present; Duplicate Detection Basis Declaration is present; all required evidence artifacts are bound to the same DatasetVersion and the same Source Reference.
- Conditions under which evaluation is INVALID: Uniqueness Key Declaration is missing; Identifier Field Declaration is missing; Duplicate Detection Basis Declaration is missing; any required evidence artifact is missing; any required evidence artifact is not bound to DatasetVersion; any required evidence artifact is not bound to Source Reference; bindings are not consistent across artifacts.
- Required disclosures when INVALID: Which required evidence artifacts are missing; which bindings are missing; which artifacts have binding mismatches; scope statement that the uniqueness evaluation is not valid for the stated DatasetVersion and Source Reference.

## Referential Integrity
- Required evidence artifacts: Reference Field Declaration; Reference Target Declaration; Relationship Cardinality Declaration; Broken Reference Register; Ambiguous Reference Register.
- Mandatory bindings: DatasetVersion; Source Reference.
- Conditions under which evaluation is VALID: Reference Field Declaration is present; Reference Target Declaration is present; Relationship Cardinality Declaration is present; all required evidence artifacts are bound to the same DatasetVersion and the same Source Reference.
- Conditions under which evaluation is INVALID: Reference Field Declaration is missing; Reference Target Declaration is missing; Relationship Cardinality Declaration is missing; any required evidence artifact is missing; any required evidence artifact is not bound to DatasetVersion; any required evidence artifact is not bound to Source Reference; bindings are not consistent across artifacts.
- Required disclosures when INVALID: Which required evidence artifacts are missing; which bindings are missing; which artifacts have binding mismatches; scope statement that the referential integrity evaluation is not valid for the stated DatasetVersion and Source Reference.

## Provenance & Lineage
- Required evidence artifacts: Source System Declaration; Extraction Declaration; Transformation Chain Declaration; Lineage Linkage Register; Provenance Completeness Register.
- Mandatory bindings: DatasetVersion; Source Reference.
- Conditions under which evaluation is VALID: Source System Declaration is present; Extraction Declaration is present; Transformation Chain Declaration is present; all required evidence artifacts are bound to the same DatasetVersion and the same Source Reference.
- Conditions under which evaluation is INVALID: Source System Declaration is missing; Extraction Declaration is missing; Transformation Chain Declaration is missing; any required evidence artifact is missing; any required evidence artifact is not bound to DatasetVersion; any required evidence artifact is not bound to Source Reference; bindings are not consistent across artifacts.
- Required disclosures when INVALID: Which required evidence artifacts are missing; which bindings are missing; which artifacts have binding mismatches; scope statement that the provenance and lineage evaluation is not valid for the stated DatasetVersion and Source Reference.

## Transformation Fidelity
- Required evidence artifacts: Transformation Specification Declaration; Parameter Snapshot Declaration; Transformation Version Declaration; Determinism Basis Declaration; Transformation Reproducibility Register.
- Mandatory bindings: DatasetVersion; Source Reference.
- Conditions under which evaluation is VALID: Transformation Specification Declaration is present; Parameter Snapshot Declaration is present; Transformation Version Declaration is present; Determinism Basis Declaration is present; all required evidence artifacts are bound to the same DatasetVersion and the same Source Reference.
- Conditions under which evaluation is INVALID: Transformation Specification Declaration is missing; Parameter Snapshot Declaration is missing; Transformation Version Declaration is missing; Determinism Basis Declaration is missing; any required evidence artifact is missing; any required evidence artifact is not bound to DatasetVersion; any required evidence artifact is not bound to Source Reference; bindings are not consistent across artifacts.
- Required disclosures when INVALID: Which required evidence artifacts are missing; which bindings are missing; which artifacts have binding mismatches; scope statement that the transformation fidelity evaluation is not valid for the stated DatasetVersion and Source Reference.

## Temporal Attribution
- Required evidence artifacts: Time Context Declaration; Effective Time Field Declaration; Time Zone Basis Declaration; Temporal Consistency Register; Temporal Attribution Completeness Register.
- Mandatory bindings: DatasetVersion; Source Reference.
- Conditions under which evaluation is VALID: Time Context Declaration is present; Effective Time Field Declaration is present; Time Zone Basis Declaration is present; all required evidence artifacts are bound to the same DatasetVersion and the same Source Reference.
- Conditions under which evaluation is INVALID: Time Context Declaration is missing; Effective Time Field Declaration is missing; Time Zone Basis Declaration is missing; any required evidence artifact is missing; any required evidence artifact is not bound to DatasetVersion; any required evidence artifact is not bound to Source Reference; bindings are not consistent across artifacts.
- Required disclosures when INVALID: Which required evidence artifacts are missing; which bindings are missing; which artifacts have binding mismatches; scope statement that the temporal attribution evaluation is not valid for the stated DatasetVersion and Source Reference.
