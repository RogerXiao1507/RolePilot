from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, ForeignKeyConstraint, Integer, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ApplicationResumeMatch(Base):
    __tablename__ = "application_resume_matches"
    __table_args__ = (
        ForeignKeyConstraint(
            ["application_id", "user_id"],
            ["applications.id", "applications.user_id"],
            name="fk_resume_matches_application_owner",
            ondelete="CASCADE",
            deferrable=True,
            initially="DEFERRED",
        ),
        ForeignKeyConstraint(
            ["resume_id", "user_id"],
            ["resumes.id", "resumes.user_id"],
            name="fk_resume_matches_resume_owner",
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
    resume_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_stale: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    overall_match_summary: Mapped[str] = mapped_column(Text, nullable=False)
    matched_skills: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    missing_skills: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    strengths_for_role: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    improvement_areas: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    suggested_resume_changes: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)

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
