"""Schemas for tenant database connections."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DatabaseConnectionConfig(BaseModel):
    host: str
    port: int | None = None
    database: str | None = None
    username: str | None = None
    password: str | None = None
    ssl: bool | None = None
    sslmode: str | None = None


class TenantConnectionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    type: Literal["postgres", "mysql"]
    config: DatabaseConnectionConfig
    is_active: bool = True


class TenantConnectionUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    config: DatabaseConnectionConfig | None = None
    is_active: bool | None = None


class TenantConnectionResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    type: str
    is_active: bool
    config: dict
    last_test_status: str | None
    last_tested_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TenantConnectionTestResponse(BaseModel):
    status: str
    details: dict | None = None
