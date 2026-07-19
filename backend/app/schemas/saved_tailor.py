from datetime import datetime
from pydantic import BaseModel, Field

from app.schemas.tailor import SourceCitation


class SavedTailoredBullet(BaseModel):
    section: str
    source_title: str
    original_bullet: str
    tailored_bullet: str
    evidence_used: list[str]
    citations: list[SourceCitation] = Field(default_factory=list)


class ApplicationTailoredResumeCreate(BaseModel):
    application_id: int
    resume_id: int
    tailored_summary: str
    tailored_skills: list[str]
    tailored_bullets: list[SavedTailoredBullet]
    tailoring_notes: list[str]


class ApplicationTailoredResumeResponse(BaseModel):
    id: int
    application_id: int
    resume_id: int
    resume_version: int
    is_stale: bool
    tailored_summary: str
    tailored_skills: list[str]
    tailored_bullets: list[SavedTailoredBullet]
    tailoring_notes: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
