import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.application_full_resume_draft import ApplicationFullResumeDraft
from app.models.application_tailored_resume import ApplicationTailoredResume
from app.models.project_evidence import ProjectEvidence
from app.models.resume_source_item import ResumeSourceItem
from app.models.user import User
from app.schemas.project_evidence import (
    ConfirmSuggestedMetricRequest,
    ConvertResumeSourceRequest,
    ProjectEvidenceCreate,
    ProjectEvidenceResponse,
    ProjectEvidenceUpdate,
)
from app.services.retrieval_service import rebuild_project_evidence_chunks_for_project
from app.services.source_service import content_fingerprint

router = APIRouter(prefix="/project-evidence", tags=["project-evidence"])
logger = logging.getLogger(__name__)


def _owned_evidence(db: Session, *, user_id: UUID, evidence_id: int) -> ProjectEvidence:
    evidence = db.scalar(
        select(ProjectEvidence).where(
            ProjectEvidence.id == evidence_id,
            ProjectEvidence.user_id == user_id,
        )
    )
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found.")
    return evidence


def _fingerprint_values(values: dict) -> str:
    fields = (
        "title",
        "category",
        "description",
        "skills",
        "keywords",
        "bullet_bank",
        "outcome",
        "start_date",
        "end_date",
        "links",
        "verified_metrics",
    )
    return content_fingerprint({field: values.get(field) for field in fields})


def _evidence_values(evidence: ProjectEvidence) -> dict:
    return {
        "title": evidence.title,
        "category": evidence.category,
        "description": evidence.description,
        "skills": evidence.skills or [],
        "keywords": evidence.keywords or [],
        "bullet_bank": evidence.bullet_bank or [],
        "outcome": evidence.outcome,
        "start_date": evidence.start_date,
        "end_date": evidence.end_date,
        "links": evidence.links or [],
        "verified_metrics": evidence.verified_metrics or [],
    }


def _mark_evidence_dependents_stale(db: Session, *, user_id: UUID) -> None:
    for model in (ApplicationTailoredResume, ApplicationFullResumeDraft):
        db.query(model).filter(model.user_id == user_id).update(
            {"is_stale": True}, synchronize_session=False
        )


def _ingest_evidence(
    db: Session,
    *,
    evidence_id: int,
    user_id: UUID,
) -> ProjectEvidence:
    evidence = _owned_evidence(db, user_id=user_id, evidence_id=evidence_id)
    evidence.ingestion_status = "pending"
    evidence.ingestion_error = None
    db.commit()

    try:
        evidence = _owned_evidence(db, user_id=user_id, evidence_id=evidence_id)
        rebuild_project_evidence_chunks_for_project(db=db, project=evidence)
        evidence.ingestion_status = "ready"
        evidence.ingestion_error = None
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Evidence ingestion failed", extra={"evidence_id": evidence_id})
        evidence = _owned_evidence(db, user_id=user_id, evidence_id=evidence_id)
        evidence.ingestion_status = "failed"
        evidence.ingestion_error = "Embedding generation failed. Retry ingestion."
        db.commit()

    db.refresh(evidence)
    return evidence


@router.post("", response_model=ProjectEvidenceResponse)
def create_project_evidence(
    payload: ProjectEvidenceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    values = payload.model_dump(mode="json", exclude={"resume_source_item_id"})
    source_item_id = payload.resume_source_item_id
    if source_item_id is not None:
        source_item = db.scalar(
            select(ResumeSourceItem).where(
                ResumeSourceItem.id == source_item_id,
                ResumeSourceItem.user_id == current_user.id,
                ResumeSourceItem.is_active.is_(True),
            )
        )
        if not source_item:
            raise HTTPException(status_code=404, detail="Resume source item not found.")

    project = ProjectEvidence(
        user_id=current_user.id,
        resume_source_item_id=source_item_id,
        ai_suggested_metrics=[],
        version=1,
        content_fingerprint=_fingerprint_values(values),
        ingestion_status="pending",
        **values,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return _ingest_evidence(
        db, evidence_id=project.id, user_id=current_user.id
    )


@router.get("", response_model=list[ProjectEvidenceResponse])
def list_project_evidence(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.scalars(
        select(ProjectEvidence)
        .where(ProjectEvidence.user_id == current_user.id)
        .order_by(ProjectEvidence.updated_at.desc(), ProjectEvidence.id.desc())
    ).all()


@router.get("/{evidence_id}", response_model=ProjectEvidenceResponse)
def get_project_evidence(
    evidence_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _owned_evidence(db, user_id=current_user.id, evidence_id=evidence_id)


@router.patch("/{evidence_id}", response_model=ProjectEvidenceResponse)
def update_project_evidence(
    evidence_id: int,
    payload: ProjectEvidenceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    evidence = _owned_evidence(db, user_id=current_user.id, evidence_id=evidence_id)
    changes = payload.model_dump(exclude_unset=True, mode="json")
    for key, value in changes.items():
        setattr(evidence, key, value)

    fingerprint = _fingerprint_values(_evidence_values(evidence))
    if fingerprint == evidence.content_fingerprint:
        return evidence

    evidence.version += 1
    evidence.content_fingerprint = fingerprint
    evidence.ingestion_status = "pending"
    evidence.ingestion_error = None
    _mark_evidence_dependents_stale(db, user_id=current_user.id)
    db.commit()
    return _ingest_evidence(db, evidence_id=evidence.id, user_id=current_user.id)


@router.delete("/{evidence_id}")
def delete_project_evidence(
    evidence_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    evidence = _owned_evidence(db, user_id=current_user.id, evidence_id=evidence_id)
    _mark_evidence_dependents_stale(db, user_id=current_user.id)
    db.delete(evidence)
    db.commit()
    return {"ok": True}


@router.post("/{evidence_id}/retry", response_model=ProjectEvidenceResponse)
def retry_project_evidence_ingestion(
    evidence_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _owned_evidence(db, user_id=current_user.id, evidence_id=evidence_id)
    return _ingest_evidence(db, evidence_id=evidence_id, user_id=current_user.id)


@router.post("/{evidence_id}/confirm-metric", response_model=ProjectEvidenceResponse)
def confirm_suggested_metric(
    evidence_id: int,
    payload: ConfirmSuggestedMetricRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    evidence = _owned_evidence(db, user_id=current_user.id, evidence_id=evidence_id)
    suggestions = list(evidence.ai_suggested_metrics or [])
    if payload.suggestion_index >= len(suggestions):
        raise HTTPException(status_code=404, detail="Metric suggestion not found.")
    metric = suggestions.pop(payload.suggestion_index)
    evidence.ai_suggested_metrics = suggestions
    evidence.verified_metrics = [*(evidence.verified_metrics or []), metric]
    evidence.version += 1
    evidence.content_fingerprint = _fingerprint_values(_evidence_values(evidence))
    _mark_evidence_dependents_stale(db, user_id=current_user.id)
    db.commit()
    return _ingest_evidence(db, evidence_id=evidence.id, user_id=current_user.id)


@router.post(
    "/from-resume-source/{source_item_id}",
    response_model=ProjectEvidenceResponse,
)
def convert_resume_source_to_evidence(
    source_item_id: UUID,
    payload: ConvertResumeSourceRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    source_item = db.scalar(
        select(ResumeSourceItem).where(
            ResumeSourceItem.id == source_item_id,
            ResumeSourceItem.user_id == current_user.id,
            ResumeSourceItem.is_active.is_(True),
        )
    )
    if not source_item:
        raise HTTPException(status_code=404, detail="Resume source item not found.")

    create_payload = ProjectEvidenceCreate(
        title=payload.title or source_item.title or "Resume evidence",
        category=payload.category,
        description=source_item.content,
        skills=payload.skills,
        keywords=payload.skills,
        bullet_bank=[source_item.content] if source_item.item_type == "bullet" else [],
        outcome=payload.outcome,
        links=payload.links,
        verified_metrics=payload.verified_metrics,
        resume_source_item_id=source_item.id,
    )
    return create_project_evidence(create_payload, current_user, db)
