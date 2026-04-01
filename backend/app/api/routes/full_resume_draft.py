from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.application import Application
from app.models.application_full_resume_draft import ApplicationFullResumeDraft
from app.models.resume import Resume
from app.schemas.saved_full_resume import (
    ApplicationFullResumeDraftCreate,
    ApplicationFullResumeDraftResponse,
)

router = APIRouter(prefix="/full-resume-drafts", tags=["full-resume-drafts"])


@router.post("", response_model=ApplicationFullResumeDraftResponse)
def save_full_resume_draft(
    payload: ApplicationFullResumeDraftCreate,
    db: Session = Depends(get_db),
):
    application = db.query(Application).filter(Application.id == payload.application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found.")

    resume = db.query(Resume).filter(Resume.id == payload.resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found.")

    existing = (
        db.query(ApplicationFullResumeDraft)
        .filter(ApplicationFullResumeDraft.application_id == payload.application_id)
        .first()
    )

    draft_payload = payload.draft_data.model_dump()

    if existing:
        existing.resume_id = payload.resume_id
        existing.draft_data = draft_payload
        db.commit()
        db.refresh(existing)
        return existing

    draft = ApplicationFullResumeDraft(
        application_id=payload.application_id,
        resume_id=payload.resume_id,
        draft_data=draft_payload,
    )

    db.add(draft)
    db.commit()
    db.refresh(draft)

    return draft


@router.get("/application/{application_id}", response_model=ApplicationFullResumeDraftResponse)
def get_full_resume_draft(application_id: int, db: Session = Depends(get_db)):
    draft = (
        db.query(ApplicationFullResumeDraft)
        .filter(ApplicationFullResumeDraft.application_id == application_id)
        .first()
    )

    if not draft:
        raise HTTPException(status_code=404, detail="No saved full resume draft found for this application.")

    return draft