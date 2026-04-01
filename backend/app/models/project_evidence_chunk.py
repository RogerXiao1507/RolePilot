from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from app.core.database import Base


class ProjectEvidenceChunk(Base):
    __tablename__ = "project_evidence_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_evidence_id: Mapped[int] = mapped_column(
        ForeignKey("project_evidence.id", ondelete="CASCADE"),
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