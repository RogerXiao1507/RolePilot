from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TailorResumeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    application_id: int = Field(gt=0)
    resume_id: int = Field(gt=0)


class SourceCitation(BaseModel):
    source_type: Literal["resume_item", "evidence"]
    source_id: str
    source_version: int = Field(gt=0)


class TailoredBullet(BaseModel):
    section: str
    source_title: str
    original_bullet: str
    tailored_bullet: str
    evidence_used: list[str]
    citations: list[SourceCitation] = Field(default_factory=list)


class TailorResumeResponse(BaseModel):
    tailored_summary: str
    tailored_skills: list[str]
    tailored_bullets: list[TailoredBullet]
    tailoring_notes: list[str]

class FullTailoredResumeDraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    application_id: int = Field(gt=0)
    resume_id: int = Field(gt=0)


class ExportSavedResumeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    application_id: int = Field(gt=0)
