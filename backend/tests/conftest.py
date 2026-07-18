import os
from types import SimpleNamespace
from uuid import UUID

import pytest


os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://test:test@localhost/test")
os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("AUTH_ISSUER", "https://rolepilot-test.auth0.com/")
os.environ.setdefault("AUTH_AUDIENCE", "https://api.rolepilot.test")

from app.api.deps import get_current_user
from app.main import app


TEST_USER = SimpleNamespace(
    id=UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
    external_subject="auth0|unit-test-user",
    email="unit@example.com",
    name="Unit Test User",
)


@pytest.fixture(autouse=True)
def authenticated_unit_user():
    app.dependency_overrides[get_current_user] = lambda: TEST_USER
    try:
        yield TEST_USER
    finally:
        app.dependency_overrides.clear()
