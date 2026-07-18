from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, get_owned_or_404
from app.models.application import Application
from app.models.application_tailored_resume import ApplicationTailoredResume
from app.models.resume import Resume
from app.models.user import User
from app.schemas.saved_tailor import (
    ApplicationTailoredResumeCreate,
    ApplicationTailoredResumeResponse,
)

router = APIRouter(prefix="/tailored-resumes", tags=["tailored-resumes"])


@router.post("", response_model=ApplicationTailoredResumeResponse)
def save_application_tailored_resume(
    payload: ApplicationTailoredResumeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_owned_or_404(
        db, Application, payload.application_id, current_user.id, "Application not found."
    )
    get_owned_or_404(db, Resume, payload.resume_id, current_user.id, "Resume not found.")

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
