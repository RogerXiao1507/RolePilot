from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, String, Text, DateTime, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON
from app.core.database import Base
from app.core.enums import ApplicationStatus


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (
        CheckConstraint(
            "status IN ('saved', 'applied', 'interview', 'offer', 'rejected')",
            name="ck_applications_status",
        ),
        UniqueConstraint("id", "user_id", name="uq_applications_id_user_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    company: Mapped[str] = mapped_column(String(200), nullable=False)
    role_title: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[ApplicationStatus] = mapped_column(
        String(32),
        nullable=False,
        default=ApplicationStatus.SAVED,
        server_default=ApplicationStatus.SAVED.value,
    )
    location: Mapped[str | None] = mapped_column(String(300), nullable=True)
    job_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    job_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    required_skills: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    preferred_skills: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    keywords: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    next_steps: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
