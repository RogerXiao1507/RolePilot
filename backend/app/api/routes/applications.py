from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.api.deps import get_current_user, get_db
from app.models.application import Application
from app.models.resume import Resume
from app.models.user import User
from app.schemas.application import ApplicationCreate, ApplicationOut, ApplicationUpdate
from app.services.source_service import mark_application_artifacts_stale

router = APIRouter(prefix="/applications", tags=["applications"])


def _active_owned_resume(
    db: Session, *, user_id, resume_id: int
) -> Resume:
    resume = db.scalar(
        select(Resume).where(
            Resume.id == resume_id,
            Resume.user_id == user_id,
            Resume.is_archived.is_(False),
        )
    )
    if not resume:
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


@router.get("", response_model=list[ApplicationOut])
def list_applications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = (
        select(Application)
        .where(Application.user_id == current_user.id)
        .order_by(Application.created_at.desc())
    )
    applications = db.scalars(stmt).all()
    return applications


@router.post("", response_model=ApplicationOut)
def create_application(
    payload: ApplicationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    values = payload.model_dump()
    selected_resume_id = values.pop("selected_resume_id", None)
    if selected_resume_id is not None:
        _active_owned_resume(
            db, user_id=current_user.id, resume_id=selected_resume_id
        )
    else:
        selected_resume_id = _default_resume_id(db, user_id=current_user.id)
    application = Application(
        user_id=current_user.id,
        selected_resume_id=selected_resume_id,
        **values,
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    return application


@router.get("/{application_id}", response_model=ApplicationOut)
def get_application(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(Application).where(
        Application.id == application_id,
        Application.user_id == current_user.id,
    )
    application = db.scalar(stmt)

    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    return application


@router.patch("/{application_id}", response_model=ApplicationOut)
def update_application(
    application_id: int,
    payload: ApplicationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(Application).where(
        Application.id == application_id,
        Application.user_id == current_user.id,
    )
    application = db.scalar(stmt)

    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    values = payload.model_dump(exclude_unset=True)
    if "selected_resume_id" in values and values["selected_resume_id"] is not None:
        _active_owned_resume(
            db,
            user_id=current_user.id,
            resume_id=values["selected_resume_id"],
        )

    if (
        "selected_resume_id" in values
        and values["selected_resume_id"] != application.selected_resume_id
    ):
        mark_application_artifacts_stale(
            db, user_id=current_user.id, application_id=application.id
        )

    for key, value in values.items():
        setattr(application, key, value)

    db.commit()
    db.refresh(application)
    return application


@router.delete("/{application_id}")
def delete_application(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(Application).where(
        Application.id == application_id,
        Application.user_id == current_user.id,
    )
    application = db.scalar(stmt)

    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    db.delete(application)
    db.commit()
    return {"ok": True}
