"""Tests for CoreContextStore.

Tests cover:
- CRUD for each category (KnowledgeNuggets, BusinessMetrics, BusinessTerms, VizDesignRules)
- Semantic search across categories
- BusinessTerm linking (synonyms, related terms)
- Permission checks (admin-only writes, tenant feature gating)
- Vector search integration
"""

from __future__ import annotations

import os
import shutil
import tempfile
from datetime import UTC, datetime

import pytest

from xlake.core import TenantContext, TenantIdentity, UserContext
from xlake.stores.config import (
    CoreContextStoreConfig,
    FSSpecLocalDocConfig,
    QdrantLocalConfig,
    SchemaEmbedderConfig,
    SqliteConfig,
)
from xlake.stores.core_context_store import (
    BusinessMetric,
    IndustryTerm,
    KnowledgeNugget,
    QdrantSqliteLocalFSCoreContextStore,
    VizDesignRule,
    create_core_context_store,
)

# =============================================================================
# Test Fixtures
# =============================================================================


def _make_dev_store(tmpdir: str) -> QdrantSqliteLocalFSCoreContextStore:
    """Create a development store with in-memory Qdrant and SQLite."""
    sqlite_path = os.path.join(tmpdir, "core_context.db")
    base_dir = os.path.join(tmpdir, "snapshots")
    os.makedirs(base_dir, exist_ok=True)
    return QdrantSqliteLocalFSCoreContextStore(
        qdrant_config=QdrantLocalConfig(path=":memory:"),
        sqlite_config=SqliteConfig(database_path=sqlite_path),
        fs_local_config=FSSpecLocalDocConfig(base_dir=base_dir),
        embedder_config=SchemaEmbedderConfig(
            strategy="fields_and_facts", model="fastembed:BAAI/bge-small-en-v1.5"
        ),
    )


def _actbi_admin_user() -> UserContext:
    """Return an ActBI admin user who can write to CoreContextStore."""
    return UserContext(
        user_id="admin1",
        tenant_id="actbi",
        role="admin",
    )


def _regular_user() -> UserContext:
    """Return a regular user who cannot write to CoreContextStore."""
    return UserContext(
        user_id="user1",
        tenant_id="customer_123",
        role="analyst",
    )


def _actbi_tenant() -> TenantContext:
    """Return the ActBI tenant context."""
    ident = TenantIdentity(
        tenant_id="actbi",
        tenant_name="ActBI",
        industry="analytics",
        region="US",
        timezone="America/New_York",
        locale="en_US",
    )
    return TenantContext(identity=ident)


def _customer_tenant() -> TenantContext:
    """Return a customer tenant context."""
    ident = TenantIdentity(
        tenant_id="customer_123",
        tenant_name="Acme Corp",
        industry="retail",
        region="EU",
        timezone="Europe/Paris",
        locale="en_US",
    )
    return TenantContext(identity=ident)


# =============================================================================
# KnowledgeNugget Tests
# =============================================================================


class TestKnowledgeNuggets:
    """Tests for DomainKnowledge (KnowledgeNugget) CRUD operations."""

    def test_upsert_and_get_nugget(self) -> None:
        tmpdir = tempfile.mkdtemp(prefix="xlake_core_")
        try:
            store = _make_dev_store(tmpdir)
            user = _actbi_admin_user()
            tenant = _actbi_tenant()

            now = datetime.now(UTC)
            nugget = KnowledgeNugget(
                nugget_id="nugget_1",
                domain="finance",
                category="accounting",
                content="EBITDA stands for Earnings Before Interest, Taxes, Depreciation, and Amortization.",
                tags=["kpi", "profitability"],
                sources=["financial_glossary", "accounting_handbook"],
                reference_uris=[
                    "https://example.com/ebitda",
                    "https://investopedia.com/ebitda",
                ],
                confidence=0.95,
                created_at=now,
                updated_at=now,
            )

            nugget_id = store.upsert_knowledge_nugget(nugget, tenant=tenant, user=user)
            assert nugget_id == "nugget_1"

            retrieved = store.get_knowledge_nugget(nugget_id, tenant=tenant, user=user)
            assert retrieved.nugget_id == "nugget_1"
            assert retrieved.domain == "finance"
            assert retrieved.content.startswith("EBITDA")
            assert "kpi" in retrieved.tags
            assert "financial_glossary" in retrieved.sources
            assert "accounting_handbook" in retrieved.sources
            assert "https://example.com/ebitda" in retrieved.reference_uris
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_get_nuggets_by_domain(self) -> None:
        tmpdir = tempfile.mkdtemp(prefix="xlake_core_")
        try:
            store = _make_dev_store(tmpdir)
            user = _actbi_admin_user()
            tenant = _actbi_tenant()
            now = datetime.now(UTC)

            # Create nuggets in different domains
            for i, (domain, category) in enumerate([
                ("finance", "accounting"),
                ("finance", "banking"),
                ("supply_chain", "logistics"),
            ]):
                store.upsert_knowledge_nugget(
                    KnowledgeNugget(
                        nugget_id=f"nugget_{i}",
                        domain=domain,
                        category=category,
                        content=f"Knowledge about {domain}/{category}",
                        created_at=now,
                        updated_at=now,
                    ),
                    tenant=tenant,
                    user=user,
                )

            # Get all finance nuggets
            finance_nuggets = store.get_knowledge_nuggets_by_domain(
                "finance", tenant=tenant, user=user
            )
            assert len(finance_nuggets) == 2

            # Get only accounting nuggets
            accounting_nuggets = store.get_knowledge_nuggets_by_domain(
                "finance", category="accounting", tenant=tenant, user=user
            )
            assert len(accounting_nuggets) == 1
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_delete_nugget(self) -> None:
        tmpdir = tempfile.mkdtemp(prefix="xlake_core_")
        try:
            store = _make_dev_store(tmpdir)
            user = _actbi_admin_user()
            tenant = _actbi_tenant()
            now = datetime.now(UTC)

            nugget = KnowledgeNugget(
                nugget_id="to_delete",
                domain="test",
                category="test",
                content="This will be deleted",
                created_at=now,
                updated_at=now,
            )
            store.upsert_knowledge_nugget(nugget, tenant=tenant, user=user)
            store.delete_knowledge_nugget("to_delete", tenant=tenant, user=user)

            with pytest.raises(KeyError):
                store.get_knowledge_nugget("to_delete", tenant=tenant, user=user)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_search_nuggets(self) -> None:
        tmpdir = tempfile.mkdtemp(prefix="xlake_core_")
        try:
            store = _make_dev_store(tmpdir)
            user = _actbi_admin_user()
            tenant = _actbi_tenant()
            now = datetime.now(UTC)

            store.upsert_knowledge_nugget(
                KnowledgeNugget(
                    nugget_id="margin_nugget",
                    domain="finance",
                    category="metrics",
                    content="Gross margin is the difference between revenue and cost of goods sold.",
                    created_at=now,
                    updated_at=now,
                ),
                tenant=tenant,
                user=user,
            )

            results = store.search_knowledge_nuggets(
                "gross margin profit", tenant=tenant, user=user
            )
            # Should find at least the margin nugget
            assert len(results) >= 1
            assert any("margin" in r.content.lower() for r in results)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_search_nuggets_by_tags(self) -> None:
        """Test that tags are included in the embedding and can be searched."""
        tmpdir = tempfile.mkdtemp(prefix="xlake_core_")
        try:
            store = _make_dev_store(tmpdir)
            user = _actbi_admin_user()
            tenant = _actbi_tenant()
            now = datetime.now(UTC)

            # Create a nugget with specific tags
            store.upsert_knowledge_nugget(
                KnowledgeNugget(
                    nugget_id="tagged_nugget",
                    domain="finance",
                    category="compliance",
                    content="Financial reporting standards for public companies.",
                    tags=["SEC", "GAAP", "regulatory"],
                    created_at=now,
                    updated_at=now,
                ),
                tenant=tenant,
                user=user,
            )

            # Search using a tag term - should find via LIKE fallback at minimum
            results = store.search_knowledge_nuggets(
                "GAAP regulatory", tenant=tenant, user=user
            )
            # The nugget should be findable (either via vector search or LIKE fallback)
            assert len(results) >= 1
            assert any(r.nugget_id == "tagged_nugget" for r in results)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


# =============================================================================
# BusinessMetric Tests
# =============================================================================


class TestBusinessMetrics:
    """Tests for BusinessMetrics CRUD operations."""

    def test_upsert_and_get_metric(self) -> None:
        tmpdir = tempfile.mkdtemp(prefix="xlake_core_")
        try:
            store = _make_dev_store(tmpdir)
            user = _actbi_admin_user()
            tenant = _actbi_tenant()
            now = datetime.now(UTC)

            metric = BusinessMetric(
                metric_id="metric_1",
                name="Gross Margin",
                domain="finance",
                formula="(revenue - cogs) / revenue",
                formula_type="arithmetic",
                input_fields=["revenue", "cogs"],
                output_unit="percentage",
                description="Measures the profitability of each sale.",
                lineage={"source": "finance_team"},
                reference_uris=["https://example.com/gross-margin"],
                created_at=now,
                updated_at=now,
            )

            metric_id = store.upsert_business_metric(metric, tenant=tenant, user=user)
            assert metric_id == "metric_1"

            retrieved = store.get_business_metric(metric_id, tenant=tenant, user=user)
            assert retrieved.name == "Gross Margin"
            assert retrieved.formula == "(revenue - cogs) / revenue"
            assert "revenue" in retrieved.input_fields
            assert "https://example.com/gross-margin" in retrieved.reference_uris
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_get_metric_by_name(self) -> None:
        tmpdir = tempfile.mkdtemp(prefix="xlake_core_")
        try:
            store = _make_dev_store(tmpdir)
            user = _actbi_admin_user()
            tenant = _actbi_tenant()
            now = datetime.now(UTC)

            store.upsert_business_metric(
                BusinessMetric(
                    metric_id="m1",
                    name="Customer Lifetime Value",
                    domain="marketing",
                    description="Expected revenue from a customer relationship.",
                    created_at=now,
                    updated_at=now,
                ),
                tenant=tenant,
                user=user,
            )

            found = store.get_business_metric_by_name(
                "Customer Lifetime Value", tenant=tenant, user=user
            )
            assert found is not None
            assert found.metric_id == "m1"

            not_found = store.get_business_metric_by_name(
                "Nonexistent Metric", tenant=tenant, user=user
            )
            assert not_found is None
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_delete_metric(self) -> None:
        tmpdir = tempfile.mkdtemp(prefix="xlake_core_")
        try:
            store = _make_dev_store(tmpdir)
            user = _actbi_admin_user()
            tenant = _actbi_tenant()
            now = datetime.now(UTC)

            store.upsert_business_metric(
                BusinessMetric(
                    metric_id="to_delete",
                    name="Temp Metric",
                    domain="test",
                    description="Will be deleted",
                    created_at=now,
                    updated_at=now,
                ),
                tenant=tenant,
                user=user,
            )
            store.delete_business_metric("to_delete", tenant=tenant, user=user)

            with pytest.raises(KeyError):
                store.get_business_metric("to_delete", tenant=tenant, user=user)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_metric_with_tags(self) -> None:
        """Test that metrics can have tags and they are persisted."""
        tmpdir = tempfile.mkdtemp(prefix="xlake_core_")
        try:
            store = _make_dev_store(tmpdir)
            user = _actbi_admin_user()
            tenant = _actbi_tenant()
            now = datetime.now(UTC)

            metric = BusinessMetric(
                metric_id="tagged_metric",
                name="Customer Acquisition Cost",
                domain="marketing",
                formula="total_marketing_spend / new_customers",
                description="Cost to acquire a new customer.",
                tags=["CAC", "growth", "unit_economics"],
                created_at=now,
                updated_at=now,
            )

            store.upsert_business_metric(metric, tenant=tenant, user=user)

            retrieved = store.get_business_metric(
                "tagged_metric", tenant=tenant, user=user
            )
            assert "CAC" in retrieved.tags
            assert "growth" in retrieved.tags
            assert len(retrieved.tags) == 3
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


# =============================================================================
# IndustryTerm Tests
# =============================================================================


class TestIndustryTerms:
    """Tests for BusinessDictionary (IndustryTerm) CRUD operations."""

    def test_upsert_and_get_term(self) -> None:
        tmpdir = tempfile.mkdtemp(prefix="xlake_core_")
        try:
            store = _make_dev_store(tmpdir)
            user = _actbi_admin_user()
            tenant = _actbi_tenant()
            now = datetime.now(UTC)

            term = IndustryTerm(
                term_id="term_1",
                term="Single Origin",
                definition="Coffee beans sourced from a single geographic location.",
                industry="coffee",
                synonyms=["single-origin", "origin coffee"],
                examples=["Ethiopian Yirgacheffe is a popular single origin."],
                tags=["specialty", "sourcing"],
                reference_uris=["https://example.com/single-origin-coffee"],
                created_at=now,
                updated_at=now,
            )

            term_id = store.upsert_industry_term(term, tenant=tenant, user=user)
            assert term_id == "term_1"

            retrieved = store.get_industry_term(term_id, tenant=tenant, user=user)
            assert retrieved.term == "Single Origin"
            assert "single-origin" in retrieved.synonyms
            assert retrieved.industry == "coffee"
            assert (
                "https://example.com/single-origin-coffee" in retrieved.reference_uris
            )
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_get_term_by_name(self) -> None:
        tmpdir = tempfile.mkdtemp(prefix="xlake_core_")
        try:
            store = _make_dev_store(tmpdir)
            user = _actbi_admin_user()
            tenant = _actbi_tenant()
            now = datetime.now(UTC)

            store.upsert_industry_term(
                IndustryTerm(
                    term_id="torque_term",
                    term="Torque",
                    definition="A measure of rotational force applied to an object.",
                    industry="automotive",
                    created_at=now,
                    updated_at=now,
                ),
                tenant=tenant,
                user=user,
            )

            found = store.get_industry_term_by_name("Torque", tenant=tenant, user=user)
            assert found is not None
            assert found.term_id == "torque_term"
            assert found.industry == "automotive"
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_link_terms(self) -> None:
        tmpdir = tempfile.mkdtemp(prefix="xlake_core_")
        try:
            store = _make_dev_store(tmpdir)
            user = _actbi_admin_user()
            tenant = _actbi_tenant()
            now = datetime.now(UTC)

            # Create two terms
            store.upsert_industry_term(
                IndustryTerm(
                    term_id="arabica",
                    term="Arabica",
                    definition="A species of coffee plant known for smooth taste",
                    industry="coffee",
                    created_at=now,
                    updated_at=now,
                ),
                tenant=tenant,
                user=user,
            )
            store.upsert_industry_term(
                IndustryTerm(
                    term_id="robusta",
                    term="Robusta",
                    definition="A species of coffee plant known for bold, bitter taste",
                    industry="coffee",
                    created_at=now,
                    updated_at=now,
                ),
                tenant=tenant,
                user=user,
            )

            # Link them as related
            store.link_industry_terms(
                "arabica",
                ["robusta"],
                relationship="related",
                tenant=tenant,
                user=user,
            )

            arabica = store.get_industry_term("arabica", tenant=tenant, user=user)
            assert "robusta" in arabica.related_terms

            # Get related terms
            related = store.get_related_industry_terms(
                "arabica", tenant=tenant, user=user
            )
            assert len(related) == 1
            assert related[0].term_id == "robusta"
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_link_terms_as_synonyms(self) -> None:
        tmpdir = tempfile.mkdtemp(prefix="xlake_core_")
        try:
            store = _make_dev_store(tmpdir)
            user = _actbi_admin_user()
            tenant = _actbi_tenant()
            now = datetime.now(UTC)

            store.upsert_industry_term(
                IndustryTerm(
                    term_id="espresso",
                    term="Espresso",
                    definition="Concentrated coffee brewed under pressure",
                    industry="coffee",
                    created_at=now,
                    updated_at=now,
                ),
                tenant=tenant,
                user=user,
            )

            store.link_industry_terms(
                "espresso",
                ["short_black_id", "shot_id"],
                relationship="synonym",
                tenant=tenant,
                user=user,
            )

            espresso = store.get_industry_term("espresso", tenant=tenant, user=user)
            assert "short_black_id" in espresso.synonyms
            assert "shot_id" in espresso.synonyms
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_term_with_tags(self) -> None:
        """Test that industry terms can have tags and they are persisted."""
        tmpdir = tempfile.mkdtemp(prefix="xlake_core_")
        try:
            store = _make_dev_store(tmpdir)
            user = _actbi_admin_user()
            tenant = _actbi_tenant()
            now = datetime.now(UTC)

            term = IndustryTerm(
                term_id="cupping",
                term="Cupping",
                definition="A standardized method for evaluating coffee quality.",
                industry="coffee",
                tags=["quality_control", "tasting", "specialty"],
                created_at=now,
                updated_at=now,
            )

            store.upsert_industry_term(term, tenant=tenant, user=user)

            retrieved = store.get_industry_term("cupping", tenant=tenant, user=user)
            assert "quality_control" in retrieved.tags
            assert "tasting" in retrieved.tags
            assert len(retrieved.tags) == 3
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


# =============================================================================
# VizDesignRule Tests
# =============================================================================


class TestVizDesignRules:
    """Tests for VisualizationDesign (VizDesignRule) CRUD operations."""

    def test_upsert_and_get_rule(self) -> None:
        tmpdir = tempfile.mkdtemp(prefix="xlake_core_")
        try:
            store = _make_dev_store(tmpdir)
            user = _actbi_admin_user()
            tenant = _actbi_tenant()
            now = datetime.now(UTC)

            rule = VizDesignRule(
                rule_id="rule_1",
                document_type="action-implementation",
                origin_path="/data-viz-bible/selection/selection-line_chart.md",
                pipeline_stage="selection",
                chart_type="line_chart",
                data_pattern="temporal-measure",
                chart_family="evolution",
                priority="P0",
                aliases=["line graph", "trend chart"],
                section_path="Selection: Line Chart > When to Use",
                content="[Line Chart - Selection - When to Use]\nShows trends over time...",
                tags=["selection", "line_chart", "evolution", "trends"],
                created_at=now,
                updated_at=now,
            )

            rule_id = store.upsert_viz_design_rule(rule, tenant=tenant, user=user)
            assert rule_id == "rule_1"

            retrieved = store.get_viz_design_rule(rule_id, tenant=tenant, user=user)
            assert retrieved.chart_type == "line_chart"
            assert retrieved.pipeline_stage == "selection"
            assert "line_chart" in retrieved.tags
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_get_chart_rules(self) -> None:
        tmpdir = tempfile.mkdtemp(prefix="xlake_core_")
        try:
            store = _make_dev_store(tmpdir)
            user = _actbi_admin_user()
            tenant = _actbi_tenant()
            now = datetime.now(UTC)

            # Create rules for different chart types and stages
            store.upsert_viz_design_rule(
                VizDesignRule(
                    rule_id="line_sel_1",
                    document_type="action-implementation",
                    origin_path="/data-viz-bible/selection/selection-line_chart.md",
                    pipeline_stage="selection",
                    chart_type="line_chart",
                    section_path="Selection: Line Chart > When to Use",
                    content="When to use line charts...",
                    tags=["selection", "line_chart"],
                    created_at=now,
                    updated_at=now,
                ),
                tenant=tenant,
                user=user,
            )
            store.upsert_viz_design_rule(
                VizDesignRule(
                    rule_id="line_sel_2",
                    document_type="action-implementation",
                    origin_path="/data-viz-bible/selection/selection-line_chart.md",
                    pipeline_stage="selection",
                    chart_type="line_chart",
                    section_path="Selection: Line Chart > Data Requirements",
                    content="Data requirements for line charts...",
                    tags=["selection", "line_chart"],
                    created_at=now,
                    updated_at=now,
                ),
                tenant=tenant,
                user=user,
            )
            store.upsert_viz_design_rule(
                VizDesignRule(
                    rule_id="bar_sel_1",
                    document_type="action-implementation",
                    origin_path="/data-viz-bible/selection/selection-bar_chart_vertical.md",
                    pipeline_stage="selection",
                    chart_type="bar_chart_vertical",
                    section_path="Selection: Bar Chart (Vertical) > When to Use",
                    content="When to use bar charts...",
                    tags=["selection", "bar_chart_vertical"],
                    created_at=now,
                    updated_at=now,
                ),
                tenant=tenant,
                user=user,
            )

            line_rules = store.get_chart_rules(
                "selection", "line_chart", tenant=tenant, user=user
            )
            assert len(line_rules) == 2
            assert all(r.chart_type == "line_chart" for r in line_rules)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_get_blueprint_rule(self) -> None:
        tmpdir = tempfile.mkdtemp(prefix="xlake_core_")
        try:
            store = _make_dev_store(tmpdir)
            user = _actbi_admin_user()
            tenant = _actbi_tenant()
            now = datetime.now(UTC)

            # Create a blueprint (action-interface) document
            store.upsert_viz_design_rule(
                VizDesignRule(
                    rule_id="selection_blueprint",
                    document_type="action-interface",
                    origin_path="/data-viz-bible/selection/selection.md",
                    pipeline_stage="selection",
                    section_path="Selection",
                    content="The Selection action determines which chart type...",
                    tags=["selection", "decision-tree"],
                    created_at=now,
                    updated_at=now,
                ),
                tenant=tenant,
                user=user,
            )

            blueprint = store.get_blueprint_rule("selection", tenant=tenant, user=user)
            assert blueprint.document_type == "action-interface"
            assert blueprint.pipeline_stage == "selection"
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_get_foundation_rules(self) -> None:
        tmpdir = tempfile.mkdtemp(prefix="xlake_core_")
        try:
            store = _make_dev_store(tmpdir)
            user = _actbi_admin_user()
            tenant = _actbi_tenant()
            now = datetime.now(UTC)

            # Create foundation documents
            store.upsert_viz_design_rule(
                VizDesignRule(
                    rule_id="schema_ref_1",
                    document_type="reference",
                    origin_path="/data-viz-bible/01-schema-reference.md",
                    category="schema",
                    section_path="Schema Reference > Field Roles",
                    content="Field roles define how data columns are classified...",
                    tags=["schema", "field-roles"],
                    created_at=now,
                    updated_at=now,
                ),
                tenant=tenant,
                user=user,
            )
            store.upsert_viz_design_rule(
                VizDesignRule(
                    rule_id="class_sys_1",
                    document_type="reference",
                    origin_path="/data-viz-bible/02-classification-system.md",
                    category="classification",
                    section_path="Classification System > Prominence",
                    content="Prominence determines visual weight...",
                    tags=["classification", "prominence"],
                    created_at=now,
                    updated_at=now,
                ),
                tenant=tenant,
                user=user,
            )

            # Get all foundation rules
            all_foundation = store.get_foundation_rules(tenant=tenant, user=user)
            assert len(all_foundation) == 2

            # Get schema rules only
            schema_rules = store.get_foundation_rules(
                category="schema", tenant=tenant, user=user
            )
            assert len(schema_rules) == 1
            assert schema_rules[0].category == "schema"
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_search_viz_design_rules_with_scores(self) -> None:
        """Test that search returns VizDesignRuleResponse with retrieval stats."""
        tmpdir = tempfile.mkdtemp(prefix="xlake_core_")
        try:
            store = _make_dev_store(tmpdir)
            user = _actbi_admin_user()
            tenant = _actbi_tenant()
            now = datetime.now(UTC)

            # Create a rule to search for
            store.upsert_viz_design_rule(
                VizDesignRule(
                    rule_id="line_chart_rule",
                    document_type="action-implementation",
                    origin_path="/data-viz-bible/selection/selection-line_chart.md",
                    pipeline_stage="selection",
                    chart_type="line_chart",
                    section_path="Selection: Line Chart > When to Use",
                    content="Use line charts for showing trends over time.",
                    tags=["selection", "line_chart", "trends"],
                    created_at=now,
                    updated_at=now,
                ),
                tenant=tenant,
                user=user,
            )

            # Search for the rule
            results = store.search_viz_design_rules(
                "line chart trends", tenant=tenant, user=user
            )

            # Should return at least one result
            assert len(results) >= 1

            # Results should be VizDesignRuleResponse with rule and stats
            for result in results:
                assert hasattr(result, "rule")
                assert hasattr(result, "stats")
                assert result.stats.rank >= 1
                # Score should be between 0 and 1 for vector search
                assert 0.0 <= result.stats.score <= 1.0
                # Rule should have expected fields
                assert result.rule.rule_id is not None
                assert result.rule.content is not None
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


# =============================================================================
# Permission Tests
# =============================================================================


class TestPermissions:
    """Tests for permission checks."""

    def test_regular_user_can_read(self) -> None:
        """Regular users should be able to read core context."""
        tmpdir = tempfile.mkdtemp(prefix="xlake_core_")
        try:
            store = _make_dev_store(tmpdir)
            admin = _actbi_admin_user()
            admin_tenant = _actbi_tenant()
            now = datetime.now(UTC)

            # Admin creates a nugget
            store.upsert_knowledge_nugget(
                KnowledgeNugget(
                    nugget_id="readable",
                    domain="test",
                    category="test",
                    content="Anyone can read this",
                    created_at=now,
                    updated_at=now,
                ),
                tenant=admin_tenant,
                user=admin,
            )

            # Regular user can read it
            regular_user = _regular_user()
            customer_tenant = _customer_tenant()
            retrieved = store.get_knowledge_nugget(
                "readable", tenant=customer_tenant, user=regular_user
            )
            assert retrieved.nugget_id == "readable"
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_regular_user_cannot_write(self) -> None:
        """Regular users should not be able to write to core context."""
        tmpdir = tempfile.mkdtemp(prefix="xlake_core_")
        try:
            store = _make_dev_store(tmpdir)
            regular_user = _regular_user()
            customer_tenant = _customer_tenant()
            now = datetime.now(UTC)

            with pytest.raises(PermissionError, match="Only ActBI admins"):
                store.upsert_knowledge_nugget(
                    KnowledgeNugget(
                        nugget_id="forbidden",
                        domain="test",
                        category="test",
                        content="Should not be saved",
                        created_at=now,
                        updated_at=now,
                    ),
                    tenant=customer_tenant,
                    user=regular_user,
                )
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_non_actbi_admin_cannot_write(self) -> None:
        """Admin users from other tenants should not be able to write."""
        tmpdir = tempfile.mkdtemp(prefix="xlake_core_")
        try:
            store = _make_dev_store(tmpdir)
            # Admin but for a different tenant
            other_admin = UserContext(
                user_id="other_admin",
                tenant_id="other_company",
                role="admin",
            )
            other_tenant = _customer_tenant()
            now = datetime.now(UTC)

            with pytest.raises(PermissionError, match="Only ActBI admins"):
                store.upsert_knowledge_nugget(
                    KnowledgeNugget(
                        nugget_id="forbidden",
                        domain="test",
                        category="test",
                        content="Should not be saved",
                        created_at=now,
                        updated_at=now,
                    ),
                    tenant=other_tenant,
                    user=other_admin,
                )
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


# =============================================================================
# Factory Function Tests
# =============================================================================


class TestFactoryFunction:
    """Tests for the create_core_context_store factory function."""

    def test_create_dev_store(self) -> None:
        tmpdir = tempfile.mkdtemp(prefix="xlake_core_")
        try:
            config = CoreContextStoreConfig(
                backend="qdrant_sqlite_localfs",
                qdrant_local=QdrantLocalConfig(path=":memory:"),
                sqlite=SqliteConfig(database_path=os.path.join(tmpdir, "test.db")),
                fsspec_local=FSSpecLocalDocConfig(base_dir=tmpdir),
                embedder=SchemaEmbedderConfig(
                    strategy="fields_and_facts",
                    model="fastembed:BAAI/bge-small-en-v1.5",
                ),
            )
            store = create_core_context_store(config)
            assert store is not None
            store.close()
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_invalid_backend_raises(self) -> None:
        # Pydantic validates the backend literal, so we test by patching the config
        config = CoreContextStoreConfig(
            backend="qdrant_sqlite_localfs",
            qdrant_local=QdrantLocalConfig(path=":memory:"),
            sqlite=SqliteConfig(database_path=":memory:"),
        )
        # Manually override the backend to simulate an invalid value
        object.__setattr__(config, "backend", "invalid_backend")
        with pytest.raises(ValueError, match="Unsupported backend"):
            create_core_context_store(config)


# =============================================================================
# Thread Safety Tests
# =============================================================================


class TestThreadSafety:
    """Tests for multi-threaded access to CoreContextStore.

    These tests verify that stores can be accessed from multiple threads,
    which is required when using LangGraph agents that run tools in thread pools.
    """

    def test_store_can_be_accessed_from_worker_thread(self) -> None:
        """Test that a store created in main thread can be read from a worker thread."""
        from concurrent.futures import ThreadPoolExecutor

        tmpdir = tempfile.mkdtemp(prefix="xlake_core_")
        try:
            store = _make_dev_store(tmpdir)
            tenant = _actbi_tenant()
            admin = _actbi_admin_user()
            now = datetime.now(UTC)

            # Create a rule in the main thread
            rule = VizDesignRule(
                rule_id="thread-test-rule",
                document_type="chart-guidance",
                origin_path="/data-viz-bible/test/thread-safety.md",
                pipeline_stage="selection",
                chart_type="bar_chart_vertical",
                content="Test rule for thread safety",
                section_path="test/thread-safety",
                priority="recommended",
                created_at=now,
                updated_at=now,
            )
            rule_id = store.upsert_viz_design_rule(rule, tenant=tenant, user=admin)

            # Access from a worker thread (simulates LangGraph tool execution)
            def read_rule_in_worker():
                return store.get_viz_design_rule(rule_id, tenant=tenant, user=admin)

            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(read_rule_in_worker)
                result = future.result(timeout=5.0)

            assert result.rule_id == rule_id
            assert result.content == "Test rule for thread safety"
        finally:
            store.close()
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_search_from_worker_thread(self) -> None:
        """Test that semantic search works from a worker thread."""
        from concurrent.futures import ThreadPoolExecutor

        tmpdir = tempfile.mkdtemp(prefix="xlake_core_")
        try:
            store = _make_dev_store(tmpdir)
            tenant = _actbi_tenant()
            admin = _actbi_admin_user()
            now = datetime.now(UTC)

            # Create a rule in the main thread
            rule = VizDesignRule(
                rule_id="thread-search-rule",
                document_type="chart-guidance",
                origin_path="/data-viz-bible/test/thread-search.md",
                pipeline_stage="selection",
                chart_type="line_chart",
                content="When showing trends over time, use a line chart",
                section_path="test/thread-search",
                priority="required",
                created_at=now,
                updated_at=now,
            )
            store.upsert_viz_design_rule(rule, tenant=tenant, user=admin)

            # Search from a worker thread
            def search_in_worker():
                return store.search_viz_design_rules(
                    "trends over time",
                    pipeline_stage="selection",
                    top_k=5,
                    tenant=tenant,
                    user=admin,
                )

            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(search_in_worker)
                results = future.result(timeout=10.0)

            # Should find the rule we created
            assert len(results) > 0
            rule_ids = [r.rule.rule_id for r in results]
            assert "thread-search-rule" in rule_ids
        finally:
            store.close()
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_concurrent_get_viz_design_rule_no_interface_error(self) -> None:
        """Test that concurrent get_viz_design_rule calls don't cause InterfaceError.

        This test reproduces the scenario where search_viz_design_rules returns
        multiple hits and then calls get_viz_design_rule for each hit. In LangGraph
        agent execution, these calls can happen concurrently from different threads.

        The InterfaceError ("bad parameter or other API misuse") can occur when:
        - Multiple threads share the same SQLite connection
        - Cursors are created/used concurrently without proper synchronization
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        tmpdir = tempfile.mkdtemp(prefix="xlake_core_")
        try:
            store = _make_dev_store(tmpdir)
            tenant = _actbi_tenant()
            admin = _actbi_admin_user()
            now = datetime.now(UTC)

            # Create multiple rules to simulate real search results
            rule_ids = []
            for i in range(10):
                rule = VizDesignRule(
                    rule_id=f"concurrent-rule-{i}",
                    document_type="chart-guidance",
                    origin_path=f"/data-viz-bible/test/concurrent-{i}.md",
                    pipeline_stage="selection",
                    chart_type="bar_chart_vertical",
                    content=f"Test rule {i} for concurrent access testing",
                    section_path=f"test/concurrent/{i}",
                    priority="recommended",
                    created_at=now,
                    updated_at=now,
                )
                rid = store.upsert_viz_design_rule(rule, tenant=tenant, user=admin)
                rule_ids.append(rid)

            # Simulate concurrent access from multiple threads (like LangGraph tool execution)
            def get_rule_in_worker(rule_id: str):
                return store.get_viz_design_rule(rule_id, tenant=tenant, user=admin)

            # Run multiple concurrent requests - this is what triggers InterfaceError
            # if the SQLite connection isn't properly handled
            errors = []
            with ThreadPoolExecutor(max_workers=5) as executor:
                # Submit all requests at once to maximize concurrency
                futures = {
                    executor.submit(get_rule_in_worker, rid): rid for rid in rule_ids
                }
                for future in as_completed(futures):
                    rid = futures[future]
                    try:
                        result = future.result(timeout=10.0)
                        assert result.rule_id == rid
                    except Exception as e:
                        errors.append((rid, type(e).__name__, str(e)))

            # No InterfaceError or other errors should occur
            assert len(errors) == 0, f"Concurrent access caused errors: {errors}"

        finally:
            store.close()
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_concurrent_search_and_get_no_interface_error(self) -> None:
        """Test mixed concurrent search and get operations don't cause InterfaceError.

        This simulates the exact pattern in search_viz_design_rules where:
        1. Vector search returns hits
        2. For each hit, get_viz_design_rule is called to fetch the full rule
        3. In async/threaded context, these can overlap with other operations
        """
        from concurrent.futures import ThreadPoolExecutor

        tmpdir = tempfile.mkdtemp(prefix="xlake_core_")
        try:
            store = _make_dev_store(tmpdir)
            tenant = _actbi_tenant()
            admin = _actbi_admin_user()
            now = datetime.now(UTC)

            # Create rules with searchable content
            for i in range(5):
                rule = VizDesignRule(
                    rule_id=f"mixed-concurrent-rule-{i}",
                    document_type="chart-guidance",
                    origin_path=f"/data-viz-bible/test/mixed-{i}.md",
                    pipeline_stage="selection",
                    chart_type="bar_chart_vertical",
                    content=f"For comparing categories, use bar charts - rule {i}",
                    section_path=f"test/mixed/{i}",
                    priority="recommended",
                    created_at=now,
                    updated_at=now,
                )
                store.upsert_viz_design_rule(rule, tenant=tenant, user=admin)

            def search_operation():
                return store.search_viz_design_rules(
                    "comparing categories bar charts",
                    pipeline_stage="selection",
                    top_k=5,
                    tenant=tenant,
                    user=admin,
                )

            def get_operation(rule_id: str):
                return store.get_viz_design_rule(rule_id, tenant=tenant, user=admin)

            # Run mixed concurrent operations
            errors = []
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = []
                # Submit multiple searches
                for _ in range(3):
                    futures.append(("search", executor.submit(search_operation)))
                # Submit multiple gets
                for i in range(5):
                    futures.append((
                        "get",
                        executor.submit(get_operation, f"mixed-concurrent-rule-{i}"),
                    ))

                for op_type, future in futures:
                    try:
                        result = future.result(timeout=10.0)
                        if op_type == "search":
                            assert isinstance(result, list)
                        else:
                            assert result is not None
                    except Exception as e:
                        errors.append((op_type, type(e).__name__, str(e)))

            assert len(errors) == 0, f"Mixed concurrent access caused errors: {errors}"

        finally:
            store.close()
            shutil.rmtree(tmpdir, ignore_errors=True)
