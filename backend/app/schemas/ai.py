from pydantic import BaseModel


class JobParseRequest(BaseModel):
    text: str


class JobUrlParseRequest(BaseModel):
    url: str


class JobParseResponse(BaseModel):
    company: str | None = None
    role_title: str | None = None
    location: str | None = None
    employment_type: str | None = None
    internship_season: str | None = None
    required_skills: list[str] = []
    preferred_skills: list[str] = []
    keywords: list[str] = []
    summary: str = ""
    next_steps: list[str] = []

class ResumeJobMatchRequest(BaseModel):
    resume_text: str
    role_title: str | None = None
    company: str | None = None
    job_summary: str | None = None
    required_skills: list[str] = []
    preferred_skills: list[str] = []
    keywords: list[str] = []


class ResumeJobMatchResponse(BaseModel):
    overall_match_summary: str
    matched_skills: list[str]
    missing_skills: list[str]
    strengths_for_role: list[str]
    improvement_areas: list[str]
    suggested_resume_changes: list[str]