# Example ESRS Report Template (CSRD Engine Output)

This template matches the structure produced by `engine_csrd` (`POST /api/v3/engines/csrd/run`).

## JSON Skeleton
```json
{
  "metadata": {
    "report_id": "string",
    "dataset_version_id": "string",
    "generated_at": "YYYY-MM-DDTHH:MM:SS+00:00",
    "standard": "ESRS",
    "version": "v0-skeleton"
  },
  "executive_summary": {
    "high_level": "string",
    "material_topics_count": 0,
    "total_emissions_tco2e": 0.0
  },
  "materiality_assessment": {
    "methodology": "string",
    "material_topics": [
      { "id": "board_diversity", "is_material": true },
      { "id": "esg_governance", "is_material": false }
    ],
    "findings": [
      {
        "id": "string",
        "dataset_version_id": "string",
        "title": "string",
        "category": "string",
        "metric": "string",
        "description": "string",
        "value": 0.0,
        "threshold": 0.0,
        "is_material": true,
        "materiality": "material",
        "financial_impact_eur": 0.0,
        "impact_score": 0.0,
        "confidence": "low|medium|high"
      }
    ]
  },
  "emission_calculations": {
    "dataset_version_id": "string",
    "scopes": {
      "scope1": { "value": 0.0, "unit": "tCO2e", "source": "string", "methodology": "direct" },
      "scope2": { "value": 0.0, "unit": "tCO2e", "source": "string", "methodology": "market-based|location-based" },
      "scope3": { "value": 0.0, "unit": "tCO2e", "source": "string", "methodology": "value_chain" }
    },
    "total_emissions_tco2e": 0.0
  },
  "data_integrity": {
    "dataset_version_id": "string",
    "immutability": "string",
    "traceability": "string",
    "limitations": "string",
    "warnings": ["MISSING_ESG_EMISSIONS", "MISSING_FINANCIAL_DATA"]
  },
  "compliance_summary": {
    "framework": "string",
    "sections_present": ["executive_summary", "materiality_assessment", "data_integrity", "compliance_summary"],
    "disclosures": []
  },
  "assumptions": [
    {
      "id": "string",
      "description": "string",
      "source": "string",
      "impact": "string",
      "sensitivity": "string"
    }
  ]
}
```

## Notes
- **Traceability**: the report itself is stored as `EvidenceRecord(kind=\"report\")` with the same `dataset_version_id`.
- **Emissions**: emissions calculations are also stored as `EvidenceRecord(kind=\"emissions\")` including `source_raw_record_id`.
- **Findings**: each finding is stored as `FindingRecord` and linked to a corresponding `EvidenceRecord(kind=\"finding\")` via `FindingEvidenceLink`.

