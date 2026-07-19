from types import SimpleNamespace
from uuid import UUID

from app.services import object_storage_service


USER_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")


class FakeS3Client:
    def __init__(self):
        self.put_request = None
        self.presign_request = None
        self.delete_request = None

    def put_object(self, **kwargs):
        self.put_request = kwargs

    def generate_presigned_url(self, operation, **kwargs):
        self.presign_request = (operation, kwargs)
        return "https://storage.example/signed-resume"

    def delete_object(self, **kwargs):
        self.delete_request = kwargs


def test_private_resume_storage_uses_encryption_and_short_lived_signed_urls(monkeypatch):
    fake_client = FakeS3Client()
    monkeypatch.setattr(object_storage_service, "_client", lambda: fake_client)
    monkeypatch.setattr(object_storage_service.settings, "object_storage_bucket", "private-resumes")
    monkeypatch.setattr(object_storage_service.settings, "object_storage_sse_algorithm", "AES256")
    monkeypatch.setattr(object_storage_service.settings, "object_storage_signed_url_seconds", 300)

    object_key = object_storage_service.store_resume_pdf(
        user_id=USER_ID,
        pdf_bytes=b"%PDF-private",
        source_fingerprint="f" * 64,
    )

    assert object_key.startswith(f"users/{USER_ID}/resumes/")
    assert object_key.endswith(".pdf")
    assert fake_client.put_request == {
        "Bucket": "private-resumes",
        "Key": object_key,
        "Body": b"%PDF-private",
        "ContentType": "application/pdf",
        "Metadata": {
            "owner-id": str(USER_ID),
            "source-fingerprint": "f" * 64,
        },
        "ServerSideEncryption": "AES256",
    }

    signed = object_storage_service.create_signed_resume_url(object_key=object_key)
    assert signed.url == "https://storage.example/signed-resume"
    assert signed.expires_in_seconds == 300
    assert fake_client.presign_request == (
        "get_object",
        {
            "Params": {"Bucket": "private-resumes", "Key": object_key},
            "ExpiresIn": 300,
        },
    )

    object_storage_service.delete_resume_pdf(object_key=object_key)
    assert fake_client.delete_request == {
        "Bucket": "private-resumes",
        "Key": object_key,
    }


def test_storage_client_requires_complete_private_storage_configuration(monkeypatch):
    monkeypatch.setattr(
        object_storage_service,
        "settings",
        SimpleNamespace(object_storage_enabled=False),
    )

    try:
        object_storage_service._client()
    except object_storage_service.ObjectStorageNotConfigured as exc:
        assert "not configured" in str(exc).lower()
    else:
        raise AssertionError("An incomplete storage configuration must not create a client")
