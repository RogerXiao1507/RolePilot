from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.models.application import Application
from app.models.project_evidence import ProjectEvidence
from app.models.resume import Resume
from app.models.resume_source_item import ResumeSourceItem
from app.models.user import User
from app.schemas.resume import (
    ResumeAnalysisResponse,
    ResumeCreate,
    ResumeListItem,
    ResumeResponse,
    ResumeSourceItemResponse,
    ResumeSourceUrlResponse,
    ResumeStructuredData,
    ResumeStructuredUpdate,
    ResumeUpdate,
)
from app.services.resume_service import analyze_resume_text, extract_text_from_pdf_bytes
from app.services.object_storage_service import (
    ObjectStorageNotConfigured,
    ObjectStorageOperationError,
    create_signed_resume_url,
    delete_resume_pdf,
    store_resume_pdf,
)
from app.services.source_service import (
    mark_application_artifacts_stale,
    mark_resume_artifacts_stale,
    resume_fingerprint,
    sync_resume_source_items,
)

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


def _owned_resume(db: Session, *, user_id: UUID, resume_id: int) -> Resume:
    resume = db.scalar(
        select(Resume).where(Resume.id == resume_id, Resume.user_id == user_id)
    )
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found.")
    return resume


def _current_default(db: Session, *, user_id: UUID) -> Resume | None:
    return db.scalar(
        select(Resume).where(
            Resume.user_id == user_id,
            Resume.is_default.is_(True),
            Resume.is_archived.is_(False),
        )
    )


def _choose_replacement_default(
    db: Session,
    *,
    user_id: UUID,
    exclude_resume_id: int,
) -> Resume | None:
    replacement = db.scalar(
        select(Resume)
        .where(
            Resume.user_id == user_id,
            Resume.id != exclude_resume_id,
            Resume.is_archived.is_(False),
        )
        .order_by(Resume.updated_at.desc(), Resume.id.desc())
        .limit(1)
    )
    if replacement:
        replacement.is_default = True
    return replacement


def _select_resume_for_applications(
    db: Session,
    *,
    user_id: UUID,
    old_resume_id: int,
    replacement_resume_id: int | None,
) -> None:
    application_ids = db.scalars(
        select(Application.id).where(
            Application.user_id == user_id,
            Application.selected_resume_id == old_resume_id,
        )
    ).all()
    for application_id in application_ids:
        mark_application_artifacts_stale(
            db,
            user_id=user_id,
            application_id=application_id,
        )
    db.execute(
        update(Application)
        .where(
            Application.user_id == user_id,
            Application.selected_resume_id == old_resume_id,
        )
        .values(selected_resume_id=replacement_resume_id)
    )


def _persist_resume(
    *,
    db: Session,
    current_user: User,
    payload: ResumeCreate,
    object_storage_key: str | None = None,
) -> Resume:
    should_be_default = payload.make_default or _current_default(
        db, user_id=current_user.id
    ) is None
    if should_be_default:
        db.execute(
            update(Resume)
            .where(Resume.user_id == current_user.id)
            .values(is_default=False)
        )

    derived_label = Path(payload.file_name).stem.strip() or "Resume"
    structured_data = payload.structured_data.model_dump()
    resume = Resume(
        user_id=current_user.id,
        label=(payload.label or derived_label)[:120],
        file_name=payload.file_name,
        extracted_text=payload.extracted_text,
        structured_data=structured_data,
        source_fingerprint=resume_fingerprint(
            extracted_text=payload.extracted_text,
            structured_data=structured_data,
        ),
        version=1,
        object_storage_key=object_storage_key,
        summary=payload.summary,
        strengths=payload.strengths,
        weaknesses=payload.weaknesses,
        wording_issues=payload.wording_issues,
        missing_metrics=payload.missing_metrics,
        suggested_improvements=payload.suggested_improvements,
        is_default=should_be_default,
        is_archived=False,
    )
    db.add(resume)
    db.flush()
    sync_resume_source_items(db, resume=resume)
    if should_be_default:
        db.execute(
            update(Application)
            .where(
                Application.user_id == current_user.id,
                Application.selected_resume_id.is_(None),
            )
            .values(selected_resume_id=resume.id)
        )
    db.commit()
    db.refresh(resume)
    return resume


@router.post("/analyze", response_model=ResumeAnalysisResponse)
async def analyze_resume(
    file: UploadFile = File(...),
    _current_user: User = Depends(get_current_user),
):
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

    return {**analysis, "extracted_text": extracted_text}


@router.post("/save", response_model=ResumeResponse)
def save_resume(
    payload: ResumeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _persist_resume(db=db, current_user=current_user, payload=payload)


@router.post("/upload", response_model=ResumeResponse)
async def upload_and_save_resume(
    file: UploadFile = File(...),
    label: str | None = Form(default=None, max_length=120),
    make_default: bool = Form(default=False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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
    structured_data = ResumeStructuredData.model_validate(
        analysis.get("structured_data") or {}
    )
    fingerprint = resume_fingerprint(
        extracted_text=extracted_text,
        structured_data=structured_data.model_dump(),
    )
    object_key = None
    if settings.object_storage_enabled:
        try:
            object_key = store_resume_pdf(
                user_id=current_user.id,
                pdf_bytes=pdf_bytes,
                source_fingerprint=fingerprint,
            )
        except ObjectStorageOperationError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    payload = ResumeCreate(
        label=label,
        make_default=make_default,
        file_name=file.filename,
        extracted_text=extracted_text,
        structured_data=structured_data,
        summary=analysis["summary"],
        strengths=analysis["strengths"],
        weaknesses=analysis["weaknesses"],
        wording_issues=analysis["wording_issues"],
        missing_metrics=analysis["missing_metrics"],
        suggested_improvements=analysis["suggested_improvements"],
    )
    try:
        return _persist_resume(
            db=db,
            current_user=current_user,
            payload=payload,
            object_storage_key=object_key,
        )
    except Exception:
        if object_key:
            try:
                delete_resume_pdf(object_key=object_key)
            except Exception:
                pass
        raise


@router.get("", response_model=list[ResumeListItem])
def list_resumes(
    include_archived: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(Resume).where(Resume.user_id == current_user.id)
    if not include_archived:
        stmt = stmt.where(Resume.is_archived.is_(False))
    return db.scalars(
        stmt.order_by(Resume.is_default.desc(), Resume.updated_at.desc(), Resume.id.desc())
    ).all()


@router.get("/default", response_model=ResumeResponse)
def get_default_resume(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    resume = _current_default(db, user_id=current_user.id)
    if not resume:
        raise HTTPException(status_code=404, detail="No default resume found.")
    return resume


@router.get("/latest", response_model=ResumeResponse, deprecated=True)
def get_latest_resume_compatibility(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Compatibility alias; callers should use /resume/default or an explicit ID."""
    resume = _current_default(db, user_id=current_user.id)
    if not resume:
        raise HTTPException(status_code=404, detail="No default resume found.")
    return resume


@router.get("/{resume_id}", response_model=ResumeResponse)
def get_resume(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _owned_resume(db, user_id=current_user.id, resume_id=resume_id)


@router.get("/{resume_id}/source-items", response_model=list[ResumeSourceItemResponse])
def list_resume_source_items(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    resume = _owned_resume(db, user_id=current_user.id, resume_id=resume_id)
    return db.scalars(
        select(ResumeSourceItem)
        .where(
            ResumeSourceItem.user_id == current_user.id,
            ResumeSourceItem.resume_id == resume.id,
            ResumeSourceItem.is_active.is_(True),
        )
        .order_by(
            ResumeSourceItem.section,
            ResumeSourceItem.item_type,
            ResumeSourceItem.ordinal,
        )
    ).all()


@router.get("/{resume_id}/source-url", response_model=ResumeSourceUrlResponse)
def get_resume_source_url(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    resume = _owned_resume(db, user_id=current_user.id, resume_id=resume_id)
    if not resume.object_storage_key:
        raise HTTPException(status_code=404, detail="No original upload is stored.")
    try:
        signed = create_signed_resume_url(object_key=resume.object_storage_key)
    except ObjectStorageNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ObjectStorageOperationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {
        "url": signed.url,
        "expires_in_seconds": signed.expires_in_seconds,
    }


@router.put("/{resume_id}/structured-data", response_model=ResumeResponse)
def replace_resume_structured_data(
    resume_id: int,
    payload: ResumeStructuredUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    resume = _owned_resume(db, user_id=current_user.id, resume_id=resume_id)
    structured_data = payload.structured_data.model_dump()
    fingerprint = resume_fingerprint(
        extracted_text=resume.extracted_text,
        structured_data=structured_data,
    )
    if fingerprint == resume.source_fingerprint:
        return resume

    resume.structured_data = structured_data
    resume.source_fingerprint = fingerprint
    resume.version += 1
    sync_resume_source_items(db, resume=resume)
    mark_resume_artifacts_stale(db, resume=resume)
    db.commit()
    db.refresh(resume)
    return resume


@router.patch("/{resume_id}", response_model=ResumeResponse)
def update_resume(
    resume_id: int,
    payload: ResumeUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    resume = _owned_resume(db, user_id=current_user.id, resume_id=resume_id)
    values = payload.model_dump(exclude_unset=True)

    if "label" in values:
        resume.label = values["label"]

    target_archived = values.get("is_archived", resume.is_archived)
    if values.get("is_default") and target_archived:
        raise HTTPException(status_code=409, detail="An archived resume cannot be the default.")

    if target_archived and not resume.is_archived:
        was_default = resume.is_default
        resume.is_archived = True
        resume.is_default = False
        db.flush()
        replacement = (
            _choose_replacement_default(
                db, user_id=current_user.id, exclude_resume_id=resume.id
            )
            if was_default
            else _current_default(db, user_id=current_user.id)
        )
        _select_resume_for_applications(
            db,
            user_id=current_user.id,
            old_resume_id=resume.id,
            replacement_resume_id=replacement.id if replacement else None,
        )
    elif not target_archived and resume.is_archived:
        resume.is_archived = False
        if _current_default(db, user_id=current_user.id) is None:
            resume.is_default = True

    if values.get("is_default"):
        db.execute(
            update(Resume)
            .where(Resume.user_id == current_user.id, Resume.id != resume.id)
            .values(is_default=False)
        )
        resume.is_default = True
        resume.is_archived = False

    db.commit()
    db.refresh(resume)
    return resume


@router.delete("/{resume_id}")
def delete_resume(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    resume = _owned_resume(db, user_id=current_user.id, resume_id=resume_id)
    if resume.object_storage_key:
        try:
            delete_resume_pdf(object_key=resume.object_storage_key)
        except ObjectStorageNotConfigured as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except ObjectStorageOperationError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
    source_item_ids = db.scalars(
        select(ResumeSourceItem.id).where(
            ResumeSourceItem.user_id == current_user.id,
            ResumeSourceItem.resume_id == resume.id,
        )
    ).all()
    if source_item_ids:
        db.execute(
            update(ProjectEvidence)
            .where(
                ProjectEvidence.user_id == current_user.id,
                ProjectEvidence.resume_source_item_id.in_(source_item_ids),
            )
            .values(resume_source_item_id=None)
        )
    replacement = _current_default(db, user_id=current_user.id)
    if replacement and replacement.id == resume.id:
        resume.is_default = False
        db.flush()
        replacement = _choose_replacement_default(
            db, user_id=current_user.id, exclude_resume_id=resume.id
        )

    _select_resume_for_applications(
        db,
        user_id=current_user.id,
        old_resume_id=resume.id,
        replacement_resume_id=replacement.id if replacement else None,
    )
    db.delete(resume)
    db.commit()
    return {"ok": True}
