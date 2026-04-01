from datetime import datetime
from pydantic import BaseModel

from app.schemas.full_resume import FullTailoredResumeDraftResponse


class ApplicationFullResumeDraftCreate(BaseModel):
    application_id: int
    resume_id: int
    draft_data: FullTailoredResumeDraftResponse


class ApplicationFullResumeDraftResponse(BaseModel):
    id: int
    application_id: int
    resume_id: int
    draft_data: FullTailoredResumeDraftResponse
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}