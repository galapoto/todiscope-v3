"""
Audit Readiness Engine — Engine Specification

This module provides the engine registration entrypoint.
The actual engine implementation is in engine.py.
"""
from __future__ import annotations

from backend.app.engines.audit_readiness.engine import register_engine

__all__ = ["register_engine"]

