from uuid import UUID
import hashlib

from sqlalchemy import DateTime, ForeignKey, ForeignKeyConstraint, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from app.core.database import Base


def _default_chunk_hash(context) -> str:
    text_value = str(context.get_current_parameters().get("chunk_text") or "")
    return hashlib.sha256(text_value.encode("utf-8")).hexdigest()


class ProjectEvidenceChunk(Base):
    __tablename__ = "project_evidence_chunks"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_evidence_id", "user_id"],
            ["project_evidence.id", "project_evidence.user_id"],
            name="fk_evidence_chunks_evidence_owner",
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
    project_evidence_id: Mapped[int] = mapped_column(
        nullable=False,
        index=True,
    )
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_type: Mapped[str] = mapped_column(String, nullable=False)
    source_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    section: Mapped[str] = mapped_column(String(40), nullable=False, default="evidence")
    title: Mapped[str] = mapped_column(String(240), nullable=False, default="Evidence")
    dates: Mapped[str | None] = mapped_column(String(100), nullable=True)
    skills: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    embedding_model: Mapped[str] = mapped_column(
        String(80), nullable=False, default="text-embedding-3-small"
    )
    content_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, default=_default_chunk_hash
    )
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    project_evidence = relationship("ProjectEvidence")
