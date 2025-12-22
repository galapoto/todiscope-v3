"""
Determinism Tests for FF-4: No Aggregation Beyond Dataset/Run

Tests preventing aggregation logic that goes beyond dataset/run scope.
"""
from __future__ import annotations

import ast
import pathlib


def test_aggregation_requires_dataset_version_id() -> None:
    """
    Structural test: Aggregation functions must require dataset_version_id.
    
    Checks that aggregation functions explicitly require dataset_version_id parameter.
    """
    root = pathlib.Path(__file__).resolve().parents[4]
    leakage_dir = root / "backend" / "app" / "engines" / "financial_forensics" / "leakage"
    
    if not leakage_dir.exists():
        return  # Skip if directory doesn't exist
    
    violations = []
    
    for path in leakage_dir.rglob("*.py"):
        if path.name == "__init__.py":
            continue
        
        try:
            content = path.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(path))
            
            # Check for function definitions with "aggregate" in name
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if "aggregate" in node.name.lower() or "sum" in node.name.lower():
                        # Check if function has dataset_version_id parameter
                        param_names = [arg.arg for arg in node.args.args]
                        if "dataset_version_id" not in param_names:
                            violations.append(
                                f"{path.relative_to(root)}:{node.lineno}: "
                                f"Function '{node.name}' appears to aggregate but lacks 'dataset_version_id' parameter"
                            )
        except SyntaxError:
            # Skip files with syntax errors
            pass
    
    assert len(violations) == 0, (
        f"Found aggregation functions without dataset_version_id requirement:\n"
        + "\n".join(f"  - {v}" for v in violations)
    )


def test_aggregation_requires_run_id() -> None:
    """
    Structural test: Aggregation functions must require run_id.
    
    Checks that aggregation functions explicitly require run_id parameter.
    """
    root = pathlib.Path(__file__).resolve().parents[4]
    leakage_dir = root / "backend" / "app" / "engines" / "financial_forensics" / "leakage"
    
    if not leakage_dir.exists():
        return  # Skip if directory doesn't exist
    
    violations = []
    
    for path in leakage_dir.rglob("*.py"):
        if path.name == "__init__.py":
            continue
        
        try:
            content = path.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(path))
            
            # Check for function definitions with "aggregate" in name
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if "aggregate" in node.name.lower() or "sum" in node.name.lower():
                        # Check if function has run_id parameter
                        param_names = [arg.arg for arg in node.args.args]
                        if "run_id" not in param_names:
                            violations.append(
                                f"{path.relative_to(root)}:{node.lineno}: "
                                f"Function '{node.name}' appears to aggregate but lacks 'run_id' parameter"
                            )
        except SyntaxError:
            # Skip files with syntax errors
            pass
    
    assert len(violations) == 0, (
        f"Found aggregation functions without run_id requirement:\n"
        + "\n".join(f"  - {v}" for v in violations)
    )


def test_no_cross_dataset_aggregation() -> None:
    """
    Structural test: No cross-dataset aggregation logic.
    
    Checks for patterns that might aggregate across multiple datasets.
    """
    root = pathlib.Path(__file__).resolve().parents[4]
    leakage_dir = root / "backend" / "app" / "engines" / "financial_forensics" / "leakage"
    
    if not leakage_dir.exists():
        return  # Skip if directory doesn't exist
    
    violations = []
    
    suspicious_patterns = [
        r"SELECT.*FROM.*WHERE.*dataset_version_id.*IN",  # SQL IN clause with multiple datasets
        r"\.filter\(.*dataset_version_id.*in_",  # SQLAlchemy in_ with multiple datasets
        r"for.*dataset.*in.*datasets",  # Python loop over multiple datasets
    ]
    
    for path in leakage_dir.rglob("*.py"):
        if path.name == "__init__.py":
            continue
        
        content = path.read_text(encoding="utf-8")
        
        import re
        for pattern in suspicious_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                violations.append(
                    f"{path.relative_to(root)}: Possible cross-dataset aggregation pattern: {pattern}"
                )
    
    # Filter false positives (e.g., in test files, comments)
    filtered_violations = []
    for v in violations:
        # Skip if violation is in a test file
        if "test" not in v.lower():
            # Check if pattern is in a comment (simple heuristic)
            path_str = v.split(":")[0] if ":" in v else ""
            if path_str:
                try:
                    file_content = (root / path_str).read_text(encoding="utf-8")
                    # If pattern appears after #, it's likely a comment
                    if "#" not in file_content[:file_content.find(v.split(":")[-1]) if ":" in v and v.split(":")[-1] in file_content else 0]:
                        filtered_violations.append(v)
                except (FileNotFoundError, ValueError):
                    # If we can't check, include it to be safe
                    filtered_violations.append(v)
    
    assert len(filtered_violations) == 0, (
        f"Found possible cross-dataset aggregation patterns:\n"
        + "\n".join(f"  - {v}" for v in filtered_violations)
    )

