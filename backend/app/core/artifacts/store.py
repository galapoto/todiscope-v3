from __future__ import annotations

from backend.app.core.artifacts.interface import ArtifactStore
from backend.app.core.config import get_settings


_STORE: ArtifactStore | None = None


def get_artifact_store() -> ArtifactStore:
    global _STORE
    if _STORE is not None:
        return _STORE
    kind = get_settings().artifact_store_kind
    if kind == "s3":
        from backend.app.core.artifacts.s3 import S3ArtifactStore

        _STORE = S3ArtifactStore()
    elif kind == "memory":
        from backend.app.core.artifacts.memory import MemoryArtifactStore

        _STORE = MemoryArtifactStore()
    else:
        raise RuntimeError(f"Unknown artifact_store kind: {kind}")
    return _STORE


def reset_artifact_store_for_tests() -> None:
    global _STORE
    _STORE = None
