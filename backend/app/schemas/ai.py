from pydantic import BaseModel, ConfigDict, Field


class JobParseRequest(BaseModel):
    text: str = Field(min_length=50, max_length=100_000)


class JobUrlParseRequest(BaseModel):
    url: str = Field(min_length=8, max_length=2048)


class JobParseResponse(BaseModel):
    company: str | None = None
    role_title: str | None = None
    location: str | None = None
    employment_type: str | None = None
    internship_season: str | None = None
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    summary: str = ""
    next_steps: list[str] = Field(default_factory=list)

class ResumeJobMatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    application_id: int = Field(gt=0)
    resume_id: int = Field(gt=0)


class ResumeJobMatchResponse(BaseModel):
    overall_match_summary: str
    matched_skills: list[str]
    missing_skills: list[str]
    strengths_for_role: list[str]
    improvement_areas: list[str]
    suggested_resume_changes: list[str]
