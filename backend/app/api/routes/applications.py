from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.api.deps import get_db
from app.models.application import Application
from app.schemas.application import ApplicationCreate, ApplicationOut, ApplicationUpdate

router = APIRouter(prefix="/applications", tags=["applications"])


@router.get("", response_model=list[ApplicationOut])
def list_applications(db: Session = Depends(get_db)):
    stmt = select(Application).order_by(Application.created_at.desc())
    applications = db.scalars(stmt).all()
    return applications


@router.post("", response_model=ApplicationOut)
def create_application(payload: ApplicationCreate, db: Session = Depends(get_db)):
    application = Application(**payload.model_dump())
    db.add(application)
    db.commit()
    db.refresh(application)
    return application


@router.get("/{application_id}", response_model=ApplicationOut)
def get_application(application_id: int, db: Session = Depends(get_db)):
    stmt = select(Application).where(Application.id == application_id)
    application = db.scalar(stmt)

    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    return application


@router.patch("/{application_id}", response_model=ApplicationOut)
def update_application(application_id: int, payload: ApplicationUpdate, db: Session = Depends(get_db)):
    stmt = select(Application).where(Application.id == application_id)
    application = db.scalar(stmt)

    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(application, key, value)

    db.commit()
    db.refresh(application)
    return application


@router.delete("/{application_id}")
def delete_application(application_id: int, db: Session = Depends(get_db)):
    stmt = select(Application).where(Application.id == application_id)
    application = db.scalar(stmt)

    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    db.delete(application)
    db.commit()
    return {"ok": True}