"""The `s3` backend (TASK-0193, REQ-0080, DEC-0074): S3-compatible object storage (AWS S3, Cloudflare R2, Backblaze B2,
MinIO) through `boto3`, an optional extra (`pip install "superstep-backend[s3]"`) that the published images include.

Downloads stream through the backend (DEC-0074 decision 3): the bucket is never shown to the browser and no presigned
URL is made. Error reasons name the failure (an S3 error code or the exception type), never the endpoint, bucket,
key or credentials."""
from __future__ import annotations
from typing import Iterator, Optional
from .base import CHUNK, AttachmentStore, StoreError


class S3Store(AttachmentStore):
    name = "s3"

    def __init__(self, bucket: str, prefix: str = "", endpoint: str = "", region: str = "", access_key: str = "",
                 secret_key: str = "", path_style: bool = False, client=None):
        if not bucket: raise StoreError("STUDIO_ATTACHMENT_S3_BUCKET is not set")
        self.bucket, self.prefix = bucket, (prefix.strip("/") + "/") if prefix.strip("/") else ""
        self.client = client or self._client(endpoint, region, access_key, secret_key, path_style)

    @staticmethod
    def _client(endpoint, region, access_key, secret_key, path_style):
        try:
            import boto3
            from botocore.config import Config
        except ImportError: raise StoreError("the s3 backend needs boto3: install superstep-backend[s3]")
        cfg = Config(signature_version="s3v4", retries={"max_attempts": 3, "mode": "standard"}, connect_timeout=5, read_timeout=30,
                     s3={"addressing_style": "path" if path_style else "auto"})
        kw = {"endpoint_url": endpoint or None, "region_name": region or None, "config": cfg}
        if access_key and secret_key: kw.update(aws_access_key_id=access_key, aws_secret_access_key=secret_key)  # else the default chain
        return boto3.client("s3", **kw)

    def _key(self, key: str) -> str:
        if not key or key.startswith("/") or ".." in key.split("/"): raise StoreError("invalid key")
        return self.prefix + key

    @staticmethod
    def _error(e: Exception, missing_codes=("NoSuchKey", "404", "NotFound")) -> StoreError:
        code = getattr(e, "response", {}).get("Error", {}).get("Code") if hasattr(e, "response") else None
        if code in missing_codes: return StoreError("not found", missing=True)
        return StoreError(f"S3 error {code}" if code else f"S3 unreachable ({type(e).__name__})")

    def put(self, key: str, data: bytes, mime: str) -> None:
        try: self.client.put_object(Bucket=self.bucket, Key=self._key(key), Body=data, ContentType=mime or "application/octet-stream")
        except StoreError: raise
        except Exception as e: raise self._error(e)

    def open(self, key: str) -> Iterator[bytes]:
        try: body = self.client.get_object(Bucket=self.bucket, Key=self._key(key))["Body"]
        except StoreError: raise
        except Exception as e: raise self._error(e)
        def chunks():
            try:
                for piece in body.iter_chunks(CHUNK):
                    if piece: yield piece
            except Exception as e: raise self._error(e)
            finally: body.close()
        return chunks()

    def read(self, key: str) -> bytes:
        return b"".join(self.open(key))

    def delete(self, key: str) -> None:
        try: self.client.delete_object(Bucket=self.bucket, Key=self._key(key))
        except StoreError: raise
        except Exception as e:
            err = self._error(e)
            if not err.missing: raise err

    def exists(self, key: str) -> bool:
        try: self.client.head_object(Bucket=self.bucket, Key=self._key(key)); return True
        except StoreError: raise
        except Exception as e:
            err = self._error(e, ("NoSuchKey", "404", "NotFound"))
            if err.missing: return False
            raise err

    def iter_keys(self) -> Iterator[tuple[str, float]]:
        def walk():
            token: Optional[str] = None
            while True:
                kw = {"Bucket": self.bucket, "Prefix": self.prefix}
                if token: kw["ContinuationToken"] = token
                try: page = self.client.list_objects_v2(**kw)
                except Exception as e: raise self._error(e)
                for o in page.get("Contents") or []:
                    yield o["Key"][len(self.prefix):], o["LastModified"].timestamp()
                if not page.get("IsTruncated"): return
                token = page.get("NextContinuationToken")
        return walk()
