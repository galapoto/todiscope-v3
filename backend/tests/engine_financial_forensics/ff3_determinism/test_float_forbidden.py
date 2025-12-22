"""
FF-3 Determinism Enforcement: Float Arithmetic Forbidden

Tests that FAIL THE BUILD if float arithmetic is used.
"""
import ast
import pathlib

import pytest


def test_no_float_arithmetic_in_matching() -> None:
    """
    BUILD FAILURE TEST: No float arithmetic in matching logic.
    
    This test will fail the build if float arithmetic is found.
    """
    engine_dir = pathlib.Path(__file__).resolve().parents[3] / "app" / "engines" / "financial_forensics"
    
    violations = []
    for py_file in engine_dir.rglob("*.py"):
        if py_file.name in ["__init__.py", "fx_convert.py"]:  # fx_convert may parse floats
            continue
        
        content = py_file.read_text(encoding="utf-8")
        
        # Simple pattern matching for float() in arithmetic context
        # Check for float() followed by arithmetic operators
        import re
        float_pattern = r"float\s*\([^)]+\)\s*[+\-*/]"
        if re.search(float_pattern, content):
            violations.append(
                f"{py_file.relative_to(engine_dir.parents[2])}: "
                f"float() used in arithmetic context"
            )
        
        # Check for float literals in arithmetic (e.g., 1.0 + 2.0)
        float_literal_pattern = r"\b\d+\.\d+\s*[+\-*/]"
        if re.search(float_literal_pattern, content):
            # This is a simple check - may have false positives in comments/strings
            # But it will catch obvious violations
            violations.append(
                f"{py_file.relative_to(engine_dir.parents[2])}: "
                f"float literal in arithmetic context (check manually)"
            )
    
    assert len(violations) == 0, (
        f"BUILD FAILURE: Found float arithmetic violations:\n"
        + "\n".join(f"  - {v}" for v in violations)
    )

