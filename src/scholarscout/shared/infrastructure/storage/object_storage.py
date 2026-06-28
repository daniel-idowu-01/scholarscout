"""
Object storage abstraction (S3-compatible).

Raw HTML snapshots, extracted content, and exports are stored in
object storage rather than PostgreSQL. This keeps the DB lean and
enables cheap, scalable storage of potentially terabytes of data.

Naming convention:
    snapshots/{university_id}/{page_id}/{scraped_at_iso}.html.gz
    snapshots/{university_id}/{page_id}/{scraped_at_iso}.md.gz
    exports/{date}/{job_id}.jsonl.gz
"""

from __future__ import annotations

import gzip
import hashlib
import logging
from datetime import UTC, datetime
from io import BytesIO
from typing import Any

import aioboto3  # type: ignore[import-untyped]
from botocore.exceptions import ClientError

from scholarscout.shared.domain.exceptions import StorageError

logger = logging.getLogger(__name__)


class ObjectStorageClient:
    def __init__(
        self,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        region: str,
        use_ssl: bool,
        bucket_snapshots: str,
        bucket_assets: str,
        bucket_exports: str,
    ) -> None:
        self._endpoint_url = endpoint_url
        self._access_key = access_key
        self._secret_key = secret_key
        self._region = region
        self._use_ssl = use_ssl
        self.bucket_snapshots = bucket_snapshots
        self.bucket_assets = bucket_assets
        self.bucket_exports = bucket_exports
        self._session = aioboto3.Session()

    def _client(self) -> Any:
        return self._session.client(
            "s3",
            endpoint_url=self._endpoint_url,
            aws_access_key_id=self._access_key,
            aws_secret_access_key=self._secret_key,
            region_name=self._region,
            use_ssl=self._use_ssl,
        )

    async def store_snapshot(
        self,
        university_id: str,
        page_id: str,
        html_content: str,
        markdown_content: str | None = None,
    ) -> tuple[str, str | None]:
        """
        Compress and store raw HTML (and optional markdown) for a crawled page.
        Returns (html_uri, markdown_uri).
        """
        ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        base_key = f"snapshots/{university_id}/{page_id}/{ts}"

        html_uri = await self._put_compressed(
            bucket=self.bucket_snapshots,
            key=f"{base_key}.html.gz",
            content=html_content.encode("utf-8"),
            content_type="text/html",
        )

        md_uri = None
        if markdown_content:
            md_uri = await self._put_compressed(
                bucket=self.bucket_snapshots,
                key=f"{base_key}.md.gz",
                content=markdown_content.encode("utf-8"),
                content_type="text/markdown",
            )

        return html_uri, md_uri

    async def get_snapshot_html(self, storage_uri: str) -> str:
        """Fetch and decompress a stored HTML snapshot."""
        bucket, key = self._parse_uri(storage_uri)
        raw = await self._get_object(bucket, key)
        return gzip.decompress(raw).decode("utf-8")

    async def store_export(self, job_id: str, content: bytes) -> str:
        date_prefix = datetime.now(UTC).strftime("%Y/%m/%d")
        key = f"exports/{date_prefix}/{job_id}.jsonl.gz"
        return await self._put_compressed(
            bucket=self.bucket_exports,
            key=key,
            content=content,
            content_type="application/x-ndjson",
        )

    async def _put_compressed(
        self, bucket: str, key: str, content: bytes, content_type: str
    ) -> str:
        compressed = gzip.compress(content, compresslevel=6)
        checksum = hashlib.sha256(content).hexdigest()

        async with self._client() as s3:
            try:
                await s3.put_object(
                    Bucket=bucket,
                    Key=key,
                    Body=BytesIO(compressed),
                    ContentType=content_type,
                    ContentEncoding="gzip",
                    Metadata={"sha256": checksum},
                )
            except ClientError as e:
                raise StorageError(f"Failed to upload {key}: {e}", cause=e) from e

        return f"s3://{bucket}/{key}"

    async def _get_object(self, bucket: str, key: str) -> bytes:
        async with self._client() as s3:
            try:
                response = await s3.get_object(Bucket=bucket, Key=key)
                return await response["Body"].read()
            except ClientError as e:
                raise StorageError(f"Failed to fetch {key}: {e}", cause=e) from e

    async def object_exists(self, storage_uri: str) -> bool:
        bucket, key = self._parse_uri(storage_uri)
        async with self._client() as s3:
            try:
                await s3.head_object(Bucket=bucket, Key=key)
                return True
            except ClientError:
                return False

    async def delete_object(self, storage_uri: str) -> None:
        bucket, key = self._parse_uri(storage_uri)
        async with self._client() as s3:
            try:
                await s3.delete_object(Bucket=bucket, Key=key)
            except ClientError as e:
                raise StorageError(f"Failed to delete {key}: {e}", cause=e) from e

    def _parse_uri(self, uri: str) -> tuple[str, str]:
        """Parse s3://bucket/key into (bucket, key)."""
        if not uri.startswith("s3://"):
            raise ValueError(f"Invalid storage URI: {uri}")
        parts = uri[5:].split("/", 1)
        return parts[0], parts[1]
