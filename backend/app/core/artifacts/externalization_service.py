from __future__ import annotations

import hashlib

from backend.app.core.artifacts.interface import StoredArtifact
from backend.app.core.artifacts.store import get_artifact_store
from backend.app.core.config import get_settings


class ArtifactImmutableWriteError(RuntimeError):
    pass


class ArtifactChecksumMismatchError(ValueError):
    pass


async def load_bytes_with_optional_checksum(*, key: str, expected_sha256: str | None) -> bytes:
    store = get_artifact_store()
    data = await store.get_bytes(key=key)
    if expected_sha256 is not None:
        actual = hashlib.sha256(data).hexdigest()
        if actual != expected_sha256:
            raise ArtifactChecksumMismatchError(
                f"ARTIFACT_CHECKSUM_MISMATCH: key={key} expected_sha256={expected_sha256} actual_sha256={actual}"
            )
    return data


def _uri_for_key(key: str) -> str:
    store = get_artifact_store()
    if store.__class__.__name__ == "MemoryArtifactStore":
        return f"memory://{key}"
    if store.__class__.__name__ == "S3ArtifactStore":
        s = get_settings()
        assert s.s3_bucket is not None
        return f"s3://{s.s3_bucket}/{key}"
    return f"unknown://{key}"


async def put_bytes_immutable(*, key: str, data: bytes, content_type: str) -> StoredArtifact:
    """
    Mechanics-only helper for immutable artifact writes.

    If the key already exists:
    - bytes must be identical (otherwise raise)
    - return a deterministic StoredArtifact describing the existing bytes
    """
    store = get_artifact_store()
    try:
        existing = await store.get_bytes(key=key)
    except Exception:
        existing = None

    if existing is not None:
        if existing != data:
            raise ArtifactImmutableWriteError(
                f"ARTIFACT_OVERWRITE_FORBIDDEN: key={key} already exists with different bytes"
            )
        sha = hashlib.sha256(data).hexdigest()
        return StoredArtifact(
            uri=_uri_for_key(key),
            sha256=sha,
            size_bytes=len(data),
            content_type=content_type,
        )

    return await store.put_bytes(key=key, data=data, content_type=content_type)

