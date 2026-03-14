from __future__ import annotations

import pytest

from xlake.core import UserContext
from xlake.stores.config import (
    CustomerAppLogicStoreConfig,
    SqliteConfig,
    SupabaseConfig,
)
from xlake.stores.customer_app_logic_store import (
    VersionSnapshot,
    create_customer_app_logic_store,
)


def test_build_store_selects_sqlite_in_development() -> None:
    cfg = CustomerAppLogicStoreConfig(
        backend="sqlite",
        sqlite=SqliteConfig(database_path=":memory:"),
    )
    store = create_customer_app_logic_store(cfg)
    try:
        ctx = store.get_user_context("u1")
        assert isinstance(ctx, UserContext)
    finally:
        store.close()


def test_build_store_selects_supabase_in_production() -> None:
    cfg = CustomerAppLogicStoreConfig(
        backend="supabase",
        supabase=SupabaseConfig(url="https://example.supabase.co", api_key="k"),
    )
    store = create_customer_app_logic_store(cfg)
    try:
        ctx = store.get_user_context("u2")
        assert isinstance(ctx, UserContext)
    finally:
        store.close()


def test_sqlite_store_user_stubs_raise_not_implemented() -> None:
    cfg = CustomerAppLogicStoreConfig(
        backend="sqlite",
        sqlite=SqliteConfig(database_path=":memory:"),
    )
    store = create_customer_app_logic_store(cfg)
    try:
        # User methods
        with pytest.raises(NotImplementedError):
            store.get_user("u")
        with pytest.raises(NotImplementedError):
            store.upsert_user({})
        with pytest.raises(NotImplementedError):
            store.delete_user("u")
        with pytest.raises(NotImplementedError):
            store.get_user_permissions("u")
        with pytest.raises(NotImplementedError):
            store.set_user_permissions("u", {})
        # Conversation methods
        with pytest.raises(NotImplementedError):
            store.get_conversation("conv")
        with pytest.raises(NotImplementedError):
            store.create_conversation({})
        with pytest.raises(NotImplementedError):
            store.append_message("conv", {})
        with pytest.raises(NotImplementedError):
            store.delete_conversation("conv")
    finally:
        store.close()


def test_supabase_store_stubs_raise_not_implemented() -> None:
    cfg = CustomerAppLogicStoreConfig(
        backend="supabase",
        supabase=SupabaseConfig(url="https://example.supabase.co", api_key="k"),
    )
    store = create_customer_app_logic_store(cfg)
    try:
        with pytest.raises(NotImplementedError):
            store.get_user("u")
        with pytest.raises(NotImplementedError):
            store.commit_version("conv", 0, "stack", {}, "test", "user")
    finally:
        store.close()


# ============================================================================
# Version Management Tests
# ============================================================================


def test_commit_version_creates_snapshot() -> None:
    """Test that commit_version creates a new version snapshot."""
    cfg = CustomerAppLogicStoreConfig(
        backend="sqlite",
        sqlite=SqliteConfig(database_path=":memory:"),
    )
    store = create_customer_app_logic_store(cfg)
    try:
        chart_stack_snapshot = {
            "id": "stack_sales",
            "title": "Sales Analysis",
            "charts": [{"id": "chart1", "title": "Revenue"}],
        }

        version = store.commit_version(
            conversation_id="conv_123",
            message_cursor=5,
            chart_stack_id="stack_sales",
            chart_stack_snapshot=chart_stack_snapshot,
            description="Initial analysis setup",
            user_id="user_alice",
        )

        assert isinstance(version, VersionSnapshot)
        assert version.version_id is not None
        assert len(version.version_id) == 12  # SHA256 truncated to 12 chars
        assert version.conversation_id == "conv_123"
        assert version.message_cursor == 5
        assert version.chart_stack_id == "stack_sales"
        assert version.chart_stack_snapshot == chart_stack_snapshot
        assert version.description == "Initial analysis setup"
        assert version.parent_version_id is None  # First commit has no parent
        assert version.committed_by == "user_alice"
        assert version.committed_at is not None
    finally:
        store.close()


def test_commit_version_links_to_parent() -> None:
    """Test that subsequent commits link to parent version."""
    cfg = CustomerAppLogicStoreConfig(
        backend="sqlite",
        sqlite=SqliteConfig(database_path=":memory:"),
    )
    store = create_customer_app_logic_store(cfg)
    try:
        # First commit
        v1 = store.commit_version(
            conversation_id="conv_123",
            message_cursor=3,
            chart_stack_id="stack_v1",
            chart_stack_snapshot={"charts": []},
            description="First version",
            user_id="alice",
        )

        # Second commit - should link to first
        v2 = store.commit_version(
            conversation_id="conv_123",
            message_cursor=7,
            chart_stack_id="stack_v2",
            chart_stack_snapshot={"charts": [{"id": "chart1"}]},
            description="Added chart",
            user_id="bob",
        )

        # Third commit - should link to second
        v3 = store.commit_version(
            conversation_id="conv_123",
            message_cursor=10,
            chart_stack_id="stack_v3",
            chart_stack_snapshot={"charts": [{"id": "chart1"}, {"id": "chart2"}]},
            description="Added another chart",
            user_id="alice",
        )

        assert v1.parent_version_id is None
        assert v2.parent_version_id == v1.version_id
        assert v3.parent_version_id == v2.version_id
    finally:
        store.close()


def test_get_version_retrieves_snapshot() -> None:
    """Test that get_version retrieves a stored snapshot."""
    cfg = CustomerAppLogicStoreConfig(
        backend="sqlite",
        sqlite=SqliteConfig(database_path=":memory:"),
    )
    store = create_customer_app_logic_store(cfg)
    try:
        original = store.commit_version(
            conversation_id="conv_456",
            message_cursor=10,
            chart_stack_id="stack_test",
            chart_stack_snapshot={"key": "value"},
            description="Test snapshot",
            user_id="user1",
        )

        retrieved = store.get_version(original.version_id)

        assert retrieved.version_id == original.version_id
        assert retrieved.conversation_id == original.conversation_id
        assert retrieved.message_cursor == original.message_cursor
        assert retrieved.chart_stack_id == original.chart_stack_id
        assert retrieved.chart_stack_snapshot == original.chart_stack_snapshot
        assert retrieved.description == original.description
        assert retrieved.committed_by == original.committed_by
    finally:
        store.close()


def test_get_version_not_found_raises() -> None:
    """Test that get_version raises ValueError for unknown version."""
    cfg = CustomerAppLogicStoreConfig(
        backend="sqlite",
        sqlite=SqliteConfig(database_path=":memory:"),
    )
    store = create_customer_app_logic_store(cfg)
    try:
        with pytest.raises(ValueError, match="not found"):
            store.get_version("nonexistent_version_id")
    finally:
        store.close()


def test_get_version_history_returns_newest_first() -> None:
    """Test that get_version_history returns versions newest to oldest."""
    cfg = CustomerAppLogicStoreConfig(
        backend="sqlite",
        sqlite=SqliteConfig(database_path=":memory:"),
    )
    store = create_customer_app_logic_store(cfg)
    try:
        v1 = store.commit_version(
            conversation_id="conv_hist",
            message_cursor=1,
            chart_stack_id="stack1",
            chart_stack_snapshot={},
            description="Version 1",
            user_id="user",
        )
        v2 = store.commit_version(
            conversation_id="conv_hist",
            message_cursor=2,
            chart_stack_id="stack2",
            chart_stack_snapshot={},
            description="Version 2",
            user_id="user",
        )
        v3 = store.commit_version(
            conversation_id="conv_hist",
            message_cursor=3,
            chart_stack_id="stack3",
            chart_stack_snapshot={},
            description="Version 3",
            user_id="user",
        )

        history = store.get_version_history("conv_hist")

        assert len(history) == 3
        assert history[0].version_id == v3.version_id  # Newest first
        assert history[1].version_id == v2.version_id
        assert history[2].version_id == v1.version_id  # Oldest last
    finally:
        store.close()


def test_get_version_history_respects_limit() -> None:
    """Test that get_version_history respects the limit parameter."""
    cfg = CustomerAppLogicStoreConfig(
        backend="sqlite",
        sqlite=SqliteConfig(database_path=":memory:"),
    )
    store = create_customer_app_logic_store(cfg)
    try:
        for i in range(5):
            store.commit_version(
                conversation_id="conv_limit",
                message_cursor=i,
                chart_stack_id=f"stack{i}",
                chart_stack_snapshot={},
                description=f"Version {i}",
                user_id="user",
            )

        history = store.get_version_history("conv_limit", limit=2)

        assert len(history) == 2
        # Should be the 2 most recent
        assert history[0].message_cursor == 4
        assert history[1].message_cursor == 3
    finally:
        store.close()


def test_get_version_history_empty_for_unknown_conversation() -> None:
    """Test that get_version_history returns empty list for unknown conversation."""
    cfg = CustomerAppLogicStoreConfig(
        backend="sqlite",
        sqlite=SqliteConfig(database_path=":memory:"),
    )
    store = create_customer_app_logic_store(cfg)
    try:
        history = store.get_version_history("unknown_conversation")
        assert history == []
    finally:
        store.close()


def test_get_latest_version_returns_most_recent() -> None:
    """Test that get_latest_version returns the most recent version."""
    cfg = CustomerAppLogicStoreConfig(
        backend="sqlite",
        sqlite=SqliteConfig(database_path=":memory:"),
    )
    store = create_customer_app_logic_store(cfg)
    try:
        store.commit_version(
            conversation_id="conv_latest",
            message_cursor=1,
            chart_stack_id="stack1",
            chart_stack_snapshot={},
            description="First",
            user_id="user",
        )
        v2 = store.commit_version(
            conversation_id="conv_latest",
            message_cursor=5,
            chart_stack_id="stack2",
            chart_stack_snapshot={"latest": True},
            description="Latest",
            user_id="user",
        )

        latest = store.get_latest_version("conv_latest")

        assert latest is not None
        assert latest.version_id == v2.version_id
        assert latest.chart_stack_snapshot == {"latest": True}
    finally:
        store.close()


def test_get_latest_version_returns_none_for_no_versions() -> None:
    """Test that get_latest_version returns None when no versions exist."""
    cfg = CustomerAppLogicStoreConfig(
        backend="sqlite",
        sqlite=SqliteConfig(database_path=":memory:"),
    )
    store = create_customer_app_logic_store(cfg)
    try:
        latest = store.get_latest_version("no_versions_conversation")
        assert latest is None
    finally:
        store.close()


def test_versions_isolated_by_conversation() -> None:
    """Test that versions are isolated per conversation."""
    cfg = CustomerAppLogicStoreConfig(
        backend="sqlite",
        sqlite=SqliteConfig(database_path=":memory:"),
    )
    store = create_customer_app_logic_store(cfg)
    try:
        # Create versions for two different conversations
        store.commit_version(
            conversation_id="conv_A",
            message_cursor=1,
            chart_stack_id="stack_a1",
            chart_stack_snapshot={},
            description="Conv A v1",
            user_id="user",
        )
        store.commit_version(
            conversation_id="conv_A",
            message_cursor=2,
            chart_stack_id="stack_a2",
            chart_stack_snapshot={},
            description="Conv A v2",
            user_id="user",
        )
        store.commit_version(
            conversation_id="conv_B",
            message_cursor=1,
            chart_stack_id="stack_b1",
            chart_stack_snapshot={},
            description="Conv B v1",
            user_id="user",
        )

        history_a = store.get_version_history("conv_A")
        history_b = store.get_version_history("conv_B")

        assert len(history_a) == 2
        assert len(history_b) == 1
        assert all(v.conversation_id == "conv_A" for v in history_a)
        assert all(v.conversation_id == "conv_B" for v in history_b)
    finally:
        store.close()


def test_version_snapshot_preserves_complex_chart_stack() -> None:
    """Test that complex chart stack snapshots are preserved correctly."""
    cfg = CustomerAppLogicStoreConfig(
        backend="sqlite",
        sqlite=SqliteConfig(database_path=":memory:"),
    )
    store = create_customer_app_logic_store(cfg)
    try:
        complex_snapshot = {
            "id": "stack_complex",
            "title": "Complex Analysis",
            "charts": [
                {
                    "id": "chart_revenue",
                    "title": "Revenue by Region",
                    "type": "bar",
                    "dimensions": [
                        {"field": "region", "type": "category"},
                        {"field": "revenue", "type": "numeric"},
                    ],
                    "filters": [{"field": "year", "operator": "eq", "value": "2024"}],
                },
                {
                    "id": "chart_growth",
                    "title": "Growth Trend",
                    "type": "line",
                    "dimensions": [
                        {"field": "month", "type": "temporal"},
                        {"field": "growth_rate", "type": "numeric"},
                    ],
                },
            ],
            "layout": {"columns": 2, "rows": 1},
            "metadata": {"author": "analyst", "created": "2024-01-15"},
        }

        version = store.commit_version(
            conversation_id="conv_complex",
            message_cursor=15,
            chart_stack_id="stack_complex",
            chart_stack_snapshot=complex_snapshot,
            description="Complex multi-chart analysis",
            user_id="analyst",
        )

        retrieved = store.get_version(version.version_id)

        assert retrieved.chart_stack_snapshot == complex_snapshot
        assert len(retrieved.chart_stack_snapshot["charts"]) == 2
        assert (
            retrieved.chart_stack_snapshot["charts"][0]["dimensions"][0]["field"]
            == "region"
        )
    finally:
        store.close()
