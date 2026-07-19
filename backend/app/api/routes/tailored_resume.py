from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, get_owned_or_404
from app.models.application import Application
from app.models.application_tailored_resume import ApplicationTailoredResume
from app.models.project_evidence import ProjectEvidence
from app.models.resume import Resume
from app.models.resume_source_item import ResumeSourceItem
from app.models.user import User
from app.schemas.saved_tailor import (
    ApplicationTailoredResumeCreate,
    ApplicationTailoredResumeResponse,
)

router = APIRouter(prefix="/tailored-resumes", tags=["tailored-resumes"])


def _validate_tailored_bullet_citations(
    db: Session,
    *,
    current_user: User,
    resume: Resume,
    tailored_bullets,
) -> None:
    resume_sources = {
        (str(item.id), item.source_version)
        for item in db.scalars(
            select(ResumeSourceItem).where(
                ResumeSourceItem.user_id == current_user.id,
                ResumeSourceItem.resume_id == resume.id,
                ResumeSourceItem.source_version == resume.version,
                ResumeSourceItem.is_active.is_(True),
            )
        ).all()
    }
    evidence_sources = {
        (str(item.id), item.version)
        for item in db.scalars(
            select(ProjectEvidence).where(
                ProjectEvidence.user_id == current_user.id,
                ProjectEvidence.ingestion_status == "ready",
            )
        ).all()
    }

    for bullet in tailored_bullets:
        if not bullet.citations:
            raise HTTPException(
                status_code=422,
                detail="Every tailored bullet must cite at least one current source.",
            )
        for citation in bullet.citations:
            catalog = (
                resume_sources
                if citation.source_type == "resume_item"
                else evidence_sources
            )
            if (citation.source_id, citation.source_version) not in catalog:
                raise HTTPException(
                    status_code=422,
                    detail="A tailored bullet citation is stale or outside this workspace.",
                )


@router.post("", response_model=ApplicationTailoredResumeResponse)
def save_application_tailored_resume(
    payload: ApplicationTailoredResumeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    application = get_owned_or_404(
        db, Application, payload.application_id, current_user.id, "Application not found."
    )
    resume = get_owned_or_404(db, Resume, payload.resume_id, current_user.id, "Resume not found.")
    if application.selected_resume_id != resume.id:
        raise HTTPException(status_code=409, detail="Select this resume for the application first.")
    _validate_tailored_bullet_citations(
        db,
        current_user=current_user,
        resume=resume,
        tailored_bullets=payload.tailored_bullets,
    )

    existing = (
        db.query(ApplicationTailoredResume)
        .filter(
            ApplicationTailoredResume.application_id == payload.application_id,
            ApplicationTailoredResume.user_id == current_user.id,
        )
        .first()
    )

    bullet_payload = [bullet.model_dump() for bullet in payload.tailored_bullets]

    if existing:
        existing.resume_id = payload.resume_id
        existing.resume_version = resume.version
        existing.is_stale = False
        existing.tailored_summary = payload.tailored_summary
        existing.tailored_skills = payload.tailored_skills
        existing.tailored_bullets = bullet_payload
        existing.tailoring_notes = payload.tailoring_notes

        db.commit()
        db.refresh(existing)
        return existing

    tailored_resume = ApplicationTailoredResume(
        user_id=current_user.id,
        application_id=payload.application_id,
        resume_id=payload.resume_id,
        resume_version=resume.version,
        is_stale=False,
        tailored_summary=payload.tailored_summary,
        tailored_skills=payload.tailored_skills,
        tailored_bullets=bullet_payload,
        tailoring_notes=payload.tailoring_notes,
    )

    db.add(tailored_resume)
    db.commit()
    db.refresh(tailored_resume)

    return tailored_resume


@router.get("/application/{application_id}", response_model=ApplicationTailoredResumeResponse)
def get_application_tailored_resume(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tailored_resume = (
        db.query(ApplicationTailoredResume)
        .filter(
            ApplicationTailoredResume.application_id == application_id,
            ApplicationTailoredResume.user_id == current_user.id,
        )
        .first()
    )

    if not tailored_resume:
        raise HTTPException(status_code=404, detail="No saved tailored resume found for this application.")

    return tailored_resume
