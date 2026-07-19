from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.enums import DiscoveryActionState, JobRecency, JobSort
from app.models.application import Application
from app.models.discovered_job import DiscoveredJob, JobSourcePosting
from app.models.job_discovery_action import JobDiscoveryAction
from app.models.job_search import JobSearch
from app.models.resume import Resume
from app.models.user import User
from app.schemas.job_discovery import (
    ConvertToApplicationRequest,
    ConvertToApplicationResponse,
    DiscoveryCatalogStatusResponse,
    DiscoveryActionRequest,
    DiscoveryActionResponse,
    DiscoveryFeedResponse,
    DiscoveryJobResponse,
    JobSearchCreate,
    JobSearchResponse,
    JobSearchUpdate,
    JobSourceResponse,
)
from app.services.job_discovery_service import build_discovery_feed, freshness_label
from app.services.job_connectors import configured_connectors


router = APIRouter(prefix="/job-discovery", tags=["job-discovery"])


@router.get("/status", response_model=DiscoveryCatalogStatusResponse)
def discovery_catalog_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    del current_user
    connectors = configured_connectors()
    source_names = sorted({connector.source_name for connector in connectors})
    return DiscoveryCatalogStatusResponse(
        configured_connector_count=len(connectors),
        configured_sources=source_names,
        active_job_count=db.scalar(
            select(func.count(DiscoveredJob.id)).where(
                DiscoveredJob.verification_status == "active"
            )
        ) or 0,
        active_source_count=db.scalar(
            select(func.count(JobSourcePosting.id)).where(
                JobSourcePosting.verification_status == "active"
            )
        ) or 0,
        last_verified_at=db.scalar(select(func.max(JobSourcePosting.last_verified_at))),
    )


def _owned_search(db: Session, *, search_id: UUID, user_id) -> JobSearch:
    search = db.scalar(
        select(JobSearch).where(
            JobSearch.id == search_id,
            JobSearch.user_id == user_id,
        )
    )
    if search is None:
        raise HTTPException(status_code=404, detail="Saved search not found")
    return search


def _active_owned_resume(db: Session, *, resume_id: int, user_id) -> Resume:
    resume = db.scalar(
        select(Resume).where(
            Resume.id == resume_id,
            Resume.user_id == user_id,
            Resume.is_archived.is_(False),
        )
    )
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")
    return resume


def _default_resume_id(db: Session, *, user_id) -> int | None:
    return db.scalar(
        select(Resume.id).where(
            Resume.user_id == user_id,
            Resume.is_default.is_(True),
            Resume.is_archived.is_(False),
        )
    )


@router.get("/searches", response_model=list[JobSearchResponse])
def list_searches(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.scalars(
        select(JobSearch)
        .where(JobSearch.user_id == current_user.id)
        .order_by(JobSearch.updated_at.desc())
    ).all()


@router.post("/searches", response_model=JobSearchResponse)
def create_search(
    payload: JobSearchCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    values = payload.model_dump(mode="json")
    resume_id = values.pop("resume_id", None)
    if resume_id is None:
        resume_id = _default_resume_id(db, user_id=current_user.id)
    else:
        _active_owned_resume(db, resume_id=resume_id, user_id=current_user.id)
    search = JobSearch(user_id=current_user.id, resume_id=resume_id, **values)
    db.add(search)
    db.commit()
    db.refresh(search)
    return search


@router.get("/searches/{search_id}", response_model=JobSearchResponse)
def get_search(
    search_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _owned_search(db, search_id=search_id, user_id=current_user.id)


@router.patch("/searches/{search_id}", response_model=JobSearchResponse)
def update_search(
    search_id: UUID,
    payload: JobSearchUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    search = _owned_search(db, search_id=search_id, user_id=current_user.id)
    values = payload.model_dump(exclude_unset=True, mode="json")
    if "resume_id" in values and values["resume_id"] is not None:
        _active_owned_resume(db, resume_id=values["resume_id"], user_id=current_user.id)

    candidate = {
        field: getattr(search, field) for field in JobSearchCreate.model_fields
    }
    candidate.update(values)
    try:
        validated = JobSearchCreate.model_validate(candidate).model_dump(mode="json")
    except ValidationError as exc:
        raise HTTPException(
            status_code=422, detail="Saved search update is invalid."
        ) from exc
    for key, value in validated.items():
        setattr(search, key, value)
    db.commit()
    db.refresh(search)
    return search


@router.delete("/searches/{search_id}")
def delete_search(
    search_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    search = _owned_search(db, search_id=search_id, user_id=current_user.id)
    db.delete(search)
    db.commit()
    return {"ok": True}


@router.get("/feed", response_model=DiscoveryFeedResponse)
def discovery_feed(
    search_id: UUID,
    recency: JobRecency | None = None,
    sort: JobSort = JobSort.RECOMMENDED,
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    search = _owned_search(db, search_id=search_id, user_id=current_user.id)
    selected_recency = recency or JobRecency(search.recency)
    ranked = build_discovery_feed(
        db,
        search=search,
        user_id=current_user.id,
        recency=selected_recency,
        sort=sort,
        limit=limit,
    )
    return DiscoveryFeedResponse(
        search_id=search.id,
        recency=selected_recency,
        sort=sort,
        items=[
            DiscoveryJobResponse(
                id=item.job.id,
                company_name=item.job.company_name,
                title=item.job.title,
                location=item.job.location,
                workplace_type=item.job.workplace_type,
                employment_type=item.job.employment_type,
                seniority_level=item.job.seniority_level,
                industry=item.job.industry,
                salary_min=item.job.salary_min,
                salary_max=item.job.salary_max,
                salary_currency=item.job.salary_currency,
                description=item.job.description,
                source_posted_at=item.job.source_posted_at,
                freshness_label=freshness_label(item.job.source_posted_at),
                preference_match_score=item.preference_match_score,
                resume_match_score=item.resume_match_score,
                recommended_score=item.recommended_score,
                match_reasons=item.match_reasons,
                action_state=item.action_state,
                sources=[
                    JobSourceResponse.model_validate(source) for source in item.sources
                ],
            )
            for item in ranked
        ],
    )


@router.put(
    "/jobs/{job_id}/action",
    response_model=DiscoveryActionResponse,
)
def set_job_action(
    job_id: UUID,
    payload: DiscoveryActionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.state == DiscoveryActionState.CONVERTED:
        raise HTTPException(
            status_code=422,
            detail="Use the convert endpoint to create an application.",
        )
    job = db.scalar(
        select(DiscoveredJob).where(
            DiscoveredJob.id == job_id,
            DiscoveredJob.verification_status == "active",
        )
    )
    if job is None:
        raise HTTPException(status_code=404, detail="Discovered job not found")
    action = db.scalar(
        select(JobDiscoveryAction).where(
            JobDiscoveryAction.user_id == current_user.id,
            JobDiscoveryAction.discovered_job_id == job_id,
        )
    )
    if action is None:
        action = JobDiscoveryAction(
            user_id=current_user.id,
            discovered_job_id=job_id,
            state=payload.state.value,
        )
        db.add(action)
    else:
        if action.state == DiscoveryActionState.CONVERTED.value:
            raise HTTPException(
                status_code=409,
                detail="Converted jobs stay linked to their application.",
            )
        action.state = payload.state.value
        action.application_id = None
    db.commit()
    return DiscoveryActionResponse(
        discovered_job_id=job_id,
        state=DiscoveryActionState(action.state),
        application_id=action.application_id,
    )


@router.delete("/jobs/{job_id}/action")
def clear_job_action(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    action = db.scalar(
        select(JobDiscoveryAction).where(
            JobDiscoveryAction.user_id == current_user.id,
            JobDiscoveryAction.discovered_job_id == job_id,
        )
    )
    if action is None:
        raise HTTPException(status_code=404, detail="Job action not found")
    if action.state == DiscoveryActionState.CONVERTED.value:
        raise HTTPException(
            status_code=409,
            detail="Converted jobs stay linked to their application.",
        )
    db.delete(action)
    db.commit()
    return {"ok": True}


@router.post(
    "/jobs/{job_id}/convert",
    response_model=ConvertToApplicationResponse,
)
def convert_to_application(
    job_id: UUID,
    payload: ConvertToApplicationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    search = _owned_search(db, search_id=payload.search_id, user_id=current_user.id)
    job = db.scalar(
        select(DiscoveredJob).where(
            DiscoveredJob.id == job_id,
            DiscoveredJob.verification_status == "active",
        )
    )
    if job is None:
        raise HTTPException(status_code=404, detail="Discovered job not found")
    action = db.scalar(
        select(JobDiscoveryAction).where(
            JobDiscoveryAction.user_id == current_user.id,
            JobDiscoveryAction.discovered_job_id == job_id,
        )
    )
    if action and action.state == "converted" and action.application_id:
        return ConvertToApplicationResponse(
            discovered_job_id=job_id,
            state=DiscoveryActionState.CONVERTED,
            application_id=action.application_id,
        )
    source = db.scalar(
        select(JobSourcePosting)
        .where(
            JobSourcePosting.discovered_job_id == job_id,
            JobSourcePosting.verification_status == "active",
        )
        .order_by(JobSourcePosting.first_seen_at.asc())
    )
    if source is None:
        raise HTTPException(status_code=409, detail="Job has no active source")
    application = Application(
        user_id=current_user.id,
        selected_resume_id=search.resume_id,
        company=job.company_name,
        role_title=job.title,
        status="saved",
        location=job.location,
        job_url=source.canonical_url,
        job_description=job.description,
    )
    db.add(application)
    db.flush()
    if action is None:
        action = JobDiscoveryAction(
            user_id=current_user.id,
            discovered_job_id=job_id,
            state="converted",
            application_id=application.id,
        )
        db.add(action)
    else:
        action.state = "converted"
        action.application_id = application.id
    db.commit()
    return ConvertToApplicationResponse(
        discovered_job_id=job_id,
        state=DiscoveryActionState.CONVERTED,
        application_id=application.id,
    )
