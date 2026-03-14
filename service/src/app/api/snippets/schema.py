"""Snippet schemas for request/response validation."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SnippetCreate(BaseModel):
    """Schema for creating a new snippet."""

    name: str = Field(..., min_length=1, max_length=255)
    body: str = Field(..., min_length=1)
    tags: list[str] = Field(default_factory=list)


class SnippetUpdate(BaseModel):
    """Schema for updating an existing snippet."""

    id: str
    name: str | None = Field(None, min_length=1, max_length=255)
    body: str | None = Field(None, min_length=1)
    tags: list[str] | None = None


class SnippetResponse(BaseModel):
    """Schema for snippet response."""

    id: str
    name: str
    body: str
    tags: list[str]
    word_count: int = Field(..., alias="wordCount")
    used_in_prompts: int = Field(default=0, alias="usedInPrompts")
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)
