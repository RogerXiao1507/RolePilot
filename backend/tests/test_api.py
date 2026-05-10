import os

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://test:test@localhost/test")
os.environ.setdefault("OPENAI_API_KEY", "test")

from app.core.database import Base

Base.metadata.create_all = lambda *args, **kwargs: None

from fastapi.testclient import TestClient

from app.api.deps import get_db
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
