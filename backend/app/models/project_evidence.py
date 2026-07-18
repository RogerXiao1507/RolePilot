from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ProjectEvidence(Base):
    __tablename__ = "project_evidence"
    __table_args__ = (
        UniqueConstraint("id", "user_id", name="uq_project_evidence_id_user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    skills: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    keywords: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    bullet_bank: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
