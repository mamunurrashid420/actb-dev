"""CustomerContextStore protocol and implementations.

Implements Section 1.2.2 (CustomerContextStore) of the XLake architecture.

Read API returns, per NL query or direct schema request, a list of records where each
record contains:
  a) the schema (schema.json file),
  b) a dictionary mapping each SchemaEntity (table, field) to a list of Facts (dated text).

Write API supports:
  - create/modify/delete schema (modify bumps version) using NL description and/or patch
  - add/modify/delete dated facts for SchemaEntities, individually and in batch

Two backends:
  - QdrantSqliteLocalFSCustomerContextStore (developer): Qdrant local, SQLite, fsspec Local FS
  - QdrantSupabaseCloudFSCustomerContextStore (staging/prod): Qdrant service, Supabase, fsspec Cloud FS
"""

from __future__ import annotations

import json
import math
import sqlite3
import uuid
from datetime import UTC, datetime
from typing import Any, Literal, Protocol, runtime_checkable

import fsspec

from ..core import TenantContext, UserContext
from ..models import Fact, SchemaContextRecord
from ..models.schema import (
    DataSchema,
    iter_field_ids,
    normalize_schema_dict_to_model,
    schema_from_json,
    schema_to_json,
)
from .config import (
    CustomerContextStoreConfig,
    FSSpecLocalDocConfig,
    FSSpecObjectDocConfig,
    QdrantLocalConfig,
    QdrantServiceConfig,
    SchemaEmbedderConfig,
    SqliteConfig,
    SupabaseConfig,
)
from .schema_embedder import FieldsAndFactsEmbedder, FieldsOnlyEmbedder, SchemaEmbedder

EntityType = Literal["table", "field"]


@runtime_checkable
class CustomerContextStore(Protocol):
    def search_context(  # pragma: no cover
        self,
        query: str,
        *,
        top_k_schemas: int = 3,
        facts_per_entity: int = 10,
        entity_types: list[EntityType] | None = None,
        tenant: TenantContext,
        user: UserContext,
    ) -> list[SchemaContextRecord]: ...

    def get_schema_context(  # pragma: no cover
        self,
        schema_id: str,
        *,
        as_of_version: int | None = None,
        facts_per_entity: int = 50,
        entity_filter: list[str] | None = None,
        tenant: TenantContext,
        user: UserContext,
    ) -> SchemaContextRecord: ...

    def get_entity_facts(  # pragma: no cover
        self,
        schema_id: str,
        entity_ids: list[str],
        *,
        limit: int = 50,
        since: str | None = None,
        until: str | None = None,
        tenant: TenantContext,
        user: UserContext,
    ) -> dict[str, list[Fact]]: ...

    def create_schema(  # pragma: no cover
        self,
        name: str,
        nl_description: str,
        *,
        schema_json: str | None = None,
        initial_facts: dict[str, list[dict[str, Any]]] | None = None,
        tenant: TenantContext,
        user: UserContext,
    ) -> dict[str, Any]: ...

    def modify_schema(  # pragma: no cover
        self,
        schema_id: str,
        nl_description: str | None = None,
        schema_json_patch: dict[str, Any] | None = None,
        *,
        schema_json: str | None = None,
        tenant: TenantContext,
        user: UserContext,
    ) -> dict[str, Any]: ...

    def delete_schema(
        self, schema_id: str, *, tenant: TenantContext, user: UserContext
    ) -> None:  # pragma: no cover
        ...

    def add_fact(  # pragma: no cover
        self,
        schema_id: str,
        entity_id: str,
        text: str,
        *,
        date: str | None = None,
        source: str | None = None,
        tags: list[str] | None = None,
        tenant: TenantContext,
        user: UserContext,
    ) -> dict[str, Any]: ...

    def add_facts_batch(  # pragma: no cover
        self,
        schema_id: str,
        items: list[dict[str, Any]],
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> dict[str, Any]: ...

    def modify_fact(  # pragma: no cover
        self,
        schema_id: str,
        fact_id: str,
        *,
        text: str | None = None,
        date: str | None = None,
        source: str | None = None,
        tags: list[str] | None = None,
        tenant: TenantContext,
        user: UserContext,
    ) -> None: ...

    def delete_fact(  # pragma: no cover
        self, schema_id: str, fact_id: str, *, tenant: TenantContext, user: UserContext
    ) -> None: ...

    def delete_facts_batch(  # pragma: no cover
        self,
        schema_id: str,
        fact_ids: list[str],
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> None: ...

    def close(self) -> None:  # pragma: no cover
        ...


class QdrantSqliteLocalFSCustomerContextStore:
    def __init__(
        self,
        *,
        qdrant_config: QdrantLocalConfig | None = None,
        sqlite_config: SqliteConfig | None = None,
        fs_local_config: FSSpecLocalDocConfig | None = None,
        embedder_config: SchemaEmbedderConfig | None = None,
    ) -> None:
        # Require explicit configs
        if qdrant_config is None or sqlite_config is None or fs_local_config is None:
            raise ValueError(
                "qdrant_config, sqlite_config and fs_local_config must be provided"
            )
        self._sqlite_config = sqlite_config
        self._fs_base = (
            fs_local_config.base_dir
            if "://" in fs_local_config.base_dir
            else f"file://{fs_local_config.base_dir}"
        )
        self._conn: sqlite3.Connection | None = None
        self._ensure_conn_and_schema()
        # Qdrant client init via config
        self._qdrant_client = self._init_qdrant_client(qdrant_config)
        # Schema embedder init via config (prefer object config; fallback to env defaults)
        self._embedder: SchemaEmbedder = self._init_schema_embedder(embedder_config)

    def _ensure_conn_and_schema(self) -> None:
        if self._conn is None:
            self._conn = sqlite3.connect(
                self._sqlite_config.database_path,
                check_same_thread=False,
            )
        conn = self._conn
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS schemas (
                schema_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                name TEXT NOT NULL,
                version INTEGER NOT NULL,
                description TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_snapshots (
                schema_id TEXT NOT NULL,
                version INTEGER NOT NULL,
                uri TEXT NOT NULL,
                created_at TEXT NOT NULL,
                actor TEXT,
                PRIMARY KEY (schema_id, version)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS entities (
                entity_id TEXT PRIMARY KEY,
                schema_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                type TEXT NOT NULL,
                name TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS facts (
                fact_id TEXT PRIMARY KEY,
                schema_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                text TEXT NOT NULL,
                date TEXT,
                source TEXT,
                tags TEXT,
                schema_version INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.commit()

    def _init_qdrant_client(
        self, cfg: QdrantLocalConfig | QdrantServiceConfig | None
    ) -> Any | None:
        if cfg is None:
            raise ValueError("Qdrant config must be provided to initialize client")
        try:
            from qdrant_client import QdrantClient  # type: ignore
        except Exception:
            QdrantClient = None  # type: ignore
        try:
            # Embedded/local mode: prefer path; default ':memory:' for tests if None/empty
            path = getattr(cfg, "path", None) or ":memory:"
            # In-memory path → use lightweight fake client to avoid native deps in tests
            if path == ":memory:":
                return _InMemoryQdrant()
            if QdrantClient is not None:
                return QdrantClient(path=path)
            return _InMemoryQdrant()
        except Exception:
            return _InMemoryQdrant()

    def _init_schema_embedder(self, cfg: SchemaEmbedderConfig | None) -> SchemaEmbedder:
        if cfg is None:
            raise ValueError("SchemaEmbedderConfig must be provided")
        strategy = (cfg.strategy or "fields_and_facts").strip()
        model = (cfg.model or "fastembed:BAAI/bge-small-en-v1.5").strip()
        if strategy == "fields_only":
            return FieldsOnlyEmbedder(model)
        return FieldsAndFactsEmbedder(model)

    def _schema_snapshot_uri(self, tenant_id: str, schema_id: str, version: int) -> str:
        return f"{self._fs_base}/tenants/{tenant_id}/schemas/{schema_id}/v{version}/schema.json"

    def _write_schema_snapshot(
        self,
        tenant_id: str,
        schema_id: str,
        version: int,
        schema_json_str: str,
    ) -> str:
        """Write a schema JSON snapshot to the object store and return its URI."""
        uri = self._schema_snapshot_uri(tenant_id, schema_id, version)
        with fsspec.open(uri, mode="w", overwrite=True) as f:
            f.write(schema_json_str)
        return uri

    @staticmethod
    def _now_iso() -> str:
        # Use timezone-aware UTC to avoid deprecation warnings
        return datetime.now(UTC).replace(microsecond=0).isoformat()

    @staticmethod
    def _ensure_tags_str(tags: list[str] | None) -> str:
        return json.dumps(tags or [], sort_keys=True)

    def _get_current_schema_version(
        self, conn: sqlite3.Connection, schema_id: str, tenant_id: str
    ) -> int:
        """
        Read current schema version for (schema_id, tenant_id).
        """
        cur = conn.cursor()
        cur.execute(
            "SELECT version FROM schemas WHERE schema_id = ? AND tenant_id = ?",
            (schema_id, tenant_id),
        )
        row = cur.fetchone()
        if not row:
            raise KeyError(f"schema_id not found: {schema_id}")
        return int(row[0])

    def _ensure_fields_collection(self, tenant_id: str, vector_size: int) -> None:
        """
        Ensure the tenant-scoped fields collection exists in Qdrant.
        """
        if self._qdrant_client is None:
            return
        collection = f"{tenant_id}__fields"
        # Try to get existing
        try:
            self._qdrant_client.get_collection(collection)
            return
        except Exception:
            pass
        # Create depending on client type
        if hasattr(self._qdrant_client, "_is_fake"):
            try:
                self._qdrant_client.create_collection(
                    collection_name=collection,
                    vectors_config={"size": vector_size, "distance": "COSINE"},
                )
            except Exception:
                return
        else:
            try:
                from qdrant_client.models import Distance, VectorParams  # type: ignore

                self._qdrant_client.create_collection(
                    collection_name=collection,
                    vectors_config=VectorParams(
                        size=vector_size, distance=Distance.COSINE
                    ),
                )
            except Exception:
                # Best-effort; ignore creation errors in dev
                return

    def _upsert_points(self, tenant_id: str, points: list[dict]) -> None:
        if self._qdrant_client is None or not points:
            return
        collection = f"{tenant_id}__fields"
        try:
            if hasattr(self._qdrant_client, "_is_fake"):
                self._qdrant_client.upsert(collection_name=collection, points=points)
                return
            from qdrant_client.models import PointStruct  # type: ignore

            typed = [
                PointStruct(id=p["id"], vector=p["vector"], payload=p["payload"])
                for p in points
            ]
            self._qdrant_client.upsert(collection_name=collection, points=typed)
        except Exception:
            return

    def _copy_facts_to_new_version(
        self,
        *,
        schema_id: str,
        tenant_id: str,
        from_version: int,
        to_version: int,
        entity_ids: list[str],
    ) -> None:
        """
        Copy all facts for the given entity_ids from from_version to to_version.
        """
        if not entity_ids or from_version == to_version:
            return
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()
        placeholders = ",".join("?" for _ in entity_ids)
        cur.execute(
            f"""
            SELECT fact_id, entity_id, text, date, source, tags
            FROM facts
            WHERE schema_id = ? AND tenant_id = ? AND schema_version = ? AND entity_id IN ({placeholders})
            ORDER BY created_at ASC, fact_id ASC
            """,
            (schema_id, tenant_id, from_version, *entity_ids),
        )
        rows = cur.fetchall()
        if not rows:
            return
        now = self._now_iso()
        for _, eid, text, date_str, source, tags_str in rows:
            new_id = str(uuid.uuid4())
            cur.execute(
                """
                INSERT INTO facts(fact_id, schema_id, tenant_id, entity_id, text, date, source, tags, created_at, updated_at, schema_version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    new_id,
                    schema_id,
                    tenant_id,
                    eid,
                    text,
                    date_str,
                    source,
                    tags_str,
                    now,
                    now,
                    to_version,
                ),
            )
        conn.commit()

    def get_schema_context(
        self,
        schema_id: str,
        *,
        as_of_version: int | None = None,
        facts_per_entity: int = 50,
        entity_filter: list[str] | None = None,
        tenant: TenantContext,
        user: UserContext,
    ) -> SchemaContextRecord:
        tenant_id = tenant.identity.tenant_id
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()
        if as_of_version is None:
            cur.execute(
                "SELECT version FROM schemas WHERE schema_id = ? AND tenant_id = ?",
                (schema_id, tenant_id),
            )
            row = cur.fetchone()
            if not row:
                raise KeyError(f"schema_id not found: {schema_id}")
            version = int(row[0])
        else:
            version = int(as_of_version)
        cur.execute(
            "SELECT uri FROM schema_snapshots WHERE schema_id = ? AND version = ?",
            (schema_id, version),
        )
        snap_row = cur.fetchone()
        if not snap_row:
            raise KeyError(f"schema snapshot not found: {schema_id} v{version}")
        uri = snap_row[0]
        with fsspec.open(uri, mode="r") as f:
            schema_obj = json.load(f)
        schema_model = normalize_schema_dict_to_model(schema_obj)

        if entity_filter is None:
            schema_field_ids = iter_field_ids(schema_model)
            cur.execute(
                """
                SELECT entity_id FROM entities WHERE schema_id = ? AND tenant_id = ?
                UNION
                SELECT DISTINCT entity_id FROM facts WHERE schema_id = ? AND tenant_id = ?
                """,
                (schema_id, tenant_id, schema_id, tenant_id),
            )
            existing_ids = [r[0] for r in cur.fetchall()]
            list({*existing_ids, *schema_field_ids})
        else:
            list(entity_filter)

        facts_by_entity: dict[str, list[Fact]] = {}
        cur.execute(
            """
            SELECT fact_id, entity_id, text, date, source, tags, created_at
            FROM facts
            WHERE schema_id = ? AND tenant_id = ? AND schema_version = ?
            ORDER BY COALESCE(date, created_at) DESC, created_at DESC, fact_id ASC
            """,
            (schema_id, tenant_id, version),
        )
        rows = cur.fetchall()
        tmp: dict[str, list[Fact]] = {}
        for fid, eid, text, date_str, source, tags_str, _created_at in rows:
            tags = json.loads(tags_str) if tags_str else []
            tmp.setdefault(eid, []).append(
                Fact(
                    fact_id=fid,
                    entity_id=eid,
                    text=text,
                    date=self._parse_dt(date_str),
                    source=source,
                    tags=tags,
                )
            )
        selected_eids = set(entity_filter) if entity_filter else None
        for eid, facts in tmp.items():
            if selected_eids is not None and eid not in selected_eids:
                continue
            facts_by_entity[eid] = facts[: max(1, facts_per_entity)]

        return SchemaContextRecord(
            data_schema=schema_obj, facts_by_entity=facts_by_entity
        )

    @staticmethod
    def _parse_dt(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            if len(value) == 10 and value[4] == "-" and value[7] == "-":
                return datetime.fromisoformat(value)
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            return None

    def get_entity_facts(
        self,
        schema_id: str,
        entity_ids: list[str],
        *,
        limit: int = 50,
        since: str | None = None,
        until: str | None = None,
        tenant: TenantContext,
        user: UserContext,
    ) -> dict[str, list[Fact]]:
        if not entity_ids:
            return {}
        tenant_id = tenant.identity.tenant_id
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()
        placeholders = ",".join("?" for _ in entity_ids)
        params: list[Any] = [schema_id, tenant_id, *entity_ids]
        where_date = ""
        if since:
            where_date += " AND COALESCE(date, created_at) >= ?"
            params.append(since)
        if until:
            where_date += " AND COALESCE(date, created_at) <= ?"
            params.append(until)
        cur.execute(
            f"""
            SELECT fact_id, entity_id, text, date, source, tags, created_at
            FROM facts
            WHERE schema_id = ? AND tenant_id = ? AND entity_id IN ({placeholders})
            {where_date}
            ORDER BY COALESCE(date, created_at) DESC, created_at DESC, fact_id ASC
            """,
            params,
        )
        rows = cur.fetchall()
        grouped: dict[str, list[Fact]] = {}
        for fid, eid, text, date_str, source, tags_str, _created_at in rows:
            tags = json.loads(tags_str) if tags_str else []
            grouped.setdefault(eid, []).append(
                Fact(
                    fact_id=fid,
                    entity_id=eid,
                    text=text,
                    date=self._parse_dt(date_str),
                    source=source,
                    tags=tags,
                )
            )
        return {eid: facts[: max(1, limit)] for eid, facts in grouped.items()}

    def _approx_schema_ids_by_sqlite(self, query: str, tenant_id: str) -> list[str]:
        q = f"%{query.lower()}%"
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()
        cur.execute(
            """
            SELECT f.schema_id, COUNT(*) as score
            FROM facts f
            WHERE f.tenant_id = ? AND LOWER(f.text) LIKE ?
            GROUP BY f.schema_id
            """,
            (tenant_id, q),
        )
        fact_scores = {row[0]: row[1] for row in cur.fetchall()}
        cur.execute(
            """
            SELECT e.schema_id, COUNT(*) as score
            FROM entities e
            WHERE e.tenant_id = ? AND LOWER(e.name) LIKE ?
            GROUP BY e.schema_id
            """,
            (tenant_id, q),
        )
        ent_scores = {row[0]: row[1] for row in cur.fetchall()}
        combined: dict[str, int] = {}
        for k, v in fact_scores.items():
            combined[k] = combined.get(k, 0) + int(v)
        for k, v in ent_scores.items():
            combined[k] = combined.get(k, 0) + int(v)
        ranked = sorted(combined.items(), key=lambda kv: (-kv[1], kv[0]))
        return [k for k, _ in ranked]

    def _assert_can_modify(self, user: UserContext) -> None:
        if not (
            user.permissions.can_modify_schema or user.role in ("admin", "manager")
        ):
            raise PermissionError("User is not allowed to modify schema or facts.")

    def create_schema(
        self,
        name: str,
        nl_description: str,
        *,
        schema_json: str | None = None,
        initial_facts: dict[str, list[dict[str, Any]]] | None = None,
        tenant: TenantContext,
        user: UserContext,
    ) -> dict[str, Any]:
        self._assert_can_modify(user)
        tenant_id = tenant.identity.tenant_id
        schema_id = str(uuid.uuid4())
        version = 1
        created_at = updated_at = self._now_iso()
        if schema_json and schema_json.strip():
            try:
                model = schema_from_json(schema_json)
            except Exception:
                model = normalize_schema_dict_to_model(json.loads(schema_json))
            model.schema_id = schema_id
            model.version = version
            if not model.name:
                model.name = name
            if not model.description:
                model.description = nl_description
            final_json = schema_to_json(model)
        else:
            schema_model = DataSchema(
                schema_id=schema_id,
                version=version,
                name=name,
                description=nl_description,
                databases=[],
            )
            final_json = schema_to_json(schema_model)
        uri = self._write_schema_snapshot(
            tenant_id=tenant_id,
            schema_id=schema_id,
            version=version,
            schema_json_str=final_json,
        )
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO schemas(schema_id, tenant_id, name, version, description, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                schema_id,
                tenant_id,
                name,
                version,
                nl_description,
                created_at,
                updated_at,
            ),
        )
        cur.execute(
            "INSERT INTO schema_snapshots(schema_id, version, uri, created_at, actor) VALUES (?, ?, ?, ?, ?)",
            (schema_id, version, uri, created_at, user.user_id),
        )
        conn.commit()
        if initial_facts:
            items: list[dict[str, Any]] = []
            for eid, facts in initial_facts.items():
                for fact in facts:
                    items.append({
                        "entity_id": eid,
                        "text": fact.get("text", ""),
                        "date": fact.get("date"),
                        "source": fact.get("source"),
                        "tags": fact.get("tags"),
                    })
            if items:
                self.add_facts_batch(schema_id, items, tenant=tenant, user=user)
        try:
            new_model = schema_from_json(final_json)
        except Exception:
            new_model = normalize_schema_dict_to_model(json.loads(final_json))
        facts_by_entity: dict[str, list[Fact]] = {}
        cur = (
            self._conn
            or sqlite3.connect(
                self._sqlite_config.database_path, check_same_thread=False
            )
        ).cursor()
        cur.execute(
            """
            SELECT fact_id, entity_id, text, date, source, tags, created_at
            FROM facts
            WHERE schema_id = ? AND tenant_id = ? AND schema_version = ?
            ORDER BY COALESCE(date, created_at) DESC, created_at DESC, fact_id ASC
            """,
            (schema_id, tenant_id, version),
        )
        for fid, eid, text, date_str, source, tags_str, _created_at in cur.fetchall():
            tags = json.loads(tags_str) if tags_str else []
            facts_by_entity.setdefault(eid, []).append(
                Fact(
                    fact_id=fid,
                    entity_id=eid,
                    text=text,
                    date=self._parse_dt(date_str),
                    source=source,
                    tags=tags,
                )
            )
        points = self._embedder.embed_schema(
            schema_model=new_model,
            tenant_id=tenant_id,
            schema_id=schema_id,
            schema_version=version,
            schema_uri=uri,
            facts_by_entity=facts_by_entity,
        )
        if points:
            self._ensure_fields_collection(
                tenant_id, vector_size=len(points[0]["vector"])
            )
            self._upsert_points(tenant_id, points)
        return {"schema_id": schema_id, "version": version}

    def modify_schema(
        self,
        schema_id: str,
        nl_description: str | None = None,
        schema_json_patch: dict[str, Any] | None = None,
        *,
        schema_json: str | None = None,
        tenant: TenantContext,
        user: UserContext,
    ) -> dict[str, Any]:
        self._assert_can_modify(user)
        tenant_id = tenant.identity.tenant_id
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()
        cur.execute(
            "SELECT name, version, description FROM schemas WHERE schema_id = ? AND tenant_id = ?",
            (schema_id, tenant_id),
        )
        row = cur.fetchone()
        if not row:
            raise KeyError(f"schema_id not found: {schema_id}")
        _name, current_version, current_desc = row[0], int(row[1]), row[2]
        new_version = current_version + 1
        cur.execute(
            "SELECT uri FROM schema_snapshots WHERE schema_id = ? AND version = ?",
            (schema_id, current_version),
        )
        snap_row = cur.fetchone()
        if not snap_row:
            raise KeyError(
                f"schema snapshot not found for current version: {schema_id}"
            )
        new_model: DataSchema
        if schema_json and schema_json.strip():
            try:
                model = schema_from_json(schema_json)
            except Exception:
                model = normalize_schema_dict_to_model(json.loads(schema_json))
            if nl_description is not None:
                current_desc = nl_description
            model.schema_id = schema_id
            model.version = new_version
            final_json = schema_to_json(model)
            new_model = model
        else:
            with fsspec.open(snap_row[0], mode="r") as f:
                schema_obj = json.load(f)
            if nl_description is not None:
                current_desc = nl_description
            if schema_json_patch:
                for k, v in schema_json_patch.items():
                    schema_obj[k] = v
            schema_obj["version"] = new_version
            schema_model = normalize_schema_dict_to_model(schema_obj)
            final_json = schema_to_json(schema_model)
            new_model = schema_model
        uri = self._write_schema_snapshot(
            tenant_id=tenant_id,
            schema_id=schema_id,
            version=new_version,
            schema_json_str=final_json,
        )
        updated_at = self._now_iso()
        cur.execute(
            "UPDATE schemas SET version = ?, description = ?, updated_at = ? WHERE schema_id = ? AND tenant_id = ?",
            (new_version, current_desc, updated_at, schema_id, tenant_id),
        )
        cur.execute(
            "INSERT INTO schema_snapshots(schema_id, version, uri, created_at, actor) VALUES (?, ?, ?, ?, ?)",
            (schema_id, new_version, uri, updated_at, user.user_id),
        )
        conn.commit()
        new_entity_ids = iter_field_ids(new_model)
        self._copy_facts_to_new_version(
            schema_id=schema_id,
            tenant_id=tenant_id,
            from_version=current_version,
            to_version=new_version,
            entity_ids=new_entity_ids,
        )
        facts_by_entity: dict[str, list[Fact]] = {}
        cur = (
            self._conn
            or sqlite3.connect(
                self._sqlite_config.database_path, check_same_thread=False
            )
        ).cursor()
        cur.execute(
            """
            SELECT fact_id, entity_id, text, date, source, tags, created_at
            FROM facts
            WHERE schema_id = ? AND tenant_id = ? AND schema_version = ?
            ORDER BY COALESCE(date, created_at) DESC, created_at DESC, fact_id ASC
            """,
            (schema_id, tenant_id, new_version),
        )
        for fid, eid, text, date_str, source, tags_str, _created_at in cur.fetchall():
            tags = json.loads(tags_str) if tags_str else []
            facts_by_entity.setdefault(eid, []).append(
                Fact(
                    fact_id=fid,
                    entity_id=eid,
                    text=text,
                    date=self._parse_dt(date_str),
                    source=source,
                    tags=tags,
                )
            )
        points = self._embedder.embed_schema(
            schema_model=new_model,
            tenant_id=tenant_id,
            schema_id=schema_id,
            schema_version=new_version,
            schema_uri=uri,
            facts_by_entity=facts_by_entity,
        )
        if points:
            self._ensure_fields_collection(
                tenant_id, vector_size=len(points[0]["vector"])
            )
            self._upsert_points(tenant_id, points)
        return {"version": new_version}

    def delete_schema(
        self, schema_id: str, *, tenant: TenantContext, user: UserContext
    ) -> None:
        self._assert_can_modify(user)
        tenant_id = tenant.identity.tenant_id
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM facts WHERE schema_id = ? AND tenant_id = ?",
            (schema_id, tenant_id),
        )
        cur.execute(
            "DELETE FROM entities WHERE schema_id = ? AND tenant_id = ?",
            (schema_id, tenant_id),
        )
        cur.execute("DELETE FROM schema_snapshots WHERE schema_id = ?", (schema_id,))
        cur.execute(
            "DELETE FROM schemas WHERE schema_id = ? AND tenant_id = ?",
            (schema_id, tenant_id),
        )
        conn.commit()

    def add_fact(
        self,
        schema_id: str,
        entity_id: str,
        text: str,
        *,
        date: str | None = None,
        source: str | None = None,
        tags: list[str] | None = None,
        tenant: TenantContext,
        user: UserContext,
    ) -> dict[str, Any]:
        self._assert_can_modify(user)
        tenant_id = tenant.identity.tenant_id
        fact_id = str(uuid.uuid4())
        created_at = updated_at = self._now_iso()
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()
        schema_version = self._get_current_schema_version(conn, schema_id, tenant_id)
        cur.execute(
            """
            INSERT INTO facts(fact_id, schema_id, tenant_id, entity_id, text, date, source, tags, created_at, updated_at, schema_version)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                fact_id,
                schema_id,
                tenant_id,
                entity_id,
                text,
                date,
                source,
                self._ensure_tags_str(tags),
                created_at,
                updated_at,
                schema_version,
            ),
        )
        conn.commit()
        return {"fact_id": fact_id}

    def add_facts_batch(
        self,
        schema_id: str,
        items: list[dict[str, Any]],
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> dict[str, Any]:
        self._assert_can_modify(user)
        if not items:
            return {"fact_ids": []}
        tenant_id = tenant.identity.tenant_id
        created_at = updated_at = self._now_iso()
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()
        schema_version = self._get_current_schema_version(conn, schema_id, tenant_id)
        fact_ids: list[str] = []
        for itm in items:
            eid = itm.get("entity_id", "")
            text = itm.get("text", "")
            if not eid or not text:
                continue
            fid = str(uuid.uuid4())
            fact_ids.append(fid)
            cur.execute(
                """
                INSERT INTO facts(fact_id, schema_id, tenant_id, entity_id, text, date, source, tags, created_at, updated_at, schema_version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fid,
                    schema_id,
                    tenant_id,
                    eid,
                    text,
                    itm.get("date"),
                    itm.get("source"),
                    self._ensure_tags_str(itm.get("tags")),
                    created_at,
                    updated_at,
                    schema_version,
                ),
            )
        conn.commit()
        return {"fact_ids": fact_ids}

    def search_context(
        self,
        query: str,
        *,
        top_k_schemas: int = 3,
        facts_per_entity: int = 10,
        entity_types: list[EntityType] | None = None,
        tenant: TenantContext,
        user: UserContext,
    ) -> list[SchemaContextRecord]:
        if not query.strip():
            return []
        tenant_id = tenant.identity.tenant_id
        # Try vector search via Qdrant first
        schema_ids_ranked: list[tuple[str, int]] = []
        used_versions: dict[str, int] = {}
        try:
            if self._qdrant_client is not None:
                collection = f"{tenant_id}__fields"
                q_vecs = self._embedder.get_embeddings([query])
                if q_vecs:
                    qvec = q_vecs[0]
                    hits = self._qdrant_client.search(
                        collection_name=collection,
                        query_vector=qvec,
                        limit=max(10, top_k_schemas * 10),
                    )
                    # Aggregate hits by (schema_id, schema_version)
                    scores: dict[tuple[str, int], float] = {}
                    for h in hits or []:
                        pl = getattr(h, "payload", {}) or {}
                        sid = pl.get("schema_id")
                        sver = pl.get("schema_version")
                        if not sid or not isinstance(sver, int):
                            continue
                        key = (sid, sver)
                        # Use best (max) score per schema/version
                        sc = float(getattr(h, "score", 0.0) or 0.0)
                        if key not in scores or sc > scores[key]:
                            scores[key] = sc
                    ranked_pairs = sorted(
                        scores.items(), key=lambda kv: (-kv[1], kv[0][0], kv[0][1])
                    )
                    for (sid, sver), _ in ranked_pairs:
                        schema_ids_ranked.append((sid, sver))
                        used_versions[sid] = sver
                    # Truncate to requested schemas
                    schema_ids_ranked = schema_ids_ranked[: max(1, top_k_schemas)]
        except Exception:
            # Fallback to approximate LIKE search when vector path fails
            schema_ids_ranked = []
            used_versions = {}
        if not schema_ids_ranked:
            # Fallback: approximate ranking via SQLite LIKE
            approx_ids = self._approx_schema_ids_by_sqlite(query, tenant_id)
            # Resolve current version per schema
            conn = self._conn or sqlite3.connect(
                self._sqlite_cfg.database_path, check_same_thread=False
            )
            cur = conn.cursor()
            for sid in approx_ids:
                cur.execute(
                    "SELECT version FROM schemas WHERE schema_id = ? AND tenant_id = ?",
                    (sid, tenant_id),
                )
                row = cur.fetchone()
                if row:
                    ver = int(row[0])
                    schema_ids_ranked.append((sid, ver))
                    used_versions[sid] = ver
            schema_ids_ranked = schema_ids_ranked[: max(1, top_k_schemas)]
        results: list[SchemaContextRecord] = []
        for schema_id, ver in schema_ids_ranked[: max(1, top_k_schemas)]:
            rec = self.get_schema_context(
                schema_id,
                as_of_version=ver,
                facts_per_entity=facts_per_entity,
                entity_filter=None,
                tenant=tenant,
                user=user,
            )
            results.append(rec)
        return results

    def close(self) -> None:
        """Close SQLite connection and Qdrant client."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None
        if hasattr(self._qdrant_client, "close") and callable(
            self._qdrant_client.close
        ):
            self._qdrant_client.close()


class _InMemoryQdrant:
    """
    Minimal in-memory Qdrant-like client for tests and dev (path=':memory:').
    Supports: get_collection, create_collection, upsert, count, search (cosine).
    """

    _is_fake = True

    def __init__(self) -> None:
        self._collections: dict[str, dict[str, Any]] = {}

    def get_collection(self, name: str) -> dict[str, Any]:
        if name not in self._collections:
            raise KeyError(name)
        return self._collections[name]

    def create_collection(self, collection_name: str, vectors_config: Any) -> None:
        if collection_name in self._collections:
            return
        size = (
            vectors_config.get("size")
            if isinstance(vectors_config, dict)
            else getattr(vectors_config, "size", None)
        )
        if not isinstance(size, int) or size <= 0:
            size = 768
        self._collections[collection_name] = {"size": size, "points": []}

    def upsert(self, collection_name: str, points: list[Any]) -> None:
        col = self.get_collection(collection_name)
        for p in points:
            col["points"].append(p)

    def count(self, collection_name: str, exact: bool = True) -> Any:
        class Cnt:
            def __init__(self, n: int) -> None:
                self.count = n

        col = self.get_collection(collection_name)
        return Cnt(len(col["points"]))

    def search(
        self, collection_name: str, query_vector: list[float], limit: int = 10
    ) -> list[Any]:
        col = self.get_collection(collection_name)
        q = query_vector
        q_norm = math.sqrt(sum(x * x for x in q)) or 1.0
        scored: list[tuple[float, Any]] = []
        for p in col["points"]:
            v = p.get("vector") or []
            dot = sum(float(a) * float(b) for a, b in zip(q, v, strict=False))
            v_norm = math.sqrt(sum(float(x) * float(x) for x in v)) or 1.0
            score = dot / (q_norm * v_norm)

            class Hit:
                def __init__(self, payload: dict[str, Any], score: float) -> None:
                    self.payload = payload
                    self.score = score

            scored.append((score, Hit(payload=p.get("payload") or {}, score=score)))
        scored.sort(key=lambda t: -t[0])
        return [hit for _, hit in scored[: max(1, limit)]]

    def close(self) -> None:
        """Clear in-memory collections."""
        self._collections.clear()

    def _approx_schema_ids_by_sqlite(self, query: str, tenant_id: str) -> list[str]:
        q = f"%{query.lower()}%"
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()
        cur.execute(
            """
            SELECT f.schema_id, COUNT(*) as score
            FROM facts f
            WHERE f.tenant_id = ? AND LOWER(f.text) LIKE ?
            GROUP BY f.schema_id
            """,
            (tenant_id, q),
        )
        fact_scores = {row[0]: row[1] for row in cur.fetchall()}
        cur.execute(
            """
            SELECT e.schema_id, COUNT(*) as score
            FROM entities e
            WHERE e.tenant_id = ? AND LOWER(e.name) LIKE ?
            GROUP BY e.schema_id
            """,
            (tenant_id, q),
        )
        ent_scores = {row[0]: row[1] for row in cur.fetchall()}
        combined: dict[str, int] = {}
        for k, v in fact_scores.items():
            combined[k] = combined.get(k, 0) + int(v)
        for k, v in ent_scores.items():
            combined[k] = combined.get(k, 0) + int(v)
        ranked = sorted(combined.items(), key=lambda kv: (-kv[1], kv[0]))
        return [k for k, _ in ranked]

    def get_schema_context(
        self,
        schema_id: str,
        *,
        as_of_version: int | None = None,
        facts_per_entity: int = 50,
        entity_filter: list[str] | None = None,
        tenant: TenantContext,
        user: UserContext,
    ) -> SchemaContextRecord:
        tenant_id = tenant.identity.tenant_id
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()
        if as_of_version is None:
            cur.execute(
                "SELECT version FROM schemas WHERE schema_id = ? AND tenant_id = ?",
                (schema_id, tenant_id),
            )
            row = cur.fetchone()
            if not row:
                raise KeyError(f"schema_id not found: {schema_id}")
            version = int(row[0])
        else:
            version = int(as_of_version)
        cur.execute(
            "SELECT uri FROM schema_snapshots WHERE schema_id = ? AND version = ?",
            (schema_id, version),
        )
        snap_row = cur.fetchone()
        if not snap_row:
            raise KeyError(f"schema snapshot not found: {schema_id} v{version}")
        uri = snap_row[0]
        with fsspec.open(uri, mode="r") as f:
            schema_obj = json.load(f)
        # Build model (supports both new 'databases' and legacy 'tables')
        schema_model = normalize_schema_dict_to_model(schema_obj)

        if entity_filter is None:
            # Derive canonical field ids from schema model (latest or as_of_version)
            schema_field_ids = iter_field_ids(schema_model)
            cur.execute(
                """
                SELECT entity_id FROM entities WHERE schema_id = ? AND tenant_id = ?
                UNION
                SELECT DISTINCT entity_id FROM facts WHERE schema_id = ? AND tenant_id = ?
                """,
                (schema_id, tenant_id, schema_id, tenant_id),
            )
            existing_ids = [r[0] for r in cur.fetchall()]
            # Union schema-driven field ids with existing ids (facts/entities)
            list({*existing_ids, *schema_field_ids})
        else:
            list(entity_filter)

        facts_by_entity: dict[str, list[Fact]] = {}
        # Fetch all facts for this schema and version; group by entity_id and trim per entity.
        cur.execute(
            """
            SELECT fact_id, entity_id, text, date, source, tags, created_at
            FROM facts
            WHERE schema_id = ? AND tenant_id = ? AND schema_version = ?
            ORDER BY COALESCE(date, created_at) DESC, created_at DESC, fact_id ASC
            """,
            (schema_id, tenant_id, version),
        )
        rows = cur.fetchall()
        tmp: dict[str, list[Fact]] = {}
        for fid, eid, text, date_str, source, tags_str, _created_at in rows:
            tags = json.loads(tags_str) if tags_str else []
            tmp.setdefault(eid, []).append(
                Fact(
                    fact_id=fid,
                    entity_id=eid,
                    text=text,
                    date=self._parse_dt(date_str),
                    source=source,
                    tags=tags,
                )
            )
        # If an entity_filter is provided, keep only those entities
        selected_eids = set(entity_filter) if entity_filter else None
        for eid, facts in tmp.items():
            if selected_eids is not None and eid not in selected_eids:
                continue
            facts_by_entity[eid] = facts[: max(1, facts_per_entity)]

        return SchemaContextRecord(
            data_schema=schema_obj, facts_by_entity=facts_by_entity
        )

    @staticmethod
    def _parse_dt(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            if len(value) == 10 and value[4] == "-" and value[7] == "-":
                return datetime.fromisoformat(value)
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            return None

    def get_entity_facts(
        self,
        schema_id: str,
        entity_ids: list[str],
        *,
        limit: int = 50,
        since: str | None = None,
        until: str | None = None,
        tenant: TenantContext,
        user: UserContext,
    ) -> dict[str, list[Fact]]:
        if not entity_ids:
            return {}
        tenant_id = tenant.identity.tenant_id
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()
        placeholders = ",".join("?" for _ in entity_ids)
        params: list[Any] = [schema_id, tenant_id, *entity_ids]
        where_date = ""
        if since:
            where_date += " AND COALESCE(date, created_at) >= ?"
            params.append(since)
        if until:
            where_date += " AND COALESCE(date, created_at) <= ?"
            params.append(until)
        cur.execute(
            f"""
            SELECT fact_id, entity_id, text, date, source, tags, created_at
            FROM facts
            WHERE schema_id = ? AND tenant_id = ? AND entity_id IN ({placeholders})
            {where_date}
            ORDER BY COALESCE(date, created_at) DESC, created_at DESC, fact_id ASC
            """,
            params,
        )
        rows = cur.fetchall()
        grouped: dict[str, list[Fact]] = {}
        for fid, eid, text, date_str, source, tags_str, _created_at in rows:
            tags = json.loads(tags_str) if tags_str else []
            grouped.setdefault(eid, []).append(
                Fact(
                    fact_id=fid,
                    entity_id=eid,
                    text=text,
                    date=self._parse_dt(date_str),
                    source=source,
                    tags=tags,
                )
            )
        return {eid: facts[: max(1, limit)] for eid, facts in grouped.items()}

    def _assert_can_modify(self, user: UserContext) -> None:
        if not (
            user.permissions.can_modify_schema or user.role in ("admin", "manager")
        ):
            raise PermissionError("User is not allowed to modify schema or facts.")

    def create_schema(
        self,
        name: str,
        nl_description: str,
        *,
        schema_json: str | None = None,
        initial_facts: dict[str, list[dict[str, Any]]] | None = None,
        tenant: TenantContext,
        user: UserContext,
    ) -> dict[str, Any]:
        self._assert_can_modify(user)
        tenant_id = tenant.identity.tenant_id
        schema_id = str(uuid.uuid4())
        version = 1
        created_at = updated_at = self._now_iso()
        # Build schema model from provided JSON or create an empty schema scaffold
        if schema_json and schema_json.strip():
            try:
                model = schema_from_json(schema_json)
            except Exception:
                # Fallback: load as dict then normalize
                model = normalize_schema_dict_to_model(json.loads(schema_json))
            # Ensure identifiers are consistent with the newly created schema
            model.schema_id = schema_id
            model.version = version
            if not model.name:
                model.name = name
            if not model.description:
                model.description = nl_description
            final_json = schema_to_json(model)
        else:
            schema_model = DataSchema(
                schema_id=schema_id,
                version=version,
                name=name,
                description=nl_description,
                databases=[],
            )
            final_json = schema_to_json(schema_model)
        # Write snapshot
        uri = self._write_schema_snapshot(
            tenant_id=tenant_id,
            schema_id=schema_id,
            version=version,
            schema_json_str=final_json,
        )
        conn = self._conn or sqlite3.connect(
            self._sqlite_cfg.database_path, check_same_thread=False
        )
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO schemas(schema_id, tenant_id, name, version, description, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                schema_id,
                tenant_id,
                name,
                version,
                nl_description,
                created_at,
                updated_at,
            ),
        )
        cur.execute(
            "INSERT INTO schema_snapshots(schema_id, version, uri, created_at, actor) VALUES (?, ?, ?, ?, ?)",
            (schema_id, version, uri, created_at, user.user_id),
        )
        conn.commit()
        if initial_facts:
            items: list[dict[str, Any]] = []
            for eid, facts in initial_facts.items():
                for fact in facts:
                    items.append({
                        "entity_id": eid,
                        "text": fact.get("text", ""),
                        "date": fact.get("date"),
                        "source": fact.get("source"),
                        "tags": fact.get("tags"),
                    })
            if items:
                self.add_facts_batch(schema_id, items, tenant=tenant, user=user)
        # Index embeddings (fields and optionally facts) via embedder
        try:
            new_model = schema_from_json(final_json)
        except Exception:
            new_model = normalize_schema_dict_to_model(json.loads(final_json))
        # collect facts for this version
        facts_by_entity: dict[str, list[Fact]] = {}
        cur = (
            self._conn
            or sqlite3.connect(
                self._sqlite_config.database_path, check_same_thread=False
            )
        ).cursor()
        cur.execute(
            """
            SELECT fact_id, entity_id, text, date, source, tags, created_at
            FROM facts
            WHERE schema_id = ? AND tenant_id = ? AND schema_version = ?
            ORDER BY COALESCE(date, created_at) DESC, created_at DESC, fact_id ASC
            """,
            (schema_id, tenant_id, version),
        )
        for fid, eid, text, date_str, source, tags_str, _created_at in cur.fetchall():
            tags = json.loads(tags_str) if tags_str else []
            facts_by_entity.setdefault(eid, []).append(
                Fact(
                    fact_id=fid,
                    entity_id=eid,
                    text=text,
                    date=self._parse_dt(date_str),
                    source=source,
                    tags=tags,
                )
            )
        points = self._embedder.embed_schema(
            schema_model=new_model,
            tenant_id=tenant_id,
            schema_id=schema_id,
            schema_version=version,
            schema_uri=uri,
            facts_by_entity=facts_by_entity,
        )
        if points:
            self._ensure_fields_collection(
                tenant_id, vector_size=len(points[0]["vector"])
            )
            self._upsert_points(tenant_id, points)
        return {"schema_id": schema_id, "version": version}

    def modify_schema(
        self,
        schema_id: str,
        nl_description: str | None = None,
        schema_json_patch: dict[str, Any] | None = None,
        *,
        schema_json: str | None = None,
        tenant: TenantContext,
        user: UserContext,
    ) -> dict[str, Any]:
        self._assert_can_modify(user)
        tenant_id = tenant.identity.tenant_id
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()
        cur.execute(
            "SELECT name, version, description FROM schemas WHERE schema_id = ? AND tenant_id = ?",
            (schema_id, tenant_id),
        )
        row = cur.fetchone()
        if not row:
            raise KeyError(f"schema_id not found: {schema_id}")
        _name, current_version, current_desc = row[0], int(row[1]), row[2]
        new_version = current_version + 1
        cur.execute(
            "SELECT uri FROM schema_snapshots WHERE schema_id = ? AND version = ?",
            (schema_id, current_version),
        )
        snap_row = cur.fetchone()
        if not snap_row:
            raise KeyError(
                f"schema snapshot not found for current version: {schema_id}"
            )
        # If full schema_json provided, prefer it; otherwise load and patch
        new_model: DataSchema
        if schema_json and schema_json.strip():
            try:
                model = schema_from_json(schema_json)
            except Exception:
                model = normalize_schema_dict_to_model(json.loads(schema_json))
            if nl_description is not None:
                current_desc = nl_description
            model.schema_id = schema_id
            model.version = new_version
            final_json = schema_to_json(model)
            new_model = model
        else:
            with fsspec.open(snap_row[0], mode="r") as f:
                schema_obj = json.load(f)
            if nl_description is not None:
                current_desc = nl_description
            if schema_json_patch:
                for k, v in schema_json_patch.items():
                    schema_obj[k] = v
            schema_obj["version"] = new_version
            # Normalize and prefer writing via model to maintain canonical shape
            schema_model = normalize_schema_dict_to_model(schema_obj)
            final_json = schema_to_json(schema_model)
            new_model = schema_model
        uri = self._write_schema_snapshot(
            tenant_id=tenant_id,
            schema_id=schema_id,
            version=new_version,
            schema_json_str=final_json,
        )
        updated_at = self._now_iso()
        cur.execute(
            "UPDATE schemas SET version = ?, description = ?, updated_at = ? WHERE schema_id = ? AND tenant_id = ?",
            (new_version, current_desc, updated_at, schema_id, tenant_id),
        )
        cur.execute(
            "INSERT INTO schema_snapshots(schema_id, version, uri, created_at, actor) VALUES (?, ?, ?, ?, ?)",
            (schema_id, new_version, uri, updated_at, user.user_id),
        )
        conn.commit()
        # Copy facts forward for matching entities first (so embedder can include them)
        new_entity_ids = iter_field_ids(new_model)
        self._copy_facts_to_new_version(
            schema_id=schema_id,
            tenant_id=tenant_id,
            from_version=current_version,
            to_version=new_version,
            entity_ids=new_entity_ids,
        )
        # Re-index embeddings for new version
        facts_by_entity: dict[str, list[Fact]] = {}
        cur = (
            self._conn
            or sqlite3.connect(
                self._sqlite_config.database_path, check_same_thread=False
            )
        ).cursor()
        cur.execute(
            """
            SELECT fact_id, entity_id, text, date, source, tags, created_at
            FROM facts
            WHERE schema_id = ? AND tenant_id = ? AND schema_version = ?
            ORDER BY COALESCE(date, created_at) DESC, created_at DESC, fact_id ASC
            """,
            (schema_id, tenant_id, new_version),
        )
        for fid, eid, text, date_str, source, tags_str, _created_at in cur.fetchall():
            tags = json.loads(tags_str) if tags_str else []
            facts_by_entity.setdefault(eid, []).append(
                Fact(
                    fact_id=fid,
                    entity_id=eid,
                    text=text,
                    date=self._parse_dt(date_str),
                    source=source,
                    tags=tags,
                )
            )
        points = self._embedder.embed_schema(
            schema_model=new_model,
            tenant_id=tenant_id,
            schema_id=schema_id,
            schema_version=new_version,
            schema_uri=uri,
            facts_by_entity=facts_by_entity,
        )
        if points:
            self._ensure_fields_collection(
                tenant_id, vector_size=len(points[0]["vector"])
            )
            self._upsert_points(tenant_id, points)
        return {"version": new_version}

    def delete_schema(
        self, schema_id: str, *, tenant: TenantContext, user: UserContext
    ) -> None:
        self._assert_can_modify(user)
        tenant_id = tenant.identity.tenant_id
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM facts WHERE schema_id = ? AND tenant_id = ?",
            (schema_id, tenant_id),
        )
        cur.execute(
            "DELETE FROM entities WHERE schema_id = ? AND tenant_id = ?",
            (schema_id, tenant_id),
        )
        cur.execute("DELETE FROM schema_snapshots WHERE schema_id = ?", (schema_id,))
        cur.execute(
            "DELETE FROM schemas WHERE schema_id = ? AND tenant_id = ?",
            (schema_id, tenant_id),
        )
        conn.commit()

    def add_fact(
        self,
        schema_id: str,
        entity_id: str,
        text: str,
        *,
        date: str | None = None,
        source: str | None = None,
        tags: list[str] | None = None,
        tenant: TenantContext,
        user: UserContext,
    ) -> dict[str, Any]:
        self._assert_can_modify(user)
        tenant_id = tenant.identity.tenant_id
        fact_id = str(uuid.uuid4())
        created_at = updated_at = self._now_iso()
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()
        # Resolve current schema version for this tenant/schema
        schema_version = self._get_current_schema_version(conn, schema_id, tenant_id)
        cur.execute(
            """
            INSERT INTO facts(fact_id, schema_id, tenant_id, entity_id, text, date, source, tags, created_at, updated_at, schema_version)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                fact_id,
                schema_id,
                tenant_id,
                entity_id,
                text,
                date,
                source,
                self._ensure_tags_str(tags),
                created_at,
                updated_at,
                schema_version,
            ),
        )
        conn.commit()
        return {"fact_id": fact_id}

    def add_facts_batch(
        self,
        schema_id: str,
        items: list[dict[str, Any]],
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> dict[str, Any]:
        self._assert_can_modify(user)
        if not items:
            return {"fact_ids": []}
        tenant_id = tenant.identity.tenant_id
        created_at = updated_at = self._now_iso()
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()
        schema_version = self._get_current_schema_version(conn, schema_id, tenant_id)
        fact_ids: list[str] = []
        for itm in items:
            eid = itm.get("entity_id", "")
            text = itm.get("text", "")
            if not eid or not text:
                continue
            fid = str(uuid.uuid4())
            fact_ids.append(fid)
            cur.execute(
                """
                INSERT INTO facts(fact_id, schema_id, tenant_id, entity_id, text, date, source, tags, created_at, updated_at, schema_version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fid,
                    schema_id,
                    tenant_id,
                    eid,
                    text,
                    itm.get("date"),
                    itm.get("source"),
                    self._ensure_tags_str(itm.get("tags")),
                    created_at,
                    updated_at,
                    schema_version,
                ),
            )
        conn.commit()
        return {"fact_ids": fact_ids}

    def modify_fact(
        self,
        schema_id: str,
        fact_id: str,
        *,
        text: str | None = None,
        date: str | None = None,
        source: str | None = None,
        tags: list[str] | None = None,
        tenant: TenantContext,
        user: UserContext,
    ) -> None:
        self._assert_can_modify(user)
        tenant_id = tenant.identity.tenant_id
        sets: list[str] = []
        params: list[Any] = []
        if text is not None:
            sets.append("text = ?")
            params.append(text)
        if date is not None:
            sets.append("date = ?")
            params.append(date)
        if source is not None:
            sets.append("source = ?")
            params.append(source)
        if tags is not None:
            sets.append("tags = ?")
            params.append(self._ensure_tags_str(tags))
        sets.append("updated_at = ?")
        params.append(self._now_iso())
        params.extend([schema_id, tenant_id, fact_id])
        conn = self._conn or sqlite3.connect(
            self._sqlite_cfg.database_path, check_same_thread=False
        )
        cur = conn.cursor()
        cur.execute(
            f"UPDATE facts SET {', '.join(sets)} WHERE schema_id = ? AND tenant_id = ? AND fact_id = ?",
            params,
        )
        conn.commit()

    def delete_fact(
        self, schema_id: str, fact_id: str, *, tenant: TenantContext, user: UserContext
    ) -> None:
        self._assert_can_modify(user)
        tenant_id = tenant.identity.tenant_id
        conn = self._conn or sqlite3.connect(
            self._sqlite_cfg.database_path, check_same_thread=False
        )
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM facts WHERE schema_id = ? AND tenant_id = ? AND fact_id = ?",
            (schema_id, tenant_id, fact_id),
        )
        conn.commit()

    def delete_facts_batch(
        self,
        schema_id: str,
        fact_ids: list[str],
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> None:
        self._assert_can_modify(user)
        if not fact_ids:
            return
        tenant_id = tenant.identity.tenant_id
        placeholders = ",".join("?" for _ in fact_ids)
        conn = self._conn or sqlite3.connect(
            self._sqlite_cfg.database_path, check_same_thread=False
        )
        cur = conn.cursor()
        cur.execute(
            f"DELETE FROM facts WHERE schema_id = ? AND tenant_id = ? AND fact_id IN ({placeholders})",
            (schema_id, tenant_id, *fact_ids),
        )
        conn.commit()


class QdrantSupabaseCloudFSCustomerContextStore:
    def __init__(
        self,
        *,
        qdrant: QdrantServiceConfig,
        supabase: SupabaseConfig,
        fs_cloud: FSSpecObjectDocConfig,
    ) -> None:
        self._qdrant_cfg = qdrant
        self._supabase_cfg = supabase
        self._fs_cloud = fs_cloud

    def search_context(
        self,
        query: str,
        *,
        top_k_schemas: int = 3,
        facts_per_entity: int = 10,
        entity_types: list[EntityType] | None = None,
        user: UserContext,
    ) -> list[SchemaContextRecord]:
        raise NotImplementedError

    def get_schema_context(
        self,
        schema_id: str,
        *,
        as_of_version: int | None = None,
        facts_per_entity: int = 50,
        entity_filter: list[str] | None = None,
        user: UserContext,
    ) -> SchemaContextRecord:
        raise NotImplementedError

    def get_entity_facts(
        self,
        schema_id: str,
        entity_ids: list[str],
        *,
        limit: int = 50,
        since: str | None = None,
        until: str | None = None,
        user: UserContext,
    ) -> dict[str, list[Fact]]:
        raise NotImplementedError

    def create_schema(
        self,
        name: str,
        nl_description: str,
        *,
        initial_facts: dict[str, list[dict[str, Any]]] | None = None,
        user: UserContext,
    ) -> dict[str, Any]:
        raise NotImplementedError

    def modify_schema(
        self,
        schema_id: str,
        nl_description: str | None = None,
        schema_json_patch: dict[str, Any] | None = None,
        *,
        user: UserContext,
    ) -> dict[str, Any]:
        raise NotImplementedError

    def delete_schema(self, schema_id: str, *, user: UserContext) -> None:
        raise NotImplementedError

    def add_fact(
        self,
        schema_id: str,
        entity_id: str,
        text: str,
        *,
        date: str | None = None,
        source: str | None = None,
        tags: list[str] | None = None,
        user: UserContext,
    ) -> dict[str, Any]:
        raise NotImplementedError

    def add_facts_batch(
        self,
        schema_id: str,
        items: list[dict[str, Any]],
        *,
        user: UserContext,
    ) -> dict[str, Any]:
        raise NotImplementedError

    def modify_fact(
        self,
        schema_id: str,
        fact_id: str,
        *,
        text: str | None = None,
        date: str | None = None,
        source: str | None = None,
        tags: list[str] | None = None,
        user: UserContext,
    ) -> None:
        raise NotImplementedError

    def delete_fact(self, schema_id: str, fact_id: str, *, user: UserContext) -> None:
        raise NotImplementedError

    def delete_facts_batch(
        self, schema_id: str, fact_ids: list[str], *, user: UserContext
    ) -> None:
        raise NotImplementedError

    def close(self) -> None:
        return None


def create_customer_context_store(
    config: CustomerContextStoreConfig,
) -> CustomerContextStore:
    if config.backend == "qdrant_sqlite_localfs":
        assert config.qdrant_local is not None, "qdrant_local config must be provided"
        assert config.sqlite is not None, "sqlite config must be provided"
        assert config.fsspec_local is not None, "fsspec_local config must be provided"
        return QdrantSqliteLocalFSCustomerContextStore(
            qdrant_config=config.qdrant_local,
            sqlite_config=config.sqlite,
            fs_local_config=config.fsspec_local,
            embedder_config=config.schema_embedder,
        )
    if config.backend == "qdrant_supabase_cloudfs":
        assert config.qdrant_service is not None, (
            "qdrant_service config must be provided"
        )
        assert config.supabase is not None, "supabase config must be provided"
        assert config.fsspec_object is not None, (
            "fsspec_object (CloudFS) config must be provided"
        )
        return QdrantSupabaseCloudFSCustomerContextStore(
            qdrant=config.qdrant_service,
            supabase=config.supabase,
            fs_cloud=config.fsspec_object,
        )
    raise ValueError(f"Unsupported backend: {config.backend}")
