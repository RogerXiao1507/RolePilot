from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str | None
    name: str | None
    onboarding_complete: bool
    created_at: datetime
