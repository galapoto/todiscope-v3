"""
Intercompany Visibility Flags for Engine #2

FF-4: Mark findings involving intercompany counterparties.
No netting or elimination logic.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class IntercompanyFlag:
    """
    Intercompany visibility flag.
    
    Marks findings involving intercompany counterparties for visibility only.
    No netting, elimination, or consolidation logic.
    """
    is_intercompany: bool
    counterparty_ids: list[str]  # Counterparty IDs involved
    detection_method: str  # How intercompany was detected (e.g., "counterparty_master", "account_pattern", "explicit_tag")
    detection_source: str  # Source of detection (e.g., "run_parameters", "canonical_field", "master_data")


def detect_intercompany(
    *,
    counterparty_id: str,
    counterparty_master: dict[str, Any] | None = None,
    account_patterns: list[str] | None = None,
    explicit_tags: list[str] | None = None,
) -> IntercompanyFlag:
    """
    Detect if a counterparty is intercompany.
    
    Detection methods (in priority order):
    1. Explicit tags (if provided)
    2. Counterparty master data (if provided)
    3. Account patterns (if provided)
    
    Args:
        counterparty_id: Counterparty ID to check
        counterparty_master: Optional master data dict with 'is_intercompany' flag
        account_patterns: Optional list of account patterns that indicate intercompany
        explicit_tags: Optional list of explicit intercompany tags
    
    Returns:
        IntercompanyFlag with detection result
    
    Note:
        This is visibility-only detection. No elimination or netting logic.
    """
    # Priority 1: Explicit tags
    if explicit_tags and counterparty_id in explicit_tags:
        return IntercompanyFlag(
            is_intercompany=True,
            counterparty_ids=[counterparty_id],
            detection_method="explicit_tag",
            detection_source="run_parameters",
        )
    
    # Priority 2: Counterparty master data
    if counterparty_master and counterparty_master.get("is_intercompany", False):
        return IntercompanyFlag(
            is_intercompany=True,
            counterparty_ids=[counterparty_id],
            detection_method="counterparty_master",
            detection_source="master_data",
        )
    
    # Priority 3: Account patterns (if counterparty matches pattern)
    if account_patterns:
        # Simple pattern matching (can be extended)
        for pattern in account_patterns:
            if pattern in counterparty_id or counterparty_id.startswith(pattern):
                return IntercompanyFlag(
                    is_intercompany=True,
                    counterparty_ids=[counterparty_id],
                    detection_method="account_pattern",
                    detection_source="run_parameters",
                )
    
    # Default: not intercompany
    return IntercompanyFlag(
        is_intercompany=False,
        counterparty_ids=[counterparty_id],
        detection_method="none",
        detection_source="default",
    )


def flag_multiple_counterparties(
    *,
    counterparty_ids: list[str],
    counterparty_master: dict[str, dict[str, Any]] | None = None,
    account_patterns: list[str] | None = None,
    explicit_tags: list[str] | None = None,
) -> IntercompanyFlag:
    """
    Detect if any counterparties in a list are intercompany.
    
    Args:
        counterparty_ids: List of counterparty IDs to check
        counterparty_master: Optional master data dict keyed by counterparty_id
        account_patterns: Optional list of account patterns
        explicit_tags: Optional list of explicit intercompany tags
    
    Returns:
        IntercompanyFlag with detection result for all counterparties
    """
    intercompany_ids = []
    
    for cp_id in counterparty_ids:
        flag = detect_intercompany(
            counterparty_id=cp_id,
            counterparty_master=counterparty_master.get(cp_id) if counterparty_master else None,
            account_patterns=account_patterns,
            explicit_tags=explicit_tags,
        )
        if flag.is_intercompany:
            intercompany_ids.append(cp_id)
    
    if intercompany_ids:
        # Determine detection method (prefer explicit > master > pattern)
        detection_method = "explicit_tag"
        detection_source = "run_parameters"
        
        if not explicit_tags:
            detection_method = "counterparty_master"
            detection_source = "master_data"
        elif not counterparty_master:
            detection_method = "account_pattern"
            detection_source = "run_parameters"
        
        return IntercompanyFlag(
            is_intercompany=True,
            counterparty_ids=intercompany_ids,
            detection_method=detection_method,
            detection_source=detection_source,
        )
    
    return IntercompanyFlag(
        is_intercompany=False,
        counterparty_ids=counterparty_ids,
        detection_method="none",
        detection_source="default",
    )


