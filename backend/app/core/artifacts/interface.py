from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StoredArtifact:
    uri: str
    sha256: str
    size_bytes: int
    content_type: str


class ArtifactStore:
    async def put_bytes(self, *, key: str, data: bytes, content_type: str) -> StoredArtifact:
        raise NotImplementedError

    async def get_bytes(self, *, key: str) -> bytes:
        raise NotImplementedError
