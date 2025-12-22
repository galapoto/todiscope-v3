from decimal import Decimal

from backend.app.engines.financial_forensics.leakage.classifier import classify_finding
from backend.app.engines.financial_forensics.leakage.exposure import compute_exposure, compute_finding_exposure
from backend.app.engines.financial_forensics.leakage.rollups import roll_up
from backend.app.engines.financial_forensics.leakage.typology import LeakageTypology


def test_typology_assignment_deterministic() -> None:
    finding = {"finding_type": "tolerance_match"}
    evidence = {"amount_comparison": {"diff_converted": "0.50"}}
    res1 = classify_finding(finding=finding, evidence_payload=evidence)
    res2 = classify_finding(finding=finding, evidence_payload=evidence)
    assert res1 == res2
    assert res1.typology == LeakageTypology.UNDERPAYMENT


def test_exposure_math_rounding() -> None:
    out = compute_exposure(diff_converted=Decimal("0.555"), rounding_mode="ROUND_HALF_UP", rounding_quantum="0.01")
    assert out.exposure_signed == Decimal("0.56")
    assert out.exposure_abs == Decimal("0.56")


def test_partial_exposure_binds_to_unmatched_amount() -> None:
    finding = {"finding_type": "partial_match", "unmatched_amount": "12.345"}
    evidence = {"rule_identity": {"executed_parameters": {"rounding_mode": "ROUND_HALF_UP", "rounding_quantum": "0.01"}}}
    out = compute_finding_exposure(finding=finding, evidence_payload=evidence)
    assert out.exposure_abs == Decimal("12.35")


def test_non_partial_exposure_does_not_use_unmatched_amount() -> None:
    finding = {"finding_type": "exact_match", "unmatched_amount": "999.99"}
    evidence = {
        "rule_identity": {"executed_parameters": {"rounding_mode": "ROUND_HALF_UP", "rounding_quantum": "0.01"}},
        "amount_comparison": {"diff_converted": "1.23"},
    }
    out = compute_finding_exposure(finding=finding, evidence_payload=evidence)
    assert out.exposure_abs == Decimal("1.23")


def test_rollups_stable() -> None:
    classified = [
        {"typology": "underpayment", "exposure_abs": "1.00"},
        {"typology": "underpayment", "exposure_abs": "2.00"},
        {"typology": "overpayment", "exposure_abs": "3.00"},
    ]
    rollups = roll_up(classified=classified)
    assert rollups.total_findings == 3
    assert rollups.total_exposure_abs == Decimal("6.00")
    assert [r.typology.value for r in rollups.by_typology] == ["overpayment", "underpayment"]
    by = {r.typology.value: (r.finding_count, r.total_exposure_abs) for r in rollups.by_typology}
    assert by["underpayment"] == (2, Decimal("3.00"))
    assert by["overpayment"] == (1, Decimal("3.00"))
