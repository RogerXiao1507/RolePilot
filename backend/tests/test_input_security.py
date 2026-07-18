from io import BytesIO
import socket

import httpx
from fastapi.testclient import TestClient
from pypdf import PdfWriter
import pytest

from app.core.config import settings
from app.main import app
from app.services.ai_service import (
    JobUrlFetchError,
    JobUrlValidationError,
    _read_limited_response,
    extract_text_from_url,
    validate_public_job_url,
)
from app.services import ai_service
from app.services.resume_service import extract_text_from_pdf_bytes
from app.services import resume_service


client = TestClient(app)


class FakeStreamResponse:
    def __init__(self, status_code, headers=None, content=b""):
        self.status_code = status_code
        self.headers = headers or {}
        self.encoding = "utf-8"
        self._content = content

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def raise_for_status(self):
        return None

    def iter_bytes(self):
        yield self._content


class FakeHttpClient:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.request_count = 0

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def stream(self, *_args, **_kwargs):
        self.request_count += 1
        return next(self.responses)


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "http://127.0.0.1/job",
        "http://[::1]/job",
        "http://169.254.169.254/latest/meta-data",
        "http://user:password@example.com/job",
        "https://example.com:8443/job",
    ],
)
def test_unsafe_job_urls_are_rejected(url):
    with pytest.raises(JobUrlValidationError):
        validate_public_job_url(url)


def test_dns_resolution_rejects_any_private_address(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.5", 443)),
        ],
    )

    with pytest.raises(JobUrlValidationError):
        validate_public_job_url("https://example.com/jobs/1")


def test_public_job_url_is_accepted_after_resolution(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443)),
        ],
    )


def test_redirect_target_is_revalidated_before_second_request(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443)),
        ],
    )
    fake_client = FakeHttpClient(
        [FakeStreamResponse(302, headers={"location": "http://127.0.0.1/private"})]
    )
    monkeypatch.setattr(ai_service.httpx, "Client", lambda **kwargs: fake_client)

    with pytest.raises(JobUrlValidationError):
        extract_text_from_url("https://example.com/job")

    assert fake_client.request_count == 1


def test_non_text_job_response_is_rejected(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443)),
        ],
    )
    fake_client = FakeHttpClient(
        [
            FakeStreamResponse(
                200,
                headers={"content-type": "application/octet-stream"},
                content=b"binary",
            )
        ]
    )
    monkeypatch.setattr(ai_service.httpx, "Client", lambda **kwargs: fake_client)

    with pytest.raises(JobUrlFetchError, match="supported text page"):
        extract_text_from_url("https://example.com/job")

    assert validate_public_job_url("https://example.com/jobs/1") == (
        "https://example.com/jobs/1"
    )


def test_remote_response_size_is_capped(monkeypatch):
    monkeypatch.setattr(settings, "job_url_max_response_bytes", 4)
    response = httpx.Response(200, content=b"12345")

    with pytest.raises(JobUrlFetchError):
        _read_limited_response(response)


def test_resume_upload_size_is_capped_before_pdf_processing(monkeypatch):
    monkeypatch.setattr(settings, "max_resume_upload_bytes", 8)

    response = client.post(
        "/resume/analyze",
        files={"file": ("resume.pdf", b"%PDF-12345", "application/pdf")},
    )

    assert response.status_code == 413


def test_resume_upload_requires_pdf_magic_bytes():
    response = client.post(
        "/resume/analyze",
        files={"file": ("resume.pdf", b"not really a pdf", "application/pdf")},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "The uploaded file is not a valid PDF."


def test_resume_upload_requires_pdf_media_type():
    response = client.post(
        "/resume/analyze",
        files={"file": ("resume.pdf", b"%PDF-placeholder", "text/plain")},
    )

    assert response.status_code == 400


def test_resume_upload_requires_pdf_filename():
    response = client.post(
        "/resume/analyze",
        files={"file": ("resume.txt", b"%PDF-placeholder", "application/pdf")},
    )

    assert response.status_code == 400


def test_resume_page_count_is_capped():
    output = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.add_blank_page(width=72, height=72)
    writer.write(output)

    with pytest.raises(ValueError, match="cannot exceed 1 pages"):
        extract_text_from_pdf_bytes(output.getvalue(), max_pages=1)


def test_extracted_resume_text_is_capped(monkeypatch):
    class FakePage:
        def extract_text(self):
            return "x" * 6

    fake_pdf = type(
        "SimplePdf",
        (),
        {"is_encrypted": False, "pages": [FakePage()]},
    )()
    monkeypatch.setattr(resume_service, "PdfReader", lambda _stream: fake_pdf)

    with pytest.raises(ValueError, match="cannot exceed 5 characters"):
        extract_text_from_pdf_bytes(b"%PDF-fake", max_text_chars=5)
