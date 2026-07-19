from fastapi import APIRouter, HTTPException, Depends
from app.schemas.ai import JobParseRequest, JobUrlParseRequest, JobParseResponse
from app.services.ai_service import (
    JobUrlFetchError,
    JobUrlValidationError,
    parse_job_description,
    parse_job_from_url,
)
from app.schemas.ai import ResumeJobMatchRequest, ResumeJobMatchResponse
from app.services.ai_service import match_resume_to_job
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, get_owned_or_404
from app.models.application import Application
from app.models.project_evidence import ProjectEvidence
from app.models.resume import Resume
from app.models.user import User
from app.schemas.tailor import TailorResumeRequest, TailorResumeResponse
from app.services.ai_service import tailor_resume_for_application


from app.models.application_tailored_resume import ApplicationTailoredResume
from app.schemas.full_resume import FullTailoredResumeDraftResponse
from app.schemas.tailor import FullTailoredResumeDraftRequest
from app.services.ai_service import (
    GeneratedContentGroundingError,
    build_full_tailored_resume_draft,
)

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/parse-job", response_model=JobParseResponse)
def parse_job(
    payload: JobParseRequest,
    _current_user: User = Depends(get_current_user),
):
    return parse_job_description(payload.text)


@router.post("/parse-job-url", response_model=JobParseResponse)
def parse_job_url(
    payload: JobUrlParseRequest,
    _current_user: User = Depends(get_current_user),
):
    try:
        return parse_job_from_url(payload.url)
    except JobUrlValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except JobUrlFetchError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    
@router.post("/match-resume-job", response_model=ResumeJobMatchResponse)
def match_resume_job(
    payload: ResumeJobMatchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    application = get_owned_or_404(
        db, Application, payload.application_id, current_user.id, "Application not found."
    )
    resume = get_owned_or_404(
        db, Resume, payload.resume_id, current_user.id, "Resume not found."
    )
    if application.selected_resume_id != resume.id:
        raise HTTPException(status_code=409, detail="Select this resume for the application first.")

    result = match_resume_to_job(
        resume_text=resume.extracted_text,
        role_title=application.role_title,
        company=application.company,
        job_summary=application.ai_summary,
        required_skills=application.required_skills,
        preferred_skills=application.preferred_skills,
        keywords=application.keywords,
    )
    return result

@router.post("/tailor-resume", response_model=TailorResumeResponse)
def tailor_resume(
    payload: TailorResumeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    application = get_owned_or_404(
        db, Application, payload.application_id, current_user.id, "Application not found."
    )
    resume = get_owned_or_404(
        db, Resume, payload.resume_id, current_user.id, "Resume not found."
    )
    if application.selected_resume_id != resume.id:
        raise HTTPException(status_code=409, detail="Select this resume for the application first.")

    try:
        result = tailor_resume_for_application(
            db=db,
            application=application,
            resume=resume,
        )
    except GeneratedContentGroundingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return result

@router.post("/full-tailored-resume", response_model=FullTailoredResumeDraftResponse)
def generate_full_tailored_resume(
    payload: FullTailoredResumeDraftRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    application = get_owned_or_404(
        db, Application, payload.application_id, current_user.id, "Application not found."
    )
    resume = get_owned_or_404(
        db, Resume, payload.resume_id, current_user.id, "Resume not found."
    )
    if application.selected_resume_id != resume.id:
        raise HTTPException(status_code=409, detail="Select this resume for the application first.")

    tailored_resume = (
        db.query(ApplicationTailoredResume)
        .filter(
            ApplicationTailoredResume.application_id == payload.application_id,
            ApplicationTailoredResume.resume_id == payload.resume_id,
            ApplicationTailoredResume.user_id == current_user.id,
        )
        .first()
    )
    if not tailored_resume:
        raise HTTPException(status_code=404, detail="No saved tailored resume found for this application.")
    if tailored_resume.is_stale or tailored_resume.resume_version != resume.version:
        raise HTTPException(
            status_code=409,
            detail="The tailored resume is stale. Regenerate it before building a full draft.",
        )

    try:
        result = build_full_tailored_resume_draft(
            application=application,
            resume=resume,
            tailored_resume=tailored_resume,
            project_evidence=(
                db.query(ProjectEvidence)
                .filter(ProjectEvidence.user_id == current_user.id)
                .all()
            ),
        )
    except GeneratedContentGroundingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return result
