from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api.deps import get_db
from app.api.routes import ai as ai_routes
from app.main import app
from app.models.application import Application
from app.models.application_tailored_resume import ApplicationTailoredResume
from app.models.project_evidence import ProjectEvidence
from app.models.resume import Resume


class FakeQuery:
    def __init__(self, rows):
        self.rows = rows

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.rows[0] if self.rows else None

    def all(self):
        return self.rows


class FakeSession:
    def __init__(self, rows_by_model):
        self.rows_by_model = rows_by_model

    def query(self, model):
        return FakeQuery(self.rows_by_model.get(model, []))

    def scalar(self, statement):
        model = statement.column_descriptions[0]["entity"]
        rows = self.rows_by_model.get(model, [])
        return rows[0] if rows else None


def test_match_loads_authoritative_resume_and_job_from_database(monkeypatch):
    application = SimpleNamespace(
        id=7,
        selected_resume_id=9,
        role_title="Backend Engineer",
        company="Example",
        ai_summary="Build APIs",
        required_skills=["Python"],
        preferred_skills=["FastAPI"],
        keywords=["PostgreSQL"],
    )
    resume = SimpleNamespace(id=9, extracted_text="Trusted server-side resume text")
    db = FakeSession({Application: [application], Resume: [resume]})
    captured = {}

    def fake_match_resume_to_job(**kwargs):
        captured.update(kwargs)
        return {
            "overall_match_summary": "A grounded match.",
            "matched_skills": ["Python"],
            "missing_skills": [],
            "strengths_for_role": ["API work"],
            "improvement_areas": [],
            "suggested_resume_changes": [],
        }

    monkeypatch.setattr(ai_routes, "match_resume_to_job", fake_match_resume_to_job)

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    try:
        response = TestClient(app).post(
            "/ai/match-resume-job",
            json={"application_id": 7, "resume_id": 9},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert captured["resume_text"] == "Trusted server-side resume text"
    assert captured["role_title"] == "Backend Engineer"


def test_match_rejects_browser_supplied_resume_text():
    response = TestClient(app).post(
        "/ai/match-resume-job",
        json={
            "application_id": 7,
            "resume_id": 9,
            "resume_text": "Browser-controlled text",
        },
    )

    assert response.status_code == 422


def test_tailor_loads_the_requested_resume_id(monkeypatch):
    application = SimpleNamespace(id=7, selected_resume_id=9)
    resume = SimpleNamespace(id=9)
    db = FakeSession({Application: [application], Resume: [resume]})
    captured = {}

    def fake_tailor(**kwargs):
        captured.update(kwargs)
        return {
            "tailored_summary": "Grounded summary",
            "tailored_skills": [],
            "tailored_bullets": [],
            "tailoring_notes": [],
        }

    monkeypatch.setattr(ai_routes, "tailor_resume_for_application", fake_tailor)

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    try:
        response = TestClient(app).post(
            "/ai/tailor-resume",
            json={"application_id": 7, "resume_id": 9},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert captured["application"] is application
    assert captured["resume"] is resume


def test_full_draft_uses_requested_resume_and_saved_tailoring(monkeypatch):
    application = SimpleNamespace(id=7, selected_resume_id=9)
    resume = SimpleNamespace(id=9, version=1)
    tailored = SimpleNamespace(
        application_id=7,
        resume_id=9,
        resume_version=1,
        is_stale=False,
    )
    evidence = SimpleNamespace(id=3)
    db = FakeSession(
        {
            Application: [application],
            Resume: [resume],
            ApplicationTailoredResume: [tailored],
            ProjectEvidence: [evidence],
        }
    )
    captured = {}
    draft = {
        "header": {
            "name": "Jane Candidate",
            "location": None,
            "phone": None,
            "email": None,
            "websites": [],
        },
        "professional_summary": "Grounded summary",
        "education": [],
        "experience": [],
        "projects": [],
        "skills": {
            "programming_languages": [],
            "frameworks_tools": [],
            "hardware_instrumentation": [],
            "technical_areas": [],
            "developer_tools": [],
        },
    }

    def fake_build(**kwargs):
        captured.update(kwargs)
        return draft

    monkeypatch.setattr(ai_routes, "build_full_tailored_resume_draft", fake_build)

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    try:
        response = TestClient(app).post(
            "/ai/full-tailored-resume",
            json={"application_id": 7, "resume_id": 9},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert captured["resume"] is resume
    assert captured["tailored_resume"] is tailored
    assert captured["project_evidence"] == [evidence]
