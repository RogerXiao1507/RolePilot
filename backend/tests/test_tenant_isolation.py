from datetime import datetime, timedelta, timezone

from fastapi import Request
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import OperationalError

from app.api.deps import get_current_user
from app.core.auth import AccessTokenClaims, get_token_claims
from app.core.database import SessionLocal
from app.main import app
from app.models.application import Application
from app.models.application_full_resume_draft import ApplicationFullResumeDraft
from app.models.application_resume_match import ApplicationResumeMatch
from app.models.application_tailored_resume import ApplicationTailoredResume
from app.models.project_evidence import ProjectEvidence
from app.models.project_evidence_chunk import ProjectEvidenceChunk
from app.models.resume import Resume
from app.models.user import User
from app.services import retrieval_service


USER_A = "auth0|tenant-a"
USER_B = "auth0|tenant-b"


def _claims_for_request(request: Request) -> AccessTokenClaims:
    subject = request.headers.get("x-test-subject")
    if subject not in {USER_A, USER_B}:
        raise AssertionError("Integration request is missing a recognized test subject")
    now = datetime.now(timezone.utc)
    return AccessTokenClaims(
        sub=subject,
        iss="https://rolepilot-test.auth0.com/",
        aud="https://api.rolepilot.test",
        iat=int(now.timestamp()),
        exp=int((now + timedelta(minutes=5)).timestamp()),
    )


def _headers(subject: str) -> dict[str, str]:
    return {"X-Test-Subject": subject}


def _resume_payload(file_name: str) -> dict:
    return {
        "file_name": file_name,
        "extracted_text": f"Trusted resume text for {file_name}",
        "summary": "Software engineer",
        "strengths": ["Python"],
        "weaknesses": [],
        "wording_issues": [],
        "missing_metrics": [],
        "suggested_improvements": [],
    }


def _match_payload(application_id: int, resume_id: int) -> dict:
    return {
        "application_id": application_id,
        "resume_id": resume_id,
        "overall_match_summary": "Grounded match",
        "matched_skills": ["Python"],
        "missing_skills": [],
        "strengths_for_role": [],
        "improvement_areas": [],
        "suggested_resume_changes": [],
    }


def _full_draft_payload(application_id: int, resume_id: int) -> dict:
    return {
        "application_id": application_id,
        "resume_id": resume_id,
        "draft_data": {
            "header": {
                "name": "Candidate",
                "location": None,
                "phone": None,
                "email": None,
                "websites": [],
            },
            "professional_summary": "Saved draft",
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
        },
    }


@pytest.fixture
def tenant_client():
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
            db.execute(text("DELETE FROM users"))
            db.commit()
    except OperationalError:
        pytest.skip("PostgreSQL integration database is unavailable")

    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides[get_token_claims] = _claims_for_request
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
        with SessionLocal() as db:
            db.execute(text("DELETE FROM users"))
            db.commit()


def _create_application(client: TestClient, subject: str, company: str) -> dict:
    response = client.post(
        "/applications",
        headers=_headers(subject),
        json={"company": company, "role_title": "Engineer", "status": "saved"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _create_resume(client: TestClient, subject: str, file_name: str) -> dict:
    response = client.post(
        "/resume/save",
        headers=_headers(subject),
        json=_resume_payload(file_name),
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_cross_user_reads_writes_relationships_retrieval_and_export_are_blocked(
    tenant_client, monkeypatch
):
    app_a = _create_application(tenant_client, USER_A, "Tenant A Co")
    app_b = _create_application(tenant_client, USER_B, "Tenant B Co")
    resume_a = _create_resume(tenant_client, USER_A, "a.pdf")
    resume_b = _create_resume(tenant_client, USER_B, "b.pdf")

    for method, path, payload in [
        ("get", f"/applications/{app_b['id']}", None),
        ("patch", f"/applications/{app_b['id']}", {"company": "Stolen"}),
        ("delete", f"/applications/{app_b['id']}", None),
    ]:
        response = tenant_client.request(
            method.upper(), path, headers=_headers(USER_A), json=payload
        )
        assert response.status_code == 404

    cross_owner_match = tenant_client.post(
        "/matches",
        headers=_headers(USER_A),
        json=_match_payload(app_a["id"], resume_b["id"]),
    )
    assert cross_owner_match.status_code == 404

    own_match = tenant_client.post(
        "/matches",
        headers=_headers(USER_B),
        json=_match_payload(app_b["id"], resume_b["id"]),
    )
    assert own_match.status_code == 200
    assert (
        tenant_client.get(
            f"/matches/application/{app_b['id']}", headers=_headers(USER_A)
        ).status_code
        == 404
    )

    saved_draft = tenant_client.post(
        "/full-resume-drafts",
        headers=_headers(USER_B),
        json=_full_draft_payload(app_b["id"], resume_b["id"]),
    )
    assert saved_draft.status_code == 200, saved_draft.text
    assert (
        tenant_client.get(
            f"/full-resume-drafts/application/{app_b['id']}",
            headers=_headers(USER_A),
        ).status_code
        == 404
    )
    assert (
        tenant_client.post(
            "/export/tailored-resume-docx",
            headers=_headers(USER_A),
            json={"application_id": app_b["id"]},
        ).status_code
        == 404
    )

    with SessionLocal() as db:
        user_a = db.scalar(select(User).where(User.external_subject == USER_A))
        user_b = db.scalar(select(User).where(User.external_subject == USER_B))
        application_a = db.get(Application, app_a["id"])
        evidence_a = ProjectEvidence(
            user_id=user_a.id,
            title="Tenant A evidence",
            category="project",
            description="Python API",
            skills=["Python"],
            keywords=["API"],
            bullet_bank=[],
        )
        evidence_b = ProjectEvidence(
            user_id=user_b.id,
            title="Tenant B evidence",
            category="project",
            description="Private hardware work",
            skills=["KiCad"],
            keywords=["PCB"],
            bullet_bank=[],
        )
        db.add_all([evidence_a, evidence_b])
        db.flush()
        db.add_all(
            [
                ProjectEvidenceChunk(
                    user_id=user_a.id,
                    project_evidence_id=evidence_a.id,
                    chunk_text="Tenant A Python API",
                    chunk_type="summary",
                    embedding=[0.0] * 1536,
                ),
                ProjectEvidenceChunk(
                    user_id=user_b.id,
                    project_evidence_id=evidence_b.id,
                    chunk_text="Tenant B private PCB",
                    chunk_type="summary",
                    embedding=[0.0] * 1536,
                ),
            ]
        )
        db.commit()
        monkeypatch.setattr(retrieval_service, "embed_text", lambda _text: [0.0] * 1536)
        chunks = retrieval_service.retrieve_relevant_chunks_for_application(
            db=db, application=application_a, top_k=10
        )
        assert [chunk.chunk_text for chunk in chunks] == ["Tenant A Python API"]

    evidence_for_a = tenant_client.get(
        "/project-evidence", headers=_headers(USER_A)
    )
    assert evidence_for_a.status_code == 200
    assert [item["title"] for item in evidence_for_a.json()] == ["Tenant A evidence"]

    own_app_ids = {
        item["id"]
        for item in tenant_client.get(
            "/applications", headers=_headers(USER_A)
        ).json()
    }
    assert own_app_ids == {app_a["id"]}
    assert resume_a["id"] != resume_b["id"]


def test_account_deletion_cascades_all_workspace_data(tenant_client):
    application = _create_application(tenant_client, USER_A, "Delete Me Co")
    resume = _create_resume(tenant_client, USER_A, "delete-me.pdf")
    match = tenant_client.post(
        "/matches",
        headers=_headers(USER_A),
        json=_match_payload(application["id"], resume["id"]),
    )
    assert match.status_code == 200
    draft = tenant_client.post(
        "/full-resume-drafts",
        headers=_headers(USER_A),
        json=_full_draft_payload(application["id"], resume["id"]),
    )
    assert draft.status_code == 200

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.external_subject == USER_A))
        evidence = ProjectEvidence(
            user_id=user.id,
            title="Delete me",
            category="project",
            description="Private evidence",
            skills=[],
            keywords=[],
            bullet_bank=[],
        )
        db.add(evidence)
        db.flush()
        db.add(
            ProjectEvidenceChunk(
                user_id=user.id,
                project_evidence_id=evidence.id,
                chunk_text="Delete me",
                chunk_type="summary",
                embedding=None,
            )
        )
        db.commit()
        user_id = user.id

    response = tenant_client.delete("/users/me", headers=_headers(USER_A))
    assert response.status_code == 200

    with SessionLocal() as db:
        assert db.get(User, user_id) is None
        for model in (
            Application,
            Resume,
            ProjectEvidence,
            ProjectEvidenceChunk,
            ApplicationResumeMatch,
            ApplicationTailoredResume,
            ApplicationFullResumeDraft,
        ):
            assert db.scalar(select(model).where(model.user_id == user_id)) is None


def test_row_level_security_is_enabled_for_every_owned_table(tenant_client):
    with SessionLocal() as db:
        rows = db.execute(
            text(
                """
                SELECT c.relname
                FROM pg_class AS c
                JOIN pg_namespace AS n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public'
                  AND c.relrowsecurity = true
                """
            )
        ).scalars()
        rls_tables = set(rows)

    assert {
        "users",
        "applications",
        "resumes",
        "project_evidence",
        "project_evidence_chunks",
        "application_resume_matches",
        "application_tailored_resumes",
        "application_full_resume_drafts",
    }.issubset(rls_tables)
