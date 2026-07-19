from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.enums import (
    DiscoveryActionState,
    JobRecency,
    JobSort,
    NotificationFrequency,
)


class JobSearchFields(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    resume_id: int | None = Field(default=None, gt=0)
    target_titles: list[str] = Field(min_length=1, max_length=20)
    adjacent_titles: list[str] = Field(default_factory=list, max_length=20)
    seniority_levels: list[str] = Field(default_factory=list, max_length=10)
    employment_types: list[str] = Field(default_factory=list, max_length=10)
    locations: list[str] = Field(default_factory=list, max_length=20)
    workplace_types: list[str] = Field(default_factory=list, max_length=5)
    salary_min: int | None = Field(default=None, ge=0)
    salary_max: int | None = Field(default=None, ge=0)
    salary_currency: str = Field(default="USD", min_length=3, max_length=3)
    industries: list[str] = Field(default_factory=list, max_length=20)
    required_keywords: list[str] = Field(default_factory=list, max_length=40)
    excluded_keywords: list[str] = Field(default_factory=list, max_length=40)
    excluded_companies: list[str] = Field(default_factory=list, max_length=40)
    recency: JobRecency = JobRecency.WEEK
    notification_frequency: NotificationFrequency = NotificationFrequency.OFF
    is_active: bool = True

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator(
        "target_titles",
        "adjacent_titles",
        "seniority_levels",
        "employment_types",
        "locations",
        "workplace_types",
        "industries",
        "required_keywords",
        "excluded_keywords",
        "excluded_companies",
        mode="before",
    )
    @classmethod
    def clean_string_lists(cls, value):
        if not isinstance(value, list):
            return value
        result: list[str] = []
        seen: set[str] = set()
        for item in value:
            cleaned = item.strip() if isinstance(item, str) else item
            if not cleaned:
                continue
            if not isinstance(cleaned, str) or len(cleaned) > 120:
                raise ValueError(
                    "Search list values must be strings of at most 120 characters"
                )
            key = cleaned.casefold()
            if key not in seen:
                result.append(cleaned)
                seen.add(key)
        return result

    @field_validator("salary_currency", mode="before")
    @classmethod
    def normalize_currency(cls, value):
        return value.strip().upper() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_salary_range(self):
        if (
            self.salary_min is not None
            and self.salary_max is not None
            and self.salary_min > self.salary_max
        ):
            raise ValueError("salary_min cannot exceed salary_max")
        return self


class JobSearchCreate(JobSearchFields):
    pass


class JobSearchUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    resume_id: int | None = Field(default=None, gt=0)
    target_titles: list[str] | None = Field(default=None, min_length=1, max_length=20)
    adjacent_titles: list[str] | None = Field(default=None, max_length=20)
    seniority_levels: list[str] | None = Field(default=None, max_length=10)
    employment_types: list[str] | None = Field(default=None, max_length=10)
    locations: list[str] | None = Field(default=None, max_length=20)
    workplace_types: list[str] | None = Field(default=None, max_length=5)
    salary_min: int | None = Field(default=None, ge=0)
    salary_max: int | None = Field(default=None, ge=0)
    salary_currency: str | None = Field(default=None, min_length=3, max_length=3)
    industries: list[str] | None = Field(default=None, max_length=20)
    required_keywords: list[str] | None = Field(default=None, max_length=40)
    excluded_keywords: list[str] | None = Field(default=None, max_length=40)
    excluded_companies: list[str] | None = Field(default=None, max_length=40)
    recency: JobRecency | None = None
    notification_frequency: NotificationFrequency | None = None
    is_active: bool | None = None

    _strip_name = field_validator("name", mode="before")(
        JobSearchFields.strip_name.__func__
    )
    _clean_lists = field_validator(
        "target_titles",
        "adjacent_titles",
        "seniority_levels",
        "employment_types",
        "locations",
        "workplace_types",
        "industries",
        "required_keywords",
        "excluded_keywords",
        "excluded_companies",
        mode="before",
    )(JobSearchFields.clean_string_lists.__func__)
    _currency = field_validator("salary_currency", mode="before")(
        JobSearchFields.normalize_currency.__func__
    )

    @model_validator(mode="after")
    def non_nullable_fields_cannot_be_cleared(self):
        non_nullable = (
            "name",
            "target_titles",
            "adjacent_titles",
            "seniority_levels",
            "employment_types",
            "locations",
            "workplace_types",
            "salary_currency",
            "industries",
            "required_keywords",
            "excluded_keywords",
            "excluded_companies",
            "recency",
            "notification_frequency",
            "is_active",
        )
        for field_name in non_nullable:
            if (
                field_name in self.model_fields_set
                and getattr(self, field_name) is None
            ):
                raise ValueError(f"{field_name} cannot be null")
        return self


class JobSearchResponse(JobSearchFields):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class JobSourceResponse(BaseModel):
    source_name: str
    external_job_id: str
    canonical_url: str
    source_posted_at: datetime | None
    source_updated_at: datetime | None
    last_verified_at: datetime
    verification_status: str

    model_config = {"from_attributes": True}


class DiscoveryJobResponse(BaseModel):
    id: UUID
    company_name: str
    title: str
    location: str | None
    workplace_type: str | None
    employment_type: str | None
    seniority_level: str | None
    industry: str | None
    salary_min: int | None
    salary_max: int | None
    salary_currency: str | None
    description: str
    source_posted_at: datetime | None
    freshness_label: str
    preference_match_score: float
    resume_match_score: float | None
    recommended_score: float
    match_reasons: list[str]
    action_state: DiscoveryActionState | None
    sources: list[JobSourceResponse]


class DiscoveryFeedResponse(BaseModel):
    search_id: UUID
    recency: JobRecency
    sort: JobSort
    items: list[DiscoveryJobResponse]


class DiscoveryActionRequest(BaseModel):
    state: DiscoveryActionState


class ConvertToApplicationRequest(BaseModel):
    search_id: UUID


class DiscoveryActionResponse(BaseModel):
    discovered_job_id: UUID
    state: DiscoveryActionState
    application_id: int | None


class ConvertToApplicationResponse(DiscoveryActionResponse):
    application_id: int


class DiscoveryCatalogStatusResponse(BaseModel):
    configured_connector_count: int
    configured_sources: list[str]
    active_job_count: int
    active_source_count: int
    last_verified_at: datetime | None
