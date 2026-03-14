"""Variable schemas for request/response validation."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class VariableType(str, Enum):
    """Supported variable types."""

    TEXT = "text"
    ENUM = "enum"
    BOOLEAN = "boolean"
    NUMBER = "number"
    JSON = "JSON"
    MULTILINE = "multiline"


class VariableCreate(BaseModel):
    """Schema for creating a new variable."""

    name: str = Field(..., min_length=1, max_length=255)
    type: VariableType
    default_value: Any = Field(..., alias="defaultValue")
    description: str = Field(..., max_length=1000)
    tags: list[str] | None = None

    model_config = ConfigDict(populate_by_name=True)


class VariableUpdate(BaseModel):
    """Schema for updating an existing variable."""

    id: str
    name: str | None = Field(None, min_length=1, max_length=255)
    type: VariableType | None = None
    default_value: Any | None = Field(None, alias="defaultValue")
    description: str | None = Field(None, max_length=1000)
    tags: list[str] | None = None

    model_config = ConfigDict(populate_by_name=True)


class VariableResponse(BaseModel):
    """Schema for variable response."""

    id: str
    name: str
    type: VariableType
    default_value: Any = Field(..., alias="defaultValue")
    description: str
    tags: list[str] | None = None
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)
