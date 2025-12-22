from __future__ import annotations

from dataclasses import dataclass

from backend.app.engines.financial_forensics.matching.framework import (
    CanonicalInput,
    MatchOutcome,
    MatchingRule,
    RuleContext,
)


@dataclass(frozen=True)
class OrchestrationLog:
    rule_id: str
    rule_version: str
    outcomes_emitted: int
    outcomes_applied: int


def _outcome_sort_key(outcome: MatchOutcome) -> tuple:
    return (outcome.rule_id, outcome.rule_version, outcome.matched_record_ids)


def run_matching(
    *,
    context: RuleContext,
    records: tuple[CanonicalInput, ...],
    rules: tuple[MatchingRule, ...],
) -> tuple[list[MatchOutcome], list[OrchestrationLog]]:
    """
    Deterministic matching orchestrator.

    Properties:
    - Explicit rule order (rules are applied in tuple order)
    - first-match-wins across rules (once a record_id is claimed, later outcomes cannot use it)
    - deterministic candidate iteration (records are passed sorted; outcomes are applied sorted)
    """
    records_sorted = tuple(sorted(records, key=lambda r: r.record_id))
    used_record_ids: set[str] = set()

    all_outcomes: list[MatchOutcome] = []
    logs: list[OrchestrationLog] = []

    for rule in rules:
        proposed = rule.apply(context=context, records=records_sorted, used_record_ids=set(used_record_ids))
        proposed_sorted = sorted(proposed, key=_outcome_sort_key)

        applied = 0
        for outcome in proposed_sorted:
            if any(rid in used_record_ids for rid in outcome.matched_record_ids):
                continue
            for rid in outcome.matched_record_ids:
                used_record_ids.add(rid)
            all_outcomes.append(outcome)
            applied += 1

        logs.append(
            OrchestrationLog(
                rule_id=rule.rule_id,
                rule_version=rule.rule_version,
                outcomes_emitted=len(proposed_sorted),
                outcomes_applied=applied,
            )
        )

    return all_outcomes, logs

