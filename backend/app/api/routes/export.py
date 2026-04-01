from pathlib import Path
import subprocess
import shutil

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.application import Application
from app.models.application_tailored_resume import ApplicationTailoredResume
from app.models.resume import Resume
from app.schemas.tailor import FullTailoredResumeDraftRequest
from app.services.ai_service import build_full_tailored_resume_draft
from app.services.export_service import EXPORT_DIR, build_tailored_resume_docx
from app.schemas.full_resume import FullTailoredResumeDraftResponse

router = APIRouter(prefix="/export", tags=["export"])


@router.post("/tailored-resume-docx")
def export_tailored_resume_docx(
    payload: FullTailoredResumeDraftRequest,
    db: Session = Depends(get_db),
):
    application = db.query(Application).filter(Application.id == payload.application_id).first()
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

    draft_data = build_full_tailored_resume_draft(
        application=application,
        resume=resume,
        tailored_resume=tailored_resume,
    )
    draft = FullTailoredResumeDraftResponse(**draft_data)

    filename = f"tailored_resume_app_{payload.application_id}.docx"
    output_path = str(EXPORT_DIR / filename)
    build_tailored_resume_docx(draft=draft, output_path=output_path)

    return FileResponse(
        output_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=filename,
    )


@router.post("/tailored-resume-pdf")
def export_tailored_resume_pdf(
    payload: FullTailoredResumeDraftRequest,
    db: Session = Depends(get_db),
):
    application = db.query(Application).filter(Application.id == payload.application_id).first()
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

    draft_data = build_full_tailored_resume_draft(
        application=application,
        resume=resume,
        tailored_resume=tailored_resume,
    )
    draft = FullTailoredResumeDraftResponse(**draft_data)

    docx_filename = f"tailored_resume_app_{payload.application_id}.docx"
    pdf_filename = f"tailored_resume_app_{payload.application_id}.pdf"

    docx_path = str(EXPORT_DIR / docx_filename)
    pdf_path = str(EXPORT_DIR / pdf_filename)

    build_tailored_resume_docx(draft=draft, output_path=docx_path)

    soffice_path = shutil.which("soffice") or "/Applications/LibreOffice.app/Contents/MacOS/soffice"

    subprocess.run(
        [
            soffice_path,
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(EXPORT_DIR),
            docx_path,
        ],
        check=True,
    )

    if not Path(pdf_path).exists():
        raise HTTPException(status_code=500, detail="PDF export failed.")

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=pdf_filename,
    )