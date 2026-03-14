"""Tests for CustomerChartStore implementation."""

from __future__ import annotations

import os
import shutil
import tempfile
from datetime import UTC, datetime

import pytest
from google.protobuf.timestamp_pb2 import Timestamp

from xlake.core import TenantContext, TenantIdentity, UserContext
from xlake.models import (
    AnnotationTarget,
    Chart,
    ChartDataSlice,
    ChartPlacement,
    ChartStack,
    ChartType,
    Dashboard,
    DashboardLayout,
    DataBinding,
    DataSource,
    Dimension,
    FieldRole,
    FieldType,
    Filter,
    Highlight,
    HighlightType,
    Insight,
    InsightType,
    OutputField,
    OutputSchema,
    Projection,
    Recommendation,
    RecommendationType,
    RefreshPolicy,
)
from xlake.stores.config import (
    FSSpecLocalDocConfig,
    SqliteConfig,
)
from xlake.stores.customer_chart_store import (
    ETLDefinition,
    SqliteCustomerChartStore,
)


def should_refresh_now(
    policy: RefreshPolicy | None,
    last_refreshed_at: Timestamp | None = None,
    now: datetime | None = None,
) -> bool:
    """Check if data should be refreshed based on refresh policy.

    Args:
        policy: RefreshPolicy protobuf message (defines the policy)
        last_refreshed_at: Timestamp of last refresh (stored in DB, not protobuf)
        now: Current time (defaults to now)
    """
    if policy is None:
        return True  # fail safe

    if now is None:
        now = datetime.now(UTC)

    if last_refreshed_at is None:
        return True

    # Convert protobuf Timestamp to datetime
    last_refreshed = last_refreshed_at.ToDatetime()
    if last_refreshed.tzinfo is None:
        last_refreshed = last_refreshed.replace(tzinfo=UTC)

    # Always-fresh policy
    if policy.max_age_seconds == 0:
        return True

    age = (now - last_refreshed).total_seconds()

    # Clock skew safety
    if age < 0:
        return False

    is_stale = age > policy.max_age_seconds

    # If stale data is not allowed, we MUST refresh
    if is_stale and not policy.allow_stale_reads:
        return True

    # Otherwise refresh only if stale reads are allowed
    return is_stale


def _make_dev_store(tmpdir: str) -> SqliteCustomerChartStore:
    """Create a SQLite-based store for testing."""
    sqlite_path = os.path.join(tmpdir, "chart.db")
    base_dir = os.path.join(tmpdir, "chart_data")
    os.makedirs(base_dir, exist_ok=True)
    return SqliteCustomerChartStore(
        sqlite_config=SqliteConfig(database_path=sqlite_path),
        fs_local_config=FSSpecLocalDocConfig(base_dir=base_dir),
    )


def _user(tenant: str = "tenant_test") -> UserContext:
    """Create a test user context."""
    return UserContext(
        user_id="u1",
        tenant_id=tenant,
        role="admin",
    )


def _tenant(tenant: str = "tenant_test") -> TenantContext:
    """Create a test tenant context."""
    ident = TenantIdentity(
        tenant_id=tenant,
        tenant_name="Test Tenant",
        industry="testing",
        region="EU",
        timezone="Europe/Paris",
        locale="en_US",
    )
    return TenantContext(identity=ident)


def test_create_and_get_chart():
    """Test creating and retrieving a chart."""
    tmpdir = tempfile.mkdtemp(prefix="xlake_chart_")
    try:
        store = _make_dev_store(tmpdir)
        uc = _user()
        tc = _tenant()

        chart = Chart(
            id="chart_violin_sales_v1",
            title="Sales Distribution by Category",
            chart_type="violin_plot",
            dimensions=[
                Dimension(field="name", type="category"),
                Dimension(field="value", type="numeric"),
            ],
            version=1,
            schema_version=1,
        )

        created = store.upsert_chart(chart, tenant=tc, user=uc)
        assert created.id == chart.id
        assert created.version == 1

        retrieved = store.get_chart(chart.id, version=1, tenant=tc, user=uc)
        assert retrieved.id == chart.id
        assert retrieved.title == chart.title
        assert retrieved.chart_type == chart.chart_type
        assert len(retrieved.dimensions) == 2

        # Test getting latest version
        retrieved_latest = store.get_chart(chart.id, tenant=tc, user=uc)
        assert retrieved_latest.version == 1
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_chart_version_bump():
    """Test that chart version increments on mutation."""
    tmpdir = tempfile.mkdtemp(prefix="xlake_chart_")
    try:
        store = _make_dev_store(tmpdir)
        uc = _user()
        tc = _tenant()

        chart_v1 = Chart(
            id="chart_test",
            title="Test Chart",
            chart_type="bar_chart_vertical",
            version=1,
            schema_version=1,
        )
        store.upsert_chart(chart_v1, tenant=tc, user=uc)

        # Update chart with new version
        chart_v2 = Chart(
            id="chart_test",
            title="Test Chart Updated",
            chart_type="line_chart",  # Changed chart type
            version=2,
            schema_version=1,
        )
        store.upsert_chart(chart_v2, tenant=tc, user=uc)

        # Both versions should exist
        v1 = store.get_chart("chart_test", version=1, tenant=tc, user=uc)
        v2 = store.get_chart("chart_test", version=2, tenant=tc, user=uc)

        assert v1.version == 1
        assert v1.chart_type == ChartType.Value("bar_chart_vertical")
        assert v2.version == 2
        assert v2.chart_type == ChartType.Value("line_chart")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_chart_data_slice_lifecycle():
    """Test creating, materializing, and refreshing chart data slices."""
    tmpdir = tempfile.mkdtemp(prefix="xlake_chart_")
    try:
        store = _make_dev_store(tmpdir)
        uc = _user()
        tc = _tenant()

        # Create output schema
        schema = OutputSchema(
            id="schema_violin_sales_v1",
            version=1,
            fields=[
                OutputField(
                    name="row_id", type=FieldType.STRING, role=FieldRole.IDENTIFIER
                ),
                OutputField(
                    name="name", type=FieldType.STRING, role=FieldRole.DIMENSION
                ),
                OutputField(name="value", type=FieldType.FLOAT, role=FieldRole.MEASURE),
            ],
            primary_key=["row_id"],
            schema_version=1,
        )
        store.upsert_output_schema(schema, tenant=tc, user=uc)

        # Create data binding
        binding = DataBinding(
            id="binding_sales_by_category",
            version=1,
            sources=[DataSource(system="customer_datalake", table="sales")],
            schema_version=1,
        )
        store.upsert_data_binding(binding, tenant=tc, user=uc)

        # Create chart
        chart = Chart(
            id="chart_violin_sales_v1",
            title="Sales Distribution",
            chart_type="violin_plot",
            version=1,
            schema_version=1,
        )
        store.upsert_chart(chart, tenant=tc, user=uc)

        # Create chart data slice with refresh policy (not yet materialized)
        refresh_policy = RefreshPolicy(
            max_age_seconds=3600,
            allow_stale_reads=True,
        )
        slice_meta = ChartDataSlice(
            id="slice_chart_violin_sales_v1",
            chart_id="chart_violin_sales_v1",
            chart_version=1,
            data_binding_id="binding_sales_by_category",
            data_binding_version=1,
            output_schema_id="schema_violin_sales_v1",
            refresh_policy=refresh_policy,
        )
        store.upsert_chart_data_slice(slice_meta, tenant=tc, user=uc)

        # Materialize data
        data = {
            "schema_id": "schema_violin_sales_v1",
            "rows": [
                {"row_id": "r1", "name": "Shoes", "value": 120.0},
                {"row_id": "r2", "name": "Shoes", "value": 95.0},
                {"row_id": "r3", "name": "Hats", "value": 40.0},
            ],
        }
        updated_slice = store.refresh_chart_data(
            "slice_chart_violin_sales_v1", data, tenant=tc, user=uc
        )

        assert updated_slice.json_uri is not None
        assert updated_slice.data_hash is not None
        assert updated_slice.schema_hash is not None
        assert updated_slice.HasField("generated_at")

        # Retrieve materialized data
        retrieved_data = store.get_chart_data(
            "slice_chart_violin_sales_v1", tenant=tc, user=uc
        )
        assert retrieved_data["schema_id"] == "schema_violin_sales_v1"
        assert len(retrieved_data["rows"]) == 3
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_dashboard_composition():
    """Test creating a dashboard with chart stacks."""
    tmpdir = tempfile.mkdtemp(prefix="xlake_chart_")
    try:
        store = _make_dev_store(tmpdir)
        uc = _user()
        tc = _tenant()

        # Create charts
        chart1 = Chart(
            id="chart1",
            title="Chart 1",
            chart_type="bar_chart_vertical",
            version=1,
            schema_version=1,
        )
        chart2 = Chart(
            id="chart2",
            title="Chart 2",
            chart_type="line_chart",
            version=1,
            schema_version=1,
        )
        store.upsert_chart(chart1, tenant=tc, user=uc)
        store.upsert_chart(chart2, tenant=tc, user=uc)

        # Create chart stack
        stack = ChartStack(
            id="stack_sales",
            title="Sales Analysis",
            charts=[chart1, chart2],
            schema_version=1,
        )
        store.upsert_chart_stack(stack, tenant=tc, user=uc)

        # Create dashboard
        dashboard = Dashboard(
            id="dashboard_main",
            title="Main Dashboard",
            description="Primary dashboard",
            stacks=[stack],
            layout=DashboardLayout(
                placements=[
                    ChartPlacement(chart_id="chart1", level=1, order=1),
                    ChartPlacement(chart_id="chart2", level=1, order=2),
                ]
            ),
            schema_version=1,
        )
        store.upsert_dashboard(dashboard, tenant=tc, user=uc)

        # Retrieve dashboard
        retrieved = store.get_dashboard("dashboard_main", tenant=tc, user=uc)
        assert retrieved.id == "dashboard_main"
        assert len(retrieved.stacks) == 1
        assert retrieved.stacks[0].id == "stack_sales"
        assert len(retrieved.stacks[0].charts) == 2
        assert retrieved.layout is not None
        assert len(retrieved.layout.placements) == 2
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_data_refresh_path():
    """Test deterministic materialization with TTL."""
    tmpdir = tempfile.mkdtemp(prefix="xlake_chart_")
    try:
        store = _make_dev_store(tmpdir)
        uc = _user()
        tc = _tenant()

        # Setup schema and binding
        schema = OutputSchema(
            id="schema_test",
            version=1,
            fields=[
                OutputField(
                    name="row_id", type=FieldType.STRING, role=FieldRole.IDENTIFIER
                )
            ],
            schema_version=1,
        )
        store.upsert_output_schema(schema, tenant=tc, user=uc)

        binding = DataBinding(
            id="binding_test",
            version=1,
            sources=[DataSource(system="customer_datalake", table="test")],
            schema_version=1,
        )
        store.upsert_data_binding(binding, tenant=tc, user=uc)

        chart = Chart(
            id="chart_test",
            title="Test",
            chart_type="bar_chart_vertical",
            version=1,
            schema_version=1,
        )
        store.upsert_chart(chart, tenant=tc, user=uc)

        # Create slice with refresh policy
        refresh_policy = RefreshPolicy(
            max_age_seconds=3600,
            allow_stale_reads=True,
        )
        slice_meta = ChartDataSlice(
            id="slice_test",
            chart_id="chart_test",
            chart_version=1,
            data_binding_id="binding_test",
            data_binding_version=1,
            output_schema_id="schema_test",
            refresh_policy=refresh_policy,
        )
        store.upsert_chart_data_slice(slice_meta, tenant=tc, user=uc)

        # Materialize initial data
        data1 = {"schema_id": "schema_test", "rows": [{"row_id": "r1"}]}
        slice1 = store.refresh_chart_data("slice_test", data1, tenant=tc, user=uc)
        assert slice1.generated_at is not None

        # Retrieve slice metadata and verify refresh_policy was stored
        retrieved = store.get_chart_data_slice("slice_test", tenant=tc, user=uc)
        assert retrieved.HasField("refresh_policy")
        assert retrieved.refresh_policy.max_age_seconds == 3600
        assert retrieved.refresh_policy.allow_stale_reads is True
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_insights_and_recommendations():
    """Test creating insights and recommendations with highlights."""
    tmpdir = tempfile.mkdtemp(prefix="xlake_chart_")
    try:
        store = _make_dev_store(tmpdir)
        uc = _user()
        tc = _tenant()

        # Setup slice
        schema = OutputSchema(
            id="schema_test",
            version=1,
            fields=[
                OutputField(
                    name="row_id", type=FieldType.STRING, role=FieldRole.IDENTIFIER
                )
            ],
            schema_version=1,
        )
        store.upsert_output_schema(schema, tenant=tc, user=uc)

        binding = DataBinding(
            id="binding_test",
            version=1,
            sources=[DataSource(system="customer_datalake", table="test")],
            schema_version=1,
        )
        store.upsert_data_binding(binding, tenant=tc, user=uc)

        chart = Chart(
            id="chart_test",
            title="Test",
            chart_type="bar_chart_vertical",
            version=1,
            schema_version=1,
        )
        store.upsert_chart(chart, tenant=tc, user=uc)

        refresh_policy = RefreshPolicy(
            max_age_seconds=3600,
            allow_stale_reads=True,
        )
        slice_meta = ChartDataSlice(
            id="slice_test",
            chart_id="chart_test",
            chart_version=1,
            data_binding_id="binding_test",
            data_binding_version=1,
            output_schema_id="schema_test",
            refresh_policy=refresh_policy,
        )
        store.upsert_chart_data_slice(slice_meta, tenant=tc, user=uc)

        # Create insight with highlight
        highlight = Highlight(
            id="highlight1",
            type=HighlightType.Value("ROW"),
            chart_data_slice_id="slice_test",
            row_ids=["r1", "r2"],
            description="Outliers detected",
        )

        insight = Insight(
            id="insight1",
            type=InsightType.Value("WARNING"),
            summary="Outliers detected in March",
            detail="Several data points exceed normal range",
            confidence=0.85,
            target=AnnotationTarget(chart_id="chart_test"),
            highlight_ids=[highlight.id],
            schema_version=1,
        )
        store.upsert_insight(insight, tenant=tc, user=uc)

        # Create recommendation
        recommendation = Recommendation(
            id="rec1",
            type=RecommendationType.Value("REPORT"),
            summary="Generate monthly report",
            detail="Consider exporting data for further analysis",
            priority="high",
            action_params={"format": "pdf", "frequency": "monthly"},
        )
        store.upsert_recommendation(recommendation, tenant=tc, user=uc)

        # Note: We don't have get methods for insights/recommendations in the protocol yet
        # but we can verify they were stored by checking the database directly
        # or by adding get methods later
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_soft_delete():
    """Test soft delete behavior."""
    tmpdir = tempfile.mkdtemp(prefix="xlake_chart_")
    try:
        store = _make_dev_store(tmpdir)
        uc = _user()
        tc = _tenant()

        chart = Chart(
            id="chart_delete_test",
            title="To Be Deleted",
            chart_type="bar_chart_vertical",
            version=1,
            schema_version=1,
        )
        store.upsert_chart(chart, tenant=tc, user=uc)

        # Verify it exists
        retrieved = store.get_chart("chart_delete_test", tenant=tc, user=uc)
        assert retrieved.id == "chart_delete_test"

        # Soft delete
        store.delete_chart("chart_delete_test", version=1, tenant=tc, user=uc)

        # Should raise error when trying to retrieve
        with pytest.raises(ValueError, match="not found"):
            store.get_chart("chart_delete_test", version=1, tenant=tc, user=uc)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_canonical_json_serialization():
    """Test that JSON serialization is canonical (stable for diffs)."""
    tmpdir = tempfile.mkdtemp(prefix="xlake_chart_")
    try:
        store = _make_dev_store(tmpdir)
        uc = _user()
        tc = _tenant()

        chart = Chart(
            id="chart_json_test",
            title="JSON Test",
            chart_type="bar_chart_vertical",
            dimensions=[
                Dimension(field="category", type="category"),
                Dimension(field="value", type="numeric"),
            ],
            filters=[Filter(field="region", operator="eq", value="EU")],
            version=1,
            schema_version=1,
        )

        store.upsert_chart(chart, tenant=tc, user=uc)
        retrieved = store.get_chart("chart_json_test", tenant=tc, user=uc)

        # Verify canonical structure (all fields present, sorted)
        assert retrieved.id == chart.id
        assert retrieved.version == chart.version
        assert retrieved.schema_version == chart.schema_version
        assert len(retrieved.dimensions) == 2
        assert len(retrieved.filters) == 1

        # Verify JSON round-trip preserves structure
        json1 = store._canonical_json(chart)
        json2 = store._canonical_json(retrieved)
        # Should be identical (canonical)
        assert json1 == json2
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_combo_chart_persistence():
    """Test storing and retrieving a combo chart with sub_charts."""
    tmpdir = tempfile.mkdtemp(prefix="xlake_chart_")
    try:
        store = _make_dev_store(tmpdir)
        uc = _user()
        tc = _tenant()

        combo = Chart(
            id="chart_combo_test",
            title="Revenue vs Margin",
            chart_type="combo",
            chart_data_slice_ids=["slice_financials"],
            version=1,
            schema_version=1,
            sub_charts=[
                Chart(
                    id="chart_combo_test__bars",
                    title="Revenue & Costs",
                    chart_type="bar_chart_vertical",
                    dimensions=[
                        Dimension(field="quarter", type="time"),
                        Dimension(field="revenue", type="numeric"),
                    ],
                ),
                Chart(
                    id="chart_combo_test__line",
                    title="Profit Margin Trend",
                    chart_type="line_chart",
                    dimensions=[
                        Dimension(field="quarter", type="time"),
                        Dimension(field="profit_margin_pct", type="numeric"),
                    ],
                ),
            ],
        )

        store.upsert_chart(combo, tenant=tc, user=uc)
        retrieved = store.get_chart("chart_combo_test", tenant=tc, user=uc)

        assert retrieved.id == "chart_combo_test"
        assert retrieved.chart_type == ChartType.Value("combo")
        assert len(retrieved.sub_charts) == 2
        assert retrieved.sub_charts[0].id == "chart_combo_test__bars"
        assert retrieved.sub_charts[0].chart_type == ChartType.Value(
            "bar_chart_vertical"
        )
        assert len(retrieved.sub_charts[0].dimensions) == 2
        assert retrieved.sub_charts[1].id == "chart_combo_test__line"
        assert retrieved.sub_charts[1].chart_type == ChartType.Value("line_chart")
        assert len(retrieved.sub_charts[1].dimensions) == 2
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_etl_definition():
    """Test ETL definition storage."""
    tmpdir = tempfile.mkdtemp(prefix="xlake_chart_")
    try:
        store = _make_dev_store(tmpdir)
        uc = _user()
        tc = _tenant()

        etl = ETLDefinition(
            etl_id="etl_sales_v1",
            version=1,
            ibis="sales.filter(sales.region == 'EU').select(sales.category, sales.amount)",
            polars="df.filter(pl.col('region') == 'EU').select(['category', 'amount'])",
        )

        created = store.upsert_etl_definition(etl, tenant=tc, user=uc)
        assert created.etl_id == etl.etl_id
        assert created.version == 1
        assert "filter" in created.ibis
        assert "pl.col" in created.polars or len(created.polars) > 0
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_refresh_policy_logic():
    """Test refresh policy logic with should_refresh_now function."""
    tmpdir = tempfile.mkdtemp(prefix="xlake_chart_")
    try:
        store = _make_dev_store(tmpdir)
        uc = _user()
        tc = _tenant()

        # Setup required artifacts
        schema = OutputSchema(
            id="schema_test",
            version=1,
            fields=[
                OutputField(
                    name="row_id", type=FieldType.STRING, role=FieldRole.IDENTIFIER
                )
            ],
            schema_version=1,
        )
        store.upsert_output_schema(schema, tenant=tc, user=uc)

        binding = DataBinding(
            id="binding_test",
            version=1,
            sources=[DataSource(system="test", table="data")],
            schema_version=1,
        )
        store.upsert_data_binding(binding, tenant=tc, user=uc)

        chart = Chart(
            id="chart_test",
            title="Test",
            chart_type="bar_chart_vertical",
            version=1,
            schema_version=1,
        )
        store.upsert_chart(chart, tenant=tc, user=uc)

        # Create a chart data slice with refresh policy
        now = datetime.now(UTC)
        from datetime import timedelta

        last_refresh_time = now - timedelta(minutes=30)
        last_refresh_ts = Timestamp()
        last_refresh_ts.FromDatetime(last_refresh_time)

        refresh_policy = RefreshPolicy(
            max_age_seconds=3600,  # 1 hour
            allow_stale_reads=True,
        )

        slice_meta = ChartDataSlice(
            id="slice_test_refresh",
            chart_id="chart_test",
            chart_version=1,
            data_binding_id="binding_test",
            data_binding_version=1,
            output_schema_id="schema_test",
            refresh_policy=refresh_policy,
        )
        store.upsert_chart_data_slice(slice_meta, tenant=tc, user=uc)

        # Manually set last_refreshed_at in DB for testing (simulating a refresh 30 min ago)
        import sqlite3

        tenant_id = tc.identity.tenant_id
        conn = sqlite3.connect(store._sqlite_config.database_path)
        cur = conn.cursor()
        cur.execute(
            "UPDATE chart_data_slices SET last_refreshed_at = ? WHERE id = ? AND tenant_id = ?",
            (last_refresh_time.isoformat(), "slice_test_refresh", tenant_id),
        )
        conn.commit()
        conn.close()

        # Retrieve and test refresh logic
        retrieved = store.get_chart_data_slice("slice_test_refresh", tenant=tc, user=uc)
        policy = retrieved.refresh_policy
        last_refreshed_at = store._last_refreshed_at_cache.get("slice_test_refresh")

        # Should not refresh - data is only 30 minutes old, max_age is 1 hour
        assert not should_refresh_now(policy, last_refreshed_at, now)

        # Should refresh - data is 2 hours old, exceeds max_age
        future_time = now + timedelta(hours=2)
        assert should_refresh_now(policy, last_refreshed_at, future_time)

        # Test with allow_stale_reads=False - should refresh even if slightly stale
        policy_no_stale = RefreshPolicy(
            max_age_seconds=3600,
            allow_stale_reads=False,
        )
        # Data is 30 minutes old, but allow_stale_reads=False means we check freshness
        # Since it's not stale yet (30 min < 60 min), should not refresh
        assert not should_refresh_now(policy_no_stale, last_refreshed_at, now)
        # But if stale, must refresh
        assert should_refresh_now(policy_no_stale, last_refreshed_at, future_time)

        # Test always-fresh policy (max_age_seconds=0)
        always_fresh = RefreshPolicy(
            max_age_seconds=0,
            allow_stale_reads=False,
        )
        assert should_refresh_now(always_fresh, last_refreshed_at, now)

        # Test None policy (fail-safe)
        assert should_refresh_now(None, None, now)

        # Test policy without last_refreshed_at
        no_refresh_time = RefreshPolicy(
            max_age_seconds=3600,
            allow_stale_reads=True,
        )
        assert should_refresh_now(no_refresh_time, None, now)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_data_binding_with_projections():
    """Test data binding with sources, filters, and projections."""
    tmpdir = tempfile.mkdtemp(prefix="xlake_chart_")
    try:
        store = _make_dev_store(tmpdir)
        uc = _user()
        tc = _tenant()

        binding = DataBinding(
            id="binding_complex",
            version=1,
            sources=[
                DataSource(system="customer_datalake", table="sales"),
                DataSource(system="customer_datalake", table="products"),
            ],
            filters=[],
            projections=[
                Projection(field="product_category", alias="name"),
                Projection(field="amount", alias="value"),
            ],
            schema_version=1,
        )

        created = store.upsert_data_binding(binding, tenant=tc, user=uc)
        assert created.id == binding.id
        assert len(created.sources) == 2
        assert len(created.projections) == 2
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_saved_filter_crud():
    """Test create, read, update, delete for saved filters."""
    tmpdir = tempfile.mkdtemp(prefix="xlake_chart_")
    try:
        store = _make_dev_store(tmpdir)
        uc = _user()
        tc = _tenant()

        # Create filter
        filter_obj = {
            "id": "filter_region_eu",
            "name": "Europe Region",
            "field": "region",
            "operator": "eq",
            "value": "EU",
        }
        created = store.upsert_filter(filter_obj, tenant=tc, user=uc)
        assert created["id"] == "filter_region_eu"
        assert created["name"] == "Europe Region"

        # Read filter
        retrieved = store.get_filter("filter_region_eu", tenant=tc, user=uc)
        assert retrieved["id"] == "filter_region_eu"
        assert retrieved["value"] == "EU"

        # Update filter
        filter_obj["value"] = "US"
        updated = store.upsert_filter(filter_obj, tenant=tc, user=uc)
        assert updated["value"] == "US"

        retrieved = store.get_filter("filter_region_eu", tenant=tc, user=uc)
        assert retrieved["value"] == "US"

        # Delete filter
        store.delete_filter("filter_region_eu", tenant=tc, user=uc)
        with pytest.raises(ValueError, match="not found"):
            store.get_filter("filter_region_eu", tenant=tc, user=uc)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_simulation_crud():
    """Test create, read, update, delete for simulations."""
    tmpdir = tempfile.mkdtemp(prefix="xlake_chart_")
    try:
        store = _make_dev_store(tmpdir)
        uc = _user()
        tc = _tenant()

        # Create simulation
        simulation = {
            "id": "sim_growth_scenario",
            "name": "High Growth Scenario",
            "description": "10% annual growth projection",
            "parameters": {"growth_rate": 0.10, "years": 5},
        }
        created = store.upsert_simulation(simulation, tenant=tc, user=uc)
        assert created["id"] == "sim_growth_scenario"
        assert created["parameters"]["growth_rate"] == 0.10

        # Read simulation
        retrieved = store.get_simulation("sim_growth_scenario", tenant=tc, user=uc)
        assert retrieved["name"] == "High Growth Scenario"

        # Update simulation
        simulation["parameters"]["growth_rate"] = 0.15
        updated = store.upsert_simulation(simulation, tenant=tc, user=uc)
        assert updated["parameters"]["growth_rate"] == 0.15

        # Delete simulation
        store.delete_simulation("sim_growth_scenario", tenant=tc, user=uc)
        with pytest.raises(ValueError, match="not found"):
            store.get_simulation("sim_growth_scenario", tenant=tc, user=uc)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_scenario_chip_crud():
    """Test create, read, update, delete for scenario chips."""
    tmpdir = tempfile.mkdtemp(prefix="xlake_chart_")
    try:
        store = _make_dev_store(tmpdir)
        uc = _user()
        tc = _tenant()

        # Create scenario chip
        chip = {
            "id": "chip_recession",
            "label": "Recession",
            "description": "Economic downturn scenario",
            "simulation_id": "sim_recession",
            "color": "#FF5733",
        }
        created = store.upsert_scenario_chip(chip, tenant=tc, user=uc)
        assert created["id"] == "chip_recession"
        assert created["label"] == "Recession"

        # Read scenario chip
        retrieved = store.get_scenario_chip("chip_recession", tenant=tc, user=uc)
        assert retrieved["description"] == "Economic downturn scenario"

        # Update scenario chip
        chip["color"] = "#33FF57"
        updated = store.upsert_scenario_chip(chip, tenant=tc, user=uc)
        assert updated["color"] == "#33FF57"

        # Delete scenario chip
        store.delete_scenario_chip("chip_recession", tenant=tc, user=uc)
        with pytest.raises(ValueError, match="not found"):
            store.get_scenario_chip("chip_recession", tenant=tc, user=uc)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_filter_requires_id():
    """Test that upserting a filter without an ID raises an error."""
    tmpdir = tempfile.mkdtemp(prefix="xlake_chart_")
    try:
        store = _make_dev_store(tmpdir)
        uc = _user()
        tc = _tenant()

        with pytest.raises(ValueError, match="'id' field"):
            store.upsert_filter({"name": "No ID"}, tenant=tc, user=uc)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_simulation_requires_id():
    """Test that upserting a simulation without an ID raises an error."""
    tmpdir = tempfile.mkdtemp(prefix="xlake_chart_")
    try:
        store = _make_dev_store(tmpdir)
        uc = _user()
        tc = _tenant()

        with pytest.raises(ValueError, match="'id' field"):
            store.upsert_simulation({"name": "No ID"}, tenant=tc, user=uc)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_scenario_chip_requires_id():
    """Test that upserting a scenario chip without an ID raises an error."""
    tmpdir = tempfile.mkdtemp(prefix="xlake_chart_")
    try:
        store = _make_dev_store(tmpdir)
        uc = _user()
        tc = _tenant()

        with pytest.raises(ValueError, match="'id' field"):
            store.upsert_scenario_chip({"label": "No ID"}, tenant=tc, user=uc)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
