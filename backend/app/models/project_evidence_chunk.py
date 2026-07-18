from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, ForeignKeyConstraint, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from app.core.database import Base


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
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    project_evidence = relationship("ProjectEvidence")
