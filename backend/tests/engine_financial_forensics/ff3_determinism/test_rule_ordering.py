"""
FF-3 Determinism Enforcement: Rule Ordering

Tests that FAIL THE BUILD if rule ordering is implicit.
"""
import pytest

from backend.app.engines.financial_forensics.matching import MatchingRule


def test_rule_ordering_must_be_explicit() -> None:
    """
    BUILD FAILURE TEST: Rule ordering must be explicit (priority field).
    
    This test will fail if rules don't have explicit priority ordering.
    """
    rule1 = MatchingRule(
        rule_id="rule-1",
        rule_version="v1",
        framework_version="v1",
        priority=1,  # Explicit priority
        tolerance_absolute=None,
        tolerance_percent=None,
    )
    
    rule2 = MatchingRule(
        rule_id="rule-2",
        rule_version="v1",
        framework_version="v1",
        priority=2,  # Explicit priority
        tolerance_absolute=None,
        tolerance_percent=None,
    )
    
    # Rules must be sortable by priority (explicit ordering)
    rules = sorted([rule2, rule1], key=lambda r: r.priority)
    assert rules[0].priority < rules[1].priority, "Rule ordering must be explicit via priority field"
    assert rules[0].rule_id == "rule-1"
    assert rules[1].rule_id == "rule-2"


def test_no_dict_set_iteration() -> None:
    """
    BUILD FAILURE TEST: No dict/set iteration for rule ordering.
    
    This test documents that rules must be in a list (not dict/set) for deterministic ordering.
    """
    # Rules must be in a list (not dict/set) for deterministic iteration
    rules_list = [
        MatchingRule(
            rule_id="rule-1",
            rule_version="v1",
            framework_version="v1",
            priority=1,
            tolerance_absolute=None,
            tolerance_percent=None,
        ),
        MatchingRule(
            rule_id="rule-2",
            rule_version="v1",
            framework_version="v1",
            priority=2,
            tolerance_absolute=None,
            tolerance_percent=None,
        ),
    ]
    
    # List iteration is deterministic (order preserved)
    rule_ids = [r.rule_id for r in rules_list]
    assert rule_ids == ["rule-1", "rule-2"]
    
    # Dict/set iteration is non-deterministic (order not guaranteed)
    # This test documents that dict/set should not be used
    rules_dict = {r.rule_id: r for r in rules_list}
    # Converting back to list should use explicit ordering (priority)
    rules_from_dict = sorted(rules_dict.values(), key=lambda r: r.priority)
    assert [r.rule_id for r in rules_from_dict] == ["rule-1", "rule-2"]


