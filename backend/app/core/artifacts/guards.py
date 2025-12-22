"""
FX Artifact Immutability Guards

Prevents:
- FX artifact mutation
- Overwrite of artifact payload
- Checksum mismatches
"""
from __future__ import annotations

from backend.app.core.artifacts.checksums import sha256_hex, verify_sha256
from backend.app.core.artifacts.interface import ArtifactStore


class FXArtifactImmutableError(RuntimeError):
    """Raised when attempting to mutate an immutable FX artifact."""
    pass


class FXArtifactChecksumMismatchError(ValueError):
    """Raised when FX artifact checksum does not match expected value."""
    pass


class FXArtifactOverwriteError(RuntimeError):
    """Raised when attempting to overwrite an existing artifact."""
    pass


async def store_fx_artifact_immutable(
    store: ArtifactStore,
    *,
    key: str,
    data: bytes,
    content_type: str,
    expected_sha256: str | None = None,
) -> str:
    """
    Store FX artifact with immutability guarantees.
    
    Args:
        store: Artifact store instance
        key: Artifact key (must be unique)
        data: Artifact payload bytes
        content_type: Content type
        expected_sha256: If provided, verify checksum matches
    
    Returns:
        sha256 hex digest of stored artifact
    
    Raises:
        FXArtifactOverwriteError: If artifact already exists at key
        FXArtifactChecksumMismatchError: If expected_sha256 provided and doesn't match
    """
    # Compute checksum
    computed_sha256 = sha256_hex(data)
    
    # Verify checksum if expected provided
    if expected_sha256 is not None:
        if computed_sha256 != expected_sha256:
            raise FXArtifactChecksumMismatchError(
                f"FX_ARTIFACT_CHECKSUM_MISMATCH: Expected {expected_sha256}, got {computed_sha256}"
            )
    
    # Check if artifact already exists (prevent overwrite)
    try:
        existing_data = await store.get_bytes(key=key)
        existing_sha256 = sha256_hex(existing_data)
        if existing_sha256 != computed_sha256:
            raise FXArtifactOverwriteError(
                f"FX_ARTIFACT_OVERWRITE_FORBIDDEN: Artifact at {key} already exists with sha256 {existing_sha256}. "
                "FX artifacts are immutable. Create new artifact with new key."
            )
        # If same checksum, return existing (idempotent)
        return existing_sha256
    except KeyError:
        # Artifact doesn't exist, safe to create
        pass
    
    # Store artifact
    stored = await store.put_bytes(key=key, data=data, content_type=content_type)
    
    # Verify stored checksum matches computed
    if stored.sha256 != computed_sha256:
        raise FXArtifactChecksumMismatchError(
            f"FX_ARTIFACT_STORAGE_CHECKSUM_MISMATCH: Computed {computed_sha256}, stored {stored.sha256}"
        )
    
    return stored.sha256


async def get_fx_artifact_with_verification(
    store: ArtifactStore,
    *,
    key: str,
    expected_sha256: str,
) -> bytes:
    """
    Retrieve FX artifact and verify checksum.
    
    Args:
        store: Artifact store instance
        key: Artifact key
        expected_sha256: Expected sha256 checksum
    
    Returns:
        Artifact payload bytes
    
    Raises:
        KeyError: If artifact not found
        FXArtifactChecksumMismatchError: If checksum doesn't match
    """
    data = await store.get_bytes(key=key)
    verify_sha256(data, expected_sha256)
    return data


