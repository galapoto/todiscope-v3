from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.evidence.models import EvidenceRecord
from backend.app.core.evidence.service import deterministic_evidence_id
from backend.app.engines.enterprise_distressed_asset_debt_stress.errors import (
    ImmutableConflictError,
    ScenarioNotFoundError,
)
from backend.app.engines.enterprise_distressed_asset_debt_stress.models import (
    Scenario,
    ScenarioExecution,
    ScenarioResult,
    StressAssumptions,
)


async def store_scenario(
    db: AsyncSession,
    *,
    scenario: Scenario,
    created_at: datetime,
) -> EvidenceRecord:
    """
    Store a scenario immutably in the evidence system.
    
    Args:
        db: Database session
        scenario: The scenario to store
        created_at: Timestamp when scenario was created
    
    Returns:
        EvidenceRecord containing the stored scenario
    
    Raises:
        ImmutableConflictError: If scenario already exists with different data
    """
    evidence_id = deterministic_evidence_id(
        dataset_version_id=scenario.dataset_version_id,
        engine_id="engine_enterprise_distressed_asset_debt_stress",
        kind="scenario",
        stable_key=scenario.scenario_id,
    )
    
    # Check for existing evidence
    existing = await db.scalar(
        select(EvidenceRecord).where(EvidenceRecord.evidence_id == evidence_id)
    )
    
    if existing is not None:
        # Verify immutability - must match exactly
        if existing.dataset_version_id != scenario.dataset_version_id:
            raise ImmutableConflictError("SCENARIO_DATASET_VERSION_MISMATCH")
        if existing.engine_id != "engine_enterprise_distressed_asset_debt_stress":
            raise ImmutableConflictError("SCENARIO_ENGINE_ID_MISMATCH")
        if existing.kind != "scenario":
            raise ImmutableConflictError("SCENARIO_KIND_MISMATCH")
        
        # Verify payload matches
        existing_payload = existing.payload
        scenario_payload = _scenario_to_payload(scenario)
        if existing_payload != scenario_payload:
            raise ImmutableConflictError("SCENARIO_PAYLOAD_MISMATCH")
        
        return existing
    
    # Create new evidence record
    from backend.app.core.evidence.service import create_evidence
    
    return await create_evidence(
        db,
        evidence_id=evidence_id,
        dataset_version_id=scenario.dataset_version_id,
        engine_id="engine_enterprise_distressed_asset_debt_stress",
        kind="scenario",
        payload=scenario_payload,
        created_at=created_at,
    )


async def store_scenario_execution(
    db: AsyncSession,
    *,
    execution: ScenarioExecution,
    created_at: datetime,
) -> EvidenceRecord:
    """
    Store a scenario execution immutably in the evidence system.
    
    Args:
        db: Database session
        execution: The execution to store
        created_at: Timestamp when execution was created
    
    Returns:
        EvidenceRecord containing the stored execution
    
    Raises:
        ImmutableConflictError: If execution already exists with different data
    """
    evidence_id = deterministic_evidence_id(
        dataset_version_id=execution.dataset_version_id,
        engine_id="engine_enterprise_distressed_asset_debt_stress",
        kind="scenario_execution",
        stable_key=execution.execution_id,
    )
    
    # Check for existing evidence
    existing = await db.scalar(
        select(EvidenceRecord).where(EvidenceRecord.evidence_id == evidence_id)
    )
    
    if existing is not None:
        # Verify immutability
        if existing.dataset_version_id != execution.dataset_version_id:
            raise ImmutableConflictError("EXECUTION_DATASET_VERSION_MISMATCH")
        if existing.engine_id != "engine_enterprise_distressed_asset_debt_stress":
            raise ImmutableConflictError("EXECUTION_ENGINE_ID_MISMATCH")
        if existing.kind != "scenario_execution":
            raise ImmutableConflictError("EXECUTION_KIND_MISMATCH")
        
        # Verify payload matches
        existing_payload = existing.payload
        execution_payload = _execution_to_payload(execution)
        if existing_payload != execution_payload:
            raise ImmutableConflictError("EXECUTION_PAYLOAD_MISMATCH")
        
        return existing
    
    # Create new evidence record
    from backend.app.core.evidence.service import create_evidence
    
    return await create_evidence(
        db,
        evidence_id=evidence_id,
        dataset_version_id=execution.dataset_version_id,
        engine_id="engine_enterprise_distressed_asset_debt_stress",
        kind="scenario_execution",
        payload=execution_payload,
        created_at=created_at,
    )


async def retrieve_scenario(
    db: AsyncSession,
    *,
    scenario_id: str,
    dataset_version_id: str,
) -> Scenario:
    """
    Retrieve a stored scenario.
    
    Args:
        db: Database session
        scenario_id: The scenario ID to retrieve
        dataset_version_id: The dataset version ID (for validation)
    
    Returns:
        The retrieved Scenario
    
    Raises:
        ScenarioNotFoundError: If scenario is not found
    """
    evidence_id = deterministic_evidence_id(
        dataset_version_id=dataset_version_id,
        engine_id="engine_enterprise_distressed_asset_debt_stress",
        kind="scenario",
        stable_key=scenario_id,
    )
    
    evidence = await db.scalar(
        select(EvidenceRecord).where(EvidenceRecord.evidence_id == evidence_id)
    )
    
    if evidence is None:
        raise ScenarioNotFoundError(f"SCENARIO_NOT_FOUND: {scenario_id}")
    
    if evidence.dataset_version_id != dataset_version_id:
        raise ScenarioNotFoundError("SCENARIO_DATASET_VERSION_MISMATCH")
    
    return _payload_to_scenario(evidence.payload)


async def retrieve_scenario_execution(
    db: AsyncSession,
    *,
    execution_id: str,
    dataset_version_id: str,
) -> ScenarioExecution:
    """
    Retrieve a stored scenario execution.
    
    Args:
        db: Database session
        execution_id: The execution ID to retrieve
        dataset_version_id: The dataset version ID (for validation)
    
    Returns:
        The retrieved ScenarioExecution
    
    Raises:
        ScenarioNotFoundError: If execution is not found
    """
    evidence_id = deterministic_evidence_id(
        dataset_version_id=dataset_version_id,
        engine_id="engine_enterprise_distressed_asset_debt_stress",
        kind="scenario_execution",
        stable_key=execution_id,
    )
    
    evidence = await db.scalar(
        select(EvidenceRecord).where(EvidenceRecord.evidence_id == evidence_id)
    )
    
    if evidence is None:
        raise ScenarioNotFoundError(f"EXECUTION_NOT_FOUND: {execution_id}")
    
    if evidence.dataset_version_id != dataset_version_id:
        raise ScenarioNotFoundError("EXECUTION_DATASET_VERSION_MISMATCH")
    
    return _payload_to_execution(evidence.payload)


async def replay_scenario(
    db: AsyncSession,
    *,
    scenario_id: str,
    dataset_version_id: str,
    financial_data: dict[str, Any],
    analysis_date: str,
    executed_by: str | None = None,
) -> ScenarioExecution:
    """
    Replay a stored scenario with the same assumptions.
    
    This ensures that a scenario can be re-executed exactly with the same
    dataset and assumptions, providing full traceability.
    
    Args:
        db: Database session
        scenario_id: The scenario ID to replay
        dataset_version_id: The dataset version ID
        financial_data: Financial data to use for execution
        analysis_date: Analysis date (ISO format string)
        executed_by: Optional identifier of who replayed the scenario
    
    Returns:
        The re-executed ScenarioExecution
    
    Raises:
        ScenarioNotFoundError: If scenario is not found
    """
    from datetime import datetime
    
    # Retrieve the original scenario
    scenario = await retrieve_scenario(
        db,
        scenario_id=scenario_id,
        dataset_version_id=dataset_version_id,
    )
    
    # Parse analysis date
    try:
        analysis_date_obj = datetime.fromisoformat(analysis_date.replace("Z", "+00:00")).date()
    except (ValueError, AttributeError):
        from datetime import date
        analysis_date_obj = date.today()
    
    # Re-execute the scenario
    from backend.app.engines.enterprise_distressed_asset_debt_stress.scenario_execution import (
        execute_scenario,
    )
    
    execution = execute_scenario(
        scenario=scenario,
        financial_data=financial_data,
        analysis_date=analysis_date_obj,
        executed_by=executed_by,
    )
    
    return execution


def _scenario_to_payload(scenario: Scenario) -> dict[str, Any]:
    """Convert Scenario to dictionary payload."""
    return {
        "scenario_id": scenario.scenario_id,
        "dataset_version_id": scenario.dataset_version_id,
        "scenario_name": scenario.scenario_name,
        "description": scenario.description,
        "time_horizon_months": scenario.time_horizon_months,
        "assumptions": {
            "revenue_change_factor": str(scenario.assumptions.revenue_change_factor),
            "cost_change_factor": str(scenario.assumptions.cost_change_factor),
            "interest_rate_change_factor": str(scenario.assumptions.interest_rate_change_factor),
            "liquidity_shock_factor": str(scenario.assumptions.liquidity_shock_factor),
            "market_value_depreciation_factor": str(scenario.assumptions.market_value_depreciation_factor),
            "collection_period_extension_days": scenario.assumptions.collection_period_extension_days,
            "payment_period_reduction_days": scenario.assumptions.payment_period_reduction_days,
        },
        "created_at": scenario.created_at,
        "created_by": scenario.created_by,
    }


def _payload_to_scenario(payload: dict[str, Any]) -> Scenario:
    """Convert dictionary payload to Scenario."""
    from decimal import Decimal
    
    assumptions_dict = payload["assumptions"]
    assumptions = StressAssumptions(
        revenue_change_factor=Decimal(str(assumptions_dict["revenue_change_factor"])),
        cost_change_factor=Decimal(str(assumptions_dict["cost_change_factor"])),
        interest_rate_change_factor=Decimal(str(assumptions_dict["interest_rate_change_factor"])),
        liquidity_shock_factor=Decimal(str(assumptions_dict["liquidity_shock_factor"])),
        market_value_depreciation_factor=Decimal(str(assumptions_dict["market_value_depreciation_factor"])),
        collection_period_extension_days=int(assumptions_dict["collection_period_extension_days"]),
        payment_period_reduction_days=int(assumptions_dict["payment_period_reduction_days"]),
    )
    
    return Scenario(
        scenario_id=payload["scenario_id"],
        dataset_version_id=payload["dataset_version_id"],
        scenario_name=payload["scenario_name"],
        description=payload["description"],
        time_horizon_months=int(payload["time_horizon_months"]),
        assumptions=assumptions,
        created_at=payload["created_at"],
        created_by=payload.get("created_by"),
    )


def _execution_to_payload(execution: ScenarioExecution) -> dict[str, Any]:
    """Convert ScenarioExecution to dictionary payload."""
    from decimal import Decimal
    
    return {
        "execution_id": execution.execution_id,
        "scenario_id": execution.scenario_id,
        "dataset_version_id": execution.dataset_version_id,
        "executed_at": execution.executed_at,
        "executed_by": execution.executed_by,
        "assumptions_used": {
            "revenue_change_factor": str(execution.assumptions_used.revenue_change_factor),
            "cost_change_factor": str(execution.assumptions_used.cost_change_factor),
            "interest_rate_change_factor": str(execution.assumptions_used.interest_rate_change_factor),
            "liquidity_shock_factor": str(execution.assumptions_used.liquidity_shock_factor),
            "market_value_depreciation_factor": str(execution.assumptions_used.market_value_depreciation_factor),
            "collection_period_extension_days": execution.assumptions_used.collection_period_extension_days,
            "payment_period_reduction_days": execution.assumptions_used.payment_period_reduction_days,
        },
        "period_results": [_period_result_to_payload(pr) for pr in execution.period_results],
        "summary": execution.summary,
    }


def _payload_to_execution(payload: dict[str, Any]) -> ScenarioExecution:
    """Convert dictionary payload to ScenarioExecution."""
    from decimal import Decimal
    from datetime import date
    
    assumptions_dict = payload["assumptions_used"]
    assumptions = StressAssumptions(
        revenue_change_factor=Decimal(str(assumptions_dict["revenue_change_factor"])),
        cost_change_factor=Decimal(str(assumptions_dict["cost_change_factor"])),
        interest_rate_change_factor=Decimal(str(assumptions_dict["interest_rate_change_factor"])),
        liquidity_shock_factor=Decimal(str(assumptions_dict["liquidity_shock_factor"])),
        market_value_depreciation_factor=Decimal(str(assumptions_dict["market_value_depreciation_factor"])),
        collection_period_extension_days=int(assumptions_dict["collection_period_extension_days"]),
        payment_period_reduction_days=int(assumptions_dict["payment_period_reduction_days"]),
    )
    
    period_results = [
        _payload_to_period_result(pr_payload)
        for pr_payload in payload["period_results"]
    ]
    
    return ScenarioExecution(
        execution_id=payload["execution_id"],
        scenario_id=payload["scenario_id"],
        dataset_version_id=payload["dataset_version_id"],
        executed_at=payload["executed_at"],
        executed_by=payload.get("executed_by"),
        assumptions_used=assumptions,
        period_results=period_results,
        summary=payload["summary"],
    )


def _period_result_to_payload(period_result: PeriodResult) -> dict[str, Any]:
    """Convert PeriodResult to dictionary payload."""
    return {
        "period_month": period_result.period_month,
        "period_date": period_result.period_date.isoformat(),
        "exposure_changes": [_exposure_change_to_payload(ec) for ec in period_result.exposure_changes],
        "cash_shortfalls": [_cash_shortfall_to_payload(cs) for cs in period_result.cash_shortfalls],
        "debt_service_coverage": _debt_service_coverage_to_payload(period_result.debt_service_coverage),
        "cumulative_exposure_change": str(period_result.cumulative_exposure_change),
        "cumulative_cash_shortfall": str(period_result.cumulative_cash_shortfall),
    }


def _payload_to_period_result(payload: dict[str, Any]) -> PeriodResult:
    """Convert dictionary payload to PeriodResult."""
    from decimal import Decimal
    from datetime import date
    
    return PeriodResult(
        period_month=int(payload["period_month"]),
        period_date=date.fromisoformat(payload["period_date"]),
        exposure_changes=[
            _payload_to_exposure_change(ec_payload)
            for ec_payload in payload["exposure_changes"]
        ],
        cash_shortfalls=[
            _payload_to_cash_shortfall(cs_payload)
            for cs_payload in payload["cash_shortfalls"]
        ],
        debt_service_coverage=_payload_to_debt_service_coverage(payload["debt_service_coverage"]),
        cumulative_exposure_change=Decimal(str(payload["cumulative_exposure_change"])),
        cumulative_cash_shortfall=Decimal(str(payload["cumulative_cash_shortfall"])),
    )


def _exposure_change_to_payload(exposure_change: ExposureChange) -> dict[str, Any]:
    """Convert ExposureChange to dictionary payload."""
    return {
        "period_month": exposure_change.period_month,
        "period_date": exposure_change.period_date.isoformat(),
        "exposure_before": str(exposure_change.exposure_before),
        "exposure_after": str(exposure_change.exposure_after),
        "exposure_change": str(exposure_change.exposure_change),
        "exposure_change_percent": str(exposure_change.exposure_change_percent),
        "asset_category": exposure_change.asset_category,
    }


def _payload_to_exposure_change(payload: dict[str, Any]) -> ExposureChange:
    """Convert dictionary payload to ExposureChange."""
    from decimal import Decimal
    from datetime import date
    
    return ExposureChange(
        period_month=int(payload["period_month"]),
        period_date=date.fromisoformat(payload["period_date"]),
        exposure_before=Decimal(str(payload["exposure_before"])),
        exposure_after=Decimal(str(payload["exposure_after"])),
        exposure_change=Decimal(str(payload["exposure_change"])),
        exposure_change_percent=Decimal(str(payload["exposure_change_percent"])),
        asset_category=payload.get("asset_category"),
    )


def _cash_shortfall_to_payload(cash_shortfall: CashShortfall) -> dict[str, Any]:
    """Convert CashShortfall to dictionary payload."""
    return {
        "period_month": cash_shortfall.period_month,
        "period_date": cash_shortfall.period_date.isoformat(),
        "cash_available": str(cash_shortfall.cash_available),
        "cash_required": str(cash_shortfall.cash_required),
        "shortfall": str(cash_shortfall.shortfall),
        "shortfall_percent": str(cash_shortfall.shortfall_percent),
        "shortfall_category": cash_shortfall.shortfall_category,
    }


def _payload_to_cash_shortfall(payload: dict[str, Any]) -> CashShortfall:
    """Convert dictionary payload to CashShortfall."""
    from decimal import Decimal
    from datetime import date
    
    return CashShortfall(
        period_month=int(payload["period_month"]),
        period_date=date.fromisoformat(payload["period_date"]),
        cash_available=Decimal(str(payload["cash_available"])),
        cash_required=Decimal(str(payload["cash_required"])),
        shortfall=Decimal(str(payload["shortfall"])),
        shortfall_percent=Decimal(str(payload["shortfall_percent"])),
        shortfall_category=payload["shortfall_category"],
    )


def _debt_service_coverage_to_payload(dsc: DebtServiceCoverage) -> dict[str, Any]:
    """Convert DebtServiceCoverage to dictionary payload."""
    return {
        "period_month": dsc.period_month,
        "period_date": dsc.period_date.isoformat(),
        "dscr": str(dsc.dscr) if dsc.dscr is not None else None,
        "interest_coverage": str(dsc.interest_coverage) if dsc.interest_coverage is not None else None,
        "principal_coverage": str(dsc.principal_coverage) if dsc.principal_coverage is not None else None,
        "total_debt_service": str(dsc.total_debt_service),
        "cash_available_for_debt_service": str(dsc.cash_available_for_debt_service),
        "coverage_status": dsc.coverage_status,
    }


def _payload_to_debt_service_coverage(payload: dict[str, Any]) -> DebtServiceCoverage:
    """Convert dictionary payload to DebtServiceCoverage."""
    from decimal import Decimal
    from datetime import date
    
    return DebtServiceCoverage(
        period_month=int(payload["period_month"]),
        period_date=date.fromisoformat(payload["period_date"]),
        dscr=Decimal(str(payload["dscr"])) if payload.get("dscr") is not None else None,
        interest_coverage=Decimal(str(payload["interest_coverage"])) if payload.get("interest_coverage") is not None else None,
        principal_coverage=Decimal(str(payload["principal_coverage"])) if payload.get("principal_coverage") is not None else None,
        total_debt_service=Decimal(str(payload["total_debt_service"])),
        cash_available_for_debt_service=Decimal(str(payload["cash_available_for_debt_service"])),
        coverage_status=payload["coverage_status"],
    )

