from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.resume import Resume
from app.schemas.resume import ResumeAnalysisResponse, ResumeCreate, ResumeResponse
from app.services.resume_service import analyze_resume_text, extract_text_from_pdf_bytes

router = APIRouter(prefix="/resume", tags=["resume"])


@router.post("/analyze", response_model=ResumeAnalysisResponse)
async def analyze_resume(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    pdf_bytes = await file.read()
    extracted_text = extract_text_from_pdf_bytes(pdf_bytes)
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