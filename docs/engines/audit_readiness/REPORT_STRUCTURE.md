# Report Purpose Statement (Non-Claiming)
This report records whether required evidence artifacts for the declared contracts are present and correctly bound to the stated DatasetVersion and Source Reference. It does not assert data correctness, completeness, suitability, or compliance.

# Required Sections (Ordered)
1. Report Identifiers
2. Scope Bindings
3. Contract Set
4. Evaluation Runs
5. Dimension Results (Presence-Only)
6. Evidence Reference Index
7. Invalidity Disclosures
8. Explicit Exclusions

# What Each Section Contains (Identifiers, Not Prose)
## 1. Report Identifiers
- Report identifier
- Engine identifier
- Report version identifier

## 2. Scope Bindings
- DatasetVersion identifier
- Source Reference identifier

## 3. Contract Set
- Contract set identifier
- Dimension identifiers included
- Contract identifier per dimension

## 4. Evaluation Runs
- Evaluation run identifier list
- Dimension evaluation identifier per run
- Run state per evaluation identifier

## 5. Dimension Results (Presence-Only)
- Dimension identifier
- Contract identifier
- Displayed outcome: VALID or INVALID
- Required evidence artifact name identifiers
- Observed evidence artifact identifiers per required name
- Binding status identifiers: DatasetVersion binding; Source Reference binding; binding consistency

## 6. Evidence Reference Index
- Evidence artifact identifier list
- Evidence artifact name identifier
- Evidence artifact kind identifier
- DatasetVersion binding identifier
- Source Reference binding identifier

## 7. Invalidity Disclosures
- Dimension identifier
- Dimension evaluation identifier
- Invalidity reason identifier list
- Contract clause category identifier per reason
- Missing evidence artifact name identifiers
- Missing binding identifiers
- Binding mismatch identifiers

## 8. Explicit Exclusions
- Exclusion identifier list for non-claims and omissions

# How VALID / INVALID Is Displayed
- Each dimension result displays exactly one outcome state: VALID or INVALID.
- VALID is displayed only when all required evidence artifacts are present and all mandatory bindings are satisfied.
- INVALID is displayed when any required evidence artifact is missing or any mandatory binding is missing or inconsistent.

# How Evidence References Are Included
- Evidence references are included only as identifiers.
- Evidence artifacts are referenced by identifier in the Dimension Results section and indexed in the Evidence Reference Index section.

# What Is Explicitly NOT Included
- No scoring, ratings, grades, or thresholds.
- No interpretation, narrative analysis, or conclusions about the data.
- No recommendations, remediation steps, or action guidance.
- No framework mappings or compliance assertions.
- No record-level content or field values.
