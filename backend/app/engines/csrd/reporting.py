from __future__ import annotations


def generate_esrs_report(
    *,
    report_id: str,
    dataset_version_id: str,
    material_findings: list[dict],
    emissions: dict,
    assumptions: list[dict],
    parameters: dict,
    generated_at: str,
    warnings: list[str],
) -> dict:
    topic_ids = ("board_diversity", "esg_governance")
    material_topics = [
        {"id": f.get("metric"), "is_material": bool(f.get("is_material"))}
        for f in material_findings
        if f.get("metric") in topic_ids
    ]
    executive_summary = {
        "high_level": "Double materiality assessment and emissions summary produced from ingested datasets.",
        "material_topics_count": len([f for f in material_findings if f.get("is_material")]),
        "total_emissions_tco2e": emissions.get("total_emissions_tco2e", 0.0),
    }

    data_integrity = {
        "dataset_version_id": dataset_version_id,
        "immutability": "Anchored to DatasetVersion; core records are write-once.",
        "traceability": "Findings are linked to source RawRecords and EvidenceRecords.",
        "limitations": parameters.get("limitations", "Input completeness and factor selection affect results."),
        "warnings": warnings,
    }

    compliance_summary = {
        "framework": "ESRS-aligned structure (skeleton)",
        "sections_present": [
            "executive_summary",
            "materiality_assessment",
            "data_integrity",
            "compliance_summary",
        ],
        "disclosures": parameters.get("disclosures", []),
    }

    return {
        "metadata": {
            "report_id": report_id,
            "dataset_version_id": dataset_version_id,
            "generated_at": generated_at,
            "standard": "ESRS",
            "version": "v0-skeleton",
        },
        "executive_summary": executive_summary,
        "materiality_assessment": {
            "methodology": "Double materiality (financial + impact) with configurable thresholds.",
            "material_topics": material_topics,
            "findings": material_findings,
        },
        "emission_calculations": emissions,
        "data_integrity": data_integrity,
        "compliance_summary": compliance_summary,
        "assumptions": assumptions,
    }
