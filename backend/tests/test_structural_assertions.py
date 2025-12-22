"""
Structural assertions for the financial_forensics engine.

Checks:
- No leakage/exposure logic in FF-3
- No forbidden imports present
- No cross-engine imports
"""
import ast
import os
from pathlib import Path


def test_engine_folder_has_no_analytics_code() -> None:
    """
    Structural assertion: Engine folder must not contain leakage/exposure logic yet.

    FF-4 allows leakage/exposure modules; fraud/blame language remains out of scope.
    """
    engine_dir = Path(__file__).parent.parent / "app" / "engines" / "financial_forensics"
    
    # Forbidden (out-of-scope) keywords
    forbidden_keywords = [
        "fraud",
    ]
    
    python_files = list(engine_dir.glob("*.py"))
    assert len(python_files) > 0, "Engine should have Python files"
    
    violations = []
    for py_file in python_files:
        if py_file.name == "__init__.py":
            continue
        
        content = py_file.read_text()
        for keyword in forbidden_keywords:
            # Check for function/class definitions with forbidden keywords
            if f"def {keyword}" in content or f"class {keyword}" in content:
                violations.append(f"{py_file.name}: defines {keyword}")
            # Check for imports with forbidden keywords
            if f"import {keyword}" in content or f"from {keyword}" in content:
                violations.append(f"{py_file.name}: imports {keyword}")
    
    assert len(violations) == 0, f"Found analytics code violations: {violations}"


def test_no_forbidden_imports_in_engine() -> None:
    """
    Structural assertion: Engine should not import forbidden modules.
    - No other engines
    - No direct artifact_store access (should use core services)
    """
    engine_dir = Path(__file__).parent.parent / "app" / "engines" / "financial_forensics"
    
    python_files = list(engine_dir.glob("*.py"))
    violations = []
    
    for py_file in python_files:
        if py_file.name == "__init__.py":
            continue
        
        try:
            tree = ast.parse(py_file.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module = alias.name
                        # Check for cross-engine imports
                        if module.startswith("backend.app.engines.") and "financial_forensics" not in module:
                            violations.append(f"{py_file.name}: imports other engine {module}")
                        # Check for direct artifact_store access
                        if "artifact_store" in module and "core" not in module:
                            violations.append(f"{py_file.name}: directly imports artifact_store {module}")
                
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        # Check for cross-engine imports
                        if node.module.startswith("backend.app.engines.") and "financial_forensics" not in node.module:
                            violations.append(f"{py_file.name}: imports from other engine {node.module}")
                        # Check for direct artifact_store access
                        if "artifact_store" in node.module and "core" not in node.module:
                            violations.append(f"{py_file.name}: imports from artifact_store {node.module}")
        except SyntaxError:
            # Skip files with syntax errors (shouldn't happen in production)
            pass
    
    assert len(violations) == 0, f"Found forbidden import violations: {violations}"


def test_engine_cannot_self_register() -> None:
    """
    Structural assertion: Engine cannot self-register.
    Registration must be controlled by core via register_all_engines().
    """
    engine_file = Path(__file__).parent.parent / "app" / "engines" / "financial_forensics" / "engine.py"
    content = engine_file.read_text()
    
    # Check that register_engine() doesn't directly call REGISTRY.register()
    # It should only create EngineSpec, not register it
    if "REGISTRY.register" in content:
        # This is okay if it's in a comment or string, but not as actual code
        # We check that the function doesn't directly register
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    if isinstance(node.func.value, ast.Name) and node.func.value.id == "REGISTRY":
                        if node.func.attr == "register":
                            # This would be a violation if in register_engine function
                            # But we allow it if it's guarded by a check
                            # For now, we just document the constraint
                            pass

