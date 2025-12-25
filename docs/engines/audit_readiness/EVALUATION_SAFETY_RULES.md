# Audit Readiness Engine — Evaluation Safety Rules

**Engine:** Audit Readiness (AR-2)  
**Version:** v1  
**Last Updated:** 2025-01-XX

---

## DatasetVersion Binding Rules

### Mandatory Binding

**Rule:** Every evaluation must be bound to a specific DatasetVersion.

**Requirements:**
- Every evaluation requires an explicit `dataset_version_id` parameter
- No implicit dataset selection is permitted
- No "latest" or "current" dataset inference is allowed
- Missing `dataset_version_id` results in evaluation failure

**Scope:**
- Evaluations are valid only for the specific DatasetVersion provided
- Cross-dataset evaluations are forbidden
- Evaluations cannot aggregate across multiple DatasetVersions
- Replay requires identical DatasetVersion parameter

### DatasetVersion Validation

**Rule:** DatasetVersion must exist and be accessible before evaluation begins.

**Requirements:**
- DatasetVersion existence must be verified
- DatasetVersion must be accessible via core data management services
- Invalid or inaccessible DatasetVersion results in evaluation failure
- No fallback to alternative DatasetVersions

---

## Invalid Evaluation Conditions

### Missing Required Parameters

An evaluation is invalid if:
- `dataset_version_id` is missing, empty, or null
- Required evaluation parameters are not provided
- Required configuration is absent

### DatasetVersion Issues

An evaluation is invalid if:
- DatasetVersion does not exist
- DatasetVersion is not accessible
- DatasetVersion is in an invalid state
- DatasetVersion binding cannot be established

### Scope Violations

An evaluation is invalid if:
- Attempts to access data outside the bound DatasetVersion
- Attempts to modify DatasetVersion or core services
- Attempts to access external data sources directly
- Attempts to import or use other engines

### Binding Violations

An evaluation is invalid if:
- Results are not bound to the specific DatasetVersion
- Results reference data from multiple DatasetVersions
- Results cannot be traced to the source DatasetVersion

---

## Required Disclosures

### Assumptions

**Required Disclosure:** All assumptions must be explicitly stated.

**Assumption Categories:**
- Data completeness assumptions
- Data quality assumptions
- Scope boundaries
- Service availability assumptions
- Infrastructure dependencies

**Disclosure Requirements:**
- Assumptions must be documented per evaluation
- Assumptions must be machine-readable
- Assumptions must be included in evaluation outputs
- Assumptions must be visible to consumers of evaluation results

### Scope Limits

**Required Disclosure:** All scope limitations must be explicitly stated.

**Scope Limit Categories:**
- DatasetVersion boundaries
- Data coverage boundaries
- Temporal boundaries
- Service dependency boundaries
- Infrastructure boundaries

**Disclosure Requirements:**
- Scope limits must be documented per evaluation
- Scope limits must be machine-readable
- Scope limits must be included in evaluation outputs
- Scope limits must be visible to consumers of evaluation results

### Validity Boundaries

**Required Disclosure:** Validity boundaries must be explicitly stated.

**Validity Boundary Categories:**
- DatasetVersion validity period
- Evaluation result validity period
- Dependency validity period
- Service validity period

**Disclosure Requirements:**
- Validity boundaries must be documented per evaluation
- Validity boundaries must be machine-readable
- Validity boundaries must be included in evaluation outputs
- Validity boundaries must be visible to consumers of evaluation results

---

## Explicit Non-Claims

### No Data Quality Assertions

**Non-Claim:** The engine does not assert data quality levels.

**Exclusions:**
- Does not claim data is "good" or "bad"
- Does not claim data meets or fails quality standards
- Does not claim data completeness levels
- Does not claim data accuracy levels

### No Compliance Assertions

**Non-Claim:** The engine does not assert compliance status.

**Exclusions:**
- Does not claim compliance with regulations
- Does not claim compliance with standards
- Does not claim compliance with policies
- Does not claim audit readiness status

### No Remediation Claims

**Non-Claim:** The engine does not claim remediation requirements.

**Exclusions:**
- Does not claim what must be fixed
- Does not claim remediation priorities
- Does not claim remediation steps
- Does not claim remediation timelines

### No Decision-Making Claims

**Non-Claim:** The engine does not make decisions or recommendations.

**Exclusions:**
- Does not claim what actions should be taken
- Does not claim what decisions should be made
- Does not claim what priorities should be set
- Does not claim what outcomes should be expected

### No Blame or Responsibility Claims

**Non-Claim:** The engine does not assign blame or responsibility.

**Exclusions:**
- Does not claim who is responsible
- Does not claim who is at fault
- Does not claim who should act
- Does not claim who should be notified

### No Future State Claims

**Non-Claim:** The engine does not claim future states or outcomes.

**Exclusions:**
- Does not claim what will happen
- Does not claim what should happen
- Does not claim what might happen
- Does not claim future risk levels

### No Comparative Claims

**Non-Claim:** The engine does not make comparative assertions.

**Exclusions:**
- Does not claim one dataset is better than another
- Does not claim improvement or degradation
- Does not claim trends or patterns over time
- Does not claim relative quality levels

---

## Evaluation Output Requirements

### Mandatory Outputs

Every evaluation must include:
- DatasetVersion binding information
- Assumptions disclosure
- Scope limits disclosure
- Validity boundaries disclosure
- Explicit non-claims statement

### Output Format

**Requirements:**
- Outputs must be machine-readable
- Outputs must be traceable to source DatasetVersion
- Outputs must include all required disclosures
- Outputs must include explicit non-claims statement

---

## Contact & Support

For questions about these evaluation safety rules or engine behavior, refer to:
- Engine documentation: `backend/app/engines/audit_readiness/README.md`
- Platform laws: `docs/NON_NEGOTIABLE_PLATFORM_LAWS.md`

---

**END OF EVALUATION SAFETY RULES**






