from __future__ import annotations

import json
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.artifacts.checksums import sha256_hex
from backend.app.core.calculation.models import CalculationEvidenceLink, CalculationRun
from backend.app.core.dataset.uuidv7 import uuid7
from backend.app.core.engine_registry.models import EngineRegistryEntry
from backend.app.core.evidence.models import EvidenceRecord
from backend.app.core.audit.service import log_calculation_action


def _hash_parameters(parameters: dict) -> str:
    encoded = json.dumps(parameters, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256_hex(encoded)


def deterministic_calculation_run_id(
    *,
    dataset_version_id: str,
    engine_id: str,
    engine_version: str,
    parameter_payload: dict,
) -> str:
    """
    Generate deterministic run_id from stable inputs.
    
    Same inputs (dataset_version_id, engine_id, engine_version, parameter_payload)
    will always produce the same run_id, enabling deterministic replay.
    
    Args:
        dataset_version_id: DatasetVersion ID
        engine_id: Engine identifier
        engine_version: Engine version
        parameter_payload: Complete parameter payload
    
    Returns:
        Deterministic run_id (UUIDv5)
    """
    param_hash = _hash_parameters(parameter_payload)
    stable = f"{dataset_version_id}|{engine_id}|{engine_version}|{param_hash}"
    namespace = uuid.UUID("00000000-0000-0000-0000-000000000046")
    return str(uuid.uuid5(namespace, stable))


async def create_calculation_run(
    db: AsyncSession,
    *,
    dataset_version_id: str,
    engine_id: str,
    engine_version: str,
    parameter_payload: dict,
    started_at: datetime,
    finished_at: datetime,
    actor_id: str | None = None,
) -> CalculationRun:
    """
    Create a new CalculationRun with full parameter introspection.
    
    Args:
        db: Database session
        dataset_version_id: DatasetVersion ID
        engine_id: Engine identifier
        engine_version: Engine version (required for reproducibility)
        parameter_payload: Complete parameter payload (stored for introspection)
        started_at: Calculation start timestamp
        finished_at: Calculation finish timestamp
        actor_id: ID of the user/actor triggering the calculation (defaults to engine_id if not provided)
    
    Returns:
        Created CalculationRun instance
    
    Raises:
        ValueError: If engine_version is not provided
    """
    if not engine_version or not isinstance(engine_version, str):
        raise ValueError("engine_version is required and must be a non-empty string")
    
    # Ensure engine is registered
    existing_engine = await db.scalar(
        select(EngineRegistryEntry).where(EngineRegistryEntry.engine_id == engine_id)
    )
    if existing_engine is None:
        db.add(EngineRegistryEntry(engine_id=engine_id, engine_version=engine_version))
    elif engine_version and existing_engine.engine_version is None:
        existing_engine.engine_version = engine_version

    # Create calculation run with deterministic run_id based on stable inputs
    # This ensures same inputs produce same run_id, enabling deterministic replay
    run_id = deterministic_calculation_run_id(
        dataset_version_id=dataset_version_id,
        engine_id=engine_id,
        engine_version=engine_version,
        parameter_payload=parameter_payload,
    )
    
    # Check if run already exists (idempotent creation)
    existing_run = await db.scalar(select(CalculationRun).where(CalculationRun.run_id == run_id))
    if existing_run is not None:
        return existing_run
    
    # Create calculation run with full parameter payload and hash computed from payload
    run = CalculationRun(
        run_id=run_id,
        dataset_version_id=dataset_version_id,
        engine_id=engine_id,
        engine_version=engine_version,
        parameter_payload=parameter_payload,  # Full payload for introspection
        parameters_hash=_hash_parameters(parameter_payload),  # Hash computed from parameter_payload
        started_at=started_at,
        finished_at=finished_at,
    )
    db.add(run)
    await db.flush()
    
    # Use actor_id if provided, otherwise fallback to engine_id for system-driven actions
    audit_actor_id = actor_id if actor_id else f"engine:{engine_id}"
    await log_calculation_action(
        db,
        actor_id=audit_actor_id,
        dataset_version_id=dataset_version_id,
        calculation_run_id=run.run_id,
        engine_id=engine_id,
        metadata={"engine_version": engine_version, "parameters_hash": run.parameters_hash},
    )
    return run


async def get_calculation_run(db: AsyncSession, *, run_id: str) -> CalculationRun | None:
    return await db.scalar(select(CalculationRun).where(CalculationRun.run_id == run_id))


def deterministic_calculation_evidence_link_id(*, calculation_run_id: str, evidence_id: str) -> str:
    namespace = uuid.UUID("00000000-0000-0000-0000-000000000045")
    return str(uuid.uuid5(namespace, f"{calculation_run_id}|{evidence_id}"))


async def link_evidence_to_calculation_run(
    db: AsyncSession,
    *,
    calculation_run_id: str,
    evidence_id: str,
) -> CalculationEvidenceLink:
    link_id = deterministic_calculation_evidence_link_id(
        calculation_run_id=calculation_run_id,
        evidence_id=evidence_id,
    )
    existing = await db.scalar(select(CalculationEvidenceLink).where(CalculationEvidenceLink.link_id == link_id))
    if existing is not None:
        return existing
    link = CalculationEvidenceLink(
        link_id=link_id,
        calculation_run_id=calculation_run_id,
        evidence_id=evidence_id,
    )
    db.add(link)
    await db.flush()
    return link


async def get_evidence_for_calculation_run(
    db: AsyncSession,
    *,
    calculation_run_id: str,
) -> list[EvidenceRecord]:
    result = await db.execute(
        select(EvidenceRecord)
        .join(CalculationEvidenceLink, EvidenceRecord.evidence_id == CalculationEvidenceLink.evidence_id)
        .where(CalculationEvidenceLink.calculation_run_id == calculation_run_id)
        .order_by(EvidenceRecord.created_at.asc(), EvidenceRecord.evidence_id.asc())
    )
    return list(result.scalars().all())
