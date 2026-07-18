from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import settings
from app.models.resume import Resume
from app.schemas.resume import ResumeAnalysisResponse, ResumeCreate, ResumeResponse
from app.services.resume_service import analyze_resume_text, extract_text_from_pdf_bytes

router = APIRouter(prefix="/resume", tags=["resume"])


async def read_upload_with_limit(file: UploadFile, max_bytes: int) -> bytes:
    payload = bytearray()
    while chunk := await file.read(1024 * 1024):
        payload.extend(chunk)
        if len(payload) > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"Resume PDF cannot exceed {max_bytes // (1024 * 1024)} MB.",
            )
    return bytes(payload)


@router.post("/analyze", response_model=ResumeAnalysisResponse)
async def analyze_resume(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Resume filename must end in .pdf.")

    pdf_bytes = await read_upload_with_limit(file, settings.max_resume_upload_bytes)
    try:
        extracted_text = extract_text_from_pdf_bytes(
            pdf_bytes,
            max_pages=settings.max_resume_pages,
            max_text_chars=settings.max_resume_text_chars,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    analysis = analyze_resume_text(extracted_text)

    return {
        **analysis,
        "extracted_text": extracted_text,
    }


@router.post("/save", response_model=ResumeResponse)
def save_resume(payload: ResumeCreate, db: Session = Depends(get_db)):
    resume = Resume(
        file_name=payload.file_name,
        extracted_text=payload.extracted_text,
        summary=payload.summary,
        strengths=payload.strengths,
        weaknesses=payload.weaknesses,
        wording_issues=payload.wording_issues,
        missing_metrics=payload.missing_metrics,
        suggested_improvements=payload.suggested_improvements,
    )

    db.add(resume)
    db.commit()
    db.refresh(resume)

    return resume


@router.get("/latest", response_model=ResumeResponse)
def get_latest_resume(db: Session = Depends(get_db)):
    resume = db.query(Resume).order_by(Resume.created_at.desc()).first()

    if not resume:
        raise HTTPException(status_code=404, detail="No saved resume found.")

    return resume
