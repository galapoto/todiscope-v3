"""
Comprehensive QA tests for AI Governance Event Logging System.

Tests verify:
- All event types (model_call, tool_call, rag_event)
- DatasetVersion enforcement
- Complete traceability
- Error handling
- Deterministic logging
- No domain logic
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
import uuid

import pytest
from sqlalchemy import select

from backend.app.core.dataset.models import DatasetVersion
from backend.app.core.dataset.service import create_dataset_version_via_ingestion
from backend.app.core.db import get_sessionmaker
from backend.app.core.governance.models import AiEventLog
from backend.app.core.governance.service import (
    DatasetVersionLoggingError,
    GovernanceMetadataMissingError,
    log_model_call,
    log_rag_event,
    log_tool_call,
    record_ai_event,
)


# ============================================================================
# Test Suite 1: Model Call Event Logging
# ============================================================================

@pytest.mark.anyio
async def test_model_call_complete_traceability(sqlite_db: None) -> None:
    """Test that model_call events capture all required traceability fields."""
    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)
        await db.commit()
        
        test_timestamp = datetime.now(timezone.utc)
        context_id = "model-context-123"
        model_version = "v2.1.0"
        
        event = await log_model_call(
            db,
            engine_id="test_engine",
            dataset_version_id=dv.id,
            model_identifier="test.model",
            inputs={"prompt": "test prompt", "temperature": 0.7},
            outputs={"response": "test response", "tokens": 150},
            model_version=model_version,
            context_id=context_id,
            governance_metadata={
                "confidence_score": 0.95,
                "decision_boundary": "high_confidence",
                "warnings": []
            },
            event_label="test_model_call",
            timestamp=test_timestamp,
        )
        await db.commit()
        
        # Verify all traceability fields
        assert event.event_type == "model_call"
        assert event.dataset_version_id == dv.id
        assert event.engine_id == "test_engine"
        assert event.model_identifier == "test.model"
        assert event.model_version == model_version
        assert event.context_id == context_id
        assert event.event_label == "test_model_call"
        assert event.created_at == test_timestamp
        
        # Verify inputs/outputs
        assert event.inputs == {"prompt": "test prompt", "temperature": 0.7}
        assert event.outputs == {"response": "test response", "tokens": 150}
        
        # Verify governance metadata
        assert event.governance_metadata["confidence_score"] == 0.95
        assert event.governance_metadata["decision_boundary"] == "high_confidence"
        
        # Verify no tool or RAG metadata for model calls
        assert event.tool_metadata is None
        assert event.rag_metadata is None


@pytest.mark.anyio
async def test_model_call_dataset_version_enforcement(sqlite_db: None) -> None:
    """Test that model_call enforces DatasetVersion existence."""
    async with get_sessionmaker()() as db:
        # Test with non-existent DatasetVersion
        with pytest.raises(DatasetVersionLoggingError, match="not found"):
            await log_model_call(
                db,
                engine_id="test_engine",
                dataset_version_id="non-existent-dv-id",
                model_identifier="test.model",
                inputs={},
                governance_metadata={"test": "metadata"},
            )
        
        # Test with None dataset_version_id
        with pytest.raises(DatasetVersionLoggingError, match="required"):
            await log_model_call(
                db,
                engine_id="test_engine",
                dataset_version_id=None,  # type: ignore
                model_identifier="test.model",
                inputs={},
                governance_metadata={"test": "metadata"},
            )
        
        # Test with empty string
        with pytest.raises(DatasetVersionLoggingError, match="required"):
            await log_model_call(
                db,
                engine_id="test_engine",
                dataset_version_id="",
                model_identifier="test.model",
                inputs={},
                governance_metadata={"test": "metadata"},
            )


@pytest.mark.anyio
async def test_model_call_governance_metadata_required(sqlite_db: None) -> None:
    """Test that model_call requires non-empty governance_metadata."""
    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)
        await db.commit()
        
        # Test with None
        with pytest.raises(GovernanceMetadataMissingError, match="required"):
            await log_model_call(
                db,
                engine_id="test_engine",
                dataset_version_id=dv.id,
                model_identifier="test.model",
                inputs={},
                governance_metadata=None,  # type: ignore
            )
        
        # Test with empty dict
        with pytest.raises(GovernanceMetadataMissingError, match="cannot be empty"):
            await log_model_call(
                db,
                engine_id="test_engine",
                dataset_version_id=dv.id,
                model_identifier="test.model",
                inputs={},
                governance_metadata={},
            )


# ============================================================================
# Test Suite 2: Tool Call Event Logging
# ============================================================================

@pytest.mark.anyio
async def test_tool_call_complete_traceability(sqlite_db: None) -> None:
    """Test that tool_call events capture all required traceability fields."""
    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)
        await db.commit()
        
        test_timestamp = datetime.now(timezone.utc)
        context_id = "tool-context-456"
        tool_name = "generate_report"
        
        event = await log_tool_call(
            db,
            engine_id="test_engine",
            dataset_version_id=dv.id,
            tool_name=tool_name,
            inputs={"report_type": "esrs", "format": "json"},
            outputs={"report_id": "report-123", "status": "generated"},
            model_identifier="custom_tool_engine",
            context_id=context_id,
            governance_metadata={
                "confidence_score": 1.0,
                "decision_boundary": "deterministic",
                "warnings": []
            },
            event_label="report_generation",
            timestamp=test_timestamp,
        )
        await db.commit()
        
        # Verify all traceability fields
        assert event.event_type == "tool_call"
        assert event.dataset_version_id == dv.id
        assert event.engine_id == "test_engine"
        assert event.model_identifier == "custom_tool_engine"
        assert event.context_id == context_id
        assert event.event_label == "report_generation"
        assert event.created_at == test_timestamp
        
        # Verify inputs/outputs
        assert event.inputs == {"report_type": "esrs", "format": "json"}
        assert event.outputs == {"report_id": "report-123", "status": "generated"}
        
        # Verify tool_metadata
        assert event.tool_metadata is not None
        assert event.tool_metadata["tool_name"] == tool_name
        assert event.tool_metadata["inputs"] == event.inputs
        assert event.tool_metadata["outputs"] == event.outputs
        
        # Verify governance metadata
        assert event.governance_metadata["confidence_score"] == 1.0
        
        # Verify no RAG metadata for tool calls
        assert event.rag_metadata is None


@pytest.mark.anyio
async def test_tool_call_default_model_identifier(sqlite_db: None) -> None:
    """Test that tool_call uses default model_identifier when not provided."""
    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)
        await db.commit()
        
        event = await log_tool_call(
            db,
            engine_id="test_engine",
            dataset_version_id=dv.id,
            tool_name="test_tool",
            inputs={},
            governance_metadata={"test": "metadata"},
        )
        await db.commit()
        
        assert event.model_identifier == "governance_tool"


@pytest.mark.anyio
async def test_tool_call_default_event_label(sqlite_db: None) -> None:
    """Test that tool_call uses tool_name as default event_label."""
    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)
        await db.commit()
        
        event = await log_tool_call(
            db,
            engine_id="test_engine",
            dataset_version_id=dv.id,
            tool_name="my_custom_tool",
            inputs={},
            governance_metadata={"test": "metadata"},
        )
        await db.commit()
        
        assert event.event_label == "my_custom_tool"


# ============================================================================
# Test Suite 3: RAG Event Logging
# ============================================================================

@pytest.mark.anyio
async def test_rag_event_complete_traceability(sqlite_db: None) -> None:
    """Test that rag_event captures all required traceability fields."""
    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)
        await db.commit()
        
        test_timestamp = datetime.now(timezone.utc)
        context_id = "rag-context-789"
        
        rag_sources = [
            {"source_type": "RawRecord", "raw_record_id": "rec-1", "dataset_version_id": dv.id},
            {"source_type": "RawRecord", "raw_record_id": "rec-2", "dataset_version_id": dv.id},
            {"source_type": "Document", "doc_id": "doc-1", "page": 5},
        ]
        
        event = await log_rag_event(
            db,
            engine_id="test_engine",
            dataset_version_id=dv.id,
            rag_sources=rag_sources,
            context_id=context_id,
            governance_metadata={
                "confidence_score": 0.85,
                "decision_boundary": "rag_retrieval",
                "retrieved_sources": len(rag_sources),
            },
            timestamp=test_timestamp,
        )
        await db.commit()
        
        # Verify all traceability fields
        assert event.event_type == "rag_event"
        assert event.dataset_version_id == dv.id
        assert event.engine_id == "test_engine"
        assert event.model_identifier == "rag_ingestion"
        assert event.context_id == context_id
        assert event.event_label == "rag_retrieval"
        assert event.created_at == test_timestamp
        
        # Verify inputs
        assert event.inputs == {"dataset_version_id": dv.id}
        assert event.outputs is None
        
        # Verify rag_metadata
        assert event.rag_metadata is not None
        assert "sources" in event.rag_metadata
        assert len(event.rag_metadata["sources"]) == 3
        assert event.rag_metadata["sources"][0]["raw_record_id"] == "rec-1"
        
        # Verify governance metadata
        assert event.governance_metadata["retrieved_sources"] == 3
        
        # Verify no tool metadata for RAG events
        assert event.tool_metadata is None


@pytest.mark.anyio
async def test_rag_event_source_normalization(sqlite_db: None) -> None:
    """Test that RAG sources are properly normalized to dicts."""
    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)
        await db.commit()
        
        # Create Mapping objects that need normalization
        class TestMapping(Mapping):
            def __init__(self, data: dict):
                self._data = data
            
            def __getitem__(self, key):
                return self._data[key]
            
            def __iter__(self):
                return iter(self._data)
            
            def __len__(self):
                return len(self._data)
        
        rag_sources = [
            TestMapping({"source_type": "RawRecord", "id": "rec-1"}),
            TestMapping({"source_type": "Document", "id": "doc-1"}),
        ]
        
        event = await log_rag_event(
            db,
            engine_id="test_engine",
            dataset_version_id=dv.id,
            rag_sources=rag_sources,
            governance_metadata={"test": "metadata"},
        )
        await db.commit()
        
        # Verify sources are normalized to dicts
        assert isinstance(event.rag_metadata["sources"][0], dict)
        assert isinstance(event.rag_metadata["sources"][1], dict)
        assert event.rag_metadata["sources"][0]["id"] == "rec-1"
        assert event.rag_metadata["sources"][1]["id"] == "doc-1"


# ============================================================================
# Test Suite 4: DatasetVersion Enforcement
# ============================================================================

@pytest.mark.anyio
async def test_all_event_types_dataset_version_enforcement(sqlite_db: None) -> None:
    """Test that all event types enforce DatasetVersion existence."""
    async with get_sessionmaker()() as db:
        non_existent_id = "definitely-does-not-exist-99999"
        
        # Test model_call
        with pytest.raises(DatasetVersionLoggingError, match="not found"):
            await log_model_call(
                db,
                engine_id="test_engine",
                dataset_version_id=non_existent_id,
                model_identifier="test.model",
                inputs={},
                governance_metadata={"test": "metadata"},
            )
        
        # Test tool_call
        with pytest.raises(DatasetVersionLoggingError, match="not found"):
            await log_tool_call(
                db,
                engine_id="test_engine",
                dataset_version_id=non_existent_id,
                tool_name="test_tool",
                inputs={},
                governance_metadata={"test": "metadata"},
            )
        
        # Test rag_event
        with pytest.raises(DatasetVersionLoggingError, match="not found"):
            await log_rag_event(
                db,
                engine_id="test_engine",
                dataset_version_id=non_existent_id,
                rag_sources=[],
                governance_metadata={"test": "metadata"},
            )
        
        # Test record_ai_event
        with pytest.raises(DatasetVersionLoggingError, match="not found"):
            await record_ai_event(
                db,
                engine_id="test_engine",
                dataset_version_id=non_existent_id,
                model_identifier="test_model",
                event_type="test_event",
                inputs={},
                governance_metadata={"test": "metadata"},
            )


@pytest.mark.anyio
async def test_dataset_version_isolation(sqlite_db: None) -> None:
    """Test that events are properly isolated by DatasetVersion."""
    async with get_sessionmaker()() as db:
        dv1 = await create_dataset_version_via_ingestion(db)
        dv2 = await create_dataset_version_via_ingestion(db)
        await db.commit()
        
        # Log events for different DatasetVersions
        event1 = await log_model_call(
            db,
            engine_id="test_engine",
            dataset_version_id=dv1.id,
            model_identifier="test.model",
            inputs={"data": "for_dv1"},
            governance_metadata={"test": "metadata1"},
        )
        
        event2 = await log_model_call(
            db,
            engine_id="test_engine",
            dataset_version_id=dv2.id,
            model_identifier="test.model",
            inputs={"data": "for_dv2"},
            governance_metadata={"test": "metadata2"},
        )
        await db.commit()
        
        # Verify events are linked to correct DatasetVersions
        assert event1.dataset_version_id == dv1.id
        assert event2.dataset_version_id == dv2.id
        assert event1.dataset_version_id != event2.dataset_version_id
        
        # Verify we can query events by DatasetVersion
        events_dv1 = (
            await db.scalars(
                select(AiEventLog).where(AiEventLog.dataset_version_id == dv1.id)
            )
        ).all()
        assert len(events_dv1) == 1
        assert events_dv1[0].event_id == event1.event_id
        
        events_dv2 = (
            await db.scalars(
                select(AiEventLog).where(AiEventLog.dataset_version_id == dv2.id)
            )
        ).all()
        assert len(events_dv2) == 1
        assert events_dv2[0].event_id == event2.event_id


# ============================================================================
# Test Suite 5: Traceability and Audit Trail
# ============================================================================

@pytest.mark.anyio
async def test_complete_audit_trail(sqlite_db: None) -> None:
    """Test that complete audit trail can be reconstructed from logged events."""
    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)
        await db.commit()
        
        base_timestamp = datetime.now(timezone.utc)
        context_id = "workflow-123"
        
        # Simulate a complete workflow: RAG -> Model -> Tool
        rag_event = await log_rag_event(
            db,
            engine_id="test_engine",
            dataset_version_id=dv.id,
            rag_sources=[{"source": "data1"}, {"source": "data2"}],
            context_id=context_id,
            governance_metadata={"step": "rag_retrieval"},
            timestamp=base_timestamp,
        )
        
        model_event = await log_model_call(
            db,
            engine_id="test_engine",
            dataset_version_id=dv.id,
            model_identifier="test.model",
            inputs={"rag_results": "processed"},
            outputs={"result": "computed"},
            context_id=context_id,
            governance_metadata={"step": "model_processing"},
            timestamp=base_timestamp,
        )
        
        tool_event = await log_tool_call(
            db,
            engine_id="test_engine",
            dataset_version_id=dv.id,
            tool_name="generate_output",
            inputs={"model_result": "computed"},
            outputs={"final_output": "generated"},
            context_id=context_id,
            governance_metadata={"step": "tool_execution"},
            timestamp=base_timestamp,
        )
        await db.commit()
        
        # Verify all events share the same context
        assert rag_event.context_id == context_id
        assert model_event.context_id == context_id
        assert tool_event.context_id == context_id
        
        # Verify all events are linked to the same DatasetVersion
        assert rag_event.dataset_version_id == dv.id
        assert model_event.dataset_version_id == dv.id
        assert tool_event.dataset_version_id == dv.id
        
        # Verify we can reconstruct the workflow
        all_events = (
            await db.scalars(
                select(AiEventLog)
                .where(AiEventLog.dataset_version_id == dv.id)
                .where(AiEventLog.context_id == context_id)
                .order_by(AiEventLog.created_at)
            )
        ).all()
        
        assert len(all_events) == 3
        assert all_events[0].event_type == "rag_event"
        assert all_events[1].event_type == "model_call"
        assert all_events[2].event_type == "tool_call"


@pytest.mark.anyio
async def test_timestamp_traceability(sqlite_db: None) -> None:
    """Test that timestamps are properly recorded and traceable."""
    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)
        await db.commit()
        
        # Test with explicit timestamp
        explicit_timestamp = datetime(2024, 1, 15, 12, 30, 45, tzinfo=timezone.utc)
        event1 = await log_model_call(
            db,
            engine_id="test_engine",
            dataset_version_id=dv.id,
            model_identifier="test.model",
            inputs={},
            governance_metadata={"test": "metadata"},
            timestamp=explicit_timestamp,
        )
        await db.commit()
        
        assert event1.created_at == explicit_timestamp
        assert event1.created_at.tzinfo == timezone.utc
        
        # Test with None timestamp (should use current time)
        before_log = datetime.now(timezone.utc)
        event2 = await log_model_call(
            db,
            engine_id="test_engine",
            dataset_version_id=dv.id,
            model_identifier="test.model",
            inputs={},
            governance_metadata={"test": "metadata"},
            timestamp=None,
        )
        after_log = datetime.now(timezone.utc)
        await db.commit()
        
        assert event2.created_at.tzinfo == timezone.utc
        assert before_log <= event2.created_at <= after_log


# ============================================================================
# Test Suite 6: Error Handling
# ============================================================================

@pytest.mark.anyio
async def test_error_handling_missing_dataset_version(sqlite_db: None) -> None:
    """Test error handling for missing DatasetVersion."""
    async with get_sessionmaker()() as db:
        # Test various invalid DatasetVersion scenarios
        invalid_ids = [
            None,
            "",
            "   ",
            "non-existent-id-12345",
        ]
        
        for invalid_id in invalid_ids:
            with pytest.raises(DatasetVersionLoggingError):
                await log_model_call(
                    db,
                    engine_id="test_engine",
                    dataset_version_id=invalid_id,  # type: ignore
                    model_identifier="test.model",
                    inputs={},
                    governance_metadata={"test": "metadata"},
                )


@pytest.mark.anyio
async def test_error_handling_missing_governance_metadata(sqlite_db: None) -> None:
    """Test error handling for missing or empty governance_metadata."""
    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)
        await db.commit()
        
        # Test None
        with pytest.raises(GovernanceMetadataMissingError, match="required"):
            await log_model_call(
                db,
                engine_id="test_engine",
                dataset_version_id=dv.id,
                model_identifier="test.model",
                inputs={},
                governance_metadata=None,  # type: ignore
            )
        
        # Test empty dict
        with pytest.raises(GovernanceMetadataMissingError, match="cannot be empty"):
            await log_model_call(
                db,
                engine_id="test_engine",
                dataset_version_id=dv.id,
                model_identifier="test.model",
                inputs={},
                governance_metadata={},
            )


@pytest.mark.anyio
async def test_error_handling_input_normalization(sqlite_db: None) -> None:
    """Test that error handling works correctly with input normalization."""
    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)
        await db.commit()
        
        # Test with None inputs (should become empty dict)
        event = await log_model_call(
            db,
            engine_id="test_engine",
            dataset_version_id=dv.id,
            model_identifier="test.model",
            inputs=None,  # type: ignore
            governance_metadata={"test": "metadata"},
        )
        await db.commit()
        
        assert event.inputs == {}


# ============================================================================
# Test Suite 7: Deterministic Logging
# ============================================================================

@pytest.mark.anyio
async def test_deterministic_logging_no_inference(sqlite_db: None) -> None:
    """Test that only explicitly logged events are persisted."""
    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)
        await db.commit()
        
        # Log one explicit event
        event = await log_model_call(
            db,
            engine_id="test_engine",
            dataset_version_id=dv.id,
            model_identifier="test.model",
            inputs={},
            governance_metadata={"test": "metadata"},
        )
        await db.commit()
        
        # Verify only the explicit event exists
        all_events = (
            await db.scalars(
                select(AiEventLog).where(AiEventLog.dataset_version_id == dv.id)
            )
        ).all()
        
        assert len(all_events) == 1
        assert all_events[0].event_id == event.event_id


@pytest.mark.anyio
async def test_deterministic_logging_replay(sqlite_db: None) -> None:
    """Test that events can be deterministically replayed from inputs/outputs."""
    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)
        await db.commit()
        
        original_inputs = {"prompt": "test", "temperature": 0.7}
        original_outputs = {"response": "result", "tokens": 100}
        
        # Log original event
        event1 = await log_model_call(
            db,
            engine_id="test_engine",
            dataset_version_id=dv.id,
            model_identifier="test.model",
            inputs=original_inputs,
            outputs=original_outputs,
            governance_metadata={"test": "metadata"},
        )
        await db.commit()
        
        # Verify inputs/outputs are stored exactly as provided
        assert event1.inputs == original_inputs
        assert event1.outputs == original_outputs
        
        # Verify we can replay using stored inputs
        # (In a real scenario, this would feed inputs back to the model)
        assert event1.inputs["prompt"] == "test"
        assert event1.inputs["temperature"] == 0.7
        assert event1.outputs["response"] == "result"
        assert event1.outputs["tokens"] == 100


# ============================================================================
# Test Suite 8: No Domain Logic
# ============================================================================

@pytest.mark.anyio
async def test_no_domain_logic_pure_mechanics(sqlite_db: None) -> None:
    """Test that logging system contains no domain logic - only mechanics."""
    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)
        await db.commit()
        
        # Test with arbitrary data - logging should work regardless of content
        arbitrary_inputs = {
            "field1": "value1",
            "field2": 42,
            "field3": {"nested": "data"},
            "field4": [1, 2, 3],
        }
        
        arbitrary_outputs = {
            "result1": "output1",
            "result2": 99,
        }
        
        arbitrary_governance = {
            "custom_field": "custom_value",
            "another_field": 123,
        }
        
        # Logging should work with any data structure
        event = await log_model_call(
            db,
            engine_id="test_engine",
            dataset_version_id=dv.id,
            model_identifier="test.model",
            inputs=arbitrary_inputs,
            outputs=arbitrary_outputs,
            governance_metadata=arbitrary_governance,
        )
        await db.commit()
        
        # Verify data is stored exactly as provided (no transformation)
        assert event.inputs == arbitrary_inputs
        assert event.outputs == arbitrary_outputs
        assert event.governance_metadata == arbitrary_governance


# ============================================================================
# Test Suite 9: Event Persistence and Retrieval
# ============================================================================

@pytest.mark.anyio
async def test_event_persistence_all_types(sqlite_db: None) -> None:
    """Test that all event types are properly persisted and retrievable."""
    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)
        await db.commit()
        
        # Log one of each event type
        model_event = await log_model_call(
            db,
            engine_id="test_engine",
            dataset_version_id=dv.id,
            model_identifier="test.model",
            inputs={},
            governance_metadata={"test": "metadata"},
        )
        
        tool_event = await log_tool_call(
            db,
            engine_id="test_engine",
            dataset_version_id=dv.id,
            tool_name="test_tool",
            inputs={},
            governance_metadata={"test": "metadata"},
        )
        
        rag_event = await log_rag_event(
            db,
            engine_id="test_engine",
            dataset_version_id=dv.id,
            rag_sources=[],
            governance_metadata={"test": "metadata"},
        )
        await db.commit()
        
        # Retrieve all events
        all_events = (
            await db.scalars(
                select(AiEventLog).where(AiEventLog.dataset_version_id == dv.id)
            )
        ).all()
        
        assert len(all_events) == 3
        
        event_types = {e.event_type for e in all_events}
        assert "model_call" in event_types
        assert "tool_call" in event_types
        assert "rag_event" in event_types
        
        # Verify we can retrieve by event type
        model_events = (
            await db.scalars(
                select(AiEventLog)
                .where(AiEventLog.dataset_version_id == dv.id)
                .where(AiEventLog.event_type == "model_call")
            )
        ).all()
        assert len(model_events) == 1
        assert model_events[0].event_id == model_event.event_id


@pytest.mark.anyio
async def test_event_unique_ids(sqlite_db: None) -> None:
    """Test that each event has a unique event_id."""
    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)
        await db.commit()
        
        # Log multiple events
        events = []
        for i in range(5):
            event = await log_model_call(
                db,
                engine_id="test_engine",
                dataset_version_id=dv.id,
                model_identifier="test.model",
                inputs={"index": i},
                governance_metadata={"test": "metadata"},
            )
            events.append(event)
        await db.commit()
        
        # Verify all event IDs are unique
        event_ids = {e.event_id for e in events}
        assert len(event_ids) == 5
        
        # Verify event IDs are valid hex strings (UUID hex format)
        for event in events:
            assert len(event.event_id) == 32  # UUID hex is 32 chars
            assert all(c in "0123456789abcdef" for c in event.event_id)


