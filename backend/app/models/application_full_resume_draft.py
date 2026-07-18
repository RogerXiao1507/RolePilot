from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, ForeignKeyConstraint, Integer, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ApplicationFullResumeDraft(Base):
    __tablename__ = "application_full_resume_drafts"
    __table_args__ = (
        ForeignKeyConstraint(
            ["application_id", "user_id"],
            ["applications.id", "applications.user_id"],
            name="fk_full_drafts_application_owner",
            ondelete="CASCADE",
            deferrable=True,
            initially="DEFERRED",
        ),
        ForeignKeyConstraint(
            ["resume_id", "user_id"],
            ["resumes.id", "resumes.user_id"],
            name="fk_full_drafts_resume_owner",
            ondelete="CASCADE",
            deferrable=True,
            initially="DEFERRED",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    application_id: Mapped[int] = mapped_column(
        nullable=False,
        unique=True,
        index=True,
    )

    resume_id: Mapped[int] = mapped_column(
        nullable=False,
        index=True,
    )

    draft_data: Mapped[dict] = mapped_column(JSONB, nullable=False)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    application = relationship("Application")
    resume = relationship("Resume", overlaps="application")
