from dataclasses import dataclass
from uuid import UUID, uuid4

from app.core.config import settings


class ObjectStorageNotConfigured(RuntimeError):
    pass


class ObjectStorageOperationError(RuntimeError):
    pass


@dataclass(frozen=True)
class SignedObjectUrl:
    url: str
    expires_in_seconds: int


def _client():
    if not settings.object_storage_enabled:
        raise ObjectStorageNotConfigured("Private object storage is not configured.")

    import boto3

    return boto3.client(
        "s3",
        endpoint_url=settings.object_storage_endpoint_url,
        region_name=settings.object_storage_region,
        aws_access_key_id=settings.object_storage_access_key_id,
        aws_secret_access_key=settings.object_storage_secret_access_key,
    )


def build_resume_object_key(*, user_id: UUID) -> str:
    return f"users/{user_id}/resumes/{uuid4()}.pdf"


def store_resume_pdf(
    *,
    user_id: UUID,
    pdf_bytes: bytes,
    source_fingerprint: str,
) -> str:
    key = build_resume_object_key(user_id=user_id)
    request = {
        "Bucket": settings.object_storage_bucket,
        "Key": key,
        "Body": pdf_bytes,
        "ContentType": "application/pdf",
        "Metadata": {
            "owner-id": str(user_id),
            "source-fingerprint": source_fingerprint,
        },
    }
    if settings.object_storage_sse_algorithm:
        request["ServerSideEncryption"] = settings.object_storage_sse_algorithm
    try:
        _client().put_object(**request)
    except ObjectStorageNotConfigured:
        raise
    except Exception as exc:
        raise ObjectStorageOperationError("Original resume upload could not be stored.") from exc
    return key


def create_signed_resume_url(*, object_key: str) -> SignedObjectUrl:
    try:
        url = _client().generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.object_storage_bucket, "Key": object_key},
            ExpiresIn=settings.object_storage_signed_url_seconds,
        )
    except ObjectStorageNotConfigured:
        raise
    except Exception as exc:
        raise ObjectStorageOperationError("A signed resume URL could not be created.") from exc
    return SignedObjectUrl(
        url=url,
        expires_in_seconds=settings.object_storage_signed_url_seconds,
    )


def delete_resume_pdf(*, object_key: str) -> None:
    try:
        _client().delete_object(Bucket=settings.object_storage_bucket, Key=object_key)
    except ObjectStorageNotConfigured:
        raise
    except Exception as exc:
        raise ObjectStorageOperationError("Original resume upload could not be deleted.") from exc
