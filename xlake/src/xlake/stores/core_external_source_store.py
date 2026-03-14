"""CoreExternalSourceStore protocol and implementations.

Implements Section 1.1.2 (CoreExternalSourceStore) of the XLake architecture.

This store manages ActBI's global repository of external data sources (weather,
macroeconomic trends, market data, commodities, stocks, industry benchmarks,
regulatory datasets) that enrich customer analyses without requiring customer ETL work.
"""

from __future__ import annotations

import json
import math
import os
import sqlite3
import uuid
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable

import fsspec

from ..core import UserContext
from ..models import ExternalDataset, MetadataMatch, QueryResult
from .config import (
    ClickHouseCloudConfig,
    CoreExternalSourceStoreConfig,
    DuckDBConfig,
    FSSpecLocalDocConfig,
    FSSpecObjectDocConfig,
    QdrantLocalConfig,
    QdrantServiceConfig,
    SchemaEmbedderConfig,
    TinybirdConfig,
)

# =============================================================================
# Protocol Definition
# =============================================================================


@runtime_checkable
class CoreExternalSourceStore(Protocol):
    """Protocol for managing global external data sources."""

    def search_datasets(  # pragma: no cover
        self,
        query: str,
        *,
        filters: dict[str, Any] | None = None,
        top_k: int = 10,
    ) -> list[ExternalDataset]:
        """Semantic search for datasets matching the query."""
        ...

    def get_dataset(self, dataset_id: str) -> ExternalDataset:  # pragma: no cover
        """Get dataset metadata and schema."""
        ...

    def query_dataset(  # pragma: no cover
        self,
        dataset_id: str,
        sql: str,
        *,
        bindings: dict[str, Any] | None = None,
    ) -> QueryResult:
        """Execute SQL query on the dataset's OLAP table."""
        ...

    def list_datasets(  # pragma: no cover
        self,
        *,
        category: str | None = None,
        tags: list[str] | None = None,
    ) -> list[ExternalDataset]:
        """List available datasets with optional filtering."""
        ...

    def register_dataset(  # pragma: no cover
        self,
        metadata: dict[str, Any],
        parquet_uri: str,
        *,
        user: UserContext,
    ) -> str:
        """Register a new dataset (admin-only)."""
        ...

    def update_dataset_metadata(  # pragma: no cover
        self,
        dataset_id: str,
        metadata: dict[str, Any],
        *,
        user: UserContext,
    ) -> None:
        """Update dataset metadata (admin-only)."""
        ...

    def ingest_parquet(  # pragma: no cover
        self,
        dataset_id: str,
        parquet_uri: str,
        *,
        user: UserContext,
    ) -> None:
        """Ingest parquet file into OLAP (admin-only)."""
        ...

    def delete_dataset(
        self, dataset_id: str, *, user: UserContext
    ) -> None:  # pragma: no cover
        """Remove a dataset (admin-only)."""
        ...

    def get_dataset_schema(self, dataset_id: str) -> dict[str, Any]:  # pragma: no cover
        """Get dataset schema definition."""
        ...

    def search_metadata(  # pragma: no cover
        self,
        query: str,
        *,
        dataset_id: str | None = None,
        top_k: int = 10,
    ) -> list[MetadataMatch]:
        """Semantic search in dataset metadata."""
        ...

    def close(self) -> None:  # pragma: no cover
        """Release resources."""
        ...


# =============================================================================
# Helper Functions
# =============================================================================


def _assert_admin(user: UserContext) -> None:
    """Raise if user is not an admin."""
    if user.role not in ("admin",):
        raise PermissionError("Only admin users can modify core external datasets.")


def _now_iso() -> str:
    """Get current UTC time as ISO string."""
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _parse_dt(value: str | None) -> datetime | None:
    """Parse ISO datetime string."""
    if not value:
        return None
    try:
        if len(value) == 10 and value[4] == "-" and value[7] == "-":
            return datetime.fromisoformat(value)
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


# =============================================================================
# Development Implementation (DuckDB + Local Qdrant + Local FS)
# =============================================================================


class _InMemoryQdrant:
    """Minimal in-memory Qdrant-like client for tests and dev."""

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

    def search(
        self, collection_name: str, query_vector: list[float], limit: int = 10
    ) -> list[Any]:
        col = self.get_collection(collection_name)
        q = list(query_vector) if hasattr(query_vector, "__iter__") else query_vector
        q_norm = math.sqrt(sum(float(x) * float(x) for x in q)) or 1.0
        scored: list[tuple[float, Any]] = []
        for p in col["points"]:
            v = p.get("vector")
            if v is None:
                v = []
            elif hasattr(v, "tolist"):
                v = v.tolist()
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


class _SimpleEmbedder:
    """Simple embedder for metadata (uses fastembed if available, otherwise fake)."""

    def __init__(self, model: str = "fastembed:BAAI/bge-small-en-v1.5") -> None:
        self.model = model
        self._vector_size = 384  # Default size

    def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Get embeddings for texts."""
        try:
            from fastembed import TextEmbedding

            embedding_model = TextEmbedding(
                model_name=self.model.split(":")[-1]
                if ":" in self.model
                else self.model
            )
            embeddings = list(embedding_model.embed(texts))
            embeddings_list = list(embeddings)
            if len(embeddings_list) > 0:
                self._vector_size = len(embeddings_list[0])
            return embeddings_list
        except Exception:
            # Fallback: return fake embeddings
            return [[0.1] * self._vector_size for _ in texts]


class DuckDBLocalQdrantLocalFSCoreExternalSourceStore:
    """Development implementation using DuckDB, local Qdrant, and local filesystem."""

    def __init__(
        self,
        *,
        olap_config: DuckDBConfig,
        qdrant_config: QdrantLocalConfig,
        fs_config: FSSpecLocalDocConfig,
        embedder_config: SchemaEmbedderConfig | None = None,
    ) -> None:
        self._olap_config = olap_config
        self._qdrant_config = qdrant_config
        self._fs_base = (
            fs_config.base_dir
            if "://" in fs_config.base_dir
            else f"file://{fs_config.base_dir}"
        )
        self._conn: sqlite3.Connection | None = None
        self._duckdb_conn: Any | None = None
        self._ensure_conn_and_schema()
        self._qdrant_client = self._init_qdrant_client(qdrant_config)
        model = (
            embedder_config.model
            if embedder_config
            else "fastembed:BAAI/bge-small-en-v1.5"
        ).strip()
        self._embedder = _SimpleEmbedder(model)
        self._ensure_qdrant_collection()

    def _ensure_conn_and_schema(self) -> None:
        """Initialize SQLite for metadata and DuckDB for OLAP."""
        # SQLite for metadata
        metadata_db = os.path.join(
            os.path.dirname(self._olap_config.database_path),
            "core_external_metadata.db",
        )
        if self._conn is None:
            self._conn = sqlite3.connect(metadata_db)
        conn = self._conn
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS datasets (
                dataset_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                category TEXT NOT NULL,
                tags TEXT NOT NULL,
                schema_json TEXT NOT NULL,
                source TEXT NOT NULL,
                table_name TEXT NOT NULL,
                parquet_uri TEXT,
                metadata_embedding_id TEXT,
                version INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                created_by TEXT
            )
            """
        )
        conn.commit()

        # DuckDB for OLAP
        if self._duckdb_conn is None:
            import duckdb

            self._duckdb_conn = duckdb.connect(self._olap_config.database_path)
        duckdb_conn = self._duckdb_conn
        duckdb_conn.execute("CREATE SCHEMA IF NOT EXISTS external_data")

    def _init_qdrant_client(self, cfg: QdrantLocalConfig) -> Any | None:
        """Initialize Qdrant client."""
        if cfg is None:
            raise ValueError("Qdrant config must be provided")
        try:
            from qdrant_client import QdrantClient
        except Exception:
            QdrantClient = None
        try:
            path = getattr(cfg, "path", None) or ":memory:"
            if path == ":memory:":
                return _InMemoryQdrant()
            if QdrantClient is not None:
                return QdrantClient(path=path)
            return _InMemoryQdrant()
        except Exception:
            return _InMemoryQdrant()

    def _ensure_qdrant_collection(self) -> None:
        """Ensure Qdrant collection exists."""
        if self._qdrant_client is None:
            return
        collection = "core_external_datasets"
        try:
            self._qdrant_client.get_collection(collection)
            return
        except Exception:
            pass
        vector_size = self._embedder._vector_size
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
                from qdrant_client.models import Distance, VectorParams

                self._qdrant_client.create_collection(
                    collection_name=collection,
                    vectors_config=VectorParams(
                        size=vector_size, distance=Distance.COSINE
                    ),
                )
            except Exception:
                return

    def _quote_ident(self, identifier: str) -> str:
        """Quote identifier for DuckDB."""
        return '"' + identifier.replace('"', '""') + '"'

    def search_datasets(
        self,
        query: str,
        *,
        filters: dict[str, Any] | None = None,
        top_k: int = 10,
    ) -> list[ExternalDataset]:
        """Semantic search for datasets."""
        if not query.strip():
            return self.list_datasets()

        # Try vector search first
        dataset_ids: list[str] = []
        try:
            if self._qdrant_client is not None:
                collection = "core_external_datasets"
                q_vecs = self._embedder.get_embeddings([query])
                if len(q_vecs) > 0:
                    qvec = q_vecs[0]
                    hits = self._qdrant_client.search(
                        collection_name=collection,
                        query_vector=qvec,
                        limit=top_k * 2,
                    )
                    for h in hits or []:
                        pl = getattr(h, "payload", {}) or {}
                        did = pl.get("dataset_id")
                        if did:
                            dataset_ids.append(did)
        except Exception:
            pass

        # Fallback to text search
        if not dataset_ids:
            conn = self._conn or sqlite3.connect(
                os.path.join(
                    os.path.dirname(self._olap_config.database_path),
                    "core_external_metadata.db",
                )
            )
            cur = conn.cursor()
            q = f"%{query.lower()}%"
            cur.execute(
                """
                SELECT dataset_id FROM datasets
                WHERE LOWER(name) LIKE ? OR LOWER(description) LIKE ?
                LIMIT ?
                """,
                (q, q, top_k),
            )
            dataset_ids = [row[0] for row in cur.fetchall()]

        # Apply filters
        if filters:
            category = filters.get("category")
            tags = filters.get("tags", [])
            if category or tags:
                filtered = []
                for did in dataset_ids[:top_k]:
                    ds = self.get_dataset(did)
                    if category and ds.category != category:
                        continue
                    if tags and not any(t in ds.tags for t in tags):
                        continue
                    filtered.append(ds)
                return filtered

        return [self.get_dataset(did) for did in dataset_ids[:top_k]]

    def get_dataset(self, dataset_id: str) -> ExternalDataset:
        """Get dataset metadata."""
        conn = self._conn or sqlite3.connect(
            os.path.join(
                os.path.dirname(self._olap_config.database_path),
                "core_external_metadata.db",
            )
        )
        cur = conn.cursor()
        cur.execute(
            "SELECT name, description, category, tags, schema_json, source, table_name, parquet_uri, metadata_embedding_id, version, updated_at FROM datasets WHERE dataset_id = ?",
            (dataset_id,),
        )
        row = cur.fetchone()
        if not row:
            raise KeyError(f"Dataset not found: {dataset_id}")
        (
            name,
            desc,
            cat,
            tags_str,
            schema_json,
            source,
            table_name,
            parquet_uri,
            emb_id,
            version,
            updated_at,
        ) = row
        tags = json.loads(tags_str) if tags_str else []
        schema = json.loads(schema_json) if schema_json else {}
        return ExternalDataset(
            dataset_id=dataset_id,
            name=name,
            description=desc,
            category=cat,
            tags=tags,
            data_schema=schema,
            source=source,
            last_updated=_parse_dt(updated_at) or datetime.now(UTC),
            table_name=table_name,
            parquet_uri=parquet_uri,
            metadata_embedding_id=emb_id,
            version=version,
        )

    def query_dataset(
        self,
        dataset_id: str,
        sql: str,
        *,
        bindings: dict[str, Any] | None = None,
    ) -> QueryResult:
        """Execute SQL query on dataset."""
        ds = self.get_dataset(dataset_id)
        # Replace table reference in SQL - use fully qualified name
        # Simple approach: replace dataset_id or table_name references
        # In production, we'd need more sophisticated SQL rewriting
        query_sql = sql.replace("{dataset_id}", dataset_id).replace(
            "{table_name}", f"external_data.{ds.table_name}"
        )
        duckdb_conn = self._duckdb_conn
        if duckdb_conn is None:
            import duckdb

            duckdb_conn = duckdb.connect(self._olap_config.database_path)
        # Execute query
        cursor = duckdb_conn.execute(query_sql)
        description = getattr(cursor, "description", None)
        column_names = [d[0] for d in description] if description else []
        rows = cursor.fetchall()
        return QueryResult(
            columns=column_names,
            rows=[dict(zip(column_names, row, strict=False)) for row in rows],
            row_count=len(rows),
        )

    def list_datasets(
        self,
        *,
        category: str | None = None,
        tags: list[str] | None = None,
    ) -> list[ExternalDataset]:
        """List datasets with optional filtering."""
        conn = self._conn or sqlite3.connect(
            os.path.join(
                os.path.dirname(self._olap_config.database_path),
                "core_external_metadata.db",
            )
        )
        cur = conn.cursor()
        query = "SELECT dataset_id FROM datasets"
        params: list[Any] = []
        conditions = []
        if category:
            conditions.append("category = ?")
            params.append(category)
        if tags:
            # Simple tag matching - in production would use JSON functions
            conditions.append("tags LIKE ?")
            params.append(f"%{tags[0]}%")
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        cur.execute(query, params)
        dataset_ids = [row[0] for row in cur.fetchall()]
        return [self.get_dataset(did) for did in dataset_ids]

    def register_dataset(
        self,
        metadata: dict[str, Any],
        parquet_uri: str,
        *,
        user: UserContext,
    ) -> str:
        """Register a new dataset."""
        _assert_admin(user)
        dataset_id = metadata.get("dataset_id") or str(uuid.uuid4())
        name = metadata.get("name", "")
        description = metadata.get("description", "")
        category = metadata.get("category", "other")
        tags = metadata.get("tags", [])
        schema = metadata.get("data_schema", {})
        source = metadata.get("source", "unknown")
        table_name = metadata.get("table_name") or f"external_{dataset_id}"

        # Copy parquet to staging location
        staged_uri = f"{self._fs_base}/datasets/{dataset_id}/v1/data.parquet"
        fs, staged_path = fsspec.core.url_to_fs(staged_uri)
        if hasattr(fs, "makedirs"):
            fs.makedirs(os.path.dirname(staged_path), exist_ok=True)
        with (
            fsspec.open(parquet_uri, mode="rb") as src,
            fsspec.open(staged_uri, mode="wb") as dst,
        ):
            dst.write(src.read())

        # Register in SQLite
        conn = self._conn or sqlite3.connect(
            os.path.join(
                os.path.dirname(self._olap_config.database_path),
                "core_external_metadata.db",
            )
        )
        cur = conn.cursor()
        now = _now_iso()
        cur.execute(
            """
            INSERT INTO datasets (dataset_id, name, description, category, tags, schema_json, source, table_name, parquet_uri, version, created_at, updated_at, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dataset_id,
                name,
                description,
                category,
                json.dumps(tags),
                json.dumps(schema),
                source,
                table_name,
                staged_uri,
                1,
                now,
                now,
                user.user_id,
            ),
        )
        conn.commit()

        # Create DuckDB view
        duckdb_conn = self._duckdb_conn
        if duckdb_conn is None:
            import duckdb

            duckdb_conn = duckdb.connect(self._olap_config.database_path)
        q_table = self._quote_ident(table_name)
        file_literal = staged_path.replace("'", "''")
        duckdb_conn.execute(
            f"CREATE OR REPLACE VIEW external_data.{q_table} AS SELECT * FROM read_parquet('{file_literal}')"
        )

        # Embed and index metadata
        self._index_metadata(dataset_id, name, description, category, tags)

        return dataset_id

    def _index_metadata(
        self,
        dataset_id: str,
        name: str,
        description: str,
        category: str,
        tags: list[str],
    ) -> None:
        """Index dataset metadata in Qdrant."""
        if self._qdrant_client is None:
            return
        text = f"{name} {description} {category} {' '.join(tags)}"
        embeddings = self._embedder.get_embeddings([text])
        if len(embeddings) == 0:
            return
        emb_id = str(uuid.uuid4())
        collection = "core_external_datasets"
        point = {
            "id": emb_id,
            "vector": embeddings[0],
            "payload": {
                "dataset_id": dataset_id,
                "name": name,
                "description": description,
                "category": category,
                "tags": tags,
            },
        }
        try:
            if hasattr(self._qdrant_client, "_is_fake"):
                self._qdrant_client.upsert(collection_name=collection, points=[point])
            else:
                from qdrant_client.models import PointStruct

                typed = PointStruct(
                    id=emb_id, vector=embeddings[0], payload=point["payload"]
                )
                self._qdrant_client.upsert(collection_name=collection, points=[typed])
            # Update SQLite with embedding ID
            conn = self._conn or sqlite3.connect(
                os.path.join(
                    os.path.dirname(self._olap_config.database_path),
                    "core_external_metadata.db",
                )
            )
            cur = conn.cursor()
            cur.execute(
                "UPDATE datasets SET metadata_embedding_id = ? WHERE dataset_id = ?",
                (emb_id, dataset_id),
            )
            conn.commit()
        except Exception:
            pass

    def update_dataset_metadata(
        self,
        dataset_id: str,
        metadata: dict[str, Any],
        *,
        user: UserContext,
    ) -> None:
        """Update dataset metadata."""
        _assert_admin(user)
        conn = self._conn or sqlite3.connect(
            os.path.join(
                os.path.dirname(self._olap_config.database_path),
                "core_external_metadata.db",
            )
        )
        cur = conn.cursor()
        updates: list[str] = []
        params: list[Any] = []
        if "name" in metadata:
            updates.append("name = ?")
            params.append(metadata["name"])
        if "description" in metadata:
            updates.append("description = ?")
            params.append(metadata["description"])
        if "category" in metadata:
            updates.append("category = ?")
            params.append(metadata["category"])
        if "tags" in metadata:
            updates.append("tags = ?")
            params.append(json.dumps(metadata["tags"]))
        if "schema" in metadata:
            updates.append("schema_json = ?")
            params.append(json.dumps(metadata["schema"]))
        updates.append("updated_at = ?")
        params.append(_now_iso())
        params.append(dataset_id)
        cur.execute(
            f"UPDATE datasets SET {', '.join(updates)} WHERE dataset_id = ?", params
        )
        conn.commit()
        # Re-index metadata
        ds = self.get_dataset(dataset_id)
        self._index_metadata(
            ds.dataset_id, ds.name, ds.description, ds.category, ds.tags
        )

    def ingest_parquet(
        self,
        dataset_id: str,
        parquet_uri: str,
        *,
        user: UserContext,
    ) -> None:
        """Ingest parquet into OLAP."""
        _assert_admin(user)
        ds = self.get_dataset(dataset_id)
        # Copy to staging
        staged_uri = (
            f"{self._fs_base}/datasets/{dataset_id}/v{ds.version + 1}/data.parquet"
        )
        fs, staged_path = fsspec.core.url_to_fs(staged_uri)
        if hasattr(fs, "makedirs"):
            fs.makedirs(os.path.dirname(staged_path), exist_ok=True)
        with (
            fsspec.open(parquet_uri, mode="rb") as src,
            fsspec.open(staged_uri, mode="wb") as dst,
        ):
            dst.write(src.read())
        # Update DuckDB view
        duckdb_conn = self._duckdb_conn
        if duckdb_conn is None:
            import duckdb

            duckdb_conn = duckdb.connect(self._olap_config.database_path)
        q_table = self._quote_ident(ds.table_name)
        file_literal = staged_path.replace("'", "''")
        duckdb_conn.execute(
            f"CREATE OR REPLACE VIEW external_data.{q_table} AS SELECT * FROM read_parquet('{file_literal}')"
        )
        # Update metadata
        conn = self._conn or sqlite3.connect(
            os.path.join(
                os.path.dirname(self._olap_config.database_path),
                "core_external_metadata.db",
            )
        )
        cur = conn.cursor()
        cur.execute(
            "UPDATE datasets SET parquet_uri = ?, version = version + 1, updated_at = ? WHERE dataset_id = ?",
            (staged_uri, _now_iso(), dataset_id),
        )
        conn.commit()

    def delete_dataset(self, dataset_id: str, *, user: UserContext) -> None:
        """Delete a dataset."""
        _assert_admin(user)
        conn = self._conn or sqlite3.connect(
            os.path.join(
                os.path.dirname(self._olap_config.database_path),
                "core_external_metadata.db",
            )
        )
        cur = conn.cursor()
        cur.execute("DELETE FROM datasets WHERE dataset_id = ?", (dataset_id,))
        conn.commit()
        # Remove from Qdrant
        if self._qdrant_client:
            try:
                ds = self.get_dataset(dataset_id)
                if ds.metadata_embedding_id:
                    collection = "core_external_datasets"
                    if hasattr(self._qdrant_client, "delete"):
                        self._qdrant_client.delete(
                            collection_name=collection,
                            points_selector=[ds.metadata_embedding_id],
                        )
            except Exception:
                pass

    def get_dataset_schema(self, dataset_id: str) -> dict[str, Any]:
        """Get dataset schema."""
        ds = self.get_dataset(dataset_id)
        return ds.data_schema

    def search_metadata(
        self,
        query: str,
        *,
        dataset_id: str | None = None,
        top_k: int = 10,
    ) -> list[MetadataMatch]:
        """Semantic search in metadata."""
        if not query.strip():
            return []
        if self._qdrant_client is None:
            return []
        collection = "core_external_datasets"
        q_vecs = self._embedder.get_embeddings([query])
        if len(q_vecs) == 0:
            return []
        hits = self._qdrant_client.search(
            collection_name=collection,
            query_vector=q_vecs[0],
            limit=top_k,
        )
        results: list[MetadataMatch] = []
        for h in hits or []:
            pl = getattr(h, "payload", {}) or {}
            did = pl.get("dataset_id")
            if dataset_id and did != dataset_id:
                continue
            score = float(getattr(h, "score", 0.0) or 0.0)
            results.append(
                MetadataMatch(
                    dataset_id=did or "",
                    score=score,
                    matched_text=pl.get("description"),
                )
            )
        return results

    def close(self) -> None:
        """Close DuckDB, SQLite connections and Qdrant client."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None
        if self._duckdb_conn is not None:
            self._duckdb_conn.close()
            self._duckdb_conn = None
        if hasattr(self._qdrant_client, "close") and callable(
            self._qdrant_client.close
        ):
            self._qdrant_client.close()


# =============================================================================
# Production Implementation (ClickHouse/Tinybird + Qdrant Cloud + Object Store)
# =============================================================================


class ClickHouseCloudQdrantCloudFSCoreExternalSourceStore:
    """Production implementation using ClickHouse Cloud, Qdrant Cloud, and object store."""

    def __init__(
        self,
        *,
        olap_config: ClickHouseCloudConfig | TinybirdConfig,
        qdrant_config: QdrantServiceConfig,
        fs_config: FSSpecObjectDocConfig,
        embedder_config: SchemaEmbedderConfig | None = None,
    ) -> None:
        self._olap_config = olap_config
        self._qdrant_config = qdrant_config
        self._fs_base = fs_config.base_uri
        self._is_tinybird = isinstance(olap_config, TinybirdConfig)
        # Initialize clients (stub for now - would connect to real services)
        model = (
            embedder_config.model
            if embedder_config
            else "fastembed:BAAI/bge-small-en-v1.5"
        ).strip()
        self._embedder = _SimpleEmbedder(model)

    def search_datasets(
        self,
        query: str,
        *,
        filters: dict[str, Any] | None = None,
        top_k: int = 10,
    ) -> list[ExternalDataset]:
        """Semantic search for datasets."""
        raise NotImplementedError("Production implementation pending")

    def get_dataset(self, dataset_id: str) -> ExternalDataset:
        """Get dataset metadata."""
        raise NotImplementedError("Production implementation pending")

    def query_dataset(
        self,
        dataset_id: str,
        sql: str,
        *,
        bindings: dict[str, Any] | None = None,
    ) -> QueryResult:
        """Execute SQL query on dataset."""
        raise NotImplementedError("Production implementation pending")

    def list_datasets(
        self,
        *,
        category: str | None = None,
        tags: list[str] | None = None,
    ) -> list[ExternalDataset]:
        """List datasets."""
        raise NotImplementedError("Production implementation pending")

    def register_dataset(
        self,
        metadata: dict[str, Any],
        parquet_uri: str,
        *,
        user: UserContext,
    ) -> str:
        """Register a new dataset."""
        raise NotImplementedError("Production implementation pending")

    def update_dataset_metadata(
        self,
        dataset_id: str,
        metadata: dict[str, Any],
        *,
        user: UserContext,
    ) -> None:
        """Update dataset metadata."""
        raise NotImplementedError("Production implementation pending")

    def ingest_parquet(
        self,
        dataset_id: str,
        parquet_uri: str,
        *,
        user: UserContext,
    ) -> None:
        """Ingest parquet into OLAP."""
        raise NotImplementedError("Production implementation pending")

    def delete_dataset(self, dataset_id: str, *, user: UserContext) -> None:
        """Delete a dataset."""
        raise NotImplementedError("Production implementation pending")

    def get_dataset_schema(self, dataset_id: str) -> dict[str, Any]:
        """Get dataset schema."""
        raise NotImplementedError("Production implementation pending")

    def search_metadata(
        self,
        query: str,
        *,
        dataset_id: str | None = None,
        top_k: int = 10,
    ) -> list[MetadataMatch]:
        """Semantic search in metadata."""
        raise NotImplementedError("Production implementation pending")

    def close(self) -> None:
        """Close connections."""
        pass


# =============================================================================
# Factory Function
# =============================================================================


def create_core_external_source_store(
    config: CoreExternalSourceStoreConfig,
) -> CoreExternalSourceStore:
    """Create a CoreExternalSourceStore instance based on config."""
    if config.backend == "duckdb":
        assert config.duckdb is not None, "duckdb config must be provided"
        assert config.qdrant_local is not None, "qdrant_local config must be provided"
        assert config.fsspec_local is not None, "fsspec_local config must be provided"
        return DuckDBLocalQdrantLocalFSCoreExternalSourceStore(
            olap_config=config.duckdb,
            qdrant_config=config.qdrant_local,
            fs_config=config.fsspec_local,
            embedder_config=config.metadata_embedder,
        )
    if config.backend in ("clickhouse_cloud", "tinybird"):
        assert config.qdrant_service is not None, (
            "qdrant_service config must be provided"
        )
        assert config.fsspec_object is not None, "fsspec_object config must be provided"
        olap_config = (
            config.clickhouse_cloud
            if config.backend == "clickhouse_cloud"
            else config.tinybird
        )
        assert olap_config is not None, f"{config.backend} config must be provided"
        return ClickHouseCloudQdrantCloudFSCoreExternalSourceStore(
            olap_config=olap_config,
            qdrant_config=config.qdrant_service,
            fs_config=config.fsspec_object,
            embedder_config=config.metadata_embedder,
        )
    raise ValueError(f"Unsupported backend: {config.backend}")
