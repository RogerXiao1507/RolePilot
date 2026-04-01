from fastapi import APIRouter, HTTPException, Depends
from app.schemas.ai import JobParseRequest, JobUrlParseRequest, JobParseResponse
from app.services.ai_service import parse_job_description, parse_job_from_url
from app.schemas.ai import ResumeJobMatchRequest, ResumeJobMatchResponse
from app.services.ai_service import match_resume_to_job
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.application import Application
from app.models.project_evidence import ProjectEvidence
from app.models.resume import Resume
from app.schemas.tailor import TailorResumeRequest, TailorResumeResponse
from app.services.ai_service import tailor_resume_for_application


from app.models.application_tailored_resume import ApplicationTailoredResume
from app.schemas.full_resume import FullTailoredResumeDraftResponse
from app.schemas.tailor import FullTailoredResumeDraftRequest
from app.services.ai_service import build_full_tailored_resume_draft

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/parse-job", response_model=JobParseResponse)
def parse_job(payload: JobParseRequest):
    try:
        return parse_job_description(payload.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse job: {str(e)}")


@router.post("/parse-job-url", response_model=JobParseResponse)
def parse_job_url(payload: JobUrlParseRequest):
    try:
        return parse_job_from_url(payload.url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse job URL: {str(e)}")
    
@router.post("/match-resume-job", response_model=ResumeJobMatchResponse)
def match_resume_job(payload: ResumeJobMatchRequest):
    result = match_resume_to_job(
        resume_text=payload.resume_text,
        role_title=payload.role_title,
        company=payload.company,
        job_summary=payload.job_summary,
        required_skills=payload.required_skills,
        preferred_skills=payload.preferred_skills,
        keywords=payload.keywords,
    )
    return result

@router.post("/tailor-resume", response_model=TailorResumeResponse)
def tailor_resume(
    payload: TailorResumeRequest,
    db: Session = Depends(get_db),
):
    application = (
        db.query(Application)
        .filter(Application.id == payload.application_id)
        .first()
    )
    if not application:
        raise HTTPException(status_code=404, detail="Application not found.")

    resume = db.query(Resume).order_by(Resume.created_at.desc()).first()
    if not resume:
        raise HTTPException(status_code=404, detail="No saved resume found.")

    result = tailor_resume_for_application(
        db=db,
        application=application,
        resume=resume,
    )

    return result

@router.post("/full-tailored-resume", response_model=FullTailoredResumeDraftResponse)
def generate_full_tailored_resume(
    payload: FullTailoredResumeDraftRequest,
    db: Session = Depends(get_db),
):
    application = (
        db.query(Application)
        .filter(Application.id == payload.application_id)
        .first()
    )
    if not application:
        raise HTTPException(status_code=404, detail="Application not found.")

    resume = db.query(Resume).order_by(Resume.created_at.desc()).first()
    if not resume:
        raise HTTPException(status_code=404, detail="No saved resume found.")

    tailored_resume = (
        db.query(ApplicationTailoredResume)
        .filter(ApplicationTailoredResume.application_id == payload.application_id)
        .first()
    )
    if not tailored_resume:
        raise HTTPException(status_code=404, detail="No saved tailored resume found for this application.")

    result = build_full_tailored_resume_draft(
        application=application,
        resume=resume,
        tailored_resume=tailored_resume,
    )

    return result