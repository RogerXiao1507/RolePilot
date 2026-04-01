from datetime import datetime
from pydantic import BaseModel


class ProjectEvidenceCreate(BaseModel):
    title: str
    category: str
    description: str
    skills: list[str]
    keywords: list[str]
    bullet_bank: list[str]


class ProjectEvidenceResponse(BaseModel):
    id: int
    title: str
    category: str
    description: str
    skills: list[str]
    keywords: list[str]
    bullet_bank: list[str]
    created_at: datetime

    model_config = {"from_attributes": True}