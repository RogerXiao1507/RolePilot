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
from app.models.resume_source_item import ResumeSourceItem
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
            ResumeSourceItem,
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
        "resume_source_items",
        "project_evidence",
        "project_evidence_chunks",
        "application_resume_matches",
        "application_tailored_resumes",
        "application_full_resume_drafts",
    }.issubset(rls_tables)


def test_resume_library_defaults_selection_archive_and_cross_user_guards(tenant_client):
    application = _create_application(tenant_client, USER_A, "Resume Choice Co")
    first = _create_resume(tenant_client, USER_A, "general.pdf")
    second_response = tenant_client.post(
        "/resume/save",
        headers=_headers(USER_A),
        json={**_resume_payload("backend.pdf"), "label": "Backend", "make_default": True},
    )
    assert second_response.status_code == 200, second_response.text
    second = second_response.json()

    items = tenant_client.get("/resume", headers=_headers(USER_A)).json()
    assert [item["label"] for item in items] == ["Backend", "general"]
    assert second["is_default"] is True
    assert items[0]["is_default"] is True
    assert items[1]["id"] == first["id"]
    assert items[1]["is_default"] is False

    # Changing the global default does not silently rewrite an explicit application choice.
    saved_application = tenant_client.get(
        f"/applications/{application['id']}", headers=_headers(USER_A)
    ).json()
    assert saved_application["selected_resume_id"] == first["id"]

    selection = tenant_client.patch(
        f"/applications/{application['id']}",
        headers=_headers(USER_A),
        json={"selected_resume_id": second["id"]},
    )
    assert selection.status_code == 200, selection.text
    assert selection.json()["selected_resume_id"] == second["id"]

    saved_match = tenant_client.post(
        "/matches",
        headers=_headers(USER_A),
        json=_match_payload(application["id"], second["id"]),
    )
    assert saved_match.status_code == 200

    foreign = _create_resume(tenant_client, USER_B, "private.pdf")
    denied = tenant_client.patch(
        f"/applications/{application['id']}",
        headers=_headers(USER_A),
        json={"selected_resume_id": foreign["id"]},
    )
    assert denied.status_code == 404

    archived = tenant_client.patch(
        f"/resume/{second['id']}",
        headers=_headers(USER_A),
        json={"is_archived": True},
    )
    assert archived.status_code == 200, archived.text
    assert archived.json()["is_archived"] is True
    assert tenant_client.get(
        f"/applications/{application['id']}", headers=_headers(USER_A)
    ).json()["selected_resume_id"] == first["id"]
    assert tenant_client.get(
        f"/matches/application/{application['id']}", headers=_headers(USER_A)
    ).json()["is_stale"] is True


def test_resume_source_ids_stay_stable_and_edits_mark_artifacts_stale(tenant_client):
    resume = _create_resume(tenant_client, USER_A, "versioned.pdf")
    application = _create_application(tenant_client, USER_A, "Version Co")
    selected = tenant_client.patch(
        f"/applications/{application['id']}",
        headers=_headers(USER_A),
        json={"selected_resume_id": resume["id"]},
    )
    assert selected.status_code == 200
    match = tenant_client.post(
        "/matches",
        headers=_headers(USER_A),
        json=_match_payload(application["id"], resume["id"]),
    )
    assert match.status_code == 200, match.text

    structured = {
        "contact": {"name": "Candidate", "email": None, "phone": None, "location": None, "links": []},
        "education": [],
        "experience": [
            {
                "title": "Engineer",
                "subtitle": "Example",
                "location": None,
                "date_range": "2025",
                "bullets": ["Built a Python API."],
            }
        ],
        "projects": [],
        "skills": ["Python"],
        "other": [],
    }
    first_update = tenant_client.put(
        f"/resume/{resume['id']}/structured-data",
        headers=_headers(USER_A),
        json={"structured_data": structured},
    )
    assert first_update.status_code == 200, first_update.text
    assert first_update.json()["version"] == 2
    source_items = tenant_client.get(
        f"/resume/{resume['id']}/source-items", headers=_headers(USER_A)
    ).json()
    bullet_id = next(item["id"] for item in source_items if item["item_type"] == "bullet")

    structured["experience"][0]["bullets"] = ["Built and deployed a Python API."]
    second_update = tenant_client.put(
        f"/resume/{resume['id']}/structured-data",
        headers=_headers(USER_A),
        json={"structured_data": structured},
    )
    assert second_update.status_code == 200
    source_items = tenant_client.get(
        f"/resume/{resume['id']}/source-items", headers=_headers(USER_A)
    ).json()
    updated_bullet = next(item for item in source_items if item["item_type"] == "bullet")
    assert updated_bullet["id"] == bullet_id
    assert updated_bullet["source_version"] == 3
    assert updated_bullet["content"] == "Built and deployed a Python API."

    # Inserting a new bullet before an unchanged one must not shift that source's UUID.
    structured["experience"][0]["bullets"] = [
        "Documented the API for internal users.",
        "Built and deployed a Python API.",
    ]
    inserted_update = tenant_client.put(
        f"/resume/{resume['id']}/structured-data",
        headers=_headers(USER_A),
        json={"structured_data": structured},
    )
    assert inserted_update.status_code == 200
    source_items = tenant_client.get(
        f"/resume/{resume['id']}/source-items", headers=_headers(USER_A)
    ).json()
    preserved_bullet = next(
        item
        for item in source_items
        if item["content"] == "Built and deployed a Python API."
    )
    assert preserved_bullet["id"] == bullet_id
    assert preserved_bullet["source_version"] == 4

    saved_match = tenant_client.get(
        f"/matches/application/{application['id']}", headers=_headers(USER_A)
    ).json()
    assert saved_match["is_stale"] is True
    assert saved_match["resume_version"] == 1


def test_saved_tailored_bullets_require_current_owned_citations(tenant_client):
    resume = _create_resume(tenant_client, USER_A, "cited.pdf")
    application = _create_application(tenant_client, USER_A, "Citation Co")
    source = tenant_client.get(
        f"/resume/{resume['id']}/source-items", headers=_headers(USER_A)
    ).json()[0]

    def payload(citations):
        return {
            "application_id": application["id"],
            "resume_id": resume["id"],
            "tailored_summary": "Grounded summary",
            "tailored_skills": [],
            "tailored_bullets": [
                {
                    "section": "Experience",
                    "source_title": "Saved resume",
                    "original_bullet": source["content"],
                    "tailored_bullet": source["content"],
                    "evidence_used": ["Saved resume"],
                    "citations": citations,
                }
            ],
            "tailoring_notes": [],
        }

    valid = tenant_client.post(
        "/tailored-resumes",
        headers=_headers(USER_A),
        json=payload(
            [
                {
                    "source_type": "resume_item",
                    "source_id": source["id"],
                    "source_version": source["source_version"],
                }
            ]
        ),
    )
    assert valid.status_code == 200, valid.text

    uncited = tenant_client.post(
        "/tailored-resumes", headers=_headers(USER_A), json=payload([])
    )
    assert uncited.status_code == 422

    foreign_resume = _create_resume(tenant_client, USER_B, "foreign-citation.pdf")
    foreign_source = tenant_client.get(
        f"/resume/{foreign_resume['id']}/source-items", headers=_headers(USER_B)
    ).json()[0]
    foreign = tenant_client.post(
        "/tailored-resumes",
        headers=_headers(USER_A),
        json=payload(
            [
                {
                    "source_type": "resume_item",
                    "source_id": foreign_source["id"],
                    "source_version": foreign_source["source_version"],
                }
            ]
        ),
    )
    assert foreign.status_code == 422


def test_evidence_ingestion_failure_is_visible_and_retryable(tenant_client, monkeypatch):
    monkeypatch.setattr(retrieval_service, "embed_text", lambda _text: [0.0] * 1536)
    created = tenant_client.post(
        "/project-evidence",
        headers=_headers(USER_A),
        json={
            "title": "API project",
            "category": "project",
            "description": "Built a Python API",
            "skills": ["Python"],
            "keywords": ["API"],
            "bullet_bank": ["Reduced latency through caching"],
            "links": [],
            "verified_metrics": [{"label": "Latency", "value": "20%", "context": "Measured in load tests"}],
        },
    )
    assert created.status_code == 200, created.text
    evidence = created.json()
    assert evidence["ingestion_status"] == "ready"
    assert evidence["version"] == 1

    def fail_embedding(_text):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(retrieval_service, "embed_text", fail_embedding)
    failed = tenant_client.patch(
        f"/project-evidence/{evidence['id']}",
        headers=_headers(USER_A),
        json={"outcome": "Shipped to users"},
    )
    assert failed.status_code == 200, failed.text
    assert failed.json()["ingestion_status"] == "failed"
    assert "provider unavailable" not in failed.json()["ingestion_error"]

    monkeypatch.setattr(retrieval_service, "embed_text", lambda _text: [0.0] * 1536)
    retried = tenant_client.post(
        f"/project-evidence/{evidence['id']}/retry",
        headers=_headers(USER_A),
    )
    assert retried.status_code == 200, retried.text
    assert retried.json()["ingestion_status"] == "ready"
    assert retried.json()["version"] == 2


def test_ai_suggested_metric_requires_explicit_user_confirmation(tenant_client, monkeypatch):
    monkeypatch.setattr(retrieval_service, "embed_text", lambda _text: [0.0] * 1536)
    created = tenant_client.post(
        "/project-evidence",
        headers=_headers(USER_A),
        json={
            "title": "Suggested metric project",
            "category": "project",
            "description": "Improved a service",
            "skills": [],
            "keywords": [],
            "bullet_bank": [],
            "links": [],
            "verified_metrics": [],
        },
    )
    assert created.status_code == 200
    evidence_id = created.json()["id"]

    with SessionLocal() as db:
        evidence = db.get(ProjectEvidence, evidence_id)
        evidence.ai_suggested_metrics = [
            {
                "label": "Latency",
                "value": "20%",
                "context": "AI suggestion awaiting user verification",
            }
        ]
        db.commit()

    before_confirmation = tenant_client.get(
        f"/project-evidence/{evidence_id}", headers=_headers(USER_A)
    ).json()
    assert before_confirmation["verified_metrics"] == []
    assert len(before_confirmation["ai_suggested_metrics"]) == 1

    confirmed = tenant_client.post(
        f"/project-evidence/{evidence_id}/confirm-metric",
        headers=_headers(USER_A),
        json={"suggestion_index": 0},
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["ai_suggested_metrics"] == []
    assert confirmed.json()["verified_metrics"] == [
        {
            "label": "Latency",
            "value": "20%",
            "context": "AI suggestion awaiting user verification",
        }
    ]
    assert confirmed.json()["version"] == 2
