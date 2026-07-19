from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api.deps import get_db
from app.api.routes import export as export_routes
from app.main import app
from app.models.application import Application
from app.models.application_full_resume_draft import ApplicationFullResumeDraft


class FakeQuery:
    def __init__(self, rows):
        self.rows = rows

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.rows[0] if self.rows else None


class FakeSession:
    def __init__(self, rows_by_model):
        self.rows_by_model = rows_by_model

    def query(self, model):
        return FakeQuery(self.rows_by_model.get(model, []))


def saved_draft_data():
    return {
        "header": {
            "name": "Jane Candidate",
            "location": "Chicago, IL",
            "phone": None,
            "email": "jane@example.com",
            "websites": [],
        },
        "professional_summary": "Saved and approved summary.",
        "education": [],
        "experience": [],
        "projects": [],
        "skills": {
            "programming_languages": ["Python"],
            "frameworks_tools": [],
            "hardware_instrumentation": [],
            "technical_areas": [],
            "developer_tools": [],
        },
    }


def test_docx_export_uses_the_same_saved_draft_every_time(monkeypatch, tmp_path):
    draft_data = saved_draft_data()
    db = FakeSession(
        {
            Application: [SimpleNamespace(id=4, selected_resume_id=9)],
            ApplicationFullResumeDraft: [
                SimpleNamespace(
                    draft_data=draft_data,
                    resume_id=9,
                    resume_version=1,
                    is_stale=False,
                )
            ],
        }
    )
    exported_drafts = []

    def fake_build_docx(*, draft, output_path):
        exported_drafts.append(draft.model_dump(mode="json"))
        with open(output_path, "wb") as output:
            output.write(b"saved draft docx")

    monkeypatch.setattr(export_routes, "EXPORT_DIR", tmp_path)
    monkeypatch.setattr(export_routes, "build_tailored_resume_docx", fake_build_docx)

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    try:
        test_client = TestClient(app)
        first = test_client.post(
            "/export/tailored-resume-docx",
            json={"application_id": 4},
        )
        second = test_client.post(
            "/export/tailored-resume-docx",
            json={"application_id": 4},
        )
    finally:
        app.dependency_overrides.clear()

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.content == second.content == b"saved draft docx"
    assert exported_drafts == [draft_data, draft_data]
    assert list(tmp_path.iterdir()) == []
