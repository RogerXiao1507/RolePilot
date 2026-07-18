import json
from types import SimpleNamespace

import pytest

from app.services import ai_service
from app.services.ai_service import (
    GeneratedContentGroundingError,
    build_full_tailored_resume_draft,
    tailor_resume_for_application,
)


def make_model_result(metric: str = "20%") -> dict:
    return {
        "header": {
            "name": "Jane Candidate",
            "location": None,
            "phone": None,
            "email": None,
            "websites": [],
        },
        "professional_summary": "Python engineer",
        "education": [],
        "experience": [
            {
                "title": "Engineer",
                "subtitle": "Example",
                "location": None,
                "date_range": "2024",
                "bullets": [f"Improved latency by {metric} using Python."],
            }
        ],
        "projects": [],
        "skills": {
            "programming_languages": ["Python", "Rust"],
            "frameworks_tools": ["KiCad"],
            "hardware_instrumentation": [],
            "technical_areas": [],
            "developer_tools": [],
        },
    }


def source_objects():
    application = SimpleNamespace(
        company="Example",
        role_title="Engineer",
        ai_summary="Python systems",
        required_skills=["Python"],
        preferred_skills=[],
        keywords=[],
        job_description="Improve latency",
    )
    resume = SimpleNamespace(
        file_name="resume.pdf",
        extracted_text=(
            "Jane Candidate\nEngineer, Example\n2024\n"
            "Improved latency by 20% using Python."
        ),
        summary="Engineer",
        strengths=[],
        weaknesses=[],
        wording_issues=[],
        missing_metrics=[],
        suggested_improvements=[],
    )
    tailored_resume = SimpleNamespace(
        tailored_summary="Python engineer",
        tailored_skills=["Python", "Rust"],
        tailored_bullets=[],
        tailoring_notes=[],
    )
    return application, resume, tailored_resume


def test_full_draft_removes_unsupported_and_hard_coded_skills(monkeypatch):
    model_result = make_model_result()
    monkeypatch.setattr(
        ai_service.client.responses,
        "create",
        lambda **kwargs: SimpleNamespace(output_text=json.dumps(model_result)),
    )
    application, resume, tailored_resume = source_objects()

    result = build_full_tailored_resume_draft(
        application=application,
        resume=resume,
        tailored_resume=tailored_resume,
        project_evidence=[],
    )

    assert result["skills"]["programming_languages"] == ["Python"]
    assert result["skills"]["frameworks_tools"] == []


def test_full_draft_rejects_unsupported_numeric_claims(monkeypatch):
    model_result = make_model_result(metric="99%")
    monkeypatch.setattr(
        ai_service.client.responses,
        "create",
        lambda **kwargs: SimpleNamespace(output_text=json.dumps(model_result)),
    )
    application, resume, tailored_resume = source_objects()

    with pytest.raises(GeneratedContentGroundingError):
        build_full_tailored_resume_draft(
            application=application,
            resume=resume,
            tailored_resume=tailored_resume,
            project_evidence=[],
        )


def test_tailored_content_filters_unsupported_skills(monkeypatch):
    application, resume, _ = source_objects()
    model_result = {
        "tailored_summary": "Python engineer",
        "tailored_skills": ["Python", "Rust"],
        "tailored_bullets": [
            {
                "section": "Experience",
                "source_title": "Engineer",
                "original_bullet": "Improved latency by 20% using Python.",
                "tailored_bullet": "Improved latency by 20% using Python.",
                "evidence_used": ["Saved Resume"],
            }
        ],
        "tailoring_notes": [],
    }
    monkeypatch.setattr(
        ai_service,
        "retrieve_relevant_chunks_for_application_hybrid",
        lambda **kwargs: [],
    )
    monkeypatch.setattr(
        ai_service.client.responses,
        "create",
        lambda **kwargs: SimpleNamespace(output_text=json.dumps(model_result)),
    )

    result = tailor_resume_for_application(
        db=SimpleNamespace(),
        application=application,
        resume=resume,
    )

    assert result["tailored_skills"] == ["Python"]


def test_tailored_content_rejects_unsupported_numeric_claims(monkeypatch):
    application, resume, _ = source_objects()
    model_result = {
        "tailored_summary": "Python engineer",
        "tailored_skills": ["Python"],
        "tailored_bullets": [
            {
                "section": "Experience",
                "source_title": "Engineer",
                "original_bullet": "Improved latency by 20% using Python.",
                "tailored_bullet": "Improved latency by 99% using Python.",
                "evidence_used": ["Saved Resume"],
            }
        ],
        "tailoring_notes": [],
    }
    monkeypatch.setattr(
        ai_service,
        "retrieve_relevant_chunks_for_application_hybrid",
        lambda **kwargs: [],
    )
    monkeypatch.setattr(
        ai_service.client.responses,
        "create",
        lambda **kwargs: SimpleNamespace(output_text=json.dumps(model_result)),
    )

    with pytest.raises(GeneratedContentGroundingError):
        tailor_resume_for_application(
            db=SimpleNamespace(),
            application=application,
            resume=resume,
        )
