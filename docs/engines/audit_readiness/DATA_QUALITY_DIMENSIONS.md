# Canonical Data Quality Dimensions

## Completeness
- Name: Completeness
- Plain-language intent: This dimension checks whether the dataset contains all required records and required fields as defined by its declared contract. It treats missing required content as a quality defect.
- What this dimension answers for an auditor: Whether the dataset is whole enough to support the stated audit procedures without relying on implicit gaps or unstated exclusions.
- What it explicitly does NOT claim: It does not claim that present data is correct, authorized, or representative of external reality.

## Validity
- Name: Validity
- Plain-language intent: This dimension checks whether each value conforms to declared constraints such as type, allowed domain, and structural format. It treats nonconforming values as quality defects.
- What this dimension answers for an auditor: Whether the dataset adheres to its stated schema and value rules so that downstream procedures interpret fields unambiguously.
- What it explicitly does NOT claim: It does not claim that valid-looking values are true, appropriate, or compliant with any policy.

## Consistency
- Name: Consistency
- Plain-language intent: This dimension checks that related fields and records do not contradict each other under declared relationships and invariants. It treats internal contradictions as quality defects.
- What this dimension answers for an auditor: Whether the dataset can be used without resolving conflicting representations of the same fact within the dataset.
- What it explicitly does NOT claim: It does not claim which side of an inconsistency reflects reality or which system is authoritative.

## Uniqueness
- Name: Uniqueness
- Plain-language intent: This dimension checks that identifiers and declared uniqueness keys do not represent the same entity or event multiple times when uniqueness is required. It treats unintended duplication as a quality defect.
- What this dimension answers for an auditor: Whether counts, populations, and linkages derived from identifiers are stable and not inflated by duplication.
- What it explicitly does NOT claim: It does not claim that duplicates are unauthorized, fraudulent, or erroneous outside the dataset’s declared rules.

## Referential Integrity
- Name: Referential Integrity
- Plain-language intent: This dimension checks that declared references between records are resolvable and structurally coherent. It treats broken or ambiguous references as quality defects.
- What this dimension answers for an auditor: Whether relationships needed for traceability and reconciliation can be followed end-to-end using identifiers present in the dataset.
- What it explicitly does NOT claim: It does not claim that the linked records are complete, correct, or substantively related beyond the declared reference.

## Provenance & Lineage
- Name: Provenance & Lineage
- Plain-language intent: This dimension checks that records carry sufficient provenance to identify their source and the deterministic steps that produced the current representation. It treats missing or unverifiable lineage as a quality defect.
- What this dimension answers for an auditor: Whether an item can be traced from reported outputs back to originating records and reproducible transformations.
- What it explicitly does NOT claim: It does not claim that the source system is correct, controlled, or authoritative.

## Transformation Fidelity
- Name: Transformation Fidelity
- Plain-language intent: This dimension checks that transformations are explicit, deterministic, and fully described by the recorded parameters and versions of the transformation logic. It treats undocumented or non-reproducible transformations as quality defects.
- What this dimension answers for an auditor: Whether the dataset’s current form can be recreated from the same inputs without hidden rules or environment-dependent behavior.
- What it explicitly does NOT claim: It does not claim that the chosen transformation is the only acceptable interpretation or that it matches any external expectation.

## Temporal Attribution
- Name: Temporal Attribution
- Plain-language intent: This dimension checks that the dataset states its time context using declared fields and that this context is preserved through transformations. It treats missing or conflicting time context as a quality defect.
- What this dimension answers for an auditor: Whether records and outputs can be interpreted at the stated point-in-time without relying on unstated assumptions about time.
- What it explicitly does NOT claim: It does not claim that records are current, timely, or complete for any period beyond the dataset’s declared context.
