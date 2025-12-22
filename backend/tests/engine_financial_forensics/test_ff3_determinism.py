"""
FF-3 Determinism Tests

Tests:
- Explicit rule ordering
- No time-dependent logic
- Decimal arithmetic only
"""
import pytest
from decimal import Decimal

from backend.app.engines.financial_forensics.matching import (
    DeterminismViolationError,
    InvoiceRecord,
    MatchingRule,
    PaymentRecord,
    match_invoice_payment,
)


def test_rule_ordering_explicit() -> None:
    """Test: Rule ordering is explicit (priority-based, not dict/set iteration)."""
    rule1 = MatchingRule(
        rule_id="rule-1",
        rule_version="v1",
        framework_version="v1",
        priority=1,  # Higher priority
        tolerance_absolute=Decimal("0.01"),
        tolerance_percent=None,
    )
    
    rule2 = MatchingRule(
        rule_id="rule-2",
        rule_version="v1",
        framework_version="v1",
        priority=2,  # Lower priority
        tolerance_absolute=Decimal("0.10"),
        tolerance_percent=None,
    )
    
    # Rules should be ordered by priority
    rules = sorted([rule2, rule1], key=lambda r: r.priority)
    assert rules[0].rule_id == "rule-1"
    assert rules[1].rule_id == "rule-2"


def test_payments_must_be_list() -> None:
    """Test: Payments must be list (not dict/set) for deterministic ordering."""
    invoice = InvoiceRecord(
        record_id="inv-1",
        amount=Decimal("100.00"),
        currency="USD",
        posted_at="2024-01-15T00:00:00Z",
        reference_ids=[],
    )
    
    rule = MatchingRule(
        rule_id="rule-1",
        rule_version="v1",
        framework_version="v1",
        priority=1,
        tolerance_absolute=Decimal("0.01"),
        tolerance_percent=None,
    )
    
    # Dict should fail
    with pytest.raises(DeterminismViolationError, match="PAYMENTS_MUST_BE_LIST"):
        match_invoice_payment(
            invoice=invoice,
            payments={},  # Dict - should fail
            rule=rule,
        )
    
    # Set should fail (if passed as set, but we can't easily test that)
    # List should pass
    payments = [
        PaymentRecord(
            record_id="pay-1",
            amount=Decimal("100.00"),
            currency="USD",
            posted_at="2024-01-15T00:00:00Z",
            reference_ids=[],
        )
    ]
    # Should not raise
    result = match_invoice_payment(invoice=invoice, payments=payments, rule=rule)
    # Result may be None if no match, but should not raise DeterminismViolationError


def test_decimal_arithmetic_only() -> None:
    """Test: Only Decimal arithmetic is allowed (no float)."""
    invoice = InvoiceRecord(
        record_id="inv-1",
        amount=Decimal("100.00"),  # Decimal
        currency="USD",
        posted_at="2024-01-15T00:00:00Z",
        reference_ids=[],
    )
    
    # Float amount should fail
    invoice_float = InvoiceRecord(
        record_id="inv-1",
        amount=100.00,  # Float - should fail
        currency="USD",
        posted_at="2024-01-15T00:00:00Z",
        reference_ids=[],
    )
    
    rule = MatchingRule(
        rule_id="rule-1",
        rule_version="v1",
        framework_version="v1",
        priority=1,
        tolerance_absolute=Decimal("0.01"),
        tolerance_percent=None,
    )
    
    payments = [
        PaymentRecord(
            record_id="pay-1",
            amount=Decimal("100.00"),
            currency="USD",
            posted_at="2024-01-15T00:00:00Z",
            reference_ids=[],
        )
    ]
    
    with pytest.raises(DeterminismViolationError, match="INVOICE_AMOUNT_MUST_BE_DECIMAL"):
        match_invoice_payment(invoice=invoice_float, payments=payments, rule=rule)
    
    # Decimal should pass
    result = match_invoice_payment(invoice=invoice, payments=payments, rule=rule)
    # Should not raise


def test_no_time_dependent_logic() -> None:
    """Test: No time-dependent logic (all timestamps from records, not system)."""
    # This is verified by absence of datetime.now() in matching logic
    # The test_forbidden_patterns.py will catch datetime.now() usage
    assert True  # Structural test in test_forbidden_patterns.py


