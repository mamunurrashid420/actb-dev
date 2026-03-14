"""Conversation schemas for request/response validation."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class MessageCreate(BaseModel):
    """Schema for creating a new message."""

    sender: Literal["user", "bot"]
    content: str = Field(..., min_length=1)


class MessageResponse(BaseModel):
    """Schema for message response."""

    id: str
    conversation_id: str
    sender: Literal["user", "bot"]
    content: str
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationCreate(BaseModel):
    """Schema for creating a new conversation."""

    title: str = Field(default="New Conversation", max_length=255)


class ConversationUpdate(BaseModel):
    """Schema for updating an existing conversation."""

    title: str | None = Field(None, max_length=255)


class ConversationResponse(BaseModel):
    """Schema for conversation response."""

    id: str
    tenant_id: str | None
    owner_user_id: str | None
    title: str
    share_tenant_role: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationWithMessages(ConversationResponse):
    """Schema for conversation with messages."""

    messages: list[MessageResponse] = Field(default_factory=list)
