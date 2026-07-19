from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.enums import ApplicationStatus


ShortText = Field(min_length=1, max_length=200)
OptionalLocation = Field(default=None, max_length=300)
OptionalUrl = Field(default=None, max_length=2048)
OptionalLongText = Field(default=None, max_length=100_000)


class ApplicationFields(BaseModel):
    @field_validator("company", "role_title", "location", mode="before", check_fields=False)
    @classmethod
    def strip_text_fields(cls, value):
        if isinstance(value, str):
            value = value.strip()
        return value


class ApplicationCreate(ApplicationFields):
    selected_resume_id: int | None = Field(default=None, gt=0)
    company: str = ShortText
    role_title: str = ShortText
    status: ApplicationStatus = ApplicationStatus.SAVED
    location: str | None = OptionalLocation
    job_url: str | None = OptionalUrl
    job_description: str | None = OptionalLongText
    ai_summary: str | None = OptionalLongText
    required_skills: list[str] | None = None
    preferred_skills: list[str] | None = None
    keywords: list[str] | None = None
    next_steps: list[str] | None = None


class ApplicationUpdate(ApplicationFields):
    selected_resume_id: int | None = Field(default=None, gt=0)
    company: str | None = Field(default=None, min_length=1, max_length=200)
    role_title: str | None = Field(default=None, min_length=1, max_length=200)
    status: ApplicationStatus | None = None
    location: str | None = OptionalLocation
    job_url: str | None = OptionalUrl
    job_description: str | None = OptionalLongText
    ai_summary: str | None = OptionalLongText
    required_skills: list[str] | None = None
    preferred_skills: list[str] | None = None
    keywords: list[str] | None = None
    next_steps: list[str] | None = None

    @model_validator(mode="after")
    def required_fields_cannot_be_cleared(self):
        for field_name in ("company", "role_title", "status"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class ApplicationOut(BaseModel):
    id: int
    selected_resume_id: int | None
    company: str
    role_title: str
    status: ApplicationStatus
    location: str | None
    job_url: str | None
    job_description: str | None
    ai_summary: str | None
    required_skills: list[str] | None
    preferred_skills: list[str] | None
    keywords: list[str] | None
    next_steps: list[str] | None
    created_at: datetime

    model_config = {"from_attributes": True}
