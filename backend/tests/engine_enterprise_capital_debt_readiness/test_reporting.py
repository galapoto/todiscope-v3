from decimal import Decimal

from backend.app.engines.enterprise_capital_debt_readiness.reporting import (
    DEFAULT_SCENARIOS,
    generate_executive_report,
)


def _dummy_readiness_result() -> dict[str, object]:
    return {
        "readiness_score": 78.25,
        "readiness_level": "good",
        "component_scores": {
            "capital_adequacy": 72.0,
            "debt_service": 70.0,
            "credit_risk": 66.0,
            "financial_forensics": 74.0,
            "deal_readiness": 80.0,
        },
        "credit_risk_details": {"risk_level": "moderate"},
        "breakdown": {
            "capital_adequacy_level": "adequate",
            "debt_service_level": "adequate",
            "credit_risk_level": "moderate",
            "debt_to_equity_category": "moderate_risk",
            "interest_coverage_category": "good",
            "liquidity_category": "adequate",
            "dscr_category": "good",
        },
    }


def test_generate_executive_report_structure() -> None:
    readiness_result = _dummy_readiness_result()
    capital_payload = {"coverage_ratio": 1.25, "flags": ["CAP_FLAG"]}
    debt_service = {"dscr": 1.8, "interest_coverage": 8.5, "flags": ["DS_FLAG"]}
    assumptions = {}
    cross_engine_data = {
        "financial_forensics": {"total_leakage_exposure": Decimal("500000"), "findings_count": 3},
        "deal_readiness": {"readiness_score": Decimal("82"), "high_findings": 1, "readiness_status": "ready"},
    }
    findings = [{"id": "f_cap"}, {"id": "f_dts"}]
    evidence_ids = ["cap_ev", "debt_ev", "readiness_ev", "scenario_ev", "summary_ev"]

    report = generate_executive_report(
        dataset_version_id="dv_report",
        generated_at="2025-01-01T00:00:00Z",
        readiness_result=readiness_result,
        capital_adequacy=capital_payload,
        debt_service=debt_service,
        assumptions=assumptions,
        cross_engine_data=cross_engine_data,
        findings=findings,
        evidence_ids=evidence_ids,
    )

    assert report["metadata"]["report_type"] == "executive_readiness"
    assert report["executive_summary"]["title"].lower().startswith("enterprise")
    assert len(report["scenario_insights"]) == len(DEFAULT_SCENARIOS)
    assert report["findings_summary"]["count"] == len(findings)
    assert report["findings_summary"]["linked_evidence"] == evidence_ids
    assert "risk_assessment" in report
