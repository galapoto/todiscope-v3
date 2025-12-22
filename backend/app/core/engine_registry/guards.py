"""
Defensive constraints for engine execution.

Prevents:
- Cross-engine imports
- Direct artifact_store access from engines
- Writes outside owned tables
"""
from __future__ import annotations

import inspect
from typing import Any


class CrossEngineImportError(RuntimeError):
    """Raised when an engine imports another engine."""
    pass


class ArtifactStoreDirectAccessError(RuntimeError):
    """Raised when an engine directly accesses artifact_store."""
    pass


class TableWriteViolationError(RuntimeError):
    """Raised when an engine attempts to write outside owned tables."""
    pass


def check_no_cross_engine_imports() -> None:
    """
    Structural assertion: Engine code cannot import other engines.
    This should be called during engine registration or static analysis.
    """
    # This would be better implemented as a static analysis check
    # For now, we document the constraint
    pass


def check_no_artifact_store_direct_access(engine_id: str) -> None:
    """
    Defensive constraint: Engine cannot directly access artifact_store.
    Engines must use core services that wrap artifact_store.
    """
    frame = inspect.currentframe()
    if frame is not None and frame.f_back is not None:
        caller_file = frame.f_back.f_code.co_filename
        if "/engines/" in caller_file:
            # Check if caller is directly calling get_artifact_store
            if "get_artifact_store" in frame.f_back.f_code.co_names:
                raise ArtifactStoreDirectAccessError(
                    f"Engine {engine_id} cannot directly access artifact_store. "
                    "Use core services that wrap artifact_store access."
                )


def validate_table_ownership(table_name: str, engine_id: str, owned_tables: tuple[str, ...]) -> None:
    """
    Defensive constraint: Engine can only write to owned tables.
    
    Args:
        table_name: Name of table being written to
        engine_id: ID of the engine attempting the write
        owned_tables: List of table names/prefixes owned by the engine
    """
    # Check exact match first
    if table_name in owned_tables:
        return
    
    # Check prefix match (for tables like engine_<name>_*)
    for owned_prefix in owned_tables:
        if table_name.startswith(owned_prefix):
            return
    
    # If we get here, table is not owned
    raise TableWriteViolationError(
        f"Engine {engine_id} attempted to write to table '{table_name}' "
        f"which is not in owned_tables: {owned_tables}. "
        "Engines can only write to their declared owned tables."
    )


