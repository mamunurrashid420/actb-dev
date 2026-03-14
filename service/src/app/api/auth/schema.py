"""Auth request/response schemas."""

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int | None = None
    user: dict | None = None


class SetPasswordRequest(BaseModel):
    password: str = Field(..., min_length=6)


class AuthContextResponse(BaseModel):
    id: str
    email: EmailStr | None = None
    claims: dict | None = None
