"""Private object storage for immutable source-file (register photo) retention.

S3-compatible (MinIO in dev). Access is via short-lived signed URLs only
(cureva-docs/04, 07). These functions are the single seam the API uses, so
tests can monkeypatch them without touching real storage.
"""
import io
import uuid

import boto3
from botocore.client import Config
from django.conf import settings


def _client():
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        region_name=settings.S3_REGION,
        config=Config(signature_version="s3v4"),
    )


def ensure_bucket():
    client = _client()
    existing = {b["Name"] for b in client.list_buckets().get("Buckets", [])}
    if settings.S3_BUCKET not in existing:
        client.create_bucket(Bucket=settings.S3_BUCKET)


def store_page(intake_id, page_number, data: bytes, content_type="image/jpeg") -> str:
    """Store one register page and return its object key."""
    ensure_bucket()
    key = f"intakes/{intake_id}/page-{page_number}-{uuid.uuid4().hex}.jpg"
    _client().put_object(Bucket=settings.S3_BUCKET, Key=key, Body=io.BytesIO(data), ContentType=content_type)
    return key


def fetch_page(object_key: str) -> bytes:
    resp = _client().get_object(Bucket=settings.S3_BUCKET, Key=object_key)
    return resp["Body"].read()


def delete_page(object_key: str) -> None:
    """Best-effort removal of one stored page (used when an intake is deleted)."""
    try:
        _client().delete_object(Bucket=settings.S3_BUCKET, Key=object_key)
    except Exception:
        # The DB record is the source of truth; an orphaned blob is harmless.
        pass


def signed_url(object_key: str, expires: int = 300) -> str:
    return _client().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.S3_BUCKET, "Key": object_key},
        ExpiresIn=expires,
    )
