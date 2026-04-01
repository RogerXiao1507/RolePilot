from pydantic import BaseModel


class TailorResumeRequest(BaseModel):
    application_id: int


class TailoredBullet(BaseModel):
    section: str
    source_title: str
    original_bullet: str
    tailored_bullet: str
    evidence_used: list[str]


class TailorResumeResponse(BaseModel):
    tailored_summary: str
    tailored_skills: list[str]
    tailored_bullets: list[TailoredBullet]
    tailoring_notes: list[str]

class FullTailoredResumeDraftRequest(BaseModel):
    application_id: int