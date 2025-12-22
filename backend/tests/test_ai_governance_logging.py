from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
import pytest
from sqlalchemy import select

from backend.app.core.dataset.models import DatasetVersion
from backend.app.core.dataset.service import create_dataset_version_via_ingestion
from backend.app.core.db import get_sessionmaker
from backend.app.core.governance.models import AiEventLog
from backend.app.core.governance.service import (
    DatasetVersionLoggingError,
    GovernanceMetadataMissingError,
    InvalidStringParameterError,
    log_model_call,
    log_rag_event,
    log_tool_call,
    record_ai_event,
)
from backend.app.engines.csrd.engine import ENGINE_ID


@pytest.mark.anyio
async def test_log_model_call_rejects_missing_governance_metadata(sqlite_db: None) -> None:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        async with db.begin():
            db.add(DatasetVersion(id="dataset-governance-missing"))

        with pytest.raises(GovernanceMetadataMissingError):
            await log_model_call(
                db,
                engine_id=ENGINE_ID,
                dataset_version_id="dataset-governance-missing",
                model_identifier="governance.test",
                inputs={"payload": "value"},
                outputs={"result": 1},
                governance_metadata=None,  # type: ignore[arg-type]
            )


@pytest.mark.anyio
async def test_log_model_call_rejects_empty_governance_metadata(sqlite_db: None) -> None:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        async with db.begin():
            db.add(DatasetVersion(id="dataset-governance-empty"))

        with pytest.raises(GovernanceMetadataMissingError):
            await log_model_call(
                db,
                engine_id=ENGINE_ID,
                dataset_version_id="dataset-governance-empty",
                model_identifier="governance.test",
                inputs={"payload": "value"},
                outputs={"result": 1},
                governance_metadata={},
            )


@pytest.mark.anyio
async def test_log_model_call_persists_event_with_governance_metadata(sqlite_db: None) -> None:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        async with db.begin():
            db.add(DatasetVersion(id="dataset-governance-success"))

        await log_model_call(
            db,
            engine_id=ENGINE_ID,
            dataset_version_id="dataset-governance-success",
            model_identifier="governance.success",
            inputs={"payload": "value"},
            outputs={"result": 1},
            governance_metadata={"confidence_score": 0.99, "decision_boundary": "success"},
        )
        await db.commit()

        statement = select(AiEventLog).where(
            AiEventLog.dataset_version_id == "dataset-governance-success",
            AiEventLog.event_type == "model_call",
        )
        event = (await db.scalars(statement)).first()
        assert event is not None
        assert event.governance_metadata["confidence_score"] == 0.99


@pytest.mark.anyio
async def test_log_tool_call_normalization_no_redundancy(sqlite_db: None) -> None:
    """Test that log_tool_call normalizes inputs/outputs only once."""
    async with get_sessionmaker()() as db:
        # Create a DatasetVersion
        dv = await create_dataset_version_via_ingestion(db)
        await db.commit()
        
        # Create test inputs/outputs that need normalization (using Mapping types)
        class TestMapping(Mapping):
            def __init__(self, data: dict):
                self._data = data
            
            def __getitem__(self, key):
                return self._data[key]
            
            def __iter__(self):
                return iter(self._data)
            
            def __len__(self):
                return len(self._data)
        
        test_inputs = TestMapping({"key1": "value1", "key2": 42})
        test_outputs = TestMapping({"result": "success", "count": 100})
        
        # Log the tool call
        event = await log_tool_call(
            db,
            engine_id="test_engine",
            dataset_version_id=dv.id,
            tool_name="test_tool",
            inputs=test_inputs,
            outputs=test_outputs,
            governance_metadata={"test": "metadata"},
        )
        await db.commit()
        
        # Verify the event was created
        assert event is not None
        assert event.event_type == "tool_call"
        assert event.tool_metadata is not None
        
        # Verify normalization happened: inputs/outputs should be dict (not TestMapping)
        assert isinstance(event.inputs, dict)
        assert isinstance(event.outputs, dict)
        assert event.inputs == {"key1": "value1", "key2": 42}
        assert event.outputs == {"result": "success", "count": 100}
        
        # Verify tool_metadata contains the same normalized values
        assert event.tool_metadata["tool_name"] == "test_tool"
        assert isinstance(event.tool_metadata["inputs"], dict)
        assert isinstance(event.tool_metadata["outputs"], dict)
        assert event.tool_metadata["inputs"] == event.inputs
        assert event.tool_metadata["outputs"] == event.outputs
        
        # Verify that inputs/outputs in tool_metadata match the event inputs/outputs
        # (This confirms normalization happened once and was reused)
        assert event.tool_metadata["inputs"] == event.inputs
        assert event.tool_metadata["outputs"] == event.outputs


@pytest.mark.anyio
async def test_log_tool_call_with_none_outputs(sqlite_db: None) -> None:
    """Test that log_tool_call handles None outputs correctly."""
    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)
        await db.commit()
        
        event = await log_tool_call(
            db,
            engine_id="test_engine",
            dataset_version_id=dv.id,
            tool_name="test_tool",
            inputs={"input": "data"},
            outputs=None,
            governance_metadata={"test": "metadata"},
        )
        await db.commit()
        
        assert event.outputs is None
        assert event.tool_metadata["outputs"] is None


@pytest.mark.anyio
async def test_log_tool_call_dataset_version_enforcement(sqlite_db: None) -> None:
    """Test that log_tool_call enforces DatasetVersion existence."""
    async with get_sessionmaker()() as db:
        # Try to log with non-existent DatasetVersion
        with pytest.raises(DatasetVersionLoggingError, match="not found"):
            await log_tool_call(
                db,
                engine_id="test_engine",
                dataset_version_id="non-existent-id",
                tool_name="test_tool",
                inputs={},
                governance_metadata={"test": "metadata"},
            )
        
        # Try with None dataset_version_id
        with pytest.raises(DatasetVersionLoggingError, match="required"):
            await log_tool_call(
                db,
                engine_id="test_engine",
                dataset_version_id=None,  # type: ignore
                tool_name="test_tool",
                inputs={},
                governance_metadata={"test": "metadata"},
            )


@pytest.mark.anyio
async def test_log_tool_call_traceability_fields(sqlite_db: None) -> None:
    """Test that log_tool_call captures all required traceability fields."""
    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)
        await db.commit()
        
        test_timestamp = datetime.now(timezone.utc)
        context_id = "test-context-123"
        
        event = await log_tool_call(
            db,
            engine_id="test_engine",
            dataset_version_id=dv.id,
            tool_name="test_tool",
            inputs={"input": "data"},
            outputs={"output": "result"},
            model_identifier="custom_model",
            context_id=context_id,
            governance_metadata={"confidence": 0.95},
            event_label="custom_label",
            timestamp=test_timestamp,
        )
        await db.commit()
        
        # Verify all traceability fields
        assert event.dataset_version_id == dv.id
        assert event.engine_id == "test_engine"
        assert event.model_identifier == "custom_model"
        assert event.context_id == context_id
        assert event.event_type == "tool_call"
        assert event.event_label == "custom_label"


@pytest.mark.anyio
async def test_optimized_dataset_version_query_exists(sqlite_db: None) -> None:
    """Test that optimized DatasetVersion existence query correctly identifies existing DatasetVersions."""
    async with get_sessionmaker()() as db:
        # Create a DatasetVersion
        dv = await create_dataset_version_via_ingestion(db)
        await db.commit()
        
        # Verify that logging works with existing DatasetVersion (uses optimized query)
        event = await log_tool_call(
            db,
            engine_id="test_engine",
            dataset_version_id=dv.id,
            tool_name="test_tool",
            inputs={"input": "data"},
            governance_metadata={"test": "metadata"},
        )
        await db.commit()
        
        # If we get here without exception, the optimized query correctly identified the DatasetVersion
        assert event is not None
        assert event.dataset_version_id == dv.id


@pytest.mark.anyio
async def test_optimized_dataset_version_query_not_exists(sqlite_db: None) -> None:
    """Test that optimized DatasetVersion existence query correctly identifies non-existent DatasetVersions."""
    async with get_sessionmaker()() as db:
        # Try to log with non-existent DatasetVersion
        # The optimized query should return None, triggering the error
        with pytest.raises(DatasetVersionLoggingError, match="not found"):
            await log_tool_call(
                db,
                engine_id="test_engine",
                dataset_version_id="non-existent-dataset-version-id-12345",
                tool_name="test_tool",
                inputs={"input": "data"},
                governance_metadata={"test": "metadata"},
            )


@pytest.mark.anyio
async def test_optimized_dataset_version_query_functionally_equivalent(sqlite_db: None) -> None:
    """Test that optimized query is functionally equivalent to selecting the entire object."""
    async with get_sessionmaker()() as db:
        # Create multiple DatasetVersions
        dv1 = await create_dataset_version_via_ingestion(db)
        dv2 = await create_dataset_version_via_ingestion(db)
        await db.commit()
        
        # Test that optimized query works for both existing DatasetVersions
        event1 = await log_model_call(
            db,
            engine_id="test_engine",
            dataset_version_id=dv1.id,
            model_identifier="test_model",
            inputs={"input": "data1"},
            governance_metadata={"test": "metadata1"},
        )
        
        event2 = await log_rag_event(
            db,
            engine_id="test_engine",
            dataset_version_id=dv2.id,
            rag_sources=[{"source": "test"}],
            governance_metadata={"test": "metadata2"},
        )
        await db.commit()
        
        # Verify both events were created successfully
        assert event1 is not None
        assert event1.dataset_version_id == dv1.id
        assert event2 is not None
        assert event2.dataset_version_id == dv2.id
        
        # Verify that non-existent DatasetVersion still raises error
        with pytest.raises(DatasetVersionLoggingError, match="not found"):
            await record_ai_event(
                db,
                engine_id="test_engine",
                dataset_version_id="definitely-does-not-exist-99999",
                model_identifier="test_model",
                event_type="test_event",
                inputs={},
                governance_metadata={"test": "metadata"},
            )


# ============================================================================
# Input Validation Tests
# ============================================================================

@pytest.mark.anyio
async def test_record_ai_event_rejects_empty_engine_id(sqlite_db: None) -> None:
    """Test that record_ai_event rejects empty engine_id."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        async with db.begin():
            db.add(DatasetVersion(id="dataset-input-validation"))

        with pytest.raises(InvalidStringParameterError, match="engine_id"):
            await record_ai_event(
                db,
                engine_id="",
                dataset_version_id="dataset-input-validation",
                model_identifier="test_model",
                event_type="test_event",
                inputs={},
                governance_metadata={"test": "metadata"},
            )


@pytest.mark.anyio
async def test_record_ai_event_rejects_whitespace_engine_id(sqlite_db: None) -> None:
    """Test that record_ai_event rejects whitespace-only engine_id."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        async with db.begin():
            db.add(DatasetVersion(id="dataset-input-validation"))

        with pytest.raises(InvalidStringParameterError, match="engine_id"):
            await record_ai_event(
                db,
                engine_id="   ",
                dataset_version_id="dataset-input-validation",
                model_identifier="test_model",
                event_type="test_event",
                inputs={},
                governance_metadata={"test": "metadata"},
            )


@pytest.mark.anyio
async def test_record_ai_event_rejects_empty_model_identifier(sqlite_db: None) -> None:
    """Test that record_ai_event rejects empty model_identifier."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        async with db.begin():
            db.add(DatasetVersion(id="dataset-input-validation"))

        with pytest.raises(InvalidStringParameterError, match="model_identifier"):
            await record_ai_event(
                db,
                engine_id="test_engine",
                dataset_version_id="dataset-input-validation",
                model_identifier="",
                event_type="test_event",
                inputs={},
                governance_metadata={"test": "metadata"},
            )


@pytest.mark.anyio
async def test_record_ai_event_rejects_whitespace_model_identifier(sqlite_db: None) -> None:
    """Test that record_ai_event rejects whitespace-only model_identifier."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        async with db.begin():
            db.add(DatasetVersion(id="dataset-input-validation"))

        with pytest.raises(InvalidStringParameterError, match="model_identifier"):
            await record_ai_event(
                db,
                engine_id="test_engine",
                dataset_version_id="dataset-input-validation",
                model_identifier="\t\n  ",
                event_type="test_event",
                inputs={},
                governance_metadata={"test": "metadata"},
            )


@pytest.mark.anyio
async def test_record_ai_event_rejects_empty_event_type(sqlite_db: None) -> None:
    """Test that record_ai_event rejects empty event_type."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        async with db.begin():
            db.add(DatasetVersion(id="dataset-input-validation"))

        with pytest.raises(InvalidStringParameterError, match="event_type"):
            await record_ai_event(
                db,
                engine_id="test_engine",
                dataset_version_id="dataset-input-validation",
                model_identifier="test_model",
                event_type="",
                inputs={},
                governance_metadata={"test": "metadata"},
            )


@pytest.mark.anyio
async def test_record_ai_event_rejects_whitespace_event_type(sqlite_db: None) -> None:
    """Test that record_ai_event rejects whitespace-only event_type."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        async with db.begin():
            db.add(DatasetVersion(id="dataset-input-validation"))

        with pytest.raises(InvalidStringParameterError, match="event_type"):
            await record_ai_event(
                db,
                engine_id="test_engine",
                dataset_version_id="dataset-input-validation",
                model_identifier="test_model",
                event_type="  \t  ",
                inputs={},
                governance_metadata={"test": "metadata"},
            )


@pytest.mark.anyio
async def test_record_ai_event_strips_whitespace_from_valid_strings(sqlite_db: None) -> None:
    """Test that record_ai_event strips whitespace from valid strings but preserves content."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        async with db.begin():
            db.add(DatasetVersion(id="dataset-input-validation"))

        event = await record_ai_event(
            db,
            engine_id="  test_engine  ",
            dataset_version_id="dataset-input-validation",
            model_identifier="  test_model  ",
            event_type="  test_event  ",
            inputs={},
            governance_metadata={"test": "metadata"},
        )
        await db.commit()

        # Verify that values were stripped but content preserved
        assert event.engine_id == "test_engine"
        assert event.model_identifier == "test_model"
        assert event.event_type == "test_event"


@pytest.mark.anyio
async def test_log_model_call_rejects_empty_engine_id(sqlite_db: None) -> None:
    """Test that log_model_call rejects empty engine_id."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        async with db.begin():
            db.add(DatasetVersion(id="dataset-input-validation"))

        with pytest.raises(InvalidStringParameterError, match="engine_id"):
            await log_model_call(
                db,
                engine_id="",
                dataset_version_id="dataset-input-validation",
                model_identifier="test_model",
                inputs={},
                governance_metadata={"test": "metadata"},
            )


@pytest.mark.anyio
async def test_log_tool_call_rejects_empty_model_identifier(sqlite_db: None) -> None:
    """Test that log_tool_call rejects empty model_identifier."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        async with db.begin():
            db.add(DatasetVersion(id="dataset-input-validation"))

        with pytest.raises(InvalidStringParameterError, match="model_identifier"):
            await log_tool_call(
                db,
                engine_id="test_engine",
                dataset_version_id="dataset-input-validation",
                tool_name="test_tool",
                inputs={},
                model_identifier="",
                governance_metadata={"test": "metadata"},
            )


@pytest.mark.anyio
async def test_log_rag_event_rejects_empty_engine_id(sqlite_db: None) -> None:
    """Test that log_rag_event rejects empty engine_id."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        async with db.begin():
            db.add(DatasetVersion(id="dataset-input-validation"))

        with pytest.raises(InvalidStringParameterError, match="engine_id"):
            await log_rag_event(
                db,
                engine_id="",
                dataset_version_id="dataset-input-validation",
                rag_sources=[],
                governance_metadata={"test": "metadata"},
            )
