from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from app.core.config import Settings
from app.core.errors import ExternalFailure, NotConfigured, failure_kind

__all__ = ["SERVER_SIDE_ENCRYPTION", "ObjectStore", "PresignedGet", "object_store"]

SERVER_SIDE_ENCRYPTION = "AES256"
SERVICE = "s3"
MISSING_CODES = frozenset({"NoSuchKey", "404"})


@dataclass(frozen=True)
class PresignedGet:
    url: str
    expires_at: datetime


class ObjectStore:
    def __init__(self, *, bucket: str, region: str, client: Any) -> None:
        if not bucket:
            raise NotConfigured("S3_BUCKET", "The media bucket is not configured")
        self.bucket = bucket
        self.region = region
        self._client = client

    @property
    def host(self) -> str:
        return f"https://{self.bucket}.s3.{self.region}.amazonaws.com"

    async def put(self, key: str, body: bytes, *, content_type: str) -> None:
        await asyncio.to_thread(self._put, key, body, content_type)

    async def get(self, key: str) -> bytes | None:
        return await asyncio.to_thread(self._get, key)

    def presigned_get(self, key: str, *, disposition: str, seconds: int, now: datetime) -> PresignedGet:
        url = self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key, "ResponseContentDisposition": disposition},
            ExpiresIn=seconds,
        )
        if not url.startswith(f"{self.host}/"):
            raise NotConfigured("S3_BUCKET", "Presigned media links must use the bucket's regional host")
        return PresignedGet(url=url, expires_at=now + timedelta(seconds=seconds))

    def _get(self, key: str) -> bytes | None:
        try:
            answer = self._client.get_object(Bucket=self.bucket, Key=key)
            return bytes(answer["Body"].read())
        except Exception as error:
            if _error_code(error) in MISSING_CODES:
                return None
            raise _failure(error, "read") from error

    def _put(self, key: str, body: bytes, content_type: str) -> None:
        try:
            self._client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=body,
                ContentType=content_type,
                ServerSideEncryption=SERVER_SIDE_ENCRYPTION,
            )
        except Exception as error:
            raise _failure(error, "store") from error


def object_store(settings: Settings, *, client: Any = None) -> ObjectStore:
    if not settings.s3_bucket:
        raise NotConfigured("S3_BUCKET", "The media bucket is not configured")
    return ObjectStore(
        bucket=settings.s3_bucket,
        region=settings.aws_region,
        client=client or _s3_client(settings.aws_region),
    )


def _s3_client(region: str) -> Any:
    import boto3
    from botocore.config import Config

    config = Config(signature_version="s3v4", s3={"addressing_style": "virtual"})
    return boto3.client(SERVICE, region_name=region, config=config)


def _error_code(error: Exception) -> str:
    response = getattr(error, "response", None) or {}
    return str((response.get("Error") or {}).get("Code") or type(error).__name__)


def _failure(error: Exception, action: str) -> ExternalFailure:
    response = getattr(error, "response", None) or {}
    status = (response.get("ResponseMetadata") or {}).get("HTTPStatusCode")
    code = _error_code(error)
    kind = failure_kind(status) if isinstance(status, int) else "unavailable"
    return ExternalFailure(
        f"Could not {action} the media object ({code})",
        kind=kind,
        retryable=kind in {"rate_limit", "unavailable"},
        status=status if isinstance(status, int) else None,
        service=SERVICE,
    )
