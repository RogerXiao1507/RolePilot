from pathlib import Path
import subprocess
import shutil
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask

from app.api.deps import get_current_user, get_db
from app.models.application import Application
from app.models.application_full_resume_draft import ApplicationFullResumeDraft
from app.models.user import User
from app.schemas.tailor import ExportSavedResumeRequest
from app.services.export_service import EXPORT_DIR, build_tailored_resume_docx
from app.schemas.full_resume import FullTailoredResumeDraftResponse

router = APIRouter(prefix="/export", tags=["export"])


def _load_saved_draft(
    *,
    application_id: int,
    current_user: User,
    db: Session,
) -> FullTailoredResumeDraftResponse:
    application = (
        db.query(Application)
        .filter(
            Application.id == application_id,
            Application.user_id == current_user.id,
        )
        .first()
    )
    if not application:
        raise HTTPException(status_code=404, detail="Application not found.")

    saved_draft = (
        db.query(ApplicationFullResumeDraft)
        .filter(
            ApplicationFullResumeDraft.application_id == application_id,
            ApplicationFullResumeDraft.user_id == current_user.id,
        )
        .first()
    )
    if not saved_draft:
        raise HTTPException(
            status_code=404,
            detail="No saved full resume draft found for this application.",
        )
    if (
        saved_draft.is_stale
        or saved_draft.resume_id != application.selected_resume_id
    ):
        raise HTTPException(
            status_code=409,
            detail="The saved draft is stale. Regenerate it before exporting.",
        )

    return FullTailoredResumeDraftResponse(**saved_draft.draft_data)


def _remove_export_files(paths: list[Path]) -> None:
    for path in paths:
        path.unlink(missing_ok=True)


@router.post("/tailored-resume-docx")
def export_tailored_resume_docx(
    payload: ExportSavedResumeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    draft = _load_saved_draft(
        application_id=payload.application_id,
        current_user=current_user,
        db=db,
    )
    download_filename = f"tailored_resume_app_{payload.application_id}.docx"
    output_path = EXPORT_DIR / f"{uuid4().hex}.docx"
    build_tailored_resume_docx(draft=draft, output_path=str(output_path))

    return FileResponse(
        str(output_path),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=download_filename,
        background=BackgroundTask(_remove_export_files, [output_path]),
    )


@router.post("/tailored-resume-pdf")
def export_tailored_resume_pdf(
    payload: ExportSavedResumeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    draft = _load_saved_draft(
        application_id=payload.application_id,
        current_user=current_user,
        db=db,
    )
    export_id = uuid4().hex
    docx_path = EXPORT_DIR / f"{export_id}.docx"
    pdf_path = EXPORT_DIR / f"{export_id}.pdf"
    download_filename = f"tailored_resume_app_{payload.application_id}.pdf"

    build_tailored_resume_docx(draft=draft, output_path=str(docx_path))

    soffice_path = shutil.which("soffice") or "/Applications/LibreOffice.app/Contents/MacOS/soffice"

    try:
        subprocess.run(
            [
                soffice_path,
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                str(EXPORT_DIR),
                str(docx_path),
            ],
            check=True,
            capture_output=True,
            timeout=60,
        )
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        _remove_export_files([docx_path, pdf_path])
        raise HTTPException(status_code=500, detail="PDF export failed.") from exc

    if not pdf_path.exists():
        _remove_export_files([docx_path, pdf_path])
        raise HTTPException(status_code=500, detail="PDF export failed.")

    return FileResponse(
        str(pdf_path),
        media_type="application/pdf",
        filename=download_filename,
        background=BackgroundTask(_remove_export_files, [docx_path, pdf_path]),
    )
