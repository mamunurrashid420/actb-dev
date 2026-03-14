"""User schemas for request/response validation."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserProfileUpdate(BaseModel):
    """Schema for updating user profile."""

    first_name: str | None = Field(None, max_length=255)
    last_name: str | None = Field(None, max_length=255)
    full_name: str | None = Field(None, max_length=255)
    company_email: str | None = Field(None, max_length=255)
    notes: str | None = None
    avatar_url: str | None = None
    department: str | None = Field(None, max_length=100)
    position: str | None = Field(None, max_length=100)
    phone: str | None = Field(None, max_length=20)
    email: str | None = Field(None, max_length=255)


class UserProfileResponse(BaseModel):
    """Schema for user profile response."""

    id: str
    email: str | None
    first_name: str | None
    last_name: str | None
    full_name: str | None
    company_email: str | None
    notes: str | None
    avatar_url: str | None
    department: str | None
    position: str | None
    phone: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CurrentUserResponse(BaseModel):
    """Schema for current user response (from auth)."""

    id: str
    email: str | None
    created_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
