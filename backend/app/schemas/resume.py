from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


class ResumeContact(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    links: list[str] = Field(default_factory=list)


class ResumeStructuredEntry(BaseModel):
    title: str
    subtitle: str | None = None
    location: str | None = None
    date_range: str | None = None
    bullets: list[str] = Field(default_factory=list)


class ResumeStructuredData(BaseModel):
    contact: ResumeContact = Field(default_factory=ResumeContact)
    education: list[ResumeStructuredEntry] = Field(default_factory=list)
    experience: list[ResumeStructuredEntry] = Field(default_factory=list)
    projects: list[ResumeStructuredEntry] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    other: list[ResumeStructuredEntry] = Field(default_factory=list)


class ResumeAnalysisResponse(BaseModel):
    summary: str
    strengths: list[str]
    weaknesses: list[str]
    wording_issues: list[str]
    missing_metrics: list[str]
    suggested_improvements: list[str]
    extracted_text: str
    structured_data: ResumeStructuredData = Field(default_factory=ResumeStructuredData)


class ResumeCreate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=120)
    make_default: bool = False
    file_name: str = Field(min_length=1, max_length=255)
    extracted_text: str = Field(min_length=1, max_length=100_000)
    structured_data: ResumeStructuredData = Field(default_factory=ResumeStructuredData)
    summary: str = Field(min_length=1, max_length=20_000)
    strengths: list[str]
    weaknesses: list[str]
    wording_issues: list[str]
    missing_metrics: list[str]
    suggested_improvements: list[str]

    @field_validator("label", mode="before")
    @classmethod
    def strip_label(cls, value):
        if isinstance(value, str):
            return value.strip()
        return value


class ResumeUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=120)
    is_default: bool | None = None
    is_archived: bool | None = None

    @field_validator("label", mode="before")
    @classmethod
    def strip_update_label(cls, value):
        if isinstance(value, str):
            return value.strip()
        return value

    @model_validator(mode="after")
    def default_can_only_be_enabled(self):
        if "is_default" in self.model_fields_set and self.is_default is not True:
            raise ValueError("is_default can only be set to true; choose another default instead")
        return self


class ResumeListItem(BaseModel):
    id: int
    label: str
    file_name: str
    is_default: bool
    is_archived: bool
    version: int
    source_fingerprint: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ResumeResponse(BaseModel):
    id: int
    label: str
    file_name: str
    extracted_text: str
    structured_data: ResumeStructuredData
    source_fingerprint: str
    version: int
    has_original_upload: bool
    summary: str
    strengths: list[str]
    weaknesses: list[str]
    wording_issues: list[str]
    missing_metrics: list[str]
    suggested_improvements: list[str]
    is_default: bool
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ResumeStructuredUpdate(BaseModel):
    structured_data: ResumeStructuredData


class ResumeSourceItemResponse(BaseModel):
    id: UUID
    resume_id: int
    source_version: int
    section: str
    item_type: str
    title: str | None
    content: str
    ordinal: int
    source_metadata: dict
    is_user_verified: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ResumeSourceUrlResponse(BaseModel):
    url: str
    expires_in_seconds: int
