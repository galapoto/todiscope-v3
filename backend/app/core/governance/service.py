from __future__ import annotations

from datetime import datetime, timezone
import uuid
from typing import Any, Mapping

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.dataset.models import DatasetVersion
from backend.app.core.governance.models import AiEventLog


class DatasetVersionLoggingError(ValueError):
    """Raised when an AI event cannot be tied to a verified DatasetVersion."""


class GovernanceMetadataMissingError(ValueError):
    """Raised when governance metadata is missing or empty during event logging."""


class InvalidStringParameterError(ValueError):
    """Raised when a required string parameter is empty or whitespace-only."""


def _validate_required_string(value: str, field_name: str) -> str:
    """Validate that a required string field is not empty or whitespace-only."""
    if not value or not isinstance(value, str):
        raise InvalidStringParameterError(f"{field_name} is required and must be a non-empty string.")
    if not value.strip():
        raise InvalidStringParameterError(f"{field_name} cannot be empty or whitespace-only.")
    return value.strip()


def _normalize_mapping(payload: Mapping[str, Any] | None) -> dict:
    return dict(payload) if payload is not None else {}


def _normalize_optional_mapping(payload: Mapping[str, Any] | None) -> dict | None:
    return dict(payload) if payload is not None else None


def _normalize_governance_metadata(payload: Mapping[str, Any]) -> dict:
    if payload is None:
        raise GovernanceMetadataMissingError("governance_metadata is required for AI event logging.")
    normalized = dict(payload)
    if not normalized:
        raise GovernanceMetadataMissingError("governance_metadata cannot be empty.")
    return normalized


async def _ensure_dataset_version_exists(db: AsyncSession, dataset_version_id: str) -> None:
    if not dataset_version_id or not isinstance(dataset_version_id, str):
        raise DatasetVersionLoggingError("DatasetVersion identifier is required for AI event logging.")
    # Optimized: select only constant 1 instead of entire DatasetVersion object
    exists = await db.scalar(select(1).where(DatasetVersion.id == dataset_version_id))
    if exists is None:
        raise DatasetVersionLoggingError(f"DatasetVersion '{dataset_version_id}' not found.")


def _current_timestamp(provided: datetime | None) -> datetime:
    return provided if provided is not None else datetime.now(timezone.utc)


async def record_ai_event(
    db: AsyncSession,
    *,
    engine_id: str,
    dataset_version_id: str,
    model_identifier: str,
    event_type: str,
    inputs: Mapping[str, Any],
    outputs: Mapping[str, Any] | None = None,
    model_version: str | None = None,
    context_id: str | None = None,
    event_label: str | None = None,
    tool_metadata: Mapping[str, Any] | None = None,
    rag_metadata: Mapping[str, Any] | None = None,
    governance_metadata: Mapping[str, Any],
    timestamp: datetime | None = None,
) -> AiEventLog:
    """
    Persist a single AI governance event. The table stores structured inputs, outputs,
    tool/RAG metadata, governance metadata, and links to DatasetVersion for traceability.

    The event is intentionally simple so it can track model calls, tool invocations,
    and RAG retrievals without changing the core architecture.
    """
    await _ensure_dataset_version_exists(db, dataset_version_id)
    
    # Validate required string fields
    engine_id = _validate_required_string(engine_id, "engine_id")
    model_identifier = _validate_required_string(model_identifier, "model_identifier")
    event_type = _validate_required_string(event_type, "event_type")

    event = AiEventLog(
        event_id=uuid.uuid4().hex,
        dataset_version_id=dataset_version_id,
        engine_id=engine_id,
        model_identifier=model_identifier,
        model_version=model_version,
        context_id=context_id,
        event_type=event_type,
        event_label=event_label,
        inputs=_normalize_mapping(inputs),
        outputs=_normalize_optional_mapping(outputs),
        tool_metadata=_normalize_optional_mapping(tool_metadata),
        rag_metadata=_normalize_optional_mapping(rag_metadata),
        governance_metadata=_normalize_governance_metadata(governance_metadata),
        created_at=_current_timestamp(timestamp),
    )
    db.add(event)
    return event


async def log_model_call(
    db: AsyncSession,
    *,
    engine_id: str,
    dataset_version_id: str,
    model_identifier: str,
    inputs: Mapping[str, Any],
    outputs: Mapping[str, Any] | None = None,
    model_version: str | None = None,
    context_id: str | None = None,
    governance_metadata: Mapping[str, Any],
    event_label: str | None = None,
    timestamp: datetime | None = None,
) -> AiEventLog:
    return await record_ai_event(
        db,
        engine_id=engine_id,
        dataset_version_id=dataset_version_id,
        model_identifier=model_identifier,
        event_type="model_call",
        inputs=inputs,
        outputs=outputs,
        model_version=model_version,
        context_id=context_id,
        event_label=event_label or model_identifier,
        governance_metadata=governance_metadata,
        timestamp=timestamp,
    )


async def log_tool_call(
    db: AsyncSession,
    *,
    engine_id: str,
    dataset_version_id: str,
    tool_name: str,
    inputs: Mapping[str, Any],
    outputs: Mapping[str, Any] | None = None,
    model_identifier: str = "governance_tool",
    context_id: str | None = None,
    governance_metadata: Mapping[str, Any],
    event_label: str | None = None,
    timestamp: datetime | None = None,
) -> AiEventLog:
    # Normalize inputs and outputs once
    normalized_inputs = _normalize_mapping(inputs)
    normalized_outputs = _normalize_optional_mapping(outputs)
    
    tool_payload = {
        "tool_name": tool_name,
        "inputs": normalized_inputs,
        "outputs": normalized_outputs,
    }
    return await record_ai_event(
        db,
        engine_id=engine_id,
        dataset_version_id=dataset_version_id,
        model_identifier=model_identifier,
        event_type="tool_call",
        inputs=normalized_inputs,
        outputs=normalized_outputs,
        context_id=context_id,
        event_label=event_label or tool_name,
        tool_metadata=tool_payload,
        governance_metadata=governance_metadata,
        timestamp=timestamp,
    )


async def log_rag_event(
    db: AsyncSession,
    *,
    engine_id: str,
    dataset_version_id: str,
    rag_sources: list[Mapping[str, Any]],
    context_id: str | None = None,
    governance_metadata: Mapping[str, Any],
    timestamp: datetime | None = None,
) -> AiEventLog:
    return await record_ai_event(
        db,
        engine_id=engine_id,
        dataset_version_id=dataset_version_id,
        model_identifier="rag_ingestion",
        event_type="rag_event",
        inputs={"dataset_version_id": dataset_version_id},
        outputs=None,
        context_id=context_id,
        event_label="rag_retrieval",
        rag_metadata={"sources": [dict(source) for source in rag_sources]},
        governance_metadata=governance_metadata,
        timestamp=timestamp,
    )
