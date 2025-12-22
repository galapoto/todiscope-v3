"""
Determinism Tests for FF-4: No Time-Based Logic

Tests preventing time-dependent logic in leakage typology and exposure calculation.
"""
from __future__ import annotations

import pathlib
import re


def test_no_datetime_now_in_leakage_code() -> None:
    """
    Structural test: No datetime.now(), date.today(), or time.time() usage
    in leakage code.
    
    Prevents non-deterministic time-dependent logic.
    """
    root = pathlib.Path(__file__).resolve().parents[4]
    leakage_dir = root / "backend" / "app" / "engines" / "financial_forensics" / "leakage"
    
    if not leakage_dir.exists():
        return  # Skip if directory doesn't exist
    
    violations = []
    
    for path in leakage_dir.rglob("*.py"):
        if path.name == "__init__.py":
            continue
        
        content = path.read_text(encoding="utf-8")
        
        # Check for datetime.now() patterns
        if "datetime.now(" in content:
            violations.append(f"{path.relative_to(root)}: contains datetime.now()")
        
        # Check for date.today()
        if "date.today(" in content:
            violations.append(f"{path.relative_to(root)}: contains date.today()")
        
        # Check for time.time()
        if "time.time(" in content:
            violations.append(f"{path.relative_to(root)}: contains time.time()")
        
        # Check for datetime.utcnow()
        if "datetime.utcnow(" in content:
            violations.append(f"{path.relative_to(root)}: contains datetime.utcnow()")
    
    assert len(violations) == 0, (
        f"Found datetime.now() violations (non-deterministic time usage):\n"
        + "\n".join(f"  - {v}" for v in violations)
    )


def test_no_environment_time_in_leakage_code() -> None:
    """
    Structural test: No environment-dependent time logic in leakage code.
    
    Checks for timezone-dependent or environment variable time usage.
    """
    root = pathlib.Path(__file__).resolve().parents[4]
    leakage_dir = root / "backend" / "app" / "engines" / "financial_forensics" / "leakage"
    
    if not leakage_dir.exists():
        return  # Skip if directory doesn't exist
    
    violations = []
    
    for path in leakage_dir.rglob("*.py"):
        if path.name == "__init__.py":
            continue
        
        content = path.read_text(encoding="utf-8")
        
        # Check for timezone.now() (Django-style, but check anyway)
        if "timezone.now(" in content:
            violations.append(f"{path.relative_to(root)}: contains timezone.now()")
        
        # Check for os.environ time-related variables
        if re.search(r'os\.environ\[["\'](TZ|TIME|DATE)', content):
            violations.append(f"{path.relative_to(root)}: uses environment time variables")
    
    assert len(violations) == 0, (
        f"Found environment time violations (non-deterministic time usage):\n"
        + "\n".join(f"  - {v}" for v in violations)
    )


