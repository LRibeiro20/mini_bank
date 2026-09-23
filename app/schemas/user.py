from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, ConfigDict


class UserBase(BaseModel):
    email: EmailStr
    is_active: bool
    mfa_enabled: bool


class UserResponse(UserBase):
    id: UUID
    created_at: datetime
    oauth_provider: str | None = None

    model_config = ConfigDict(from_attributes=True)
