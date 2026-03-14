"""Core Pydantic models used across XLake."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ContextRef(BaseModel):
    """Reference to an execution context domain."""

    tenant_id: str = Field(..., description="Tenant identifier, e.g. 'acme'")
    environment: str = Field(
        default="dev", description="Environment name: dev, staging, or prod"
    )


class Permissions(BaseModel):
    """Fine-grained permission and visibility configuration for a user."""

    can_view_fields: list[str] = Field(
        default_factory=list, description="Field identifiers the user can view"
    )
    can_view_tables: list[str] = Field(
        default_factory=list, description="Table identifiers the user can view"
    )
    can_view_kpis: list[str] = Field(
        default_factory=list, description="KPI identifiers the user can view"
    )
    can_view_dashboards: list[str] = Field(
        default_factory=list, description="Dashboard identifiers the user can view"
    )
    can_run_queries: bool = Field(
        default=True, description="Whether the user may execute data queries"
    )
    can_modify_schema: bool = Field(
        default=False, description="Whether the user may modify schema or relationships"
    )


class Preferences(BaseModel):
    """User UI and behavior preferences that impact result rendering."""

    units: str = Field(default="EUR", description="Preferred units, e.g., 'EUR'")
    timezone: str = Field(default="UTC", description="IANA timezone string")
    verbosity: str = Field(
        default="concise", description="Preferred response verbosity: concise|verbose"
    )


class UserContext(BaseModel):
    """Top-level request context used by XLake APIs and agents."""

    user_id: str = Field(..., description="Unique user identifier")
    tenant_id: str = Field(..., description="Tenant/workspace identifier")
    role: str = Field(..., description="Role used for coarse-grained authorization")
    permissions: Permissions = Field(
        default_factory=Permissions, description="Fine-grained permissions"
    )
    preferences: Preferences = Field(
        default_factory=Preferences, description="User presentation preferences"
    )


# -----------------------------------------------------------------------------
# Tenant Context Models
# -----------------------------------------------------------------------------


class TenantIdentity(BaseModel):
    """Tenant identity and routing information used for isolation and logging."""

    tenant_id: str = Field(
        ..., description="Unique tenant identifier, e.g., 'tenant_42'"
    )
    tenant_name: str = Field(..., description="Human-readable tenant name")
    industry: str = Field(..., description="Primary industry, e.g., 'manufacturing'")
    region: str = Field(..., description="Geographic region code, e.g., 'EU'")
    timezone: str = Field(..., description="Tenant timezone, e.g., 'Europe/Paris'")
    locale: str = Field(..., description="IETF BCP 47 locale tag, e.g., 'fr_FR'")


class TenantPermissions(BaseModel):
    """Tenant-scoped permissions and capability gates (distinct from user-level)."""

    allowed_external_sources: list[str] = Field(
        default_factory=list,
        description="External sources the tenant is allowed to use (e.g., weather_api).",
    )
    restricted_fields: list[str] = Field(
        default_factory=list,
        description="Field identifiers that are disallowed for the tenant.",
    )
    restricted_tables: list[str] = Field(
        default_factory=list,
        description="Table identifiers that are disallowed for the tenant.",
    )
    allow_schema_updates: bool = Field(
        default=True, description="Whether schema augmentation/updates are allowed."
    )
    allow_simulation_writeback: bool = Field(
        default=True,
        description="Whether simulation datasets can be saved for this tenant.",
    )
    allowed_capabilities: list[str] = Field(
        default_factory=list,
        description="High-level capabilities (query_data, run_simulation, import_data, publish_dashboard).",
    )


class ConnectorRef(BaseModel):
    """Reference configuration for a tenant-owned connector to internal data sources."""

    connector_id: str = Field(..., description="Stable ID, e.g., 'pg_sales'")
    type: Literal[
        "postgres", "bigquery", "snowflake", "redshift", "duckdb", "jdbc", "other"
    ] = Field(..., description="Connector type.")
    # Common optional properties depending on type
    host: str | None = Field(
        default=None, description="Hostname for SQL databases (if applicable)."
    )
    database: str | None = Field(
        default=None, description="Database/schema name (if applicable)."
    )
    project: str | None = Field(
        default=None, description="Cloud project (e.g., BigQuery)."
    )
    dataset: str | None = Field(
        default=None, description="Dataset name (e.g., BigQuery)."
    )
    credentials_ref: str = Field(
        ..., description="Secret manager reference, e.g., 'vault:acme/pg_sales'."
    )
    status: Literal["active", "inactive"] = Field(
        default="active", description="Operational status of the connector."
    )
    # Escape hatch for connector-specific options
    options: dict[str, Any] | None = Field(
        default=None, description="Connector-specific options (optional)."
    )


class NarrativePolicy(BaseModel):
    """Tenant-level narrative and communication policy (company preference)."""

    tone: Literal["executive", "analytical", "concise", "friendly"] = Field(
        default="analytical", description="Default tone for generated narratives."
    )
    default_language: str = Field(
        default="en", description="Default language for narratives and UI copy."
    )
    allowed_narrative_modes: list[str] = Field(
        default_factory=lambda: ["formal", "executive", "technical"],
        description="Allowed narrative modes available to agents.",
    )


class TenantContext(BaseModel):
    """Aggregated tenant context used by agents and stores for isolation and policy.

    Includes:
    - Identity: isolation, routing, audit, time-based aggregation correctness
    - Permissions: tenant-level capability gates and restrictions
    - Connectors: structured data sources for CustomerDataLakeStore
    - Narrative policy: consistent, company-level communication preferences
    """

    identity: TenantIdentity = Field(
        ..., description="Tenant identity and routing info."
    )
    permissions: TenantPermissions = Field(
        default_factory=TenantPermissions,
        description="Tenant-scoped permissions and capability gates.",
    )
    connectors: list[ConnectorRef] = Field(
        default_factory=list,
        description="List of configured connectors for tenant data sources.",
    )
    narrative_policy: NarrativePolicy = Field(
        default_factory=NarrativePolicy,
        description="Tenant-level narrative configuration and policy.",
    )
