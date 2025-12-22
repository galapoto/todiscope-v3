"""
FF-3 Determinism Enforcement: datetime.now() Forbidden

Tests that FAIL THE BUILD if datetime.now() is used.
"""
import pathlib
import re

import pytest


def test_no_datetime_now_in_matching() -> None:
    """
    BUILD FAILURE TEST: No datetime.now() in matching logic.
    
    This test will fail the build if datetime.now() is found in matching code.
    """
    engine_dir = pathlib.Path(__file__).resolve().parents[3] / "app" / "engines" / "financial_forensics"
    
    forbidden_patterns = [
        r"datetime\.now\(",
        r"date\.today\(",
        r"time\.time\(",
        r"datetime\.utcnow\(",
    ]
    
    violations = []
    for py_file in engine_dir.rglob("*.py"):
        if py_file.name in ["__init__.py", "run.py"]:  # run.py may have datetime.now for metadata
            continue
        
        content = py_file.read_text(encoding="utf-8")
        for pattern in forbidden_patterns:
            if re.search(pattern, content):
                violations.append(f"{py_file.relative_to(engine_dir.parents[2])}: contains '{pattern}'")
    
    assert len(violations) == 0, (
        f"BUILD FAILURE: Found datetime.now() violations in matching logic:\n"
        + "\n".join(f"  - {v}" for v in violations)
    )


