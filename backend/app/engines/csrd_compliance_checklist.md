# CSRD Compliance Checklist

This checklist helps users ensure that their workflows meet **CSRD compliance** requirements and validates that the CSRD engine has properly processed their data.

## Usage

After running the CSRD engine (`/api/v3/engines/csrd/run`), use this checklist to verify that all compliance requirements have been met.

---

## Checklist Items

### ✅ Materiality Assessment Completed

**Description:** Double materiality assessment has been performed, identifying material ESG risks and their financial impacts.

**Verification:**
- [ ] Report contains `materiality_assessment` section
- [ ] Material topics identified and categorized (emissions, governance, opportunities)
- [ ] Each finding includes:
  - Materiality determination (`is_material`: true/false)
  - Financial impact estimate (EUR)
  - Impact score
  - Confidence level
  - Threshold comparison (value vs. threshold)

**Expected Output:**
```json
{
  "materiality_assessment": {
    "methodology": "Double materiality (financial + impact) with configurable thresholds.",
    "material_topics": [...],
    "findings": [...]
  }
}
```

---

### ✅ Emission Factors Calculated

**Description:** Emission calculations have been performed for Scope 1, Scope 2, and Scope 3 emissions.

**Verification:**
- [ ] Report contains `emission_calculations` section
- [ ] All three scopes (scope1, scope2, scope3) are present
- [ ] Each scope includes:
  - Value (tCO2e)
  - Unit (tCO2e)
  - Source (reported_or_default, IEA, etc.)
  - Methodology (direct, market-based/location-based, value_chain)
- [ ] Total emissions calculated: `total_emissions_tco2e`

**Expected Output:**
```json
{
  "emission_calculations": {
    "dataset_version_id": "...",
    "scopes": {
      "scope1": {"value": ..., "unit": "tCO2e", "source": "...", "methodology": "direct"},
      "scope2": {"value": ..., "unit": "tCO2e", "source": "...", "methodology": "market-based"},
      "scope3": {"value": ..., "unit": "tCO2e", "source": "...", "methodology": "value_chain"}
    },
    "total_emissions_tco2e": ...
  }
}
```

---

### ✅ Evidence Linked to DatasetVersion

**Description:** All evidence (reports, emissions, findings) is properly linked to DatasetVersion for immutability and traceability.

**Verification:**
- [ ] Report metadata contains `dataset_version_id`
- [ ] Emissions payload contains `dataset_version_id`
- [ ] Response contains `emissions_evidence_id` and `report_evidence_id`
- [ ] All findings have corresponding evidence records in database
- [ ] Evidence records are queryable by `dataset_version_id`

**Expected Output:**
```json
{
  "dataset_version_id": "...",
  "emissions_evidence_id": "...",
  "report_evidence_id": "...",
  "report": {
    "metadata": {
      "dataset_version_id": "..."
    },
    "data_integrity": {
      "dataset_version_id": "...",
      "immutability": "Anchored to DatasetVersion; core records are write-once.",
      "traceability": "Findings are linked to source RawRecords and EvidenceRecords."
    }
  }
}
```

**Database Verification:**
- Query `evidence_records` table filtering by `dataset_version_id` to verify all evidence is linked
- Verify `finding_record` entries have `dataset_version_id` foreign key
- Verify `finding_evidence_link` entries connect findings to evidence

---

### ✅ Report Sections Generated

**Description:** Complete ESRS-aligned report has been generated with all required sections.

**Verification:**
- [ ] **Metadata** section present with:
  - `report_id`
  - `dataset_version_id`
  - `generated_at` timestamp
  - `standard`: "ESRS"
  - `version`: "v0-skeleton"

- [ ] **Executive Summary** section present with:
  - High-level overview
  - Material topics count
  - Total emissions summary

- [ ] **Materiality Assessment** section present with:
  - Methodology description
  - Material topics list
  - Detailed findings

- [ ] **Emission Calculations** section present with:
  - Scope 1, 2, 3 details
  - Total emissions

- [ ] **Data Integrity** section present with:
  - DatasetVersion linkage
  - Immutability statement
  - Traceability statement
  - Limitations and warnings

- [ ] **Compliance Summary** section present with:
  - Framework alignment
  - Sections present list
  - Disclosures

- [ ] **Assumptions** section present with:
  - All assumptions used in calculations
  - Each assumption includes: id, description, source, impact, sensitivity

**Expected Sections:**
```
1. metadata
2. executive_summary
3. materiality_assessment
4. emission_calculations
5. data_integrity
6. compliance_summary
7. assumptions
```

---

### ✅ Assumptions Documented

**Description:** All assumptions used in materiality assessment and emission calculations are explicitly documented.

**Verification:**
- [ ] Report contains `assumptions` array
- [ ] Each assumption includes all required fields:
  - `id`: Unique identifier
  - `description`: Clear description of the assumption
  - `source`: Source of the assumption (config parameter, engine convention, etc.)
  - `impact`: How the assumption affects the results
  - `sensitivity`: Sensitivity analysis (High/Medium/Low)

**Common Assumptions:**
- Carbon price assumption (default: 100 EUR/tCO2e)
- Emission factor assumptions (if using activity data)
- Materiality threshold assumptions
- Unit convention assumptions

**Expected Output:**
```json
{
  "assumptions": [
    {
      "id": "assumption_carbon_price",
      "description": "Carbon price used to translate emissions into financial exposure.",
      "source": "Config parameter carbon_price_eur_per_tco2e (default 100 EUR/tCO2e)",
      "impact": "Directly affects estimated financial exposure for emissions.",
      "sensitivity": "High - linear with carbon price."
    },
    ...
  ]
}
```

**Additional Verification:**
- Assumptions are included in evidence payloads (query evidence_records)
- Assumptions are traceable to specific findings via evidence links

---

## Compliance Status Summary

After completing all checklist items, document your compliance status:

- **Materiality Assessment Completed**: [✅ Yes / ❌ No]
- **Emission Factors Calculated**: [✅ Yes / ❌ No]
- **Evidence Linked to DatasetVersion**: [✅ Yes / ❌ No]
- **Report Sections Generated**: [✅ Yes / ❌ No]
- **Assumptions Documented**: [✅ Yes / ❌ No]

**Overall Compliance Status:** [✅ Compliant / ❌ Non-Compliant]

---

## Notes

- All checklist items must be marked as **Yes** for full CSRD compliance
- Evidence linking is critical for audit-readiness and regulatory compliance
- Assumptions must be explicitly documented per ESRS requirements
- DatasetVersion immutability ensures data integrity throughout the reporting process

---

**Last Updated:** 2025-01-XX  
**Engine Version:** CSRD Engine v1  
**ESRS Alignment:** v0-skeleton
