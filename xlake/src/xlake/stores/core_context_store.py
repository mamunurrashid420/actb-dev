"""CoreContextStore protocol and implementations.

Implements Section 1.1.1 (CoreContextStore) of the XLake architecture.

The CoreContextStore is ActBI's global semantic memory containing cross-industry
domain knowledge. It exposes four distinct knowledge categories:
  - DomainKnowledge: KnowledgeNugget entries (expert knowledge about business domains)
  - BusinessMetrics: BusinessMetric entries (KPI/metric definitions with formulas)
  - BusinessDictionary: IndustryTerm entries (industry-specific terms with definitions, synonyms, relationships)
  - VisualizationDesign: DesignRule entries (chart selection rules for data patterns)

All APIs require both TenantContext (for permission/feature gating) and UserContext
(for authorization). Only ActBI admins can modify core context.

Two backends:
  - QdrantSqliteLocalFSCoreContextStore (developer): Qdrant local, SQLite, fsspec Local FS
  - QdrantSupabaseCloudFSCoreContextStore (staging/prod): Qdrant service, Supabase, fsspec Cloud FS
"""

from __future__ import annotations

import contextlib
import json
import math
import sqlite3
import threading
import uuid
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable

from ..core import TenantContext, UserContext
from ..models import (
    BusinessMetric,
    IndustryTerm,
    KnowledgeNugget,
    RetrievalStats,
    VizDesignRule,
    VizDesignRuleResponse,
)
from .config import (
    CoreContextStoreConfig,
    FSSpecLocalDocConfig,
    FSSpecObjectDocConfig,
    QdrantLocalConfig,
    QdrantServiceConfig,
    SchemaEmbedderConfig,
    SqliteConfig,
    SupabaseConfig,
)

# =============================================================================
# Protocol Definition
# =============================================================================


@runtime_checkable
class CoreContextStore(Protocol):
    """Protocol for CoreContextStore implementations."""

    # === DOMAIN KNOWLEDGE (KnowledgeNuggets) ===

    def search_knowledge_nuggets(
        self,
        query: str,
        *,
        domains: list[str] | None = None,
        top_k: int = 10,
        tenant: TenantContext,
        user: UserContext,
    ) -> list[KnowledgeNugget]:
        """Search for knowledge nuggets by semantic similarity."""
        ...

    def get_knowledge_nugget(
        self,
        nugget_id: str,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> KnowledgeNugget:
        """Get a specific knowledge nugget by ID."""
        ...

    def get_knowledge_nuggets_by_domain(
        self,
        domain: str,
        *,
        category: str | None = None,
        limit: int = 50,
        tenant: TenantContext,
        user: UserContext,
    ) -> list[KnowledgeNugget]:
        """Get knowledge nuggets filtered by domain and optionally category."""
        ...

    def upsert_knowledge_nugget(
        self,
        nugget: KnowledgeNugget,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> str:
        """Upsert a knowledge nugget. Returns the nugget ID."""
        ...

    def delete_knowledge_nugget(
        self,
        nugget_id: str,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> None:
        """Delete a knowledge nugget by ID."""
        ...

    # === BUSINESS METRICS ===

    def search_business_metrics(
        self,
        query: str,
        *,
        domains: list[str] | None = None,
        top_k: int = 10,
        tenant: TenantContext,
        user: UserContext,
    ) -> list[BusinessMetric]:
        """Search for business metrics by semantic similarity."""
        ...

    def get_business_metric(
        self,
        metric_id: str,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> BusinessMetric:
        """Get a specific business metric by ID."""
        ...

    def get_business_metric_by_name(
        self,
        name: str,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> BusinessMetric | None:
        """Get a business metric by name."""
        ...

    def upsert_business_metric(
        self,
        metric: BusinessMetric,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> str:
        """Upsert a business metric. Returns the metric ID."""
        ...

    def delete_business_metric(
        self,
        metric_id: str,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> None:
        """Delete a business metric by ID."""
        ...

    # === BUSINESS DICTIONARY (Industry Terms) ===

    def search_industry_terms(
        self,
        query: str,
        *,
        industries: list[str] | None = None,
        top_k: int = 10,
        tenant: TenantContext,
        user: UserContext,
    ) -> list[IndustryTerm]:
        """Search for industry terms by semantic similarity."""
        ...

    def get_industry_term(
        self,
        term_id: str,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> IndustryTerm:
        """Get a specific industry term by ID."""
        ...

    def get_industry_term_by_name(
        self,
        term: str,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> IndustryTerm | None:
        """Get an industry term by name."""
        ...

    def get_related_industry_terms(
        self,
        term_id: str,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> list[IndustryTerm]:
        """Get all related industry terms for a given term."""
        ...

    def upsert_industry_term(
        self,
        term: IndustryTerm,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> str:
        """Upsert an industry term. Returns the term ID."""
        ...

    def link_industry_terms(
        self,
        term_id: str,
        related_term_ids: list[str],
        *,
        relationship: str = "related",  # "related", "synonym", "antonym"
        tenant: TenantContext,
        user: UserContext,
    ) -> None:
        """Link an industry term to other related terms."""
        ...

    def delete_industry_term(
        self,
        term_id: str,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> None:
        """Delete an industry term by ID."""
        ...

    # === VISUALIZATION DESIGN (VizDesignRule) ===

    def get_viz_design_rule(
        self,
        rule_id: str,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> VizDesignRule:
        """Get a specific viz design rule by ID."""
        ...

    def get_blueprint_rule(
        self,
        pipeline_stage: str,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> VizDesignRule:
        """Get the blueprint (interface document) for a pipeline stage.

        Blueprint documents describe the overall process for each stage:
        - selection: Decision tree and process for chart type selection
        - refinement: Classification system and decluttering process
        - formatting: Style application process
        - implementation: Code generation process

        These are stored as single chunks since they describe complete processes.

        Args:
            pipeline_stage: "selection" | "refinement" | "formatting" | "implementation"

        Returns:
            Single VizDesignRule containing the blueprint document.

        Raises:
            KeyError: If no blueprint exists for the given stage.
        """
        ...

    def get_chart_rules(
        self,
        pipeline_stage: str,
        chart_type: str,
        *,
        library: str | None = None,
        tenant: TenantContext,
        user: UserContext,
    ) -> list[VizDesignRule]:
        """Get all rules for a specific chart type at a pipeline stage.

        Chart-specific documents are split by section, so this returns
        multiple VizDesignRule chunks (e.g., "When to Use", "Data Requirements", etc.)

        Args:
            pipeline_stage: "selection" | "refinement" | "formatting" | "implementation"
            chart_type: Chart type slug (e.g., "line_chart", "bar_chart_vertical")
            library: Required for implementation stage (e.g., "recharts", "d3")

        Returns:
            List of VizDesignRule chunks for the chart type.
        """
        ...

    def get_foundation_rules(
        self,
        *,
        category: str | None = None,
        tenant: TenantContext,
        user: UserContext,
    ) -> list[VizDesignRule]:
        """Get foundation/reference document rules.

        Args:
            category: "schema" | "classification" | "index" | None (all)

        Returns:
            List of VizDesignRule chunks from foundation documents.
        """
        ...

    def search_viz_design_rules(
        self,
        query: str,
        *,
        pipeline_stage: str | None = None,
        chart_types: list[str] | None = None,
        priorities: list[str] | None = None,
        tags: list[str] | None = None,
        top_k: int = 10,
        tenant: TenantContext,
        user: UserContext,
    ) -> list[VizDesignRuleResponse]:
        """Semantic search with metadata filtering.

        Args:
            query: Natural language search query.
            pipeline_stage: Filter by pipeline stage.
            chart_types: Filter by chart types.
            priorities: Filter by priority levels (e.g., ["P0", "P1"]).
            tags: Filter by tags.
            top_k: Maximum number of results.

        Returns:
            List of VizDesignRuleResponse with rules and retrieval stats.
        """
        ...

    def upsert_viz_design_rule(
        self,
        rule: VizDesignRule,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> str:
        """Upsert a viz design rule. Returns the rule ID."""
        ...

    def delete_viz_design_rule(
        self,
        rule_id: str,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> None:
        """Delete a viz design rule by ID."""
        ...

    def close(self) -> None:
        """Close the store and release resources."""
        ...


# =============================================================================
# In-Memory Qdrant Client (for development/testing)
# =============================================================================


class _InMemoryQdrant:
    """Minimal in-memory Qdrant-like client for tests and dev (path=':memory:')."""

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
        # Update existing points or add new ones
        existing_ids = {p["id"] for p in col["points"]}
        for p in points:
            pid = p["id"] if isinstance(p, dict) else p.id
            if pid in existing_ids:
                # Remove old point
                col["points"] = [x for x in col["points"] if x.get("id") != pid]
            col["points"].append(
                p
                if isinstance(p, dict)
                else {"id": pid, "vector": p.vector, "payload": p.payload}
            )

    def delete(self, collection_name: str, points_selector: Any) -> None:
        col = self.get_collection(collection_name)
        ids_to_delete = set(
            points_selector.points
            if hasattr(points_selector, "points")
            else points_selector
        )
        col["points"] = [p for p in col["points"] if p.get("id") not in ids_to_delete]

    def count(self, collection_name: str, exact: bool = True) -> Any:
        class Cnt:
            def __init__(self, n: int) -> None:
                self.count = n

        col = self.get_collection(collection_name)
        return Cnt(len(col["points"]))

    def search(
        self,
        collection_name: str,
        query_vector: list[float],
        limit: int = 10,
        query_filter: Any = None,
    ) -> list[Any]:
        col = self.get_collection(collection_name)
        q = query_vector
        q_norm = math.sqrt(sum(x * x for x in q)) or 1.0
        scored: list[tuple[float, Any]] = []

        for p in col["points"]:
            # Apply filter if provided
            if query_filter is not None:
                payload = p.get("payload") or {}
                # Simple filter support for "must" conditions with FieldCondition
                if hasattr(query_filter, "must"):
                    skip = False
                    for cond in query_filter.must:
                        if hasattr(cond, "key") and hasattr(cond, "match"):
                            key = cond.key
                            match_val = (
                                cond.match.value
                                if hasattr(cond.match, "value")
                                else None
                            )
                            if payload.get(key) != match_val:
                                skip = True
                                break
                    if skip:
                        continue

            v = p.get("vector") or []
            dot = sum(float(a) * float(b) for a, b in zip(q, v, strict=False))
            v_norm = math.sqrt(sum(float(x) * float(x) for x in v)) or 1.0
            score = dot / (q_norm * v_norm)

            class Hit:
                def __init__(
                    self, payload: dict[str, Any], score: float, id: str
                ) -> None:
                    self.payload = payload
                    self.score = score
                    self.id = id

            scored.append((
                score,
                Hit(payload=p.get("payload") or {}, score=score, id=p.get("id", "")),
            ))

        scored.sort(key=lambda t: -t[0])
        return [hit for _, hit in scored[: max(1, limit)]]

    def close(self) -> None:
        """Clear in-memory collections."""
        self._collections.clear()


# =============================================================================
# Simple Embedder for Core Context
# =============================================================================


class _SimpleCoreEmbedder:
    """Simple embedder for core context entries using fastembed."""

    def __init__(self, model: str = "fastembed:BAAI/bge-small-en-v1.5") -> None:
        self._model_name = model
        self._embedding_model: Any = None

    def _ensure_model(self) -> None:
        if self._embedding_model is not None:
            return
        try:
            from fastembed import TextEmbedding  # type: ignore

            # Extract model name from "fastembed:MODEL_NAME" format
            model_name = self._model_name
            if model_name.startswith("fastembed:"):
                model_name = model_name[len("fastembed:") :]
            self._embedding_model = TextEmbedding(model_name=model_name)
        except ImportError:
            self._embedding_model = None

    def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Get embeddings for a list of texts."""
        self._ensure_model()
        if self._embedding_model is None:
            # Return zero vectors if fastembed not available
            return [[0.0] * 384 for _ in texts]
        embeddings = list(self._embedding_model.embed(texts))
        return [list(e) for e in embeddings]


# =============================================================================
# SQLite-based Development Implementation
# =============================================================================


class QdrantSqliteLocalFSCoreContextStore:
    """Development backend using SQLite for metadata and in-memory Qdrant for vectors."""

    # Qdrant collection names (global, no tenant prefix)
    COLLECTION_NUGGETS = "core__knowledge_nuggets"
    COLLECTION_METRICS = "core__business_metrics"
    COLLECTION_TERMS = "core__industry_terms"
    COLLECTION_VIZ_RULES = "core__viz_design_rules"

    def __init__(
        self,
        *,
        qdrant_config: QdrantLocalConfig | None = None,
        sqlite_config: SqliteConfig | None = None,
        fs_local_config: FSSpecLocalDocConfig | None = None,
        embedder_config: SchemaEmbedderConfig | None = None,
    ) -> None:
        if qdrant_config is None or sqlite_config is None:
            raise ValueError("qdrant_config and sqlite_config must be provided")

        self._sqlite_config = sqlite_config
        self._fs_config = fs_local_config
        self._conn: sqlite3.Connection | None = None
        self._db_lock = threading.Lock()  # Lock for thread-safe SQLite access
        self._ensure_conn_and_schema()

        # Initialize Qdrant client
        self._qdrant_client = self._init_qdrant_client(qdrant_config)

        # Initialize embedder
        model = (
            embedder_config.model
            if embedder_config
            else "fastembed:BAAI/bge-small-en-v1.5"
        )
        self._embedder = _SimpleCoreEmbedder(model)

    def _ensure_conn_and_schema(self) -> None:
        if self._conn is None:
            self._conn = sqlite3.connect(
                self._sqlite_config.database_path,
                check_same_thread=False,
            )
        conn = self._conn
        cur = conn.cursor()

        # Knowledge Nuggets table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS knowledge_nuggets (
                id TEXT PRIMARY KEY,
                domain TEXT NOT NULL,
                category TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT,
                sources TEXT,
                reference_uris TEXT,
                confidence REAL DEFAULT 1.0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        # Business Metrics table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS business_metrics (
                id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                domain TEXT NOT NULL,
                formula TEXT,
                formula_type TEXT DEFAULT 'arithmetic',
                input_fields TEXT,
                output_unit TEXT,
                description TEXT NOT NULL,
                lineage TEXT,
                tags TEXT,
                reference_uris TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        # Industry Terms table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS industry_terms (
                id TEXT PRIMARY KEY,
                term TEXT UNIQUE NOT NULL,
                definition TEXT NOT NULL,
                industry TEXT NOT NULL,
                synonyms TEXT,
                related_terms TEXT,
                antonyms TEXT,
                examples TEXT,
                tags TEXT,
                reference_uris TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        # Viz Design Rules table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS viz_design_rules (
                id TEXT PRIMARY KEY,
                document_type TEXT NOT NULL,
                origin_path TEXT NOT NULL,
                pipeline_stage TEXT,
                chart_type TEXT,
                library TEXT,
                data_pattern TEXT,
                chart_family TEXT,
                priority TEXT,
                aliases TEXT,
                section_path TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT,
                category TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        # Create indexes for common queries
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_viz_design_rules_pipeline_stage
            ON viz_design_rules(pipeline_stage)
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_viz_design_rules_chart_type
            ON viz_design_rules(chart_type)
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_viz_design_rules_document_type
            ON viz_design_rules(document_type)
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_viz_design_rules_category
            ON viz_design_rules(category)
            """
        )

        conn.commit()

    def _init_qdrant_client(self, cfg: QdrantLocalConfig) -> Any:
        try:
            from qdrant_client import QdrantClient  # type: ignore
        except ImportError:
            QdrantClient = None  # type: ignore

        path = cfg.path or ":memory:"
        if path == ":memory:":
            return _InMemoryQdrant()
        if QdrantClient is not None:
            try:
                return QdrantClient(path=path)
            except Exception:
                return _InMemoryQdrant()
        return _InMemoryQdrant()

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(UTC).replace(microsecond=0).isoformat()

    def _assert_can_read(self, tenant: TenantContext, user: UserContext) -> None:
        """All tenants can read core context (basic feature)."""
        pass  # No restriction on reads

    def _assert_can_write(self, tenant: TenantContext, user: UserContext) -> None:
        """Only ActBI admins can modify core context."""
        if user.role != "admin" or user.tenant_id != "actbi":
            raise PermissionError("Only ActBI admins can modify CoreContextStore")

    def _ensure_collection(self, collection_name: str, vector_size: int = 384) -> None:
        """Ensure a Qdrant collection exists."""
        try:
            self._qdrant_client.get_collection(collection_name)
        except Exception:
            if hasattr(self._qdrant_client, "_is_fake"):
                self._qdrant_client.create_collection(
                    collection_name=collection_name,
                    vectors_config={"size": vector_size, "distance": "COSINE"},
                )
            else:
                try:
                    from qdrant_client.models import (  # type: ignore
                        Distance,
                        VectorParams,
                    )

                    self._qdrant_client.create_collection(
                        collection_name=collection_name,
                        vectors_config=VectorParams(
                            size=vector_size, distance=Distance.COSINE
                        ),
                    )
                except Exception:
                    pass

    def _upsert_vector(
        self,
        collection_name: str,
        point_id: str,
        vector: list[float],
        payload: dict[str, Any],
    ) -> None:
        """Upsert a vector point to Qdrant."""
        self._ensure_collection(collection_name, len(vector))
        if hasattr(self._qdrant_client, "_is_fake"):
            self._qdrant_client.upsert(
                collection_name=collection_name,
                points=[{"id": point_id, "vector": vector, "payload": payload}],
            )
        else:
            try:
                from qdrant_client.models import PointStruct  # type: ignore

                self._qdrant_client.upsert(
                    collection_name=collection_name,
                    points=[PointStruct(id=point_id, vector=vector, payload=payload)],
                )
            except Exception:
                pass

    def _delete_vector(self, collection_name: str, point_id: str) -> None:
        """Delete a vector point from Qdrant."""
        try:
            if hasattr(self._qdrant_client, "_is_fake"):

                class FakeSelector:
                    def __init__(self, points: list[str]) -> None:
                        self.points = points

                self._qdrant_client.delete(collection_name, FakeSelector([point_id]))
            else:
                from qdrant_client.models import PointIdsList  # type: ignore

                self._qdrant_client.delete(
                    collection_name, PointIdsList(points=[point_id])
                )
        except Exception:
            pass

    def _search_vectors(
        self,
        collection_name: str,
        query: str,
        top_k: int = 10,
        filter_field: str | None = None,
        filter_values: list[str] | None = None,
    ) -> list[str]:
        """Search vectors and return matching IDs."""
        try:
            self._ensure_collection(collection_name)
            embeddings = self._embedder.get_embeddings([query])
            if not embeddings:
                return []

            query_filter = None
            if filter_field and filter_values:
                if hasattr(self._qdrant_client, "_is_fake"):
                    # Simple filter for in-memory client
                    class FakeMatch:
                        def __init__(self, value: str) -> None:
                            self.value = value

                    class FakeCond:
                        def __init__(self, key: str, match: Any) -> None:
                            self.key = key
                            self.match = match

                    class FakeFilter:
                        def __init__(self, must: list[Any]) -> None:
                            self.must = must

                    # For simplicity, just filter by first value
                    if filter_values:
                        query_filter = FakeFilter([
                            FakeCond(filter_field, FakeMatch(filter_values[0]))
                        ])
                else:
                    try:
                        from qdrant_client.models import (
                            FieldCondition,
                            Filter,
                            MatchAny,
                        )  # type: ignore

                        query_filter = Filter(
                            must=[
                                FieldCondition(
                                    key=filter_field, match=MatchAny(any=filter_values)
                                )
                            ]
                        )
                    except ImportError:
                        pass

            hits = self._qdrant_client.search(
                collection_name=collection_name,
                query_vector=embeddings[0],
                limit=top_k,
                query_filter=query_filter,
            )
            return [h.id for h in (hits or [])]
        except Exception:
            return []

    # =========================================================================
    # DOMAIN KNOWLEDGE (KnowledgeNuggets)
    # =========================================================================

    def search_knowledge_nuggets(
        self,
        query: str,
        *,
        domains: list[str] | None = None,
        top_k: int = 10,
        tenant: TenantContext,
        user: UserContext,
    ) -> list[KnowledgeNugget]:
        self._assert_can_read(tenant, user)

        # Try vector search first
        ids = self._search_vectors(
            self.COLLECTION_NUGGETS,
            query,
            top_k,
            filter_field="domain" if domains else None,
            filter_values=domains,
        )

        if ids:
            return [
                self.get_knowledge_nugget(nid, tenant=tenant, user=user) for nid in ids
            ]

        # Fallback to LIKE search
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()
        params: list[Any] = [f"%{query.lower()}%"]
        domain_clause = ""
        if domains:
            placeholders = ",".join("?" for _ in domains)
            domain_clause = f" AND domain IN ({placeholders})"
            params.extend(domains)
        params.append(top_k)

        cur.execute(
            f"""
            SELECT id FROM knowledge_nuggets
            WHERE LOWER(content) LIKE ?{domain_clause}
            LIMIT ?
            """,
            params,
        )
        return [
            self.get_knowledge_nugget(row[0], tenant=tenant, user=user)
            for row in cur.fetchall()
        ]

    def get_knowledge_nugget(
        self,
        nugget_id: str,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> KnowledgeNugget:
        self._assert_can_read(tenant, user)
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()
        cur.execute("SELECT * FROM knowledge_nuggets WHERE id = ?", (nugget_id,))
        row = cur.fetchone()
        if not row:
            raise KeyError(f"KnowledgeNugget not found: {nugget_id}")
        return self._row_to_nugget(row)

    def get_knowledge_nuggets_by_domain(
        self,
        domain: str,
        *,
        category: str | None = None,
        limit: int = 50,
        tenant: TenantContext,
        user: UserContext,
    ) -> list[KnowledgeNugget]:
        self._assert_can_read(tenant, user)
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()
        params: list[Any] = [domain]
        cat_clause = ""
        if category:
            cat_clause = " AND category = ?"
            params.append(category)
        params.append(limit)

        cur.execute(
            f"SELECT * FROM knowledge_nuggets WHERE domain = ?{cat_clause} LIMIT ?",
            params,
        )
        return [self._row_to_nugget(row) for row in cur.fetchall()]

    def upsert_knowledge_nugget(
        self,
        nugget: KnowledgeNugget,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> str:
        self._assert_can_write(tenant, user)
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()

        now = self._now_iso()
        nugget_id = nugget.nugget_id or str(uuid.uuid4())

        cur.execute(
            """
            INSERT INTO knowledge_nuggets (id, domain, category, content, tags, sources, reference_uris, confidence, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                domain = excluded.domain,
                category = excluded.category,
                content = excluded.content,
                tags = excluded.tags,
                sources = excluded.sources,
                reference_uris = excluded.reference_uris,
                confidence = excluded.confidence,
                updated_at = excluded.updated_at
            """,
            (
                nugget_id,
                nugget.domain,
                nugget.category,
                nugget.content,
                json.dumps(nugget.tags),
                json.dumps(nugget.sources),
                json.dumps(nugget.reference_uris),
                nugget.confidence,
                now,
                now,
            ),
        )
        conn.commit()

        # Update vector index (include tags in embedding)
        tags_text = " ".join(nugget.tags) if nugget.tags else ""
        text_for_embedding = (
            f"{nugget.domain} {nugget.category} {nugget.content} {tags_text}".strip()
        )
        embeddings = self._embedder.get_embeddings([text_for_embedding])
        if embeddings:
            self._upsert_vector(
                self.COLLECTION_NUGGETS,
                nugget_id,
                embeddings[0],
                {"domain": nugget.domain, "category": nugget.category},
            )

        return nugget_id

    def delete_knowledge_nugget(
        self,
        nugget_id: str,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> None:
        self._assert_can_write(tenant, user)
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()
        cur.execute("DELETE FROM knowledge_nuggets WHERE id = ?", (nugget_id,))
        conn.commit()
        self._delete_vector(self.COLLECTION_NUGGETS, nugget_id)

    def _row_to_nugget(self, row: tuple[Any, ...]) -> KnowledgeNugget:
        return KnowledgeNugget(
            nugget_id=row[0],
            domain=row[1],
            category=row[2],
            content=row[3],
            tags=json.loads(row[4]) if row[4] else [],
            sources=json.loads(row[5]) if row[5] else [],
            reference_uris=json.loads(row[6]) if row[6] else [],
            confidence=row[7] or 1.0,
            created_at=datetime.fromisoformat(row[8]),
            updated_at=datetime.fromisoformat(row[9]),
        )

    # =========================================================================
    # BUSINESS METRICS
    # =========================================================================

    def search_business_metrics(
        self,
        query: str,
        *,
        domains: list[str] | None = None,
        top_k: int = 10,
        tenant: TenantContext,
        user: UserContext,
    ) -> list[BusinessMetric]:
        self._assert_can_read(tenant, user)

        ids = self._search_vectors(
            self.COLLECTION_METRICS,
            query,
            top_k,
            filter_field="domain" if domains else None,
            filter_values=domains,
        )

        if ids:
            return [
                self.get_business_metric(mid, tenant=tenant, user=user) for mid in ids
            ]

        # Fallback to LIKE search
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()
        params: list[Any] = [f"%{query.lower()}%", f"%{query.lower()}%"]
        domain_clause = ""
        if domains:
            placeholders = ",".join("?" for _ in domains)
            domain_clause = f" AND domain IN ({placeholders})"
            params.extend(domains)
        params.append(top_k)

        cur.execute(
            f"""
            SELECT id FROM business_metrics
            WHERE (LOWER(name) LIKE ? OR LOWER(description) LIKE ?){domain_clause}
            LIMIT ?
            """,
            params,
        )
        return [
            self.get_business_metric(row[0], tenant=tenant, user=user)
            for row in cur.fetchall()
        ]

    def get_business_metric(
        self,
        metric_id: str,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> BusinessMetric:
        self._assert_can_read(tenant, user)
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()
        cur.execute("SELECT * FROM business_metrics WHERE id = ?", (metric_id,))
        row = cur.fetchone()
        if not row:
            raise KeyError(f"BusinessMetric not found: {metric_id}")
        return self._row_to_metric(row)

    def get_business_metric_by_name(
        self,
        name: str,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> BusinessMetric | None:
        self._assert_can_read(tenant, user)
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()
        cur.execute("SELECT * FROM business_metrics WHERE name = ?", (name,))
        row = cur.fetchone()
        if not row:
            return None
        return self._row_to_metric(row)

    def upsert_business_metric(
        self,
        metric: BusinessMetric,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> str:
        self._assert_can_write(tenant, user)
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()

        now = self._now_iso()
        metric_id = metric.metric_id or str(uuid.uuid4())

        cur.execute(
            """
            INSERT INTO business_metrics (id, name, domain, formula, formula_type, input_fields, output_unit, description, lineage, tags, reference_uris, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                domain = excluded.domain,
                formula = excluded.formula,
                formula_type = excluded.formula_type,
                input_fields = excluded.input_fields,
                output_unit = excluded.output_unit,
                description = excluded.description,
                lineage = excluded.lineage,
                tags = excluded.tags,
                reference_uris = excluded.reference_uris,
                updated_at = excluded.updated_at
            """,
            (
                metric_id,
                metric.name,
                metric.domain,
                metric.formula,
                metric.formula_type,
                json.dumps(metric.input_fields),
                metric.output_unit,
                metric.description,
                json.dumps(metric.lineage),
                json.dumps(metric.tags),
                json.dumps(metric.reference_uris),
                now,
                now,
            ),
        )
        conn.commit()

        # Update vector index (include tags in embedding)
        tags_text = " ".join(metric.tags) if metric.tags else ""
        text_for_embedding = (
            f"{metric.name} {metric.domain} {metric.description} {tags_text}".strip()
        )
        embeddings = self._embedder.get_embeddings([text_for_embedding])
        if embeddings:
            self._upsert_vector(
                self.COLLECTION_METRICS,
                metric_id,
                embeddings[0],
                {"domain": metric.domain, "name": metric.name},
            )

        return metric_id

    def delete_business_metric(
        self,
        metric_id: str,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> None:
        self._assert_can_write(tenant, user)
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()
        cur.execute("DELETE FROM business_metrics WHERE id = ?", (metric_id,))
        conn.commit()
        self._delete_vector(self.COLLECTION_METRICS, metric_id)

    def _row_to_metric(self, row: tuple[Any, ...]) -> BusinessMetric:
        return BusinessMetric(
            metric_id=row[0],
            name=row[1],
            domain=row[2],
            formula=row[3],
            formula_type=row[4] or "arithmetic",
            input_fields=json.loads(row[5]) if row[5] else [],
            output_unit=row[6],
            description=row[7],
            lineage=json.loads(row[8]) if row[8] else {},
            tags=json.loads(row[9]) if row[9] else [],
            reference_uris=json.loads(row[10]) if row[10] else [],
            created_at=datetime.fromisoformat(row[11]),
            updated_at=datetime.fromisoformat(row[12]),
        )

    # =========================================================================
    # BUSINESS DICTIONARY (Industry Terms)
    # =========================================================================

    def search_industry_terms(
        self,
        query: str,
        *,
        industries: list[str] | None = None,
        top_k: int = 10,
        tenant: TenantContext,
        user: UserContext,
    ) -> list[IndustryTerm]:
        self._assert_can_read(tenant, user)

        ids = self._search_vectors(
            self.COLLECTION_TERMS,
            query,
            top_k,
            filter_field="industry" if industries else None,
            filter_values=industries,
        )

        if ids:
            return [
                self.get_industry_term(tid, tenant=tenant, user=user) for tid in ids
            ]

        # Fallback to LIKE search
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()
        params: list[Any] = [f"%{query.lower()}%", f"%{query.lower()}%"]
        industry_clause = ""
        if industries:
            placeholders = ",".join("?" for _ in industries)
            industry_clause = f" AND industry IN ({placeholders})"
            params.extend(industries)
        params.append(top_k)

        cur.execute(
            f"""
            SELECT id FROM industry_terms
            WHERE (LOWER(term) LIKE ? OR LOWER(definition) LIKE ?){industry_clause}
            LIMIT ?
            """,
            params,
        )
        return [
            self.get_industry_term(row[0], tenant=tenant, user=user)
            for row in cur.fetchall()
        ]

    def get_industry_term(
        self,
        term_id: str,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> IndustryTerm:
        self._assert_can_read(tenant, user)
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()
        cur.execute("SELECT * FROM industry_terms WHERE id = ?", (term_id,))
        row = cur.fetchone()
        if not row:
            raise KeyError(f"IndustryTerm not found: {term_id}")
        return self._row_to_term(row)

    def get_industry_term_by_name(
        self,
        term: str,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> IndustryTerm | None:
        self._assert_can_read(tenant, user)
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()
        cur.execute("SELECT * FROM industry_terms WHERE term = ?", (term,))
        row = cur.fetchone()
        if not row:
            return None
        return self._row_to_term(row)

    def get_related_industry_terms(
        self,
        term_id: str,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> list[IndustryTerm]:
        self._assert_can_read(tenant, user)
        term = self.get_industry_term(term_id, tenant=tenant, user=user)
        related: list[IndustryTerm] = []
        for related_id in term.related_terms:
            with contextlib.suppress(KeyError):
                related.append(
                    self.get_industry_term(related_id, tenant=tenant, user=user)
                )
        return related

    def upsert_industry_term(
        self,
        term: IndustryTerm,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> str:
        self._assert_can_write(tenant, user)
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()

        now = self._now_iso()
        term_id = term.term_id or str(uuid.uuid4())

        cur.execute(
            """
            INSERT INTO industry_terms (id, term, definition, industry, synonyms, related_terms, antonyms, examples, tags, reference_uris, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                term = excluded.term,
                definition = excluded.definition,
                industry = excluded.industry,
                synonyms = excluded.synonyms,
                related_terms = excluded.related_terms,
                antonyms = excluded.antonyms,
                examples = excluded.examples,
                tags = excluded.tags,
                reference_uris = excluded.reference_uris,
                updated_at = excluded.updated_at
            """,
            (
                term_id,
                term.term,
                term.definition,
                term.industry,
                json.dumps(term.synonyms),
                json.dumps(term.related_terms),
                json.dumps(term.antonyms),
                json.dumps(term.examples),
                json.dumps(term.tags),
                json.dumps(term.reference_uris),
                now,
                now,
            ),
        )
        conn.commit()

        # Update vector index (include tags in embedding)
        tags_text = " ".join(term.tags) if term.tags else ""
        text_for_embedding = (
            f"{term.term} {term.industry} {term.definition} {tags_text}".strip()
        )
        embeddings = self._embedder.get_embeddings([text_for_embedding])
        if embeddings:
            self._upsert_vector(
                self.COLLECTION_TERMS,
                term_id,
                embeddings[0],
                {"industry": term.industry, "term": term.term},
            )

        return term_id

    def link_industry_terms(
        self,
        term_id: str,
        related_term_ids: list[str],
        *,
        relationship: str = "related",
        tenant: TenantContext,
        user: UserContext,
    ) -> None:
        self._assert_can_write(tenant, user)
        term = self.get_industry_term(term_id, tenant=tenant, user=user)

        if relationship == "synonym":
            updated_synonyms = list(set(term.synonyms + related_term_ids))
            term.synonyms = updated_synonyms
        elif relationship == "antonym":
            updated_antonyms = list(set(term.antonyms + related_term_ids))
            term.antonyms = updated_antonyms
        else:  # "related"
            updated_related = list(set(term.related_terms + related_term_ids))
            term.related_terms = updated_related

        # Update in database
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()
        now = self._now_iso()
        cur.execute(
            """
            UPDATE industry_terms SET
                synonyms = ?,
                related_terms = ?,
                antonyms = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                json.dumps(term.synonyms),
                json.dumps(term.related_terms),
                json.dumps(term.antonyms),
                now,
                term_id,
            ),
        )
        conn.commit()

    def delete_industry_term(
        self,
        term_id: str,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> None:
        self._assert_can_write(tenant, user)
        conn = self._conn or sqlite3.connect(
            self._sqlite_config.database_path, check_same_thread=False
        )
        cur = conn.cursor()
        cur.execute("DELETE FROM industry_terms WHERE id = ?", (term_id,))
        conn.commit()
        self._delete_vector(self.COLLECTION_TERMS, term_id)

    def _row_to_term(self, row: tuple[Any, ...]) -> IndustryTerm:
        return IndustryTerm(
            term_id=row[0],
            term=row[1],
            definition=row[2],
            industry=row[3],
            synonyms=json.loads(row[4]) if row[4] else [],
            related_terms=json.loads(row[5]) if row[5] else [],
            antonyms=json.loads(row[6]) if row[6] else [],
            examples=json.loads(row[7]) if row[7] else [],
            tags=json.loads(row[8]) if row[8] else [],
            reference_uris=json.loads(row[9]) if row[9] else [],
            created_at=datetime.fromisoformat(row[10]),
            updated_at=datetime.fromisoformat(row[11]),
        )

    # =========================================================================
    # VISUALIZATION DESIGN (VizDesignRule)
    # =========================================================================

    def get_viz_design_rule(
        self,
        rule_id: str,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> VizDesignRule:
        """Get a specific viz design rule by ID."""
        self._assert_can_read(tenant, user)
        with self._db_lock:
            conn = self._conn or sqlite3.connect(
                self._sqlite_config.database_path, check_same_thread=False
            )
            cur = conn.cursor()
            cur.execute("SELECT * FROM viz_design_rules WHERE id = ?", (rule_id,))
            row = cur.fetchone()
        if not row:
            raise KeyError(f"VizDesignRule not found: {rule_id}")
        return self._row_to_viz_rule(row)

    def get_blueprint_rule(
        self,
        pipeline_stage: str,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> VizDesignRule:
        """Get the blueprint (interface document) for a pipeline stage."""
        self._assert_can_read(tenant, user)
        with self._db_lock:
            conn = self._conn or sqlite3.connect(
                self._sqlite_config.database_path, check_same_thread=False
            )
            cur = conn.cursor()
            cur.execute(
                """
                SELECT * FROM viz_design_rules
                WHERE document_type = 'action-interface' AND pipeline_stage = ?
                LIMIT 1
                """,
                (pipeline_stage,),
            )
            row = cur.fetchone()
        if not row:
            raise KeyError(f"Blueprint not found for stage: {pipeline_stage}")
        return self._row_to_viz_rule(row)

    def get_chart_rules(
        self,
        pipeline_stage: str,
        chart_type: str,
        *,
        library: str | None = None,
        tenant: TenantContext,
        user: UserContext,
    ) -> list[VizDesignRule]:
        """Get all rules for a specific chart type at a pipeline stage."""
        self._assert_can_read(tenant, user)
        with self._db_lock:
            conn = self._conn or sqlite3.connect(
                self._sqlite_config.database_path, check_same_thread=False
            )
            cur = conn.cursor()

            if library:
                cur.execute(
                    """
                    SELECT * FROM viz_design_rules
                    WHERE pipeline_stage = ? AND chart_type = ? AND library = ?
                    ORDER BY section_path
                    """,
                    (pipeline_stage, chart_type, library),
                )
            else:
                cur.execute(
                    """
                    SELECT * FROM viz_design_rules
                    WHERE pipeline_stage = ? AND chart_type = ? AND library IS NULL
                    ORDER BY section_path
                    """,
                    (pipeline_stage, chart_type),
                )
            rows = cur.fetchall()
        return [self._row_to_viz_rule(row) for row in rows]

    def get_foundation_rules(
        self,
        *,
        category: str | None = None,
        tenant: TenantContext,
        user: UserContext,
    ) -> list[VizDesignRule]:
        """Get foundation/reference document rules."""
        self._assert_can_read(tenant, user)
        with self._db_lock:
            conn = self._conn or sqlite3.connect(
                self._sqlite_config.database_path, check_same_thread=False
            )
            cur = conn.cursor()

            if category:
                cur.execute(
                    """
                    SELECT * FROM viz_design_rules
                    WHERE document_type = 'reference' AND category = ?
                    ORDER BY origin_path, section_path
                    """,
                    (category,),
                )
            else:
                cur.execute(
                    """
                    SELECT * FROM viz_design_rules
                    WHERE document_type = 'reference'
                    ORDER BY origin_path, section_path
                    """
                )
            rows = cur.fetchall()
        return [self._row_to_viz_rule(row) for row in rows]

    def search_viz_design_rules(
        self,
        query: str,
        *,
        pipeline_stage: str | None = None,
        chart_types: list[str] | None = None,
        priorities: list[str] | None = None,
        tags: list[str] | None = None,
        top_k: int = 10,
        tenant: TenantContext,
        user: UserContext,
    ) -> list[VizDesignRuleResponse]:
        """Semantic search with metadata filtering."""
        self._assert_can_read(tenant, user)

        # Build filter for vector search
        filter_conditions: dict[str, Any] = {}
        if pipeline_stage:
            filter_conditions["pipeline_stage"] = pipeline_stage
        if chart_types and len(chart_types) == 1:
            filter_conditions["chart_type"] = chart_types[0]
        if priorities and len(priorities) == 1:
            filter_conditions["priority"] = priorities[0]

        # Try vector search first
        hits = self._search_viz_vectors(
            query,
            top_k,
            filter_conditions=filter_conditions if filter_conditions else None,
        )

        if hits:
            results: list[VizDesignRuleResponse] = []
            rank = 0
            for rid, score in hits:
                try:
                    rule = self.get_viz_design_rule(rid, tenant=tenant, user=user)
                    # Apply additional filters that couldn't be done in vector search
                    if (
                        chart_types
                        and len(chart_types) > 1
                        and rule.chart_type not in chart_types
                    ):
                        continue
                    if (
                        priorities
                        and len(priorities) > 1
                        and rule.priority not in priorities
                    ):
                        continue
                    if tags and not any(t in rule.tags for t in tags):
                        continue
                    rank += 1
                    results.append(
                        VizDesignRuleResponse(
                            rule=rule,
                            stats=RetrievalStats(rank=rank, score=score),
                        )
                    )
                except KeyError:
                    continue
            return results

        # Fallback to LIKE search (no scores available, use 0.0)
        with self._db_lock:
            conn = self._conn or sqlite3.connect(
                self._sqlite_config.database_path, check_same_thread=False
            )
            cur = conn.cursor()
            params: list[Any] = [f"%{query.lower()}%", f"%{query.lower()}%"]
            where_clauses = ["(LOWER(content) LIKE ? OR LOWER(section_path) LIKE ?)"]

            if pipeline_stage:
                where_clauses.append("pipeline_stage = ?")
                params.append(pipeline_stage)
            if chart_types:
                placeholders = ",".join("?" for _ in chart_types)
                where_clauses.append(f"chart_type IN ({placeholders})")
                params.extend(chart_types)
            if priorities:
                placeholders = ",".join("?" for _ in priorities)
                where_clauses.append(f"priority IN ({placeholders})")
                params.extend(priorities)

            params.append(top_k)

            cur.execute(
                f"""
                SELECT * FROM viz_design_rules
                WHERE {" AND ".join(where_clauses)}
                LIMIT ?
                """,
                params,
            )

            rows = cur.fetchall()

        rules = [self._row_to_viz_rule(row) for row in rows]

        # Filter by tags if specified (need to check JSON array)
        if tags:
            rules = [r for r in rules if any(t in r.tags for t in tags)]

        # Wrap in VizDesignRuleResponse with 0.0 scores (fallback search)
        return [
            VizDesignRuleResponse(
                rule=rule,
                stats=RetrievalStats(rank=i + 1, score=0.0),
            )
            for i, rule in enumerate(rules)
        ]

    def _search_viz_vectors(
        self,
        query: str,
        top_k: int = 10,
        filter_conditions: dict[str, Any] | None = None,
    ) -> list[tuple[str, float]]:
        """Search viz design rule vectors and return matching (ID, score) pairs."""
        try:
            self._ensure_collection(self.COLLECTION_VIZ_RULES)
            embeddings = self._embedder.get_embeddings([query])
            if not embeddings:
                return []

            query_filter = None
            if filter_conditions:
                if hasattr(self._qdrant_client, "_is_fake"):
                    # Simple filter for in-memory client - use first condition
                    class FakeMatch:
                        def __init__(self, value: str) -> None:
                            self.value = value

                    class FakeCond:
                        def __init__(self, key: str, match: Any) -> None:
                            self.key = key
                            self.match = match

                    class FakeFilter:
                        def __init__(self, must: list[Any]) -> None:
                            self.must = must

                    must_conditions = [
                        FakeCond(k, FakeMatch(v))
                        for k, v in filter_conditions.items()
                        if v is not None
                    ]
                    if must_conditions:
                        query_filter = FakeFilter(must_conditions)
                else:
                    try:
                        from qdrant_client.models import (
                            FieldCondition,
                            Filter,
                            MatchValue,
                        )  # type: ignore

                        must_conditions = [
                            FieldCondition(key=k, match=MatchValue(value=v))
                            for k, v in filter_conditions.items()
                            if v is not None
                        ]
                        if must_conditions:
                            query_filter = Filter(must=must_conditions)
                    except ImportError:
                        pass

            hits = self._qdrant_client.search(
                collection_name=self.COLLECTION_VIZ_RULES,
                query_vector=embeddings[0],
                limit=top_k,
                query_filter=query_filter,
            )
            return [(h.id, h.score) for h in (hits or [])]
        except Exception:
            return []

    def upsert_viz_design_rule(
        self,
        rule: VizDesignRule,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> str:
        """Upsert a viz design rule. Returns the rule ID."""
        self._assert_can_write(tenant, user)
        now = self._now_iso()
        rule_id = rule.rule_id or str(uuid.uuid4())

        with self._db_lock:
            conn = self._conn or sqlite3.connect(
                self._sqlite_config.database_path, check_same_thread=False
            )
            cur = conn.cursor()

            cur.execute(
                """
                INSERT INTO viz_design_rules (
                    id, document_type, origin_path, pipeline_stage, chart_type, library,
                    data_pattern, chart_family, priority, aliases, section_path, content,
                    tags, category, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    document_type = excluded.document_type,
                    origin_path = excluded.origin_path,
                    pipeline_stage = excluded.pipeline_stage,
                    chart_type = excluded.chart_type,
                    library = excluded.library,
                    data_pattern = excluded.data_pattern,
                    chart_family = excluded.chart_family,
                    priority = excluded.priority,
                    aliases = excluded.aliases,
                    section_path = excluded.section_path,
                    content = excluded.content,
                    tags = excluded.tags,
                    category = excluded.category,
                    updated_at = excluded.updated_at
                """,
                (
                    rule_id,
                    rule.document_type,
                    rule.origin_path,
                    rule.pipeline_stage,
                    rule.chart_type,
                    rule.library,
                    rule.data_pattern,
                    rule.chart_family,
                    rule.priority,
                    json.dumps(rule.aliases),
                    rule.section_path,
                    rule.content,
                    json.dumps(rule.tags),
                    rule.category,
                    now,
                    now,
                ),
            )
            conn.commit()

        # Update vector index with rich payload for filtering
        # Embed the content with contextual information for better semantic search
        text_for_embedding = rule.content
        embeddings = self._embedder.get_embeddings([text_for_embedding])
        if embeddings:
            payload = {
                "document_type": rule.document_type,
                "pipeline_stage": rule.pipeline_stage,
                "chart_type": rule.chart_type,
                "library": rule.library,
                "data_pattern": rule.data_pattern,
                "priority": rule.priority,
                "tags": rule.tags,
                "origin_path": rule.origin_path,
                "section_path": rule.section_path,
                "category": rule.category,
            }
            self._upsert_vector(
                self.COLLECTION_VIZ_RULES,
                rule_id,
                embeddings[0],
                payload,
            )

        return rule_id

    def delete_viz_design_rule(
        self,
        rule_id: str,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> None:
        """Delete a viz design rule by ID."""
        self._assert_can_write(tenant, user)
        with self._db_lock:
            conn = self._conn or sqlite3.connect(
                self._sqlite_config.database_path, check_same_thread=False
            )
            cur = conn.cursor()
            cur.execute("DELETE FROM viz_design_rules WHERE id = ?", (rule_id,))
            conn.commit()
        self._delete_vector(self.COLLECTION_VIZ_RULES, rule_id)

    def _row_to_viz_rule(self, row: tuple[Any, ...]) -> VizDesignRule:
        """Convert a database row to a VizDesignRule instance."""
        return VizDesignRule(
            rule_id=row[0],
            document_type=row[1],
            origin_path=row[2],
            pipeline_stage=row[3],
            chart_type=row[4],
            library=row[5],
            data_pattern=row[6],
            chart_family=row[7],
            priority=row[8],
            aliases=json.loads(row[9]) if row[9] else [],
            section_path=row[10],
            content=row[11],
            tags=json.loads(row[12]) if row[12] else [],
            category=row[13],
            created_at=datetime.fromisoformat(row[14])
            if row[14]
            else datetime.now(UTC),
            updated_at=datetime.fromisoformat(row[15])
            if row[15]
            else datetime.now(UTC),
        )

    def close(self) -> None:
        """Close SQLite connection and Qdrant client."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None
        if hasattr(self._qdrant_client, "close") and callable(
            self._qdrant_client.close
        ):
            self._qdrant_client.close()


# =============================================================================
# Production Backend (Stub)
# =============================================================================


class QdrantSupabaseCloudFSCoreContextStore:
    """Production backend using Qdrant Cloud, Supabase, and cloud object storage.

    This is a stub implementation - full implementation would use actual
    Qdrant Cloud and Supabase clients.
    """

    def __init__(
        self,
        *,
        qdrant: QdrantServiceConfig,
        supabase: SupabaseConfig,
        fs_cloud: FSSpecObjectDocConfig,
        embedder_config: SchemaEmbedderConfig | None = None,
    ) -> None:
        self._qdrant_cfg = qdrant
        self._supabase_cfg = supabase
        self._fs_cloud = fs_cloud
        self._embedder_cfg = embedder_config

    def search_knowledge_nuggets(
        self, *args: Any, **kwargs: Any
    ) -> list[KnowledgeNugget]:
        raise NotImplementedError("Production backend not yet implemented")

    def get_knowledge_nugget(self, *args: Any, **kwargs: Any) -> KnowledgeNugget:
        raise NotImplementedError("Production backend not yet implemented")

    def get_knowledge_nuggets_by_domain(
        self, *args: Any, **kwargs: Any
    ) -> list[KnowledgeNugget]:
        raise NotImplementedError("Production backend not yet implemented")

    def upsert_knowledge_nugget(self, *args: Any, **kwargs: Any) -> str:
        raise NotImplementedError("Production backend not yet implemented")

    def delete_knowledge_nugget(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError("Production backend not yet implemented")

    def search_business_metrics(
        self, *args: Any, **kwargs: Any
    ) -> list[BusinessMetric]:
        raise NotImplementedError("Production backend not yet implemented")

    def get_business_metric(self, *args: Any, **kwargs: Any) -> BusinessMetric:
        raise NotImplementedError("Production backend not yet implemented")

    def get_business_metric_by_name(
        self, *args: Any, **kwargs: Any
    ) -> BusinessMetric | None:
        raise NotImplementedError("Production backend not yet implemented")

    def upsert_business_metric(self, *args: Any, **kwargs: Any) -> str:
        raise NotImplementedError("Production backend not yet implemented")

    def delete_business_metric(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError("Production backend not yet implemented")

    def search_industry_terms(self, *args: Any, **kwargs: Any) -> list[IndustryTerm]:
        raise NotImplementedError("Production backend not yet implemented")

    def get_industry_term(self, *args: Any, **kwargs: Any) -> IndustryTerm:
        raise NotImplementedError("Production backend not yet implemented")

    def get_industry_term_by_name(
        self, *args: Any, **kwargs: Any
    ) -> IndustryTerm | None:
        raise NotImplementedError("Production backend not yet implemented")

    def get_related_industry_terms(
        self, *args: Any, **kwargs: Any
    ) -> list[IndustryTerm]:
        raise NotImplementedError("Production backend not yet implemented")

    def upsert_industry_term(self, *args: Any, **kwargs: Any) -> str:
        raise NotImplementedError("Production backend not yet implemented")

    def link_industry_terms(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError("Production backend not yet implemented")

    def delete_industry_term(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError("Production backend not yet implemented")

    def get_viz_design_rule(self, *args: Any, **kwargs: Any) -> VizDesignRule:
        raise NotImplementedError("Production backend not yet implemented")

    def get_blueprint_rule(self, *args: Any, **kwargs: Any) -> VizDesignRule:
        raise NotImplementedError("Production backend not yet implemented")

    def get_chart_rules(self, *args: Any, **kwargs: Any) -> list[VizDesignRule]:
        raise NotImplementedError("Production backend not yet implemented")

    def get_foundation_rules(self, *args: Any, **kwargs: Any) -> list[VizDesignRule]:
        raise NotImplementedError("Production backend not yet implemented")

    def search_viz_design_rules(
        self, *args: Any, **kwargs: Any
    ) -> list[VizDesignRuleResponse]:
        raise NotImplementedError("Production backend not yet implemented")

    def upsert_viz_design_rule(self, *args: Any, **kwargs: Any) -> str:
        raise NotImplementedError("Production backend not yet implemented")

    def delete_viz_design_rule(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError("Production backend not yet implemented")

    def close(self) -> None:
        pass


# =============================================================================
# Factory Function
# =============================================================================


def create_core_context_store(config: CoreContextStoreConfig) -> CoreContextStore:
    """Create a CoreContextStore instance based on configuration."""
    if config.backend == "qdrant_sqlite_localfs":
        assert config.qdrant_local is not None, "qdrant_local config must be provided"
        assert config.sqlite is not None, "sqlite config must be provided"
        return QdrantSqliteLocalFSCoreContextStore(
            qdrant_config=config.qdrant_local,
            sqlite_config=config.sqlite,
            fs_local_config=config.fsspec_local,
            embedder_config=config.embedder,
        )
    if config.backend == "qdrant_supabase_cloudfs":
        assert config.qdrant_service is not None, (
            "qdrant_service config must be provided"
        )
        assert config.supabase is not None, "supabase config must be provided"
        assert config.fsspec_object is not None, "fsspec_object config must be provided"
        return QdrantSupabaseCloudFSCoreContextStore(
            qdrant=config.qdrant_service,
            supabase=config.supabase,
            fs_cloud=config.fsspec_object,
            embedder_config=config.embedder,
        )
    raise ValueError(f"Unsupported backend: {config.backend}")
