from datetime import datetime
from pydantic import BaseModel


class ApplicationCreate(BaseModel):
    company: str
    role_title: str
    status: str = "saved"
    location: str | None = None
    job_url: str | None = None
    job_description: str | None = None
    ai_summary: str | None = None
    required_skills: list[str] | None = None
    preferred_skills: list[str] | None = None
    keywords: list[str] | None = None
    next_steps: list[str] | None = None


class ApplicationUpdate(BaseModel):
    company: str | None = None
    role_title: str | None = None
    status: str | None = None
    location: str | None = None
    job_url: str | None = None
    job_description: str | None = None
    ai_summary: str | None = None
    required_skills: list[str] | None = None
    preferred_skills: list[str] | None = None
    keywords: list[str] | None = None
    next_steps: list[str] | None = None


class ApplicationOut(BaseModel):
    id: int
    company: str
    role_title: str
    status: str
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