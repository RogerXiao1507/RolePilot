from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.application import Application
from app.models.application_resume_match import ApplicationResumeMatch
from app.models.resume import Resume
from app.schemas.match import (
    ApplicationResumeMatchCreate,
    ApplicationResumeMatchResponse,
)

router = APIRouter(prefix="/matches", tags=["matches"])


@router.post("", response_model=ApplicationResumeMatchResponse)
def save_application_resume_match(
    payload: ApplicationResumeMatchCreate,
    db: Session = Depends(get_db),
):
    application = db.query(Application).filter(Application.id == payload.application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found.")

    resume = db.query(Resume).filter(Resume.id == payload.resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found.")

    existing_match = (
        db.query(ApplicationResumeMatch)
        .filter(ApplicationResumeMatch.application_id == payload.application_id)
        .first()
    )

    if existing_match:
        existing_match.resume_id = payload.resume_id
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
        application_id=payload.application_id,
        resume_id=payload.resume_id,
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
def get_application_resume_match(application_id: int, db: Session = Depends(get_db)):
    match = (
        db.query(ApplicationResumeMatch)
        .filter(ApplicationResumeMatch.application_id == application_id)
        .first()
    )

    if not match:
        raise HTTPException(status_code=404, detail="No saved match found for this application.")

    return match