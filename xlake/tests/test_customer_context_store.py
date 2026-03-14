from __future__ import annotations

import os
import shutil
import tempfile
from datetime import UTC, datetime

from xlake.core import TenantContext, TenantIdentity, UserContext
from xlake.stores.config import (
    FSSpecLocalDocConfig,
    QdrantLocalConfig,
    SchemaEmbedderConfig,
    SqliteConfig,
)
from xlake.stores.customer_context_store import (
    QdrantSqliteLocalFSCustomerContextStore,
)


def _make_dev_store(tmpdir: str) -> QdrantSqliteLocalFSCustomerContextStore:
    sqlite_path = os.path.join(tmpdir, "ctx.db")
    base_dir = os.path.join(tmpdir, "snapshots")
    os.makedirs(base_dir, exist_ok=True)
    return QdrantSqliteLocalFSCustomerContextStore(
        qdrant_config=QdrantLocalConfig(path=":memory:"),
        sqlite_config=SqliteConfig(database_path=sqlite_path),
        fs_local_config=FSSpecLocalDocConfig(base_dir=base_dir),
        embedder_config=SchemaEmbedderConfig(
            strategy="fields_and_facts", model="fastembed:BAAI/bge-small-en-v1.5"
        ),
    )


def _user(tenant: str = "tenant_test") -> UserContext:
    return UserContext(
        user_id="u1",
        tenant_id=tenant,
        role="admin",
    )


def _tenant(tenant: str = "tenant_test") -> TenantContext:
    ident = TenantIdentity(
        tenant_id=tenant,
        tenant_name="Test Tenant",
        industry="testing",
        region="EU",
        timezone="Europe/Paris",
        locale="en_US",
    )
    return TenantContext(identity=ident)


def test_create_and_get_schema_context():
    tmpdir = tempfile.mkdtemp(prefix="xlake_ctx_")
    try:
        store = _make_dev_store(tmpdir)
        uc = _user()
        tc = _tenant()
        res = store.create_schema(
            name="Sales",
            nl_description="Schema describing sales tables and fields.",
            tenant=tc,
            user=uc,
        )
        schema_id = res["schema_id"]
        ctx = store.get_schema_context(schema_id, tenant=tc, user=uc)
        assert ctx.data_schema["name"] == "Sales"
        assert ctx.data_schema["version"] == 1
        assert isinstance(ctx.facts_by_entity, dict)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_add_and_search_facts():
    tmpdir = tempfile.mkdtemp(prefix="xlake_ctx_")
    try:
        store = _make_dev_store(tmpdir)
        uc = _user()
        tc = _tenant()
        res = store.create_schema(
            name="Inventory",
            nl_description="Inventory schema.",
            tenant=tc,
            user=uc,
        )
        schema_id = res["schema_id"]
        # Add facts for a couple of entities (may not exist in entities table yet; that's ok for testing facts)
        f1 = store.add_fact(
            schema_id=schema_id,
            entity_id="table:inventory",
            text="Inventory table holds stock levels.",
            date=datetime.now(UTC).date().isoformat(),
            tenant=tc,
            user=uc,
        )
        assert "fact_id" in f1

        f2 = store.add_fact(
            schema_id=schema_id,
            entity_id="field:inventory.stock_qty",
            text="stock_qty is numeric.",
            tenant=tc,
            user=uc,
        )
        assert "fact_id" in f2

        # NL search should find the schema by text
        results = store.search_context("stock", tenant=tc, user=uc)
        assert len(results) >= 1
        # Facts by entity should include the field we added
        found = any(
            "field:inventory.stock_qty" in rec.facts_by_entity
            and rec.facts_by_entity["field:inventory.stock_qty"]
            for rec in results
        )
        assert found
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_create_with_schema_json_and_get_context():
    tmpdir = tempfile.mkdtemp(prefix="xlake_ctx_")
    try:
        store = _make_dev_store(tmpdir)
        uc = _user()
        tc = _tenant()
        # Realistic schema with 2 databases, 2 tables each, 3 fields per table
        schema_json = """
        {
          "name": "Company Unified Schema",
          "description": "Two databases with multiple tables and fields",
          "databases": [
            {
              "name": "sales",
              "tables": [
                {
                  "name": "orders",
                  "description": "Customer orders",
                  "fields": [
                    {"name": "order_id", "type": "text", "nullable": false},
                    {"name": "customer_id", "type": "text", "nullable": false},
                    {"name": "amount", "type": "float", "nullable": false}
                  ]
                },
                {
                  "name": "order_items",
                  "description": "Order line items",
                  "fields": [
                    {"name": "item_id", "type": "text", "nullable": false},
                    {"name": "order_id", "type": "text", "nullable": false},
                    {"name": "price", "type": "float", "nullable": false}
                  ]
                }
              ]
            },
            {
              "name": "marketing",
              "tables": [
                {
                  "name": "campaigns",
                  "description": "Campaign metadata",
                  "fields": [
                    {"name": "campaign_id", "type": "text", "nullable": false},
                    {"name": "name", "type": "text", "nullable": false},
                    {"name": "budget", "type": "float", "nullable": false}
                  ]
                },
                {
                  "name": "leads",
                  "description": "Lead records",
                  "fields": [
                    {"name": "lead_id", "type": "text", "nullable": false},
                    {"name": "source", "type": "text", "nullable": true},
                    {"name": "score", "type": "int", "nullable": true}
                  ]
                }
              ]
            }
          ]
        }
        """.strip()

        # Build two facts for each field using the canonical id <db>:<table>.<column>
        field_ids = [
            # sales.orders
            "sales:orders.order_id",
            "sales:orders.customer_id",
            "sales:orders.amount",
            # sales.order_items
            "sales:order_items.item_id",
            "sales:order_items.order_id",
            "sales:order_items.price",
            # marketing.campaigns
            "marketing:campaigns.campaign_id",
            "marketing:campaigns.name",
            "marketing:campaigns.budget",
            # marketing.leads
            "marketing:leads.lead_id",
            "marketing:leads.source",
            "marketing:leads.score",
        ]
        initial_facts = {
            fid: [
                {"text": f"{fid} is a critical column."},
                {"text": f"{fid} is used in reporting."},
            ]
            for fid in field_ids
        }

        res = store.create_schema(
            name="Company Unified Schema",
            nl_description="Two-database schema with facts per field",
            schema_json=schema_json,
            initial_facts=initial_facts,
            tenant=tc,
            user=uc,
        )
        schema_id = res["schema_id"]

        # Retrieve schema context and validate structure
        ctx = store.get_schema_context(schema_id, tenant=tc, user=uc)
        assert ctx.data_schema["name"] == "Company Unified Schema"
        assert "databases" in ctx.data_schema and len(ctx.data_schema["databases"]) == 2

        # Validate facts per field (2 each)
        # It's possible some facts are trimmed by facts_per_entity default; pass large limit by fetching entity facts
        facts = store.get_entity_facts(
            schema_id=schema_id,
            entity_ids=field_ids,
            limit=10,
            tenant=tc,
            user=uc,
        )
        assert set(facts.keys()).issuperset(set(field_ids))
        for fid in field_ids:
            assert len(facts.get(fid, [])) >= 2
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_embeddings_upsert_on_create_schema():
    tmpdir = tempfile.mkdtemp(prefix="xlake_ctx_")
    try:
        store = _make_dev_store(tmpdir)
        uc = _user()
        tc = _tenant()
        # Force embeddings path to be deterministic and available (no model download)
        store._embedder.get_embeddings = lambda texts: [[1.0, 0.0, 0.0] for _ in texts]  # type: ignore[attr-defined]
        # Simple schema with two fields
        schema_json = """
        {
          "name": "VecTest",
          "description": "Schema for embedding upsert test",
          "databases": [
            {
              "name": "db1",
              "tables": [
                {
                  "name": "t1",
                  "fields": [
                    {"name": "a", "type": "text", "nullable": false},
                    {"name": "b", "type": "float", "nullable": true}
                  ]
                }
              ]
            }
          ]
        }
        """.strip()
        store.create_schema(
            name="VecTest",
            nl_description="Embedding upsert test schema.",
            schema_json=schema_json,
            tenant=tc,
            user=uc,
        )
        # Count vectors in per-tenant fields collection
        collection = f"{tc.identity.tenant_id}__fields"
        qclient = store._qdrant_client  # type: ignore[attr-defined]
        assert qclient is not None
        cnt = qclient.count(collection_name=collection, exact=True)
        # At least 2 field vectors should be present
        assert getattr(cnt, "count", 0) >= 2
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_vector_search_retrieves_schema_and_facts():
    tmpdir = tempfile.mkdtemp(prefix="xlake_ctx_")
    try:
        store = _make_dev_store(tmpdir)
        uc = _user()
        tc = _tenant()
        # Deterministic embeddings for write and query, avoid model downloads
        store._embedder.get_embeddings = lambda texts: [[1.0, 0.0, 0.0] for _ in texts]  # type: ignore[attr-defined]
        # Minimal schema with a single field
        schema_json = """
        {
          "name": "VecRetrieve",
          "description": "Schema for vector retrieval test",
          "databases": [
            {
              "name": "dbx",
              "tables": [
                {
                  "name": "tab",
                  "fields": [
                    {"name": "col", "type": "text", "nullable": false}
                  ]
                }
              ]
            }
          ]
        }
        """.strip()
        res = store.create_schema(
            name="VecRetrieve",
            nl_description="Vector search retrieval test.",
            schema_json=schema_json,
            tenant=tc,
            user=uc,
        )
        schema_id = res["schema_id"]
        # Add a fact on the field of this schema
        fid = "dbx:tab.col"
        store.add_fact(
            schema_id=schema_id,
            entity_id=fid,
            text="Column col describes a name.",
            tenant=tc,
            user=uc,
        )
        # Ensure fallback LIKE is not used by making it return empty ranking
        store._approx_schema_ids_by_sqlite = lambda q, t: []  # type: ignore[attr-defined]
        # Vector-based search path should return this schema and include the field fact
        results = store.search_context("name", tenant=tc, user=uc)
        assert len(results) >= 1
        rec = results[0]
        assert rec.data_schema["name"] == "VecRetrieve"
        assert fid in rec.facts_by_entity and len(rec.facts_by_entity[fid]) >= 1
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_embedder_strategies_fields_only_vs_fields_and_facts():
    tmpdir = tempfile.mkdtemp(prefix="xlake_ctx_")
    try:
        # fields_only
        os.environ["XLAKE_CUSTOMER_CONTEXT_STORE_SCHEMA_EMBEDDER"] = "fields_only"
        store = _make_dev_store(tmpdir)
        uc = _user()
        tc = _tenant()
        store._embedder.get_embeddings = lambda texts: [[1.0, 0.0, 0.0] for _ in texts]  # type: ignore[attr-defined]
        schema_json = """
        {
          "name": "StrategyTest",
          "databases": [
            {
              "name": "db1",
              "tables": [
                {
                  "name": "t1",
                  "fields": [
                    {"name": "a", "type": "text", "nullable": false},
                    {"name": "b", "type": "float", "nullable": true}
                  ]
                }
              ]
            }
          ]
        }
        """.strip()
        store.create_schema(
            name="StrategyTest",
            nl_description="Fields only embedding test",
            schema_json=schema_json,
            tenant=tc,
            user=uc,
        )
        collection = f"{tc.identity.tenant_id}__fields"
        cnt1 = store._qdrant_client.count(collection_name=collection, exact=True)  # type: ignore[attr-defined]
        fields_only_count = getattr(cnt1, "count", 0)
        assert fields_only_count >= 2
        # fields_and_facts
        os.environ["XLAKE_CUSTOMER_CONTEXT_STORE_SCHEMA_EMBEDDER"] = "fields_and_facts"
        store2 = _make_dev_store(tmpdir)
        store2._embedder.get_embeddings = lambda texts: [[1.0, 0.0, 0.0] for _ in texts]  # type: ignore[attr-defined]
        uc2 = _user()
        tc2 = _tenant()
        res2 = store2.create_schema(
            name="StrategyTest",
            nl_description="Fields and facts embedding test",
            schema_json=schema_json,
            tenant=tc2,
            user=uc2,
        )
        # add a fact and expect extra point in vector store after modify (or reindex)
        schema_id2 = res2["schema_id"]
        store2.add_fact(
            schema_id=schema_id2,
            entity_id="db1:t1.a",
            text="A fact about a",
            tenant=tc2,
            user=uc2,
        )
        # Trigger re-embedding by bumping version with a no-op patch
        store2.modify_schema(schema_id2, schema_json_patch={}, tenant=tc2, user=uc2)
        collection2 = f"{tc2.identity.tenant_id}__fields"
        cnt2 = store2._qdrant_client.count(collection_name=collection2, exact=True)  # type: ignore[attr-defined]
        fields_and_facts_count = getattr(cnt2, "count", 0)
        assert fields_and_facts_count >= 3  # 2 fields + at least 1 fact
    finally:
        os.environ.pop("XLAKE_CUSTOMER_CONTEXT_STORE_SCHEMA_EMBEDDER", None)
        shutil.rmtree(tmpdir, ignore_errors=True)
