"""CustomerAppLogicStore protocol, implementations, and factory.

Manages tenant-scoped application metadata and business logic:
- Users, roles, permissions
- Conversations
- Version management (git-like commits linking conversations to chart stacks)

Note: Chart-related artifacts (charts, stacks, dashboards, filters, scenarios)
are managed by CustomerChartStore.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field

from ..core import UserContext
from .config import (
    CustomerAppLogicStoreConfig,
    SqliteConfig,
    SupabaseConfig,
)

# ============================================================================
# Version Management Models
# ============================================================================


class VersionSnapshot(BaseModel):
    """A commit-like snapshot linking a conversation state to a chart stack state.

    Works like a git commit - captures the state at a point in time and allows
    traversing version history through parent_version_id.

    Attributes:
        version_id: Unique identifier for this version (auto-generated hash).
        conversation_id: The conversation this version belongs to.
        message_cursor: Number of messages included in this version snapshot.
            Messages after this cursor are not part of this version.
        chart_stack_id: The chart stack captured in this version.
        chart_stack_snapshot: Serialized snapshot of the chart stack state.
            Stored as JSON dict to allow "checkout" without fetching from ChartStore.
        description: Human-readable commit message describing the version.
        parent_version_id: Previous version in the history chain (None for first commit).
        committed_by: User ID who created this version.
        committed_at: Timestamp when this version was created.
    """

    version_id: str
    conversation_id: str
    message_cursor: int = Field(
        ge=0, description="Number of messages included in this version"
    )
    chart_stack_id: str
    chart_stack_snapshot: dict[str, Any] = Field(default_factory=dict)
    description: str = ""
    parent_version_id: str | None = None
    committed_by: str
    committed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


# ============================================================================
# Protocol Interface
# ============================================================================


@runtime_checkable
class CustomerAppLogicStore(Protocol):
    """Protocol for tenant-scoped application metadata and business logic."""

    def get_user_context(self, user_id: str) -> UserContext:  # pragma: no cover
        """Return the UserContext for the specified user."""
        ...

    def close(self) -> None:  # pragma: no cover
        """Release resources held by the store (connections, clients)."""
        ...

    # Users, roles, permissions
    def get_user(self, user_id: str) -> dict[str, Any]:  # pragma: no cover
        """Return a user object."""
        ...

    def upsert_user(self, user: dict[str, Any]) -> str:  # pragma: no cover
        """Create or update a user, returning the user_id."""
        ...

    def delete_user(self, user_id: str) -> None:  # pragma: no cover
        """Delete a user."""
        ...

    def get_user_permissions(self, user_id: str) -> dict[str, Any]:  # pragma: no cover
        """Return permissions for a user."""
        ...

    def set_user_permissions(  # pragma: no cover
        self, user_id: str, permissions: dict[str, Any]
    ) -> None:
        """Set permissions for a user."""
        ...

    # Conversations
    def get_conversation(
        self, conversation_id: str
    ) -> dict[str, Any]:  # pragma: no cover
        """Return a conversation."""
        ...

    def create_conversation(
        self, conversation: dict[str, Any]
    ) -> str:  # pragma: no cover
        """Create a conversation, returning its id."""
        ...

    def append_message(  # pragma: no cover
        self, conversation_id: str, message: dict[str, Any]
    ) -> None:
        """Append a message to a conversation."""
        ...

    def delete_conversation(self, conversation_id: str) -> None:  # pragma: no cover
        """Delete a conversation."""
        ...

    # Version management (git-like commits)
    def commit_version(  # pragma: no cover
        self,
        conversation_id: str,
        message_cursor: int,
        chart_stack_id: str,
        chart_stack_snapshot: dict[str, Any],
        description: str,
        user_id: str,
    ) -> VersionSnapshot:
        """Create a new version snapshot linking conversation state to chart stack state.

        Like 'git commit' - captures the current state and links to parent version.

        Args:
            conversation_id: The conversation to snapshot.
            message_cursor: Number of messages to include (messages[0:cursor]).
            chart_stack_id: The chart stack to link.
            chart_stack_snapshot: Serialized chart stack state for checkout.
            description: Commit message describing this version.
            user_id: User creating this version.

        Returns:
            The created VersionSnapshot with auto-generated version_id.
        """
        ...

    def get_version(self, version_id: str) -> VersionSnapshot:  # pragma: no cover
        """Return a specific version snapshot by ID.

        Args:
            version_id: The unique version identifier.

        Returns:
            The VersionSnapshot.

        Raises:
            ValueError: If version not found.
        """
        ...

    def get_version_history(  # pragma: no cover
        self, conversation_id: str, limit: int | None = None
    ) -> list[VersionSnapshot]:
        """Return version history for a conversation, newest first.

        Args:
            conversation_id: The conversation to get history for.
            limit: Maximum number of versions to return (None for all).

        Returns:
            List of VersionSnapshot objects, ordered newest to oldest.
        """
        ...

    def get_latest_version(  # pragma: no cover
        self, conversation_id: str
    ) -> VersionSnapshot | None:
        """Return the most recent version for a conversation.

        Args:
            conversation_id: The conversation to get latest version for.

        Returns:
            The latest VersionSnapshot, or None if no versions exist.
        """
        ...


# ============================================================================
# SQLite Implementation
# ============================================================================


class SqliteCustomerAppLogicStore(CustomerAppLogicStore):
    """SQLite-backed app logic store for local development."""

    def __init__(self, config: SqliteConfig) -> None:
        self._config: SqliteConfig = config
        self._conn: sqlite3.Connection | None = None
        self._ensure_schema()

    def _ensure_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(
                self._config.database_path,
                check_same_thread=False,
            )
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _ensure_schema(self) -> None:
        """Create database tables if they don't exist."""
        conn = self._ensure_conn()
        cur = conn.cursor()

        # Version snapshots table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS version_snapshots (
                version_id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                message_cursor INTEGER NOT NULL,
                chart_stack_id TEXT NOT NULL,
                chart_stack_snapshot TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                parent_version_id TEXT,
                committed_by TEXT NOT NULL,
                committed_at TEXT NOT NULL,
                FOREIGN KEY (parent_version_id) REFERENCES version_snapshots(version_id)
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_versions_conversation ON version_snapshots(conversation_id, committed_at DESC)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_versions_parent ON version_snapshots(parent_version_id)"
        )

        conn.commit()

    def _generate_version_id(
        self,
        conversation_id: str,
        message_cursor: int,
        chart_stack_id: str,
        committed_at: datetime,
    ) -> str:
        """Generate a deterministic version ID (like a git commit hash)."""
        content = f"{conversation_id}:{message_cursor}:{chart_stack_id}:{committed_at.isoformat()}"
        return hashlib.sha256(content.encode()).hexdigest()[:12]

    def get_user_context(self, user_id: str) -> UserContext:
        """Return a basic UserContext; production systems should back this with tables."""
        return UserContext(
            user_id=user_id,
            tenant_id="dev-tenant",
            role="viewer",
        )

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    # --- User CRUD Stubs ---
    def get_user(self, user_id: str) -> dict[str, Any]:
        raise NotImplementedError

    def upsert_user(self, user: dict[str, Any]) -> str:
        raise NotImplementedError

    def delete_user(self, user_id: str) -> None:
        raise NotImplementedError

    def get_user_permissions(self, user_id: str) -> dict[str, Any]:
        raise NotImplementedError

    def set_user_permissions(self, user_id: str, permissions: dict[str, Any]) -> None:
        raise NotImplementedError

    # --- Conversation CRUD Stubs ---
    def get_conversation(self, conversation_id: str) -> dict[str, Any]:
        raise NotImplementedError

    def create_conversation(self, conversation: dict[str, Any]) -> str:
        raise NotImplementedError

    def append_message(self, conversation_id: str, message: dict[str, Any]) -> None:
        raise NotImplementedError

    def delete_conversation(self, conversation_id: str) -> None:
        raise NotImplementedError

    # --- Version Management ---
    def commit_version(
        self,
        conversation_id: str,
        message_cursor: int,
        chart_stack_id: str,
        chart_stack_snapshot: dict[str, Any],
        description: str,
        user_id: str,
    ) -> VersionSnapshot:
        """Create a new version snapshot linking conversation state to chart stack state."""
        conn = self._ensure_conn()
        cur = conn.cursor()

        committed_at = datetime.now(UTC)
        version_id = self._generate_version_id(
            conversation_id, message_cursor, chart_stack_id, committed_at
        )

        # Find parent version (latest version for this conversation)
        cur.execute(
            """
            SELECT version_id FROM version_snapshots
            WHERE conversation_id = ?
            ORDER BY committed_at DESC
            LIMIT 1
            """,
            (conversation_id,),
        )
        row = cur.fetchone()
        parent_version_id = row["version_id"] if row else None

        snapshot = VersionSnapshot(
            version_id=version_id,
            conversation_id=conversation_id,
            message_cursor=message_cursor,
            chart_stack_id=chart_stack_id,
            chart_stack_snapshot=chart_stack_snapshot,
            description=description,
            parent_version_id=parent_version_id,
            committed_by=user_id,
            committed_at=committed_at,
        )

        cur.execute(
            """
            INSERT INTO version_snapshots (
                version_id, conversation_id, message_cursor, chart_stack_id,
                chart_stack_snapshot, description, parent_version_id,
                committed_by, committed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot.version_id,
                snapshot.conversation_id,
                snapshot.message_cursor,
                snapshot.chart_stack_id,
                json.dumps(snapshot.chart_stack_snapshot, sort_keys=True),
                snapshot.description,
                snapshot.parent_version_id,
                snapshot.committed_by,
                snapshot.committed_at.isoformat(),
            ),
        )
        conn.commit()
        return snapshot

    def get_version(self, version_id: str) -> VersionSnapshot:
        """Return a specific version snapshot by ID."""
        conn = self._ensure_conn()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT * FROM version_snapshots WHERE version_id = ?
            """,
            (version_id,),
        )
        row = cur.fetchone()
        if row is None:
            raise ValueError(f"Version not found: {version_id}")
        return self._row_to_snapshot(row)

    def get_version_history(
        self, conversation_id: str, limit: int | None = None
    ) -> list[VersionSnapshot]:
        """Return version history for a conversation, newest first."""
        conn = self._ensure_conn()
        cur = conn.cursor()

        if limit is not None:
            cur.execute(
                """
                SELECT * FROM version_snapshots
                WHERE conversation_id = ?
                ORDER BY committed_at DESC
                LIMIT ?
                """,
                (conversation_id, limit),
            )
        else:
            cur.execute(
                """
                SELECT * FROM version_snapshots
                WHERE conversation_id = ?
                ORDER BY committed_at DESC
                """,
                (conversation_id,),
            )

        return [self._row_to_snapshot(row) for row in cur.fetchall()]

    def get_latest_version(self, conversation_id: str) -> VersionSnapshot | None:
        """Return the most recent version for a conversation."""
        versions = self.get_version_history(conversation_id, limit=1)
        return versions[0] if versions else None

    def _row_to_snapshot(self, row: sqlite3.Row) -> VersionSnapshot:
        """Convert a database row to a VersionSnapshot."""
        return VersionSnapshot(
            version_id=row["version_id"],
            conversation_id=row["conversation_id"],
            message_cursor=row["message_cursor"],
            chart_stack_id=row["chart_stack_id"],
            chart_stack_snapshot=json.loads(row["chart_stack_snapshot"]),
            description=row["description"],
            parent_version_id=row["parent_version_id"],
            committed_by=row["committed_by"],
            committed_at=datetime.fromisoformat(row["committed_at"]),
        )


# ============================================================================
# Supabase Implementation
# ============================================================================


class SupabaseCustomerAppLogicStore(CustomerAppLogicStore):
    """Supabase-backed app logic store for staging/production."""

    def __init__(self, config: SupabaseConfig) -> None:
        self._config: SupabaseConfig = config
        # Real implementation would initialize a Supabase/PostgREST client here

    def get_user_context(self, user_id: str) -> UserContext:
        """Fetch the UserContext from Supabase-backed tables."""
        return UserContext(
            user_id=user_id,
            tenant_id="prod-tenant",
            role="viewer",
        )

    def close(self) -> None:
        return None

    # --- User CRUD Stubs ---
    def get_user(self, user_id: str) -> dict[str, Any]:
        raise NotImplementedError

    def upsert_user(self, user: dict[str, Any]) -> str:
        raise NotImplementedError

    def delete_user(self, user_id: str) -> None:
        raise NotImplementedError

    def get_user_permissions(self, user_id: str) -> dict[str, Any]:
        raise NotImplementedError

    def set_user_permissions(self, user_id: str, permissions: dict[str, Any]) -> None:
        raise NotImplementedError

    # --- Conversation CRUD Stubs ---
    def get_conversation(self, conversation_id: str) -> dict[str, Any]:
        raise NotImplementedError

    def create_conversation(self, conversation: dict[str, Any]) -> str:
        raise NotImplementedError

    def append_message(self, conversation_id: str, message: dict[str, Any]) -> None:
        raise NotImplementedError

    def delete_conversation(self, conversation_id: str) -> None:
        raise NotImplementedError

    # --- Version Management Stubs ---
    def commit_version(
        self,
        conversation_id: str,
        message_cursor: int,
        chart_stack_id: str,
        chart_stack_snapshot: dict[str, Any],
        description: str,
        user_id: str,
    ) -> VersionSnapshot:
        raise NotImplementedError

    def get_version(self, version_id: str) -> VersionSnapshot:
        raise NotImplementedError

    def get_version_history(
        self, conversation_id: str, limit: int | None = None
    ) -> list[VersionSnapshot]:
        raise NotImplementedError

    def get_latest_version(self, conversation_id: str) -> VersionSnapshot | None:
        raise NotImplementedError


# ============================================================================
# Factory Function
# ============================================================================


def create_customer_app_logic_store(
    config: CustomerAppLogicStoreConfig,
) -> CustomerAppLogicStore:
    """Create a CustomerAppLogicStore instance based on a store-specific config.

    The caller is responsible for choosing the appropriate configuration for the
    active environment.
    """
    if config.backend == "sqlite":
        assert config.sqlite is not None, "sqlite config must be provided"
        return SqliteCustomerAppLogicStore(config.sqlite)
    if config.backend == "supabase":
        assert config.supabase is not None, "supabase config must be provided"
        return SupabaseCustomerAppLogicStore(config.supabase)
    raise ValueError(f"Unsupported backend: {config.backend}")
