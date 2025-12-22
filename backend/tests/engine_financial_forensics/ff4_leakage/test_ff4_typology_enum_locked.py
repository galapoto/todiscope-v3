from backend.app.engines.financial_forensics.leakage.typology import LeakageTypology


def test_leakage_typology_enum_locked_v1() -> None:
    expected = {
        "unmatched_invoice",
        "unmatched_payment",
        "overpayment",
        "underpayment",
        "timing_mismatch",
        "partial_settlement_residual",
    }
    actual = {t.value for t in LeakageTypology}
    assert actual == expected

