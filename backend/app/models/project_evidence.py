from uuid import UUID
import hashlib

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _default_evidence_fingerprint(context) -> str:
    values = context.get_current_parameters()
    text = "|".join(
        str(values.get(field) or "")
        for field in ("title", "category", "description", "skills", "keywords", "bullet_bank")
    )
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class ProjectEvidence(Base):
    __tablename__ = "project_evidence"
    __table_args__ = (
        UniqueConstraint("id", "user_id", name="uq_project_evidence_id_user_id"),
        CheckConstraint(
            "ingestion_status IN ('pending', 'ready', 'failed')",
            name="ck_project_evidence_ingestion_status",
        ),
        ForeignKeyConstraint(
            ["resume_source_item_id", "user_id"],
            ["resume_source_items.id", "resume_source_items.user_id"],
            name="fk_project_evidence_resume_source_owner",
            ondelete="RESTRICT",
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
    title: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    skills: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    keywords: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    bullet_bank: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_date: Mapped[str | None] = mapped_column(String(40), nullable=True)
    end_date: Mapped[str | None] = mapped_column(String(40), nullable=True)
    links: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    verified_metrics: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, default=list)
    ai_suggested_metrics: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, default=list)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    content_fingerprint: Mapped[str] = mapped_column(
        String(64), nullable=False, default=_default_evidence_fingerprint
    )
    ingestion_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="ready", server_default="pending"
    )
    ingestion_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    resume_source_item_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True
    )

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
