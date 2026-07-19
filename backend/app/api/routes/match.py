from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, get_owned_or_404
from app.models.application import Application
from app.models.application_resume_match import ApplicationResumeMatch
from app.models.resume import Resume
from app.models.user import User
from app.schemas.match import (
    ApplicationResumeMatchCreate,
    ApplicationResumeMatchResponse,
)

router = APIRouter(prefix="/matches", tags=["matches"])


@router.post("", response_model=ApplicationResumeMatchResponse)
def save_application_resume_match(
    payload: ApplicationResumeMatchCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    application = get_owned_or_404(
        db, Application, payload.application_id, current_user.id, "Application not found."
    )
    resume = get_owned_or_404(db, Resume, payload.resume_id, current_user.id, "Resume not found.")
    if application.selected_resume_id != resume.id:
        raise HTTPException(status_code=409, detail="Select this resume for the application first.")

    existing_match = (
        db.query(ApplicationResumeMatch)
        .filter(
            ApplicationResumeMatch.application_id == payload.application_id,
            ApplicationResumeMatch.user_id == current_user.id,
        )
        .first()
    )

    if existing_match:
        existing_match.resume_id = payload.resume_id
        existing_match.resume_version = resume.version
        existing_match.is_stale = False
        existing_match.overall_match_summary = payload.overall_match_summary
        existing_match.matched_skills = payload.matched_skills
        existing_match.missing_skills = payload.missing_skills
        existing_match.strengths_for_role = payload.strengths_for_role
        existing_match.improvement_areas = payload.improvement_areas
        existing_match.suggested_resume_changes = payload.suggested_resume_changes

        db.commit()
        db.refresh(existing_match)
        return existing_match

    new_match = ApplicationResumeMatch(
        user_id=current_user.id,
        application_id=payload.application_id,
        resume_id=payload.resume_id,
        resume_version=resume.version,
        is_stale=False,
        overall_match_summary=payload.overall_match_summary,
        matched_skills=payload.matched_skills,
        missing_skills=payload.missing_skills,
        strengths_for_role=payload.strengths_for_role,
        improvement_areas=payload.improvement_areas,
        suggested_resume_changes=payload.suggested_resume_changes,
    )

    db.add(new_match)
    db.commit()
    db.refresh(new_match)

    return new_match


@router.get("/application/{application_id}", response_model=ApplicationResumeMatchResponse)
def get_application_resume_match(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    match = (
        db.query(ApplicationResumeMatch)
        .filter(
            ApplicationResumeMatch.application_id == application_id,
            ApplicationResumeMatch.user_id == current_user.id,
        )
        .first()
    )

    if not match:
        raise HTTPException(status_code=404, detail="No saved match found for this application.")

    return match
