from datetime import datetime
from pydantic import BaseModel, Field


class ResumeAnalysisResponse(BaseModel):
    summary: str
    strengths: list[str]
    weaknesses: list[str]
    wording_issues: list[str]
    missing_metrics: list[str]
    suggested_improvements: list[str]
    extracted_text: str


class ResumeCreate(BaseModel):
    file_name: str = Field(min_length=1, max_length=255)
    extracted_text: str = Field(min_length=1, max_length=100_000)
    summary: str = Field(min_length=1, max_length=20_000)
    strengths: list[str]
    weaknesses: list[str]
    wording_issues: list[str]
    missing_metrics: list[str]
    suggested_improvements: list[str]


class ResumeResponse(BaseModel):
    id: int
    file_name: str
    extracted_text: str
    summary: str
    strengths: list[str]
    weaknesses: list[str]
    wording_issues: list[str]
    missing_metrics: list[str]
    suggested_improvements: list[str]
    created_at: datetime

    model_config = {"from_attributes": True}
