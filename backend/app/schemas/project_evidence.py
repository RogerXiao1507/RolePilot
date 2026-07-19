from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.core.enums import EvidenceIngestionStatus


class EvidenceMetric(BaseModel):
    label: str = Field(min_length=1, max_length=120)
    value: str = Field(min_length=1, max_length=120)
    context: str | None = Field(default=None, max_length=500)


class ProjectEvidenceFields(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    category: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=20_000)
    skills: list[str] = Field(default_factory=list, max_length=100)
    keywords: list[str] = Field(default_factory=list, max_length=100)
    bullet_bank: list[str] = Field(default_factory=list, max_length=100)
    outcome: str | None = Field(default=None, max_length=5_000)
    start_date: str | None = Field(default=None, max_length=40)
    end_date: str | None = Field(default=None, max_length=40)
    links: list[str] = Field(default_factory=list, max_length=20)
    verified_metrics: list[EvidenceMetric] = Field(default_factory=list, max_length=50)

    @field_validator("title", "category", "description", "outcome", mode="before")
    @classmethod
    def strip_text(cls, value):
        return value.strip() if isinstance(value, str) else value


class ProjectEvidenceCreate(ProjectEvidenceFields):
    resume_source_item_id: UUID | None = None


class ProjectEvidenceUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=240)
    category: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = Field(default=None, min_length=1, max_length=20_000)
    skills: list[str] | None = Field(default=None, max_length=100)
    keywords: list[str] | None = Field(default=None, max_length=100)
    bullet_bank: list[str] | None = Field(default=None, max_length=100)
    outcome: str | None = Field(default=None, max_length=5_000)
    start_date: str | None = Field(default=None, max_length=40)
    end_date: str | None = Field(default=None, max_length=40)
    links: list[str] | None = Field(default=None, max_length=20)
    verified_metrics: list[EvidenceMetric] | None = Field(default=None, max_length=50)


class ConfirmSuggestedMetricRequest(BaseModel):
    suggestion_index: int = Field(ge=0)


class ConvertResumeSourceRequest(BaseModel):
    title: str | None = Field(default=None, max_length=240)
    category: str = Field(default="resume", min_length=1, max_length=80)
    outcome: str | None = Field(default=None, max_length=5_000)
    skills: list[str] = Field(default_factory=list, max_length=100)
    links: list[str] = Field(default_factory=list, max_length=20)
    verified_metrics: list[EvidenceMetric] = Field(default_factory=list, max_length=50)


class ProjectEvidenceResponse(BaseModel):
    id: int
    title: str
    category: str
    description: str
    skills: list[str]
    keywords: list[str]
    bullet_bank: list[str]
    outcome: str | None
    start_date: str | None
    end_date: str | None
    links: list[str]
    verified_metrics: list[EvidenceMetric]
    ai_suggested_metrics: list[EvidenceMetric]
    version: int
    content_fingerprint: str
    ingestion_status: EvidenceIngestionStatus
    ingestion_error: str | None
    resume_source_item_id: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
