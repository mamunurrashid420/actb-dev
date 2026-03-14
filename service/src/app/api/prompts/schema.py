"""Prompt schemas for request/response validation."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SnippetBlock(BaseModel):
    """A block that references a snippet."""

    type: Literal["snippet"] = "snippet"
    snippet_id: str = Field(..., alias="snippetId")

    model_config = ConfigDict(populate_by_name=True)


class TextBlock(BaseModel):
    """A block containing plain text."""

    type: Literal["text"] = "text"
    text: str


PromptBlock = SnippetBlock | TextBlock


class PromptCreate(BaseModel):
    """Schema for creating a new prompt."""

    name: str = Field(..., min_length=1, max_length=255)
    tags: list[str] = Field(default_factory=list)
    blocks: list[PromptBlock] = Field(default_factory=list)


class PromptUpdate(BaseModel):
    """Schema for updating an existing prompt."""

    id: str
    name: str | None = Field(None, min_length=1, max_length=255)
    tags: list[str] | None = None
    blocks: list[PromptBlock] | None = None


class PromptResponse(BaseModel):
    """Schema for prompt response."""

    id: str
    name: str
    tags: list[str]
    blocks: list[PromptBlock]
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)
