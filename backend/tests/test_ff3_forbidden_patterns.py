"""
Forbidden Patterns Tests (Engine #2)

Scope:
- Fraud/blame language is always forbidden
- Intercompany elimination is always forbidden
- Aggregation is forbidden until explicitly introduced later
"""
import pathlib
import re

from backend.app.engines.financial_forensics import confidence, finding, matching, review


def test_no_fraud_language() -> None:
    """
    Structural assertion: No fraud/blame language in engine code.
    """
    engine_dir = pathlib.Path(__file__).resolve().parents[2] / "app" / "engines" / "financial_forensics"
    
    forbidden_words = [
        "fraud",
        "fraudulent",
        "fraudster",
        "criminal",
        "theft",
        "steal",
        "embezzle",
        "blame",
        "responsible",
        "culprit",
        "guilty",
        "accuse",
        "accusation",
    ]
    
    violations = []
    for py_file in engine_dir.rglob("*.py"):
        if py_file.name == "__init__.py":
            continue
        
        content = py_file.read_text(encoding="utf-8").lower()
        for word in forbidden_words:
            if word in content:
                # Check if it's in a comment or string (might be in test names)
                # For now, flag all occurrences
                violations.append(f"{py_file.name}: contains '{word}'")
    
    assert len(violations) == 0, (
        f"Found fraud/blame language violations:\n"
        + "\n".join(f"  - {v}" for v in violations)
    )


def test_no_aggregation_logic() -> None:
    """
    Structural assertion: No aggregation logic in matching/normalization.
    """
    engine_dir = pathlib.Path(__file__).resolve().parents[2] / "app" / "engines" / "financial_forensics"
    
    forbidden_patterns = [
        r"\.sum\(\)",
        r"\.aggregate\(",
        r"GROUP BY",
        r"groupby\(",
        r"\.group_by\(",
    ]
    
    violations = []
    for py_file in engine_dir.rglob("*.py"):
        if py_file.name in ["__init__.py", "fx_convert.py"]:  # fx_convert may have sum for conversion
            continue
        
        content = py_file.read_text(encoding="utf-8")
        for pattern in forbidden_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                violations.append(f"{py_file.name}: contains aggregation pattern '{pattern}'")
    
    # Note: sum() for list summation is allowed (e.g., sum(payments))
    # Only flag SQL aggregation or pandas-style aggregation
    assert len(violations) == 0, (
        f"Found aggregation logic violations:\n"
        + "\n".join(f"  - {v}" for v in violations)
    )


def test_no_leakage_logic() -> None:
    """
    Deprecated by FF-4: leakage modules are now allowed.
    """
    assert True


def test_no_intercompany_elimination() -> None:
    """
    Structural assertion: No intercompany elimination logic.
    """
    engine_dir = pathlib.Path(__file__).resolve().parents[2] / "app" / "engines" / "financial_forensics"
    
    forbidden_patterns = [
        "intercompany.*eliminat",
        "intercompany.*consolidat",
        "intercompany.*net",
        "intercompany.*balance",
        "eliminate.*intercompany",
        "consolidate.*intercompany",
    ]
    
    violations = []
    for py_file in engine_dir.rglob("*.py"):
        if py_file.name == "__init__.py":
            continue
        
        content = py_file.read_text(encoding="utf-8").lower()
        for pattern in forbidden_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                violations.append(f"{py_file.name}: contains intercompany elimination pattern '{pattern}'")
    
    assert len(violations) == 0, (
        f"Found intercompany elimination violations:\n"
        + "\n".join(f"  - {v}" for v in violations)
    )

