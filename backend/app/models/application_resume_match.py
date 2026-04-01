from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ApplicationResumeMatch(Base):
    __tablename__ = "application_resume_matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    resume_id: Mapped[int] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

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
    resume = relationship("Resume")