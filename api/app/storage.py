"""Object storage. Local disk by default; S3-compatible when configured."""
from __future__ import annotations

import shutil
from pathlib import Path

from app.config import get_settings


class Storage:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.root = Path(self.settings.storage_dir)
        self.root.mkdir(parents=True, exist_ok=True)
        self._client = None
        if self.settings.uses_s3:
            import boto3

            self._client = boto3.client(
                "s3",
                endpoint_url=self.settings.s3_endpoint,
                aws_access_key_id=self.settings.s3_access_key,
                aws_secret_access_key=self.settings.s3_secret_key,
                region_name=self.settings.s3_region,
            )
            self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        assert self._client is not None
        name = self.settings.s3_bucket
        existing = [b["Name"] for b in self._client.list_buckets().get("Buckets", [])]
        if name not in existing:
            self._client.create_bucket(Bucket=name)

    def put(self, key: str, data: bytes, content_type: str) -> str:
        key = key.lstrip("/")
        if self._client is not None:
            self._client.put_object(
                Bucket=self.settings.s3_bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
            )
            return key
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    def exists(self, key: str) -> bool:
        key = key.lstrip("/")
        if self._client is not None:
            try:
                self._client.head_object(Bucket=self.settings.s3_bucket, Key=key)
            except Exception as exc:
                response = getattr(exc, "response", None)
                code = ""
                status = None
                if isinstance(response, dict):
                    code = str(response.get("Error", {}).get("Code", ""))
                    status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")
                if status == 404 or code in {"404", "NoSuchKey", "NotFound"}:
                    return False
                message = str(exc)
                if "404" in message or "Not Found" in message or "NoSuchKey" in message:
                    return False
                raise
            return True
        return (self.root / key).is_file()

    def put_file(self, key: str, path: Path, content_type: str) -> str:
        key = key.lstrip("/")
        if self._client is not None:
            self._client.upload_file(
                str(path),
                self.settings.s3_bucket,
                key,
                ExtraArgs={"ContentType": content_type},
            )
            return key
        dest = self.root / key
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, dest)
        return key

    def get(self, key: str) -> bytes:
        key = key.lstrip("/")
        if self._client is not None:
            obj = self._client.get_object(Bucket=self.settings.s3_bucket, Key=key)
            return obj["Body"].read()
        return (self.root / key).read_bytes()

    def list_prefix(self, prefix: str) -> list[tuple[str, int]]:
        prefix = prefix.lstrip("/")
        if self._client is not None:
            paginator = self._client.get_paginator("list_objects_v2")
            out: list[tuple[str, int]] = []
            for page in paginator.paginate(Bucket=self.settings.s3_bucket, Prefix=prefix):
                for item in page.get("Contents", []):
                    out.append((item["Key"], int(item["Size"])))
            return out
        base = self.root / prefix
        if not base.exists():
            return []
        return [(str(p.relative_to(self.root)).replace("\\", "/"), p.stat().st_size)
                for p in base.rglob("*") if p.is_file()]

    def delete(self, key: str) -> None:
        key = key.lstrip("/")
        if self._client is not None:
            self._client.delete_object(Bucket=self.settings.s3_bucket, Key=key)
            return
        path = self.root / key
        if path.is_file():
            path.unlink()

    def delete_prefix(self, prefix: str) -> int:
        freed = 0
        for key, size in self.list_prefix(prefix):
            freed += size
            if self._client is not None:
                self._client.delete_object(Bucket=self.settings.s3_bucket, Key=key)
            else:
                path = self.root / key
                if path.exists():
                    path.unlink()
        return freed


_storage: Storage | None = None


def get_storage() -> Storage:
    global _storage
    if _storage is None:
        _storage = Storage()
    return _storage


def reset_storage() -> None:
    global _storage
    _storage = None
