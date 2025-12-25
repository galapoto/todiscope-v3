"""
Evidence Creation for Credit Readiness and Capital Raising Strategies

This module provides functions for creating evidence records that are bound
to DatasetVersion and follow the append-only immutability pattern.

Platform Law Compliance:
- All evidence is bound to DatasetVersion
- Evidence creation is idempotent and deterministic
- Evidence IDs are derived from stable keys
- No mutation operations (append-only)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.evidence.service import create_evidence, deterministic_evidence_id


ENGINE_ID = "engine_enterprise_capital_debt_readiness"
_EVIDENCE_CREATED_AT = datetime(2000, 1, 1, tzinfo=timezone.utc)


async def create_credit_readiness_evidence(
    db: AsyncSession,
    *,
    dataset_version_id: str,
    stable_key: str,
    credit_readiness_data: dict[str, Any],
) -> str:
    """
    Create evidence record for credit readiness assessment.
    
    Args:
        db: Database session
        dataset_version_id: DatasetVersion ID (UUIDv7)
        stable_key: Stable key for deterministic evidence ID generation
        credit_readiness_data: Credit readiness calculation results
    
    Returns:
        Evidence ID (deterministic UUIDv5)
    """
    evidence_id = deterministic_evidence_id(
        dataset_version_id=dataset_version_id,
        engine_id=ENGINE_ID,
        kind="credit_readiness",
        stable_key=stable_key,
    )
    
    await create_evidence(
        db,
        evidence_id=evidence_id,
        dataset_version_id=dataset_version_id,
        engine_id=ENGINE_ID,
        kind="credit_readiness",
        payload={
            "assessment_type": "credit_readiness",
            "data": credit_readiness_data,
        },
        created_at=_EVIDENCE_CREATED_AT,
    )
    
    return evidence_id


async def create_capital_strategy_evidence(
    db: AsyncSession,
    *,
    dataset_version_id: str,
    stable_key: str,
    capital_strategy_data: dict[str, Any],
) -> str:
    """
    Create evidence record for capital raising strategy assessment.
    
    Args:
        db: Database session
        dataset_version_id: DatasetVersion ID (UUIDv7)
        stable_key: Stable key for deterministic evidence ID generation
        capital_strategy_data: Capital strategy calculation results
    
    Returns:
        Evidence ID (deterministic UUIDv5)
    """
    evidence_id = deterministic_evidence_id(
        dataset_version_id=dataset_version_id,
        engine_id=ENGINE_ID,
        kind="capital_strategy",
        stable_key=stable_key,
    )
    
    await create_evidence(
        db,
        evidence_id=evidence_id,
        dataset_version_id=dataset_version_id,
        engine_id=ENGINE_ID,
        kind="capital_strategy",
        payload={
            "assessment_type": "capital_strategy",
            "data": capital_strategy_data,
        },
        created_at=_EVIDENCE_CREATED_AT,
    )
    
    return evidence_id


async def create_debt_capacity_evidence(
    db: AsyncSession,
    *,
    dataset_version_id: str,
    stable_key: str,
    debt_capacity_data: dict[str, Any],
) -> str:
    """
    Create evidence record for debt capacity assessment.
    
    Args:
        db: Database session
        dataset_version_id: DatasetVersion ID (UUIDv7)
        stable_key: Stable key for deterministic evidence ID generation
        debt_capacity_data: Debt capacity calculation results
    
    Returns:
        Evidence ID (deterministic UUIDv5)
    """
    evidence_id = deterministic_evidence_id(
        dataset_version_id=dataset_version_id,
        engine_id=ENGINE_ID,
        kind="debt_capacity",
        stable_key=stable_key,
    )
    
    await create_evidence(
        db,
        evidence_id=evidence_id,
        dataset_version_id=dataset_version_id,
        engine_id=ENGINE_ID,
        kind="debt_capacity",
        payload={
            "assessment_type": "debt_capacity",
            "data": debt_capacity_data,
        },
        created_at=_EVIDENCE_CREATED_AT,
    )
    
    return evidence_id


async def create_equity_capacity_evidence(
    db: AsyncSession,
    *,
    dataset_version_id: str,
    stable_key: str,
    equity_capacity_data: dict[str, Any],
) -> str:
    """
    Create evidence record for equity capacity assessment.
    
    Args:
        db: Database session
        dataset_version_id: DatasetVersion ID (UUIDv7)
        stable_key: Stable key for deterministic evidence ID generation
        equity_capacity_data: Equity capacity calculation results
    
    Returns:
        Evidence ID (deterministic UUIDv5)
    """
    evidence_id = deterministic_evidence_id(
        dataset_version_id=dataset_version_id,
        engine_id=ENGINE_ID,
        kind="equity_capacity",
        stable_key=stable_key,
    )
    
    await create_evidence(
        db,
        evidence_id=evidence_id,
        dataset_version_id=dataset_version_id,
        engine_id=ENGINE_ID,
        kind="equity_capacity",
        payload={
            "assessment_type": "equity_capacity",
            "data": equity_capacity_data,
        },
        created_at=_EVIDENCE_CREATED_AT,
    )
    
    return evidence_id


async def create_financial_market_access_evidence(
    db: AsyncSession,
    *,
    dataset_version_id: str,
    stable_key: str,
    market_access_data: dict[str, Any],
) -> str:
    """
    Create evidence record for financial market access assessment.
    
    Args:
        db: Database session
        dataset_version_id: DatasetVersion ID (UUIDv7)
        stable_key: Stable key for deterministic evidence ID generation
        market_access_data: Market access assessment results
    
    Returns:
        Evidence ID (deterministic UUIDv5)
    """
    evidence_id = deterministic_evidence_id(
        dataset_version_id=dataset_version_id,
        engine_id=ENGINE_ID,
        kind="financial_market_access",
        stable_key=stable_key,
    )
    
    await create_evidence(
        db,
        evidence_id=evidence_id,
        dataset_version_id=dataset_version_id,
        engine_id=ENGINE_ID,
        kind="financial_market_access",
        payload={
            "assessment_type": "financial_market_access",
            "data": market_access_data,
        },
        created_at=_EVIDENCE_CREATED_AT,
    )
    
    return evidence_id






