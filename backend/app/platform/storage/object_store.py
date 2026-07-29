"""对象存储抽象。

原始文档、页图、缩略图都放对象存储，数据库只存 key。开发用 MinIO，生产用
S3 / OSS——两者 API 兼容，所以只有一个实现，靠 endpoint 区分。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Protocol

import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.platform.config import Settings, get_settings
from app.platform.errors import AppError


class StorageError(AppError):
    code = "storage_error"
    message = "对象存储操作失败"


@dataclass(frozen=True, slots=True)
class PresignedUpload:
    url: str
    key: str
    expires_in: int


class ObjectStore(Protocol):
    def presign_upload(self, key: str, content_type: str) -> PresignedUpload: ...

    def presign_download(self, key: str) -> str: ...

    def put(self, key: str, data: bytes, content_type: str) -> None: ...

    def get(self, key: str) -> bytes: ...


class S3ObjectStore:
    def __init__(self, settings: Settings | None = None) -> None:
        settings = settings or get_settings()
        self._bucket = settings.s3_bucket
        self._ttl = settings.s3_presign_ttl_seconds
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            region_name=settings.s3_region,
            aws_access_key_id=settings.s3_access_key.get_secret_value(),
            aws_secret_access_key=settings.s3_secret_key.get_secret_value(),
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )

    def ensure_bucket(self) -> None:
        """本地开发用：桶不存在就建。生产由基础设施预置，不走这里。"""
        try:
            self._client.head_bucket(Bucket=self._bucket)
        except ClientError:
            self._client.create_bucket(Bucket=self._bucket)

    def presign_upload(self, key: str, content_type: str) -> PresignedUpload:
        try:
            url = self._client.generate_presigned_url(
                "put_object",
                Params={"Bucket": self._bucket, "Key": key, "ContentType": content_type},
                ExpiresIn=self._ttl,
            )
        except (BotoCoreError, ClientError) as exc:
            raise StorageError() from exc
        return PresignedUpload(url=url, key=key, expires_in=self._ttl)

    def presign_download(self, key: str) -> str:
        try:
            return self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": key},
                ExpiresIn=self._ttl,
            )
        except (BotoCoreError, ClientError) as exc:
            raise StorageError() from exc

    def put(self, key: str, data: bytes, content_type: str) -> None:
        try:
            self._client.put_object(
                Bucket=self._bucket, Key=key, Body=data, ContentType=content_type
            )
        except (BotoCoreError, ClientError) as exc:
            raise StorageError() from exc

    def get(self, key: str) -> bytes:
        try:
            resp = self._client.get_object(Bucket=self._bucket, Key=key)
            return resp["Body"].read()
        except (BotoCoreError, ClientError) as exc:
            raise StorageError() from exc


def document_key(tenant_id: uuid.UUID, document_id: uuid.UUID, filename: str) -> str:
    """租户前缀在最外层，便于按租户做生命周期规则与用量统计。"""
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    return f"tenants/{tenant_id}/documents/{document_id}/original.{suffix}"


def page_image_key(tenant_id: uuid.UUID, document_id: uuid.UUID, page_no: int) -> str:
    return f"tenants/{tenant_id}/documents/{document_id}/pages/{page_no:04d}.webp"
