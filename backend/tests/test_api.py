from fastapi.testclient import TestClient

from app.api.deps import get_db
from app.api.routes import ai as ai_routes
from app.main import app


class EmptySession:
    def scalar(self, stmt):
        return None


def override_get_db():
    yield EmptySession()


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Request-ID"]


def test_root_endpoint():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "RolePilot backend is running"}


def test_missing_application_returns_404():
    app.dependency_overrides[get_db] = override_get_db

    try:
        response = client.get("/applications/999")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json() == {"detail": "Application not found"}


def test_invalid_application_status_is_rejected_before_database_access():
    response = client.post(
        "/applications",
        json={
            "company": "Example",
            "role_title": "Engineer",
            "status": "maybe",
        },
    )

    assert response.status_code == 422


def test_required_application_field_cannot_be_cleared():
    response = client.patch("/applications/1", json={"company": None})

    assert response.status_code == 422


def test_unexpected_errors_are_logged_behind_a_safe_response(monkeypatch):
    def fail_without_leaking(_text):
        raise RuntimeError("secret upstream details")

    monkeypatch.setattr(ai_routes, "parse_job_description", fail_without_leaking)
    safe_client = TestClient(app, raise_server_exceptions=False)
    response = safe_client.post("/ai/parse-job", json={"text": "x" * 60})

    assert response.status_code == 500
    assert response.json()["detail"] == "An unexpected error occurred."
    assert response.json()["request_id"] == response.headers["X-Request-ID"]
    assert "secret upstream details" not in response.text
