from __future__ import annotations

import hashlib

from backend.app.core.artifacts.interface import ArtifactStore, StoredArtifact


class MemoryArtifactStore(ArtifactStore):
    def __init__(self) -> None:
        self._data: dict[str, tuple[bytes, str]] = {}

    async def put_bytes(self, *, key: str, data: bytes, content_type: str) -> StoredArtifact:
        sha = hashlib.sha256(data).hexdigest()
        self._data[key] = (data, content_type)
        return StoredArtifact(uri=f"memory://{key}", sha256=sha, size_bytes=len(data), content_type=content_type)

    async def get_bytes(self, *, key: str) -> bytes:
        if key not in self._data:
            raise KeyError(key)
        return self._data[key][0]

