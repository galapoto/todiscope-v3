import pathlib
import ast

from backend.app.core.forbidden_patterns.rules import FORBIDDEN_TOKENS_IN_CORE


def test_core_contains_no_forbidden_tokens() -> None:
    root = pathlib.Path(__file__).resolve().parents[2]
    core_dir = root / "backend" / "app" / "core"
    for path in core_dir.rglob("*.py"):
        text = path.read_text(encoding="utf-8").lower()
        for token in FORBIDDEN_TOKENS_IN_CORE:
            assert token not in text, f"Forbidden token '{token}' in core file: {path}"


def test_core_does_not_import_engines() -> None:
    root = pathlib.Path(__file__).resolve().parents[2]
    core_dir = root / "backend" / "app" / "core"
    for path in core_dir.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith("backend.app.engines"), f"Core imports engines in {path}"
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith("backend.app.engines"), f"Core imports engines in {path}"


def test_engines_do_not_import_each_other() -> None:
    root = pathlib.Path(__file__).resolve().parents[2]
    engines_dir = root / "backend" / "app" / "engines"
    for path in engines_dir.rglob("*.py"):
        if path.name == "__init__.py":
            continue
        engine_name = path.relative_to(engines_dir).parts[0]
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith("backend.app.engines."):
                    assert node.module.startswith(
                        f"backend.app.engines.{engine_name}."
                    ), f"Engine-to-engine import in {path}"
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("backend.app.engines."):
                        assert alias.name.startswith(
                            f"backend.app.engines.{engine_name}."
                        ), f"Engine-to-engine import in {path}"


def test_engines_do_not_import_artifact_store() -> None:
    """
    Mechanical guard: Engines must not access `artifact_store` directly.
    They may call core-owned services (e.g. `fx_service`) that encapsulate artifact_store usage.
    """
    root = pathlib.Path(__file__).resolve().parents[2]
    engines_dir = root / "backend" / "app" / "engines"
    disallowed_prefixes = (
        "backend.app.core.artifacts.store",
        "backend.app.core.artifacts.s3",
        "backend.app.core.artifacts.memory",
        "backend.app.core.artifacts.interface",
    )
    disallowed_third_party = ("boto3", "botocore", "minio")
    for path in engines_dir.rglob("*.py"):
        if path.name == "__init__.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith(disallowed_prefixes), (
                    f"Engine {path} imports disallowed artifacts module: {node.module}. "
                    "Engines must not access artifact_store directly; use core services."
                )
                assert not node.module.split(".")[0] in disallowed_third_party, (
                    f"Engine {path} imports disallowed third-party client: {node.module}. "
                    "artifact_store access is core-only."
                )
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith(disallowed_prefixes), (
                        f"Engine {path} imports disallowed artifacts module: {alias.name}. "
                        "Engines must not access artifact_store directly; use core services."
                    )
                    assert not alias.name.split(".")[0] in disallowed_third_party, (
                        f"Engine {path} imports disallowed third-party client: {alias.name}. "
                        "artifact_store access is core-only."
                    )


def test_no_datetime_now_in_engines_or_artifacts() -> None:
    """
    Deterministic-time guard: No datetime.now(), date.today(), or time.time() usage
    in engines or core artifacts code.
    
    Prevents non-deterministic time-dependent logic.
    """
    root = pathlib.Path(__file__).resolve().parents[2]
    
    # Check engines
    engines_dir = root / "backend" / "app" / "engines"
    violations = []
    
    for path in engines_dir.rglob("*.py"):
        if path.name == "__init__.py":
            continue
        content = path.read_text(encoding="utf-8")
        
        # Check for datetime.now() patterns
        if "datetime.now(" in content:
            violations.append(f"{path.relative_to(root)}: contains datetime.now()")
        if "date.today(" in content:
            violations.append(f"{path.relative_to(root)}: contains date.today()")
        if "time.time(" in content:
            violations.append(f"{path.relative_to(root)}: contains time.time()")
        if "datetime.utcnow(" in content:
            violations.append(f"{path.relative_to(root)}: contains datetime.utcnow()")
    
    # Check core artifacts
    artifacts_dir = root / "backend" / "app" / "core" / "artifacts"
    for path in artifacts_dir.rglob("*.py"):
        if path.name == "__init__.py":
            continue
        content = path.read_text(encoding="utf-8")
        
        # Check for datetime.now() patterns
        if "datetime.now(" in content:
            violations.append(f"{path.relative_to(root)}: contains datetime.now()")
        if "date.today(" in content:
            violations.append(f"{path.relative_to(root)}: contains date.today()")
        if "time.time(" in content:
            violations.append(f"{path.relative_to(root)}: contains time.time()")
        if "datetime.utcnow(" in content:
            violations.append(f"{path.relative_to(root)}: contains datetime.utcnow()")
    
    assert len(violations) == 0, (
        f"Found datetime.now() violations (non-deterministic time usage):\n"
        + "\n".join(f"  - {v}" for v in violations)
    )
