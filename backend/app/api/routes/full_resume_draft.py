from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, get_owned_or_404
from app.models.application import Application
from app.models.application_full_resume_draft import ApplicationFullResumeDraft
from app.models.resume import Resume
from app.models.user import User
from app.schemas.saved_full_resume import (
    ApplicationFullResumeDraftCreate,
    ApplicationFullResumeDraftResponse,
)

router = APIRouter(prefix="/full-resume-drafts", tags=["full-resume-drafts"])


@router.post("", response_model=ApplicationFullResumeDraftResponse)
def save_full_resume_draft(
    payload: ApplicationFullResumeDraftCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    application = get_owned_or_404(
        db, Application, payload.application_id, current_user.id, "Application not found."
    )
    resume = get_owned_or_404(db, Resume, payload.resume_id, current_user.id, "Resume not found.")
    if application.selected_resume_id != resume.id:
        raise HTTPException(status_code=409, detail="Select this resume for the application first.")

    existing = (
        db.query(ApplicationFullResumeDraft)
        .filter(
            ApplicationFullResumeDraft.application_id == payload.application_id,
            ApplicationFullResumeDraft.user_id == current_user.id,
        )
        .first()
    )

    draft_payload = payload.draft_data.model_dump()

    if existing:
        existing.resume_id = payload.resume_id
        existing.resume_version = resume.version
        existing.is_stale = False
        existing.draft_data = draft_payload
        db.commit()
        db.refresh(existing)
        return existing

    draft = ApplicationFullResumeDraft(
        user_id=current_user.id,
        application_id=payload.application_id,
        resume_id=payload.resume_id,
        resume_version=resume.version,
        is_stale=False,
        draft_data=draft_payload,
    )

    db.add(draft)
    db.commit()
    db.refresh(draft)

    return draft


@router.get("/application/{application_id}", response_model=ApplicationFullResumeDraftResponse)
def get_full_resume_draft(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    draft = (
        db.query(ApplicationFullResumeDraft)
        .filter(
            ApplicationFullResumeDraft.application_id == application_id,
            ApplicationFullResumeDraft.user_id == current_user.id,
        )
        .first()
    )

    if not draft:
        raise HTTPException(status_code=404, detail="No saved full resume draft found for this application.")

    return draft
