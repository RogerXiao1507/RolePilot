from datetime import datetime
from pydantic import BaseModel


class ApplicationResumeMatchCreate(BaseModel):
    application_id: int
    resume_id: int
    overall_match_summary: str
    matched_skills: list[str]
    missing_skills: list[str]
    strengths_for_role: list[str]
    improvement_areas: list[str]
    suggested_resume_changes: list[str]


class ApplicationResumeMatchResponse(BaseModel):
    id: int
    application_id: int
    resume_id: int
    overall_match_summary: str
    matched_skills: list[str]
    missing_skills: list[str]
    strengths_for_role: list[str]
    improvement_areas: list[str]
    suggested_resume_changes: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}