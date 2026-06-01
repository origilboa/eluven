"""S3 storage for document files."""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false

from __future__ import annotations

from typing import Any

import boto3  # pyright: ignore[reportMissingTypeStubs]
from botocore.exceptions import ClientError  # pyright: ignore[reportMissingTypeStubs]

from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)


class StorageService:
    """Upload, download, and manage documents in S3."""

    def __init__(self, s3_client: Any | None = None) -> None:
        self._bucket = settings.s3_documents_bucket
        self._client = s3_client or boto3.client("s3", region_name=settings.aws_region)

    def upload_file(self, file_bytes: bytes, s3_key: str, content_type: str) -> None:
        """Upload file bytes to the documents bucket."""
        logger.info(
            "s3_upload_started",
            s3_key=s3_key,
            content_type=content_type,
            size_bytes=len(file_bytes),
        )
        try:
            self._client.put_object(
                Bucket=self._bucket,
                Key=s3_key,
                Body=file_bytes,
                ContentType=content_type,
            )
        except ClientError as exc:
            logger.exception("s3_upload_failed", s3_key=s3_key)
            raise RuntimeError(f"Failed to upload {s3_key}") from exc

        logger.info("s3_upload_complete", s3_key=s3_key, size_bytes=len(file_bytes))

    def download_file(self, s3_key: str) -> bytes:
        """Download file bytes from the documents bucket."""
        logger.info("s3_download_started", s3_key=s3_key)
        try:
            response = self._client.get_object(Bucket=self._bucket, Key=s3_key)
            body = bytes(response["Body"].read())
        except ClientError as exc:
            logger.exception("s3_download_failed", s3_key=s3_key)
            raise RuntimeError(f"Failed to download {s3_key}") from exc

        logger.info("s3_download_complete", s3_key=s3_key, size_bytes=len(body))
        return body

    def delete_file(self, s3_key: str) -> None:
        """Remove a file from S3 (database record is unchanged)."""
        logger.info("s3_delete_started", s3_key=s3_key)
        try:
            self._client.delete_object(Bucket=self._bucket, Key=s3_key)
        except ClientError as exc:
            logger.exception("s3_delete_failed", s3_key=s3_key)
            raise RuntimeError(f"Failed to delete {s3_key}") from exc

        logger.info("s3_delete_complete", s3_key=s3_key)

    def generate_presigned_url(
        self,
        s3_key: str,
        expiry_seconds: int | None = None,
    ) -> str:
        """Generate a presigned GET URL for direct download."""
        expires_in = expiry_seconds or settings.s3_presigned_url_expiry_seconds
        logger.info("s3_presigned_url_started", s3_key=s3_key, expiry_seconds=expires_in)
        try:
            url: str = self._client.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": self._bucket, "Key": s3_key},
                ExpiresIn=expires_in,
            )
        except ClientError as exc:
            logger.exception("s3_presigned_url_failed", s3_key=s3_key)
            raise RuntimeError(f"Failed to generate presigned URL for {s3_key}") from exc

        logger.info("s3_presigned_url_complete", s3_key=s3_key)
        return url
