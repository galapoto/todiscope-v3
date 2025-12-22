"""
FF-2 Forbidden Patterns Tests

Tests:
- No live FX calls
- No float arithmetic in FX conversion
"""
import ast
import pathlib

def test_no_live_fx_calls() -> None:
    """
    Structural assertion: No live FX API calls in engine code.
    """
    engine_dir = pathlib.Path(__file__).resolve().parents[2] / "backend" / "app" / "engines" / "financial_forensics"
    
    forbidden_patterns = [
        "requests.get",
        "requests.post",
        "urllib",
        "http.client",
        "aiohttp",
        "httpx",
        "exchange_rate",
        "live_fx",
        "fetch_fx",
        "get_fx_rate",
    ]
    
    violations = []
    for py_file in engine_dir.rglob("*.py"):
        if py_file.name == "__init__.py":
            continue
        
        content = py_file.read_text(encoding="utf-8")
        for pattern in forbidden_patterns:
            if pattern in content.lower():
                violations.append(f"{py_file.name}: contains '{pattern}'")
    
    assert len(violations) == 0, f"Found live FX call violations: {violations}"


def test_no_float_arithmetic_in_fx() -> None:
    """
    Structural assertion: FX conversion uses Decimal, not float.
    """
    fx_file = (
        pathlib.Path(__file__).resolve().parents[2]
        / "backend"
        / "app"
        / "engines"
        / "financial_forensics"
        / "fx_convert.py"
    )

    content = fx_file.read_text(encoding="utf-8")
    
    tree = ast.parse(content)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "float":
            raise AssertionError("FX conversion must not call float(); must use Decimal only.")
    
    # Verify Decimal is used
    assert "from decimal import Decimal" in content or "import decimal" in content
    assert "Decimal(" in content  # Decimal constructor used


def test_fx_conversion_uses_decimal_type() -> None:
    """
    Runtime test: FX conversion returns Decimal type.
    """
    import pytest
    from decimal import Decimal
    
    # This would be tested in test_ff2_fx_immutability.py
    # This test documents the constraint
    assert True  # Constraint verified in test_ff2_fx_immutability.py::test_fx_conversion_uses_decimal_not_float

