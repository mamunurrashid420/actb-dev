"""CustomerChartStore protocol and implementations.

Implements the CustomerChartStore interface from XLake-CustomerChartStore-Design.md.

Manages chart-related artifacts including:
- Chart, ChartStack, Dashboard specifications (Spec Plane)
- DataBinding, ETLDefinition, OutputSchema
- ChartDataSlice metadata and materialized JSON data (Data Plane)
- Insights and Recommendations

Two backends:
- SqliteCustomerChartStore (development): SQLite + fsspec Local FS
- SupabaseCustomerChartStore (staging/prod): Supabase + fsspec Cloud FS
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable

import fsspec
from google.protobuf.json_format import MessageToDict, Parse
from google.protobuf.timestamp_pb2 import Timestamp
from pydantic import BaseModel

from ..core import TenantContext, UserContext
from ..models import (
    Chart,
    ChartDataSlice,
    ChartStack,
    Dashboard,
    DataBinding,
    Insight,
    OutputSchema,
    Recommendation,
)
from .config import (
    CustomerChartStoreConfig,
    FSSpecLocalDocConfig,
    FSSpecObjectDocConfig,
    SqliteConfig,
    SupabaseConfig,
)

# ============================================================================
# Non-protobuf Models (stored as JSON)
# ============================================================================


class ETLDefinition(BaseModel):
    """ETL definition stored as versioned source code strings (not protobuf)."""

    etl_id: str
    version: int = 1
    ibis: str = ""
    polars: str = ""


# ============================================================================
# Protocol Interface
# ============================================================================


@runtime_checkable
class CustomerChartStore(Protocol):
    """Protocol for storing and retrieving chart artifacts."""

    # Read APIs
    def get_chart(
        self,
        chart_id: str,
        version: int | None = None,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> Chart:  # pragma: no cover
        """Return a chart by ID and optional version."""
        ...

    def get_chart_stack(
        self, chart_stack_id: str, *, tenant: TenantContext, user: UserContext
    ) -> ChartStack:  # pragma: no cover
        """Return a chart stack by ID."""
        ...

    def get_dashboard(
        self, dashboard_id: str, *, tenant: TenantContext, user: UserContext
    ) -> Dashboard:  # pragma: no cover
        """Return a dashboard by ID."""
        ...

    def get_chart_data_slice(
        self, slice_id: str, *, tenant: TenantContext, user: UserContext
    ) -> ChartDataSlice:  # pragma: no cover
        """Return chart data slice metadata by ID."""
        ...

    def get_chart_data(
        self, slice_id: str, *, tenant: TenantContext, user: UserContext
    ) -> dict[str, Any]:  # pragma: no cover
        """Return JSON data rows for a chart data slice."""
        ...

    # Write APIs (Upserts)
    def upsert_chart(
        self, chart: Chart, *, tenant: TenantContext, user: UserContext
    ) -> Chart:  # pragma: no cover
        """Create or update a chart (with version bump if needed)."""
        ...

    def upsert_chart_stack(
        self, stack: ChartStack, *, tenant: TenantContext, user: UserContext
    ) -> ChartStack:  # pragma: no cover
        """Create or update a chart stack."""
        ...

    def upsert_dashboard(
        self, dashboard: Dashboard, *, tenant: TenantContext, user: UserContext
    ) -> Dashboard:  # pragma: no cover
        """Create or update a dashboard."""
        ...

    def upsert_data_binding(
        self, binding: DataBinding, *, tenant: TenantContext, user: UserContext
    ) -> DataBinding:  # pragma: no cover
        """Create or update a data binding (with version bump if needed)."""
        ...

    def upsert_etl_definition(
        self, etl: ETLDefinition, *, tenant: TenantContext, user: UserContext
    ) -> ETLDefinition:  # pragma: no cover
        """Create or update an ETL definition (with version bump if needed)."""
        ...

    def upsert_output_schema(
        self, schema: OutputSchema, *, tenant: TenantContext, user: UserContext
    ) -> OutputSchema:  # pragma: no cover
        """Create or update an output schema (with version bump if needed)."""
        ...

    def upsert_chart_data_slice(
        self, slice: ChartDataSlice, *, tenant: TenantContext, user: UserContext
    ) -> ChartDataSlice:  # pragma: no cover
        """Create or update a chart data slice."""
        ...

    def upsert_insight(
        self, insight: Insight, *, tenant: TenantContext, user: UserContext
    ) -> Insight:  # pragma: no cover
        """Create or update an insight."""
        ...

    def upsert_recommendation(
        self,
        recommendation: Recommendation,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> Recommendation:  # pragma: no cover
        """Create or update a recommendation."""
        ...

    # Delete APIs (Soft deletes)
    def delete_chart(
        self, chart_id: str, version: int, *, tenant: TenantContext, user: UserContext
    ) -> None:  # pragma: no cover
        """Soft delete a chart version."""
        ...

    def delete_dashboard(
        self, dashboard_id: str, *, tenant: TenantContext, user: UserContext
    ) -> None:  # pragma: no cover
        """Soft delete a dashboard."""
        ...

    def delete_chart_data_slice(
        self, slice_id: str, *, tenant: TenantContext, user: UserContext
    ) -> None:  # pragma: no cover
        """Soft delete a chart data slice."""
        ...

    # Refresh API
    def refresh_chart_data(
        self,
        slice_id: str,
        data: dict[str, Any],
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> ChartDataSlice:  # pragma: no cover
        """Materialize chart data and update slice metadata."""
        ...

    def close(self) -> None:  # pragma: no cover
        """Release resources held by the store."""
        ...

    # Filter APIs (saved/named filters)
    def get_filter(
        self, filter_id: str, *, tenant: TenantContext, user: UserContext
    ) -> dict[str, Any]:  # pragma: no cover
        """Return a saved filter definition by ID."""
        ...

    def upsert_filter(
        self, filter_obj: dict[str, Any], *, tenant: TenantContext, user: UserContext
    ) -> dict[str, Any]:  # pragma: no cover
        """Create or update a saved filter, returning the filter object."""
        ...

    def delete_filter(
        self, filter_id: str, *, tenant: TenantContext, user: UserContext
    ) -> None:  # pragma: no cover
        """Soft delete a saved filter."""
        ...

    # Simulation APIs
    def get_simulation(
        self, simulation_id: str, *, tenant: TenantContext, user: UserContext
    ) -> dict[str, Any]:  # pragma: no cover
        """Return a simulation scenario by ID."""
        ...

    def upsert_simulation(
        self, simulation: dict[str, Any], *, tenant: TenantContext, user: UserContext
    ) -> dict[str, Any]:  # pragma: no cover
        """Create or update a simulation scenario, returning the simulation object."""
        ...

    def delete_simulation(
        self, simulation_id: str, *, tenant: TenantContext, user: UserContext
    ) -> None:  # pragma: no cover
        """Soft delete a simulation scenario."""
        ...

    # Scenario Chip APIs
    def get_scenario_chip(
        self, chip_id: str, *, tenant: TenantContext, user: UserContext
    ) -> dict[str, Any]:  # pragma: no cover
        """Return a scenario chip by ID."""
        ...

    def upsert_scenario_chip(
        self, chip: dict[str, Any], *, tenant: TenantContext, user: UserContext
    ) -> dict[str, Any]:  # pragma: no cover
        """Create or update a scenario chip, returning the chip object."""
        ...

    def delete_scenario_chip(
        self, chip_id: str, *, tenant: TenantContext, user: UserContext
    ) -> None:  # pragma: no cover
        """Soft delete a scenario chip."""
        ...


# ============================================================================
# SQLite Implementation
# ============================================================================


class SqliteCustomerChartStore:
    """SQLite-backed CustomerChartStore implementation for development."""

    def __init__(
        self,
        *,
        sqlite_config: SqliteConfig | None = None,
        fs_local_config: FSSpecLocalDocConfig | None = None,
    ) -> None:
        """Initialize SQLite store with configs."""
        if sqlite_config is None or fs_local_config is None:
            raise ValueError("sqlite_config and fs_local_config must be provided")
        self._sqlite_config = sqlite_config
        self._fs_base = (
            fs_local_config.base_dir
            if "://" in fs_local_config.base_dir
            else f"file://{fs_local_config.base_dir}"
        )
        self._conn: sqlite3.Connection | None = None
        self._ensure_conn_and_schema()

    def _ensure_conn_and_schema(self) -> None:
        """Create connection and initialize database schema."""
        if self._conn is None:
            self._conn = sqlite3.connect(
                self._sqlite_config.database_path,
                check_same_thread=False,
            )
            self._conn.row_factory = sqlite3.Row
        conn = self._conn
        cur = conn.cursor()

        # Charts table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS charts (
                id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                version INTEGER NOT NULL,
                schema_version INTEGER NOT NULL DEFAULT 1,
                spec_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                deleted_at TEXT,
                PRIMARY KEY (id, tenant_id, version)
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_charts_tenant_active ON charts(tenant_id, id, version) WHERE deleted_at IS NULL"
        )

        # Chart stacks table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS chart_stacks (
                id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                schema_version INTEGER NOT NULL DEFAULT 1,
                spec_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                deleted_at TEXT,
                PRIMARY KEY (id, tenant_id)
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_chart_stacks_tenant_active ON chart_stacks(tenant_id, id) WHERE deleted_at IS NULL"
        )

        # Dashboards table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS dashboards (
                id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                schema_version INTEGER NOT NULL DEFAULT 1,
                spec_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                deleted_at TEXT,
                PRIMARY KEY (id, tenant_id)
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_dashboards_tenant_active ON dashboards(tenant_id, id) WHERE deleted_at IS NULL"
        )

        # Data bindings table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS data_bindings (
                id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                version INTEGER NOT NULL,
                schema_version INTEGER NOT NULL DEFAULT 1,
                spec_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                deleted_at TEXT,
                PRIMARY KEY (id, tenant_id, version)
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_data_bindings_tenant_active ON data_bindings(tenant_id, id, version) WHERE deleted_at IS NULL"
        )

        # ETL definitions table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS etl_definitions (
                id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                version INTEGER NOT NULL,
                etl_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                deleted_at TEXT,
                PRIMARY KEY (id, tenant_id, version)
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_etl_definitions_tenant_active ON etl_definitions(tenant_id, id, version) WHERE deleted_at IS NULL"
        )

        # Output schemas table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS output_schemas (
                id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                version INTEGER NOT NULL,
                schema_version INTEGER NOT NULL DEFAULT 1,
                spec_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                deleted_at TEXT,
                PRIMARY KEY (id, tenant_id, version)
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_output_schemas_tenant_active ON output_schemas(tenant_id, id, version) WHERE deleted_at IS NULL"
        )

        # Chart data slices table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS chart_data_slices (
                id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                spec_json TEXT NOT NULL,
                last_refreshed_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                deleted_at TEXT,
                PRIMARY KEY (id, tenant_id)
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_chart_data_slices_tenant_active ON chart_data_slices(tenant_id, id) WHERE deleted_at IS NULL"
        )
        # Note: We can't index on nested protobuf fields directly in SQLite
        # If needed, we could add separate columns for chart_id/chart_version for indexing

        # Insights table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS insights (
                id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                schema_version INTEGER NOT NULL DEFAULT 1,
                spec_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                deleted_at TEXT,
                PRIMARY KEY (id, tenant_id)
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_insights_tenant_active ON insights(tenant_id, id) WHERE deleted_at IS NULL"
        )

        # Recommendations table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS recommendations (
                id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                schema_version INTEGER NOT NULL DEFAULT 1,
                spec_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                deleted_at TEXT,
                PRIMARY KEY (id, tenant_id)
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_recommendations_tenant_active ON recommendations(tenant_id, id) WHERE deleted_at IS NULL"
        )

        # Saved filters table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS saved_filters (
                id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                spec_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                deleted_at TEXT,
                PRIMARY KEY (id, tenant_id)
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_saved_filters_tenant_active ON saved_filters(tenant_id, id) WHERE deleted_at IS NULL"
        )

        # Simulations table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS simulations (
                id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                spec_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                deleted_at TEXT,
                PRIMARY KEY (id, tenant_id)
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_simulations_tenant_active ON simulations(tenant_id, id) WHERE deleted_at IS NULL"
        )

        # Scenario chips table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS scenario_chips (
                id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                spec_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                deleted_at TEXT,
                PRIMARY KEY (id, tenant_id)
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_scenario_chips_tenant_active ON scenario_chips(tenant_id, id) WHERE deleted_at IS NULL"
        )

        conn.commit()

    def _canonical_json(self, obj: Any) -> str:
        """Serialize to canonical JSON (alphabetical keys, explicit defaults).

        Handles both protobuf messages and Pydantic models.
        """
        # Check if it's a protobuf message (has DESCRIPTOR attribute)
        if hasattr(obj, "DESCRIPTOR"):
            # Use MessageToDict for protobuf messages
            data = MessageToDict(
                obj,
                always_print_fields_with_no_presence=True,
                preserving_proto_field_name=True,
            )
        elif isinstance(obj, BaseModel):
            # Use model_dump for Pydantic models
            data = obj.model_dump(exclude_none=False, mode="json")
        else:
            # Fallback for dicts
            data = obj
        return json.dumps(data, indent=2, sort_keys=True)

    def _now_iso(self) -> str:
        """Return current timestamp as ISO8601 string."""
        return datetime.now(UTC).isoformat()

    def _assert_can_modify(self, user: UserContext) -> None:
        """Assert user has permission to modify (placeholder)."""
        # TODO: Implement permission checks
        pass

    # Read APIs
    def get_chart(
        self,
        chart_id: str,
        version: int | None = None,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> Chart:
        """Return a chart by ID and optional version."""
        tenant_id = tenant.identity.tenant_id
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()

        if version is not None:
            cur.execute(
                """
                SELECT spec_json FROM charts
                WHERE id = ? AND tenant_id = ? AND version = ? AND deleted_at IS NULL
                """,
                (chart_id, tenant_id, version),
            )
        else:
            # Get latest version
            cur.execute(
                """
                SELECT spec_json FROM charts
                WHERE id = ? AND tenant_id = ? AND deleted_at IS NULL
                ORDER BY version DESC LIMIT 1
                """,
                (chart_id, tenant_id),
            )

        row = cur.fetchone()
        if row is None:
            raise ValueError(f"Chart not found: {chart_id} (version={version})")
        return Parse(row["spec_json"], Chart())

    def get_chart_stack(
        self, chart_stack_id: str, *, tenant: TenantContext, user: UserContext
    ) -> ChartStack:
        """Return a chart stack by ID."""
        tenant_id = tenant.identity.tenant_id
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()
        cur.execute(
            """
            SELECT spec_json FROM chart_stacks
            WHERE id = ? AND tenant_id = ? AND deleted_at IS NULL
            """,
            (chart_stack_id, tenant_id),
        )
        row = cur.fetchone()
        if row is None:
            raise ValueError(f"ChartStack not found: {chart_stack_id}")
        return Parse(row["spec_json"], ChartStack())

    def get_dashboard(
        self, dashboard_id: str, *, tenant: TenantContext, user: UserContext
    ) -> Dashboard:
        """Return a dashboard by ID."""
        tenant_id = tenant.identity.tenant_id
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()
        cur.execute(
            """
            SELECT spec_json FROM dashboards
            WHERE id = ? AND tenant_id = ? AND deleted_at IS NULL
            """,
            (dashboard_id, tenant_id),
        )
        row = cur.fetchone()
        if row is None:
            raise ValueError(f"Dashboard not found: {dashboard_id}")
        return Parse(row["spec_json"], Dashboard())

    def get_chart_data_slice(
        self, slice_id: str, *, tenant: TenantContext, user: UserContext
    ) -> ChartDataSlice:
        """Return chart data slice metadata by ID."""
        tenant_id = tenant.identity.tenant_id
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()
        cur.execute(
            """
            SELECT spec_json, last_refreshed_at FROM chart_data_slices
            WHERE id = ? AND tenant_id = ? AND deleted_at IS NULL
            """,
            (slice_id, tenant_id),
        )
        row = cur.fetchone()
        if row is None:
            raise ValueError(f"ChartDataSlice not found: {slice_id}")

        # Parse ChartDataSlice protobuf message from JSON
        slice_msg = Parse(row["spec_json"], ChartDataSlice())

        # Note: last_refreshed_at is stored in DB, not in protobuf
        # Store it in a cache for retrieval via getattr
        if not hasattr(self, "_last_refreshed_at_cache"):
            self._last_refreshed_at_cache: dict[str, Timestamp] = {}
        if row["last_refreshed_at"]:
            dt = datetime.fromisoformat(row["last_refreshed_at"].replace("Z", "+00:00"))
            ts = Timestamp()
            ts.FromDatetime(dt)
            self._last_refreshed_at_cache[slice_id] = ts

        return slice_msg

    def get_chart_data(
        self, slice_id: str, *, tenant: TenantContext, user: UserContext
    ) -> dict[str, Any]:
        """Return JSON data rows for a chart data slice."""
        slice_meta = self.get_chart_data_slice(slice_id, tenant=tenant, user=user)
        if slice_meta.json_uri is None:
            raise ValueError(f"ChartDataSlice {slice_id} has no materialized data")

        # Read from fsspec
        protocol = self._fs_base.split("://")[0] if "://" in self._fs_base else "file"
        base_path = (
            self._fs_base.split("://", 1)[1]
            if "://" in self._fs_base
            else self._fs_base
        )

        # Extract relative path from json_uri
        if slice_meta.json_uri.startswith(self._fs_base):
            rel_path = slice_meta.json_uri[len(self._fs_base) :].lstrip("/")
        else:
            # Assume it's already a relative path or full path
            rel_path = slice_meta.json_uri.replace(self._fs_base, "").lstrip("/")

        fs = fsspec.filesystem(protocol)
        full_path = f"{base_path}/{rel_path}" if protocol == "file" else rel_path

        with fs.open(full_path, "r") as f:
            return json.load(f)

    # Write APIs
    def upsert_chart(
        self, chart: Chart, *, tenant: TenantContext, user: UserContext
    ) -> Chart:
        """Create or update a chart (with version bump if needed)."""
        self._assert_can_modify(user)
        tenant_id = tenant.identity.tenant_id
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()

        # Check if chart exists and determine if version bump is needed
        cur.execute(
            """
            SELECT version, spec_json FROM charts
            WHERE id = ? AND tenant_id = ? AND version = ? AND deleted_at IS NULL
            """,
            (chart.id, tenant_id, chart.version),
        )
        existing = cur.fetchone()

        now = self._now_iso()
        spec_json = self._canonical_json(chart)

        if existing is None:
            # New chart version
            cur.execute(
                """
                INSERT INTO charts (id, tenant_id, version, schema_version, spec_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chart.id,
                    tenant_id,
                    chart.version,
                    chart.schema_version,
                    spec_json,
                    now,
                    now,
                ),
            )
        else:
            # Update existing version
            cur.execute(
                """
                UPDATE charts
                SET spec_json = ?, schema_version = ?, updated_at = ?
                WHERE id = ? AND tenant_id = ? AND version = ? AND deleted_at IS NULL
                """,
                (
                    spec_json,
                    chart.schema_version,
                    now,
                    chart.id,
                    tenant_id,
                    chart.version,
                ),
            )

        conn.commit()
        return chart

    def upsert_chart_stack(
        self, stack: ChartStack, *, tenant: TenantContext, user: UserContext
    ) -> ChartStack:
        """Create or update a chart stack."""
        self._assert_can_modify(user)
        tenant_id = tenant.identity.tenant_id
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()

        now_dt = datetime.now(UTC)
        now_ts = Timestamp()
        now_ts.FromDatetime(now_dt)

        # Set timestamps if not already set
        if not stack.HasField("created_at"):
            stack.created_at.CopyFrom(now_ts)
        stack.updated_at.CopyFrom(now_ts)
        spec_json = self._canonical_json(stack)

        cur.execute(
            """
            INSERT INTO chart_stacks (id, tenant_id, schema_version, spec_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id, tenant_id) DO UPDATE SET
                spec_json = excluded.spec_json,
                schema_version = excluded.schema_version,
                updated_at = excluded.updated_at
            """,
            (
                stack.id,
                tenant_id,
                stack.schema_version,
                spec_json,
                now_dt.isoformat(),
                now_dt.isoformat(),
            ),
        )
        conn.commit()
        return stack

    def upsert_dashboard(
        self, dashboard: Dashboard, *, tenant: TenantContext, user: UserContext
    ) -> Dashboard:
        """Create or update a dashboard."""
        self._assert_can_modify(user)
        tenant_id = tenant.identity.tenant_id
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()

        now_dt = datetime.now(UTC)
        now_ts = Timestamp()
        now_ts.FromDatetime(now_dt)

        # Set timestamps if not already set
        if not dashboard.HasField("created_at"):
            dashboard.created_at.CopyFrom(now_ts)
        dashboard.updated_at.CopyFrom(now_ts)
        spec_json = self._canonical_json(dashboard)

        cur.execute(
            """
            INSERT INTO dashboards (id, tenant_id, schema_version, spec_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id, tenant_id) DO UPDATE SET
                spec_json = excluded.spec_json,
                schema_version = excluded.schema_version,
                updated_at = excluded.updated_at
            """,
            (
                dashboard.id,
                tenant_id,
                dashboard.schema_version,
                spec_json,
                now_dt.isoformat(),
                now_dt.isoformat(),
            ),
        )
        conn.commit()
        return dashboard

    def upsert_data_binding(
        self, binding: DataBinding, *, tenant: TenantContext, user: UserContext
    ) -> DataBinding:
        """Create or update a data binding (with version bump if needed)."""
        self._assert_can_modify(user)
        tenant_id = tenant.identity.tenant_id
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()

        now = self._now_iso()
        spec_json = self._canonical_json(binding)

        cur.execute(
            """
            INSERT INTO data_bindings (id, tenant_id, version, schema_version, spec_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id, tenant_id, version) DO UPDATE SET
                spec_json = excluded.spec_json,
                schema_version = excluded.schema_version,
                updated_at = excluded.updated_at
            """,
            (
                binding.id,
                tenant_id,
                binding.version,
                binding.schema_version,
                spec_json,
                now,
                now,
            ),
        )
        conn.commit()
        return binding

    def upsert_etl_definition(
        self, etl: ETLDefinition, *, tenant: TenantContext, user: UserContext
    ) -> ETLDefinition:
        """Create or update an ETL definition (with version bump if needed)."""
        self._assert_can_modify(user)
        tenant_id = tenant.identity.tenant_id
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()

        now = self._now_iso()
        etl_json = self._canonical_json(etl)

        cur.execute(
            """
            INSERT INTO etl_definitions (id, tenant_id, version, etl_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id, tenant_id, version) DO UPDATE SET
                etl_json = excluded.etl_json,
                updated_at = excluded.updated_at
            """,
            (etl.etl_id, tenant_id, etl.version, etl_json, now, now),
        )
        conn.commit()
        return etl

    def upsert_output_schema(
        self, schema: OutputSchema, *, tenant: TenantContext, user: UserContext
    ) -> OutputSchema:
        """Create or update an output schema (with version bump if needed)."""
        self._assert_can_modify(user)
        tenant_id = tenant.identity.tenant_id
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()

        now = self._now_iso()
        spec_json = self._canonical_json(schema)

        cur.execute(
            """
            INSERT INTO output_schemas (id, tenant_id, version, schema_version, spec_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id, tenant_id, version) DO UPDATE SET
                spec_json = excluded.spec_json,
                schema_version = excluded.schema_version,
                updated_at = excluded.updated_at
            """,
            (
                schema.id,
                tenant_id,
                schema.version,
                schema.schema_version,
                spec_json,
                now,
                now,
            ),
        )
        conn.commit()
        return schema

    def upsert_chart_data_slice(
        self, slice: ChartDataSlice, *, tenant: TenantContext, user: UserContext
    ) -> ChartDataSlice:
        """Create or update a chart data slice."""
        self._assert_can_modify(user)
        tenant_id = tenant.identity.tenant_id
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()

        now = self._now_iso()
        spec_json = self._canonical_json(slice)

        # Preserve existing last_refreshed_at if updating (don't overwrite on upsert)
        # Only set it if this is a new slice
        cur.execute(
            """
            SELECT last_refreshed_at FROM chart_data_slices
            WHERE id = ? AND tenant_id = ?
            """,
            (slice.id, tenant_id),
        )
        existing = cur.fetchone()
        last_refreshed_at = existing["last_refreshed_at"] if existing else None

        cur.execute(
            """
            INSERT INTO chart_data_slices (id, tenant_id, spec_json, last_refreshed_at, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id, tenant_id) DO UPDATE SET
                spec_json = excluded.spec_json,
                last_refreshed_at = COALESCE(excluded.last_refreshed_at, chart_data_slices.last_refreshed_at),
                updated_at = excluded.updated_at
            """,
            (slice.id, tenant_id, spec_json, last_refreshed_at, now, now),
        )
        conn.commit()
        return slice

    def upsert_insight(
        self, insight: Insight, *, tenant: TenantContext, user: UserContext
    ) -> Insight:
        """Create or update an insight."""
        self._assert_can_modify(user)
        tenant_id = tenant.identity.tenant_id
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()

        now_dt = datetime.now(UTC)
        now_ts = Timestamp()
        now_ts.FromDatetime(now_dt)

        # Set timestamp if not already set
        if not insight.HasField("created_at"):
            insight.created_at.CopyFrom(now_ts)
        spec_json = self._canonical_json(insight)

        cur.execute(
            """
            INSERT INTO insights (id, tenant_id, schema_version, spec_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id, tenant_id) DO UPDATE SET
                spec_json = excluded.spec_json,
                schema_version = excluded.schema_version,
                updated_at = excluded.updated_at
            """,
            (
                insight.id,
                tenant_id,
                insight.schema_version,
                spec_json,
                now_dt.isoformat(),
                now_dt.isoformat(),
            ),
        )
        conn.commit()
        return insight

    def upsert_recommendation(
        self,
        recommendation: Recommendation,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> Recommendation:
        """Create or update a recommendation."""
        self._assert_can_modify(user)
        tenant_id = tenant.identity.tenant_id
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()

        now_dt = datetime.now(UTC)
        spec_json = self._canonical_json(recommendation)

        # Recommendation proto has no schema_version or created_at;
        # these are tracked as store-level metadata in the DB row.
        cur.execute(
            """
            INSERT INTO recommendations (id, tenant_id, schema_version, spec_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id, tenant_id) DO UPDATE SET
                spec_json = excluded.spec_json,
                updated_at = excluded.updated_at
            """,
            (
                recommendation.id,
                tenant_id,
                1,  # store-level schema version
                spec_json,
                now_dt.isoformat(),
                now_dt.isoformat(),
            ),
        )
        conn.commit()
        return recommendation

    # Delete APIs
    def delete_chart(
        self, chart_id: str, version: int, *, tenant: TenantContext, user: UserContext
    ) -> None:
        """Soft delete a chart version."""
        self._assert_can_modify(user)
        tenant_id = tenant.identity.tenant_id
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE charts SET deleted_at = ?
            WHERE id = ? AND tenant_id = ? AND version = ? AND deleted_at IS NULL
            """,
            (self._now_iso(), chart_id, tenant_id, version),
        )
        conn.commit()

    def delete_dashboard(
        self, dashboard_id: str, *, tenant: TenantContext, user: UserContext
    ) -> None:
        """Soft delete a dashboard."""
        self._assert_can_modify(user)
        tenant_id = tenant.identity.tenant_id
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE dashboards SET deleted_at = ?
            WHERE id = ? AND tenant_id = ? AND deleted_at IS NULL
            """,
            (self._now_iso(), dashboard_id, tenant_id),
        )
        conn.commit()

    def delete_chart_data_slice(
        self, slice_id: str, *, tenant: TenantContext, user: UserContext
    ) -> None:
        """Soft delete a chart data slice."""
        self._assert_can_modify(user)
        tenant_id = tenant.identity.tenant_id
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE chart_data_slices SET deleted_at = ?
            WHERE id = ? AND tenant_id = ? AND deleted_at IS NULL
            """,
            (self._now_iso(), slice_id, tenant_id),
        )
        conn.commit()

    # Refresh API
    def refresh_chart_data(
        self,
        slice_id: str,
        data: dict[str, Any],
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> ChartDataSlice:
        """Materialize chart data and update slice metadata."""
        self._assert_can_modify(user)
        tenant_id = tenant.identity.tenant_id

        # Get slice metadata
        slice_meta = self.get_chart_data_slice(slice_id, tenant=tenant, user=user)

        # Compute hashes
        data_json = json.dumps(data, sort_keys=True)
        data_hash = hashlib.sha256(data_json.encode()).hexdigest()

        # Get output schema for schema hash
        schema = self.get_output_schema(
            slice_meta.output_schema_id, tenant=tenant, user=user
        )
        schema_json = self._canonical_json(schema)
        schema_hash = hashlib.sha256(schema_json.encode()).hexdigest()

        # Store JSON data via fsspec
        # Construct relative path from base
        rel_path = f"chart_data/{slice_meta.chart_id}/{slice_meta.chart_version}/{slice_id}.json"
        json_uri = f"{self._fs_base}/{rel_path}"

        # Get filesystem and write
        protocol = self._fs_base.split("://")[0] if "://" in self._fs_base else "file"
        base_path = (
            self._fs_base.split("://", 1)[1]
            if "://" in self._fs_base
            else self._fs_base
        )
        fs = fsspec.filesystem(protocol)
        full_path = f"{base_path}/{rel_path}" if protocol == "file" else rel_path

        # Ensure directory exists
        dir_path = "/".join(full_path.split("/")[:-1])
        fs.makedirs(dir_path, exist_ok=True)

        with fs.open(full_path, "w") as f:
            json.dump(data, f, indent=2, sort_keys=True)

        # Update slice metadata (protobuf ChartDataSlice)
        now_dt = datetime.now(UTC)
        now_ts = Timestamp()
        now_ts.FromDatetime(now_dt)

        slice_meta.json_uri = json_uri
        slice_meta.data_hash = data_hash
        slice_meta.schema_hash = schema_hash
        slice_meta.generated_at.CopyFrom(now_ts)

        # Upsert the slice spec
        result = self.upsert_chart_data_slice(slice_meta, tenant=tenant, user=user)

        # Update last_refreshed_at in DB (stored separately, not in protobuf)
        tenant_id = tenant.identity.tenant_id
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()
        cur.execute(
            "UPDATE chart_data_slices SET last_refreshed_at = ? WHERE id = ? AND tenant_id = ?",
            (now_dt.isoformat(), slice_id, tenant_id),
        )
        conn.commit()
        if self._conn is None:
            conn.close()

        # Update cache
        if not hasattr(self, "_last_refreshed_at_cache"):
            self._last_refreshed_at_cache = {}
        self._last_refreshed_at_cache[slice_id] = now_ts

        return result

    def get_output_schema(
        self,
        schema_id: str,
        version: int | None = None,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> OutputSchema:
        """Helper to get output schema (used by refresh_chart_data)."""
        tenant_id = tenant.identity.tenant_id
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()

        if version is not None:
            cur.execute(
                """
                SELECT spec_json FROM output_schemas
                WHERE id = ? AND tenant_id = ? AND version = ? AND deleted_at IS NULL
                """,
                (schema_id, tenant_id, version),
            )
        else:
            cur.execute(
                """
                SELECT spec_json FROM output_schemas
                WHERE id = ? AND tenant_id = ? AND deleted_at IS NULL
                ORDER BY version DESC LIMIT 1
                """,
                (schema_id, tenant_id),
            )

        row = cur.fetchone()
        if row is None:
            raise ValueError(f"OutputSchema not found: {schema_id} (version={version})")
        return Parse(row["spec_json"], OutputSchema())

    # Filter APIs
    def get_filter(
        self, filter_id: str, *, tenant: TenantContext, user: UserContext
    ) -> dict[str, Any]:
        """Return a saved filter definition by ID."""
        tenant_id = tenant.identity.tenant_id
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()
        cur.execute(
            """
            SELECT spec_json FROM saved_filters
            WHERE id = ? AND tenant_id = ? AND deleted_at IS NULL
            """,
            (filter_id, tenant_id),
        )
        row = cur.fetchone()
        if row is None:
            raise ValueError(f"Filter not found: {filter_id}")
        return json.loads(row["spec_json"])

    def upsert_filter(
        self, filter_obj: dict[str, Any], *, tenant: TenantContext, user: UserContext
    ) -> dict[str, Any]:
        """Create or update a saved filter, returning the filter object."""
        self._assert_can_modify(user)
        tenant_id = tenant.identity.tenant_id
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()

        filter_id = filter_obj.get("id")
        if not filter_id:
            raise ValueError("Filter must have an 'id' field")

        now = self._now_iso()
        spec_json = json.dumps(filter_obj, indent=2, sort_keys=True)

        cur.execute(
            """
            INSERT INTO saved_filters (id, tenant_id, spec_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id, tenant_id) DO UPDATE SET
                spec_json = excluded.spec_json,
                updated_at = excluded.updated_at
            """,
            (filter_id, tenant_id, spec_json, now, now),
        )
        conn.commit()
        return filter_obj

    def delete_filter(
        self, filter_id: str, *, tenant: TenantContext, user: UserContext
    ) -> None:
        """Soft delete a saved filter."""
        self._assert_can_modify(user)
        tenant_id = tenant.identity.tenant_id
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE saved_filters SET deleted_at = ?
            WHERE id = ? AND tenant_id = ? AND deleted_at IS NULL
            """,
            (self._now_iso(), filter_id, tenant_id),
        )
        conn.commit()

    # Simulation APIs
    def get_simulation(
        self, simulation_id: str, *, tenant: TenantContext, user: UserContext
    ) -> dict[str, Any]:
        """Return a simulation scenario by ID."""
        tenant_id = tenant.identity.tenant_id
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()
        cur.execute(
            """
            SELECT spec_json FROM simulations
            WHERE id = ? AND tenant_id = ? AND deleted_at IS NULL
            """,
            (simulation_id, tenant_id),
        )
        row = cur.fetchone()
        if row is None:
            raise ValueError(f"Simulation not found: {simulation_id}")
        return json.loads(row["spec_json"])

    def upsert_simulation(
        self, simulation: dict[str, Any], *, tenant: TenantContext, user: UserContext
    ) -> dict[str, Any]:
        """Create or update a simulation scenario, returning the simulation object."""
        self._assert_can_modify(user)
        tenant_id = tenant.identity.tenant_id
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()

        simulation_id = simulation.get("id")
        if not simulation_id:
            raise ValueError("Simulation must have an 'id' field")

        now = self._now_iso()
        spec_json = json.dumps(simulation, indent=2, sort_keys=True)

        cur.execute(
            """
            INSERT INTO simulations (id, tenant_id, spec_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id, tenant_id) DO UPDATE SET
                spec_json = excluded.spec_json,
                updated_at = excluded.updated_at
            """,
            (simulation_id, tenant_id, spec_json, now, now),
        )
        conn.commit()
        return simulation

    def delete_simulation(
        self, simulation_id: str, *, tenant: TenantContext, user: UserContext
    ) -> None:
        """Soft delete a simulation scenario."""
        self._assert_can_modify(user)
        tenant_id = tenant.identity.tenant_id
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE simulations SET deleted_at = ?
            WHERE id = ? AND tenant_id = ? AND deleted_at IS NULL
            """,
            (self._now_iso(), simulation_id, tenant_id),
        )
        conn.commit()

    # Scenario Chip APIs
    def get_scenario_chip(
        self, chip_id: str, *, tenant: TenantContext, user: UserContext
    ) -> dict[str, Any]:
        """Return a scenario chip by ID."""
        tenant_id = tenant.identity.tenant_id
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()
        cur.execute(
            """
            SELECT spec_json FROM scenario_chips
            WHERE id = ? AND tenant_id = ? AND deleted_at IS NULL
            """,
            (chip_id, tenant_id),
        )
        row = cur.fetchone()
        if row is None:
            raise ValueError(f"Scenario chip not found: {chip_id}")
        return json.loads(row["spec_json"])

    def upsert_scenario_chip(
        self, chip: dict[str, Any], *, tenant: TenantContext, user: UserContext
    ) -> dict[str, Any]:
        """Create or update a scenario chip, returning the chip object."""
        self._assert_can_modify(user)
        tenant_id = tenant.identity.tenant_id
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()

        chip_id = chip.get("id")
        if not chip_id:
            raise ValueError("Scenario chip must have an 'id' field")

        now = self._now_iso()
        spec_json = json.dumps(chip, indent=2, sort_keys=True)

        cur.execute(
            """
            INSERT INTO scenario_chips (id, tenant_id, spec_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id, tenant_id) DO UPDATE SET
                spec_json = excluded.spec_json,
                updated_at = excluded.updated_at
            """,
            (chip_id, tenant_id, spec_json, now, now),
        )
        conn.commit()
        return chip

    def delete_scenario_chip(
        self, chip_id: str, *, tenant: TenantContext, user: UserContext
    ) -> None:
        """Soft delete a scenario chip."""
        self._assert_can_modify(user)
        tenant_id = tenant.identity.tenant_id
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE scenario_chips SET deleted_at = ?
            WHERE id = ? AND tenant_id = ? AND deleted_at IS NULL
            """,
            (self._now_iso(), chip_id, tenant_id),
        )
        conn.commit()

    def close(self) -> None:
        """Release resources held by the store."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None


# ============================================================================
# Supabase Implementation (Placeholder)
# ============================================================================


class SupabaseCustomerChartStore:
    """Supabase-backed CustomerChartStore implementation for staging/production."""

    def __init__(
        self,
        *,
        supabase_config: SupabaseConfig | None = None,
        fs_object_config: FSSpecObjectDocConfig | None = None,
    ) -> None:
        """Initialize Supabase store with configs."""
        if supabase_config is None or fs_object_config is None:
            raise ValueError("supabase_config and fs_object_config must be provided")
        self._supabase_config = supabase_config
        self._fs_object_config = fs_object_config

    def get_chart(
        self,
        chart_id: str,
        version: int | None = None,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> Chart:
        """Return a chart by ID and optional version."""
        raise NotImplementedError("Supabase implementation not yet implemented")

    def get_chart_stack(
        self, chart_stack_id: str, *, tenant: TenantContext, user: UserContext
    ) -> ChartStack:
        """Return a chart stack by ID."""
        raise NotImplementedError("Supabase implementation not yet implemented")

    def get_dashboard(
        self, dashboard_id: str, *, tenant: TenantContext, user: UserContext
    ) -> Dashboard:
        """Return a dashboard by ID."""
        raise NotImplementedError("Supabase implementation not yet implemented")

    def get_chart_data_slice(
        self, slice_id: str, *, tenant: TenantContext, user: UserContext
    ) -> ChartDataSlice:
        """Return chart data slice metadata by ID."""
        raise NotImplementedError("Supabase implementation not yet implemented")

    def get_chart_data(
        self, slice_id: str, *, tenant: TenantContext, user: UserContext
    ) -> dict[str, Any]:
        """Return JSON data rows for a chart data slice."""
        raise NotImplementedError("Supabase implementation not yet implemented")

    def upsert_chart(
        self, chart: Chart, *, tenant: TenantContext, user: UserContext
    ) -> Chart:
        """Create or update a chart."""
        raise NotImplementedError("Supabase implementation not yet implemented")

    def upsert_chart_stack(
        self, stack: ChartStack, *, tenant: TenantContext, user: UserContext
    ) -> ChartStack:
        """Create or update a chart stack."""
        raise NotImplementedError("Supabase implementation not yet implemented")

    def upsert_dashboard(
        self, dashboard: Dashboard, *, tenant: TenantContext, user: UserContext
    ) -> Dashboard:
        """Create or update a dashboard."""
        raise NotImplementedError("Supabase implementation not yet implemented")

    def upsert_data_binding(
        self, binding: DataBinding, *, tenant: TenantContext, user: UserContext
    ) -> DataBinding:
        """Create or update a data binding."""
        raise NotImplementedError("Supabase implementation not yet implemented")

    def upsert_etl_definition(
        self, etl: ETLDefinition, *, tenant: TenantContext, user: UserContext
    ) -> ETLDefinition:
        """Create or update an ETL definition."""
        raise NotImplementedError("Supabase implementation not yet implemented")

    def upsert_output_schema(
        self, schema: OutputSchema, *, tenant: TenantContext, user: UserContext
    ) -> OutputSchema:
        """Create or update an output schema."""
        raise NotImplementedError("Supabase implementation not yet implemented")

    def upsert_chart_data_slice(
        self, slice: ChartDataSlice, *, tenant: TenantContext, user: UserContext
    ) -> ChartDataSlice:
        """Create or update a chart data slice."""
        raise NotImplementedError("Supabase implementation not yet implemented")

    def upsert_insight(
        self, insight: Insight, *, tenant: TenantContext, user: UserContext
    ) -> Insight:
        """Create or update an insight."""
        raise NotImplementedError("Supabase implementation not yet implemented")

    def upsert_recommendation(
        self,
        recommendation: Recommendation,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> Recommendation:
        """Create or update a recommendation."""
        raise NotImplementedError("Supabase implementation not yet implemented")

    def delete_chart(
        self, chart_id: str, version: int, *, tenant: TenantContext, user: UserContext
    ) -> None:
        """Soft delete a chart version."""
        raise NotImplementedError("Supabase implementation not yet implemented")

    def delete_dashboard(
        self, dashboard_id: str, *, tenant: TenantContext, user: UserContext
    ) -> None:
        """Soft delete a dashboard."""
        raise NotImplementedError("Supabase implementation not yet implemented")

    def delete_chart_data_slice(
        self, slice_id: str, *, tenant: TenantContext, user: UserContext
    ) -> None:
        """Soft delete a chart data slice."""
        raise NotImplementedError("Supabase implementation not yet implemented")

    def refresh_chart_data(
        self,
        slice_id: str,
        data: dict[str, Any],
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> ChartDataSlice:
        """Materialize chart data and update slice metadata."""
        raise NotImplementedError("Supabase implementation not yet implemented")

    # Filter APIs
    def get_filter(
        self, filter_id: str, *, tenant: TenantContext, user: UserContext
    ) -> dict[str, Any]:
        """Return a saved filter definition by ID."""
        raise NotImplementedError("Supabase implementation not yet implemented")

    def upsert_filter(
        self, filter_obj: dict[str, Any], *, tenant: TenantContext, user: UserContext
    ) -> dict[str, Any]:
        """Create or update a saved filter."""
        raise NotImplementedError("Supabase implementation not yet implemented")

    def delete_filter(
        self, filter_id: str, *, tenant: TenantContext, user: UserContext
    ) -> None:
        """Soft delete a saved filter."""
        raise NotImplementedError("Supabase implementation not yet implemented")

    # Simulation APIs
    def get_simulation(
        self, simulation_id: str, *, tenant: TenantContext, user: UserContext
    ) -> dict[str, Any]:
        """Return a simulation scenario by ID."""
        raise NotImplementedError("Supabase implementation not yet implemented")

    def upsert_simulation(
        self, simulation: dict[str, Any], *, tenant: TenantContext, user: UserContext
    ) -> dict[str, Any]:
        """Create or update a simulation scenario."""
        raise NotImplementedError("Supabase implementation not yet implemented")

    def delete_simulation(
        self, simulation_id: str, *, tenant: TenantContext, user: UserContext
    ) -> None:
        """Soft delete a simulation scenario."""
        raise NotImplementedError("Supabase implementation not yet implemented")

    # Scenario Chip APIs
    def get_scenario_chip(
        self, chip_id: str, *, tenant: TenantContext, user: UserContext
    ) -> dict[str, Any]:
        """Return a scenario chip by ID."""
        raise NotImplementedError("Supabase implementation not yet implemented")

    def upsert_scenario_chip(
        self, chip: dict[str, Any], *, tenant: TenantContext, user: UserContext
    ) -> dict[str, Any]:
        """Create or update a scenario chip."""
        raise NotImplementedError("Supabase implementation not yet implemented")

    def delete_scenario_chip(
        self, chip_id: str, *, tenant: TenantContext, user: UserContext
    ) -> None:
        """Soft delete a scenario chip."""
        raise NotImplementedError("Supabase implementation not yet implemented")

    def close(self) -> None:
        """Release resources held by the store."""
        pass


# ============================================================================
# Factory Function
# ============================================================================


def create_customer_chart_store(config: CustomerChartStoreConfig) -> CustomerChartStore:
    """Create a CustomerChartStore instance based on config."""
    if config.backend == "sqlite":
        assert config.sqlite is not None, "sqlite config must be provided"
        assert config.fsspec_local is not None, "fsspec_local config must be provided"
        return SqliteCustomerChartStore(
            sqlite_config=config.sqlite,
            fs_local_config=config.fsspec_local,
        )
    if config.backend == "supabase":
        assert config.supabase is not None, "supabase config must be provided"
        assert config.fsspec_object is not None, "fsspec_object config must be provided"
        return SupabaseCustomerChartStore(
            supabase_config=config.supabase,
            fs_object_config=config.fsspec_object,
        )
    raise ValueError(f"Unsupported backend: {config.backend}")
