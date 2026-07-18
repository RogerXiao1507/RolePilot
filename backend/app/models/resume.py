from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Resume(Base):
    __tablename__ = "resumes"
    __table_args__ = (
        UniqueConstraint("id", "user_id", name="uq_resumes_id_user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_name: Mapped[str] = mapped_column(String, nullable=False)
    extracted_text: Mapped[str] = mapped_column(Text, nullable=False)

    summary: Mapped[str] = mapped_column(Text, nullable=False)
    strengths: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    weaknesses: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    wording_issues: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    missing_metrics: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    suggested_improvements: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
