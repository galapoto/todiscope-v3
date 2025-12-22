"""
Determinism Tests for FF-4: No Hidden Defaults

Tests preventing hidden defaults in leakage typology and exposure calculation.
"""
from __future__ import annotations

import ast
import pathlib

import pytest


def test_no_hidden_defaults_in_leakage_code() -> None:
    """
    Structural test: No hidden defaults in leakage code.
    
    Checks for:
    - No default values in function signatures that affect leakage typology
    - No hardcoded thresholds or tolerances
    - No implicit currency assumptions
    """
    root = pathlib.Path(__file__).resolve().parents[4]
    leakage_dir = root / "backend" / "app" / "engines" / "financial_forensics" / "leakage"
    
    if not leakage_dir.exists():
        pytest.skip("Leakage directory does not exist")
    
    violations = []
    
    for path in leakage_dir.rglob("*.py"):
        if path.name == "__init__.py":
            continue
        
        try:
            content = path.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(path))
            
            # Check for function definitions with default values that might affect leakage
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Check for default values in leakage-related functions
                    if any(
                        keyword in node.name.lower()
                        for keyword in ["leakage", "exposure", "typology", "intercompany"]
                    ):
                        for arg in node.args.args:
                            # Check if this arg has a default value
                            arg_index = node.args.args.index(arg)
                            if arg_index < len(node.args.defaults):
                                default = node.args.defaults[arg_index]
                                # Check if default is a non-trivial value (not None, not empty dict/list)
                                if isinstance(default, (ast.Constant, ast.Num)):
                                    if isinstance(default, ast.Constant):
                                        val = default.value
                                    else:
                                        val = default.n
                                    
                                    # Allow None, empty dict/list, but flag other defaults
                                    if val not in (None, {}, []):
                                        violations.append(
                                            f"{path.relative_to(root)}:{node.lineno}: "
                                            f"Function '{node.name}' has default value for '{arg.arg}': {val}"
                                        )
        except SyntaxError:
            # Skip files with syntax errors (they'll be caught by other tests)
            pass
    
    assert len(violations) == 0, (
        f"Found hidden defaults in leakage code:\n"
        + "\n".join(f"  - {v}" for v in violations)
    )


def test_no_hardcoded_thresholds() -> None:
    """
    Structural test: No hardcoded thresholds or tolerances in leakage code.
    
    Checks for hardcoded numeric values that might be thresholds.
    """
    root = pathlib.Path(__file__).resolve().parents[4]
    leakage_dir = root / "backend" / "app" / "engines" / "financial_forensics" / "leakage"
    
    if not leakage_dir.exists():
        pytest.skip("Leakage directory does not exist")
    
    violations = []
    
    # Suspicious numeric patterns (thresholds, tolerances, limits)
    suspicious_patterns = [
        (r"\b0\.0[0-9]+\b", "Possible tolerance value"),
        (r"\b[0-9]+\.[0-9]{2,}\b", "Possible threshold value"),
        (r"\b(100|1000|10000)\b", "Possible limit value"),
    ]
    
    for path in leakage_dir.rglob("*.py"):
        if path.name == "__init__.py":
            continue
        
        content = path.read_text(encoding="utf-8")
        
        # Skip test files and docstrings
        if "test" in path.name.lower():
            continue
        
        import re
        for pattern, reason in suspicious_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                # Check if it's in a comment or string literal (allow those)
                line_start = content.rfind("\n", 0, match.start()) + 1
                line = content[line_start:match.end()]
                if not (line.strip().startswith("#") or '"' in line or "'" in line):
                    violations.append(
                        f"{path.relative_to(root)}: Possible hardcoded threshold: {match.group()} ({reason})"
                    )
    
    # Allow some violations if they're clearly not thresholds (e.g., version numbers, IDs)
    # Filter out false positives
    filtered_violations = [
        v for v in violations
        if not any(
            ignore in v.lower()
            for ignore in ["version", "id", "uuid", "sha256", "test", "example"]
        )
    ]
    
    assert len(filtered_violations) == 0, (
        f"Found possible hardcoded thresholds in leakage code:\n"
        + "\n".join(f"  - {v}" for v in filtered_violations)
    )


def test_no_implicit_currency_assumptions() -> None:
    """
    Structural test: No implicit currency assumptions in leakage code.
    
    Checks for hardcoded currency codes or currency-related defaults.
    """
    root = pathlib.Path(__file__).resolve().parents[4]
    leakage_dir = root / "backend" / "app" / "engines" / "financial_forensics" / "leakage"
    
    if not leakage_dir.exists():
        pytest.skip("Leakage directory does not exist")
    
    violations = []
    
    # Common currency codes that should not be hardcoded
    common_currencies = ["USD", "EUR", "GBP", "JPY", "CHF"]
    
    for path in leakage_dir.rglob("*.py"):
        if path.name == "__init__.py":
            continue
        
        content = path.read_text(encoding="utf-8")
        
        # Skip test files
        if "test" in path.name.lower():
            continue
        
        for currency in common_currencies:
            # Check for hardcoded currency (not in comments, strings, or test data)
            pattern = rf'["\']{currency}["\']'
            import re
            matches = re.finditer(pattern, content)
            for match in matches:
                # Check if it's in a comment
                line_start = content.rfind("\n", 0, match.start()) + 1
                line = content[line_start:match.end()]
                if not line.strip().startswith("#"):
                    # Allow if it's clearly in a test or example
                    if "test" not in path.name.lower() and "example" not in content.lower():
                        violations.append(
                            f"{path.relative_to(root)}: Possible hardcoded currency '{currency}'"
                        )
    
    assert len(violations) == 0, (
        f"Found possible implicit currency assumptions in leakage code:\n"
        + "\n".join(f"  - {v}" for v in violations)
    )


