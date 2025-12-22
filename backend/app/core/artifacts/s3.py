from __future__ import annotations

import hashlib
from urllib.parse import urlparse

import boto3

from backend.app.core.artifacts.interface import ArtifactStore, StoredArtifact
from backend.app.core.config import get_settings


class S3ArtifactStore(ArtifactStore):
    def __init__(self) -> None:
        s = get_settings()
        if not (s.s3_endpoint_url and s.s3_access_key_id and s.s3_secret_access_key and s.s3_bucket):
            raise RuntimeError("S3 artifact_store not configured")
        self._bucket = s.s3_bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=s.s3_endpoint_url,
            aws_access_key_id=s.s3_access_key_id,
            aws_secret_access_key=s.s3_secret_access_key,
            region_name="us-east-1",
        )

    async def put_bytes(self, *, key: str, data: bytes, content_type: str) -> StoredArtifact:
        sha = hashlib.sha256(data).hexdigest()
        self._client.put_object(Bucket=self._bucket, Key=key, Body=data, ContentType=content_type)
        return StoredArtifact(
            uri=f"s3://{self._bucket}/{key}",
            sha256=sha,
            size_bytes=len(data),
            content_type=content_type,
        )

    async def get_bytes(self, *, key: str) -> bytes:
        obj = self._client.get_object(Bucket=self._bucket, Key=key)
        return obj["Body"].read()

