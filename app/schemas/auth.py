import re
from pydantic import BaseModel, EmailStr, field_validator


class UserCreate(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        # First capital letter, at least one number, at least special character, minimum 8 characters
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if len(v.encode('utf-8')) > 72:
            raise ValueError("Password cannot be longer than 72 bytes")
        if not re.match(r"^[A-Z]", v):
            raise ValueError("Password must start with a capital letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain at least one special character")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class MFAVerify(BaseModel):
    token: str


class Token(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str
    mfa_required: bool = False

class TokenRefresh(BaseModel):
    refresh_token: str

class OAuth2TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int
