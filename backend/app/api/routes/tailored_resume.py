from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.application import Application
from app.models.application_tailored_resume import ApplicationTailoredResume
from app.models.resume import Resume
from app.schemas.saved_tailor import (
    ApplicationTailoredResumeCreate,
    ApplicationTailoredResumeResponse,
)

router = APIRouter(prefix="/tailored-resumes", tags=["tailored-resumes"])


@router.post("", response_model=ApplicationTailoredResumeResponse)
def save_application_tailored_resume(
    payload: ApplicationTailoredResumeCreate,
    db: Session = Depends(get_db),
):
    application = db.query(Application).filter(Application.id == payload.application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found.")

    resume = db.query(Resume).filter(Resume.id == payload.resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found.")

    existing = (
        db.query(ApplicationTailoredResume)
        .filter(ApplicationTailoredResume.application_id == payload.application_id)
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
def get_application_tailored_resume(application_id: int, db: Session = Depends(get_db)):
    tailored_resume = (
        db.query(ApplicationTailoredResume)
        .filter(ApplicationTailoredResume.application_id == application_id)
        .first()
    )

    if not tailored_resume:
        raise HTTPException(status_code=404, detail="No saved tailored resume found for this application.")

    return tailored_resume