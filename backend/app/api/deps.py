from collections.abc import Generator
from uuid import UUID

from fastapi import Depends, HTTPException
from sqlalchemy import event, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth import AccessTokenClaims, get_token_claims
from app.core.database import SessionLocal
from app.models.user import User


LEGACY_EXTERNAL_SUBJECT = "legacy|rolepilot-owner"


@event.listens_for(Session, "after_begin")
def restore_auth_context_after_transaction_boundary(
    session: Session, transaction, connection
) -> None:
    external_subject = session.info.get("auth_external_subject")
    user_id = session.info.get("auth_user_id")
    if external_subject:
        connection.execute(
            text("SELECT set_config('app.current_subject', :subject, true)"),
            {"subject": external_subject},
        )
    if user_id:
        connection.execute(
            text("SELECT set_config('app.current_user_id', :user_id, true)"),
            {"user_id": str(user_id)},
        )


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _set_auth_context(
    db: Session, *, external_subject: str, user_id: UUID | None = None
) -> None:
    db.info["auth_external_subject"] = external_subject
    if user_id is not None:
        db.info["auth_user_id"] = user_id
    db.execute(
        text("SELECT set_config('app.current_subject', :subject, true)"),
        {"subject": external_subject},
    )
    if user_id is not None:
        db.execute(
            text("SELECT set_config('app.current_user_id', :user_id, true)"),
            {"user_id": str(user_id)},
        )


def get_current_user(
    claims: AccessTokenClaims = Depends(get_token_claims),
    db: Session = Depends(get_db),
) -> User:
    if claims.sub == LEGACY_EXTERNAL_SUBJECT:
        raise HTTPException(status_code=403, detail="This identity cannot sign in.")

    _set_auth_context(db, external_subject=claims.sub)
    user = db.scalar(select(User).where(User.external_subject == claims.sub))

    if user is None:
        user = User(
            external_subject=claims.sub,
            email=claims.email,
            name=claims.name,
        )
        db.add(user)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            _set_auth_context(db, external_subject=claims.sub)
            user = db.scalar(select(User).where(User.external_subject == claims.sub))
            if user is None:
                raise
        else:
            db.refresh(user)
    else:
        changed = False
        if claims.email and claims.email != user.email:
            user.email = claims.email
            changed = True
        if claims.name and claims.name != user.name:
            user.name = claims.name
            changed = True
        if changed:
            db.commit()
            db.refresh(user)

    _set_auth_context(db, external_subject=claims.sub, user_id=user.id)
    return user


def get_owned_or_404(
    db: Session,
    model: type,
    resource_id: int,
    user_id: UUID,
    detail: str,
):
    resource = db.scalar(
        select(model).where(model.id == resource_id, model.user_id == user_id)
    )
    if resource is None:
        raise HTTPException(status_code=404, detail=detail)
    return resource
