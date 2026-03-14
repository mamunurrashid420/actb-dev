"""Tests for BusinessClient and its sub-clients."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import Mock

import pytest

from xlake.api.business_client import (
    BusinessClient,
    ConversationBusinessClient,
    FactsBusinessClient,
    IndustryBusinessClient,
    KnowledgeBusinessClient,
    KPIBusinessClient,
    SchemaBusinessClient,
    SemanticBusinessClient,
)
from xlake.api.models import (
    KPI,
    ActiveState,
    ConversationContext,
    Entity,
    FactCreate,
    FactInfo,
    FullSchema,
    GraphResult,
    IndustryTermCreate,
    IndustryTermInfo,
    IndustryTermSummary,
    InsightInput,
    KnowledgeNuggetCreate,
    KnowledgeNuggetInfo,
    KnowledgeNuggetSummary,
    KnowledgeObject,
    KPIDefinition,
    KPISummary,
    SchemaSemantics,
    StateUpdate,
)
from xlake.core import (
    Permissions,
    Preferences,
    TenantContext,
    TenantIdentity,
    UserContext,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def tenant_context() -> TenantContext:
    """Create a test TenantContext."""
    return TenantContext(
        identity=TenantIdentity(
            tenant_id="test-tenant-001",
            tenant_name="Test Tenant",
            industry="technology",
            region="EU",
            timezone="Europe/Rome",
            locale="en_US",
        ),
    )


@pytest.fixture
def user_context() -> UserContext:
    """Create a test UserContext with full permissions."""
    return UserContext(
        user_id="test-user-001",
        tenant_id="test-tenant-001",
        role="admin",
        permissions=Permissions(
            can_view_fields=["*"],
            can_view_tables=["*"],
            can_view_kpis=["*"],
            can_view_dashboards=["*"],
            can_run_queries=True,
            can_modify_schema=True,
        ),
        preferences=Preferences(
            units="EUR",
            timezone="Europe/Rome",
            verbosity="concise",
        ),
    )


@pytest.fixture
def mock_business_metric() -> Mock:
    """Create a mock BusinessMetric."""
    metric = Mock()
    metric.metric_id = "metric_001"
    metric.name = "Gross Margin"
    metric.domain = "finance"
    metric.description = "Revenue minus cost of goods sold"
    metric.formula = "(revenue - cogs) / revenue"
    metric.formula_type = "ratio"
    metric.input_fields = ["revenue", "cogs"]
    metric.output_unit = "%"
    metric.tags = ["finance", "profitability"]
    metric.lineage = ["sales_fact", "cost_fact"]
    metric.created_at = datetime(2025, 1, 1)
    metric.updated_at = datetime(2025, 1, 1)
    return metric


@pytest.fixture
def mock_fact() -> Mock:
    """Create a mock Fact."""
    fact = Mock()
    fact.fact_id = "fact_001"
    fact.entity_id = "sales.revenue"
    fact.text = "Revenue represents the total income from sales"
    fact.date = datetime(2025, 1, 1)
    fact.source = "user_input"
    fact.tags = ["definition", "finance"]
    return fact


@pytest.fixture
def mock_schema_record(mock_fact: Mock) -> Mock:
    """Create a mock SchemaContextRecord."""
    record = Mock()
    record.data_schema = {
        "schema_id": "schema_001",
        "name": "Sales Schema",
        "version": 1,
        "description": "Sales data schema",
        "databases": [{"name": "sales_db"}],
    }
    record.facts_by_entity = {
        "sales.revenue": [mock_fact],
        "sales.cost": [],
    }
    return record


@pytest.fixture
def mock_knowledge_nugget() -> Mock:
    """Create a mock KnowledgeNugget."""
    nugget = Mock()
    nugget.nugget_id = "nugget_001"
    nugget.domain = "finance"
    nugget.category = "definition"
    nugget.content = "Gross margin is a key profitability metric"
    nugget.tags = ["finance", "margin"]
    nugget.sources = ["accounting_handbook"]
    nugget.reference_uris = ["https://example.com/finance/margin"]
    nugget.confidence = 0.95
    nugget.created_at = datetime(2025, 1, 1)
    nugget.updated_at = datetime(2025, 1, 1)
    return nugget


@pytest.fixture
def mock_industry_term() -> Mock:
    """Create a mock IndustryTerm."""
    term = Mock()
    term.term_id = "term_001"
    term.term = "Arabica"
    term.definition = "A species of coffee known for smooth, complex flavor"
    term.industry = "coffee"
    term.synonyms = ["Coffea arabica"]
    term.related_terms = ["term_002"]
    term.antonyms = []
    term.examples = ["Ethiopian Yirgacheffe", "Colombian Supremo"]
    term.tags = ["coffee", "species"]
    term.reference_uris = ["https://example.com/coffee/arabica"]
    term.created_at = datetime(2025, 1, 1)
    term.updated_at = datetime(2025, 1, 1)
    return term


@pytest.fixture
def mock_related_industry_term() -> Mock:
    """Create a mock related IndustryTerm."""
    term = Mock()
    term.term_id = "term_002"
    term.term = "Robusta"
    term.definition = (
        "A species of coffee known for its bold flavor and higher caffeine"
    )
    term.industry = "coffee"
    term.synonyms = ["Coffea canephora"]
    term.related_terms = ["term_001"]
    term.antonyms = []
    term.examples = ["Vietnamese coffee", "Italian espresso blends"]
    term.tags = ["coffee", "species"]
    term.reference_uris = []
    term.created_at = datetime(2025, 1, 1)
    term.updated_at = datetime(2025, 1, 1)
    return term


@pytest.fixture
def mock_core_context_store(
    mock_business_metric: Mock,
    mock_knowledge_nugget: Mock,
    mock_industry_term: Mock,
    mock_related_industry_term: Mock,
) -> Mock:
    """Create a mock CoreContextStore."""
    store = Mock()
    # Business metrics
    store.search_business_metrics.return_value = [mock_business_metric]
    store.get_business_metric.return_value = mock_business_metric
    store.upsert_business_metric.return_value = "metric_001"
    store.delete_business_metric.return_value = None
    # Knowledge nuggets
    store.search_knowledge_nuggets.return_value = [mock_knowledge_nugget]
    store.get_knowledge_nugget.return_value = mock_knowledge_nugget
    store.get_knowledge_nuggets_by_domain.return_value = [mock_knowledge_nugget]
    store.upsert_knowledge_nugget.return_value = "nugget_001"
    store.delete_knowledge_nugget.return_value = None
    # Industry terms
    store.search_industry_terms.return_value = [mock_industry_term]
    store.get_industry_term.return_value = mock_industry_term
    store.get_industry_term_by_name.return_value = mock_industry_term
    store.get_related_industry_terms.return_value = [mock_related_industry_term]
    store.upsert_industry_term.return_value = "term_001"
    store.link_industry_terms.return_value = None
    store.delete_industry_term.return_value = None
    return store


@pytest.fixture
def mock_customer_context_store(mock_schema_record: Mock, mock_fact: Mock) -> Mock:
    """Create a mock CustomerContextStore."""
    store = Mock()
    store.get_schema_context.return_value = mock_schema_record
    store.search_context.return_value = [mock_schema_record]
    store.add_fact.return_value = {"fact_id": "fact_002"}
    store.get_entity_facts.return_value = {"sales.revenue": [mock_fact]}
    store.modify_fact.return_value = None
    store.delete_fact.return_value = None
    return store


@pytest.fixture
def mock_app_logic_store() -> Mock:
    """Create a mock CustomerAppLogicStore."""
    store = Mock()
    store.get_conversation.return_value = {
        "thread_id": "thread_001",
        "summary": "Discussion about revenue metrics",
        "messages": [
            {
                "id": "msg_001",
                "sender": "user",
                "text": "What is our gross margin?",
                "mentioned_entities": ["gross_margin"],
            },
            {
                "id": "msg_002",
                "sender": "assistant",
                "text": "The gross margin is 42%",
                "type": "insight",
            },
        ],
        "active_state": {
            "active_chart_id": "chart_001",
            "active_dashboard_id": "dashboard_001",
            "active_simulations": [],
            "active_filters": [{"field": "region", "value": "EMEA"}],
            "last_referenced_entities": ["gross_margin"],
        },
    }
    store.append_message.return_value = None
    return store


@pytest.fixture
def mock_external_store() -> Mock:
    """Create a mock CoreExternalSourceStore."""
    return Mock()


# =============================================================================
# KPIBusinessClient Tests
# =============================================================================


class TestKPIBusinessClient:
    """Tests for KPIBusinessClient."""

    def test_list_kpis(
        self,
        mock_core_context_store: Mock,
        mock_app_logic_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test listing all KPIs."""
        client = KPIBusinessClient(
            core_context_store=mock_core_context_store,
            app_logic_store=mock_app_logic_store,
        )

        result = client.list(tenant=tenant_context, user=user_context)

        assert len(result) == 1
        assert isinstance(result[0], KPISummary)
        assert result[0].kpi_id == "metric_001"
        assert result[0].name == "Gross Margin"
        mock_core_context_store.search_business_metrics.assert_called_once()

    def test_get_kpi(
        self,
        mock_core_context_store: Mock,
        mock_app_logic_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test getting a KPI by ID."""
        client = KPIBusinessClient(
            core_context_store=mock_core_context_store,
            app_logic_store=mock_app_logic_store,
        )

        result = client.get("metric_001", tenant=tenant_context, user=user_context)

        assert isinstance(result, KPI)
        assert result.kpi_id == "metric_001"
        assert result.name == "Gross Margin"
        assert result.formula == "(revenue - cogs) / revenue"
        mock_core_context_store.get_business_metric.assert_called_once()

    def test_get_kpi_definition(
        self,
        mock_core_context_store: Mock,
        mock_app_logic_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test getting a KPI definition with lineage."""
        client = KPIBusinessClient(
            core_context_store=mock_core_context_store,
            app_logic_store=mock_app_logic_store,
        )

        result = client.get_definition(
            "metric_001", tenant=tenant_context, user=user_context
        )

        assert isinstance(result, KPIDefinition)
        assert result.kpi_id == "metric_001"
        # Lineage is converted to dict format
        assert result.lineage == {"sources": ["sales_fact", "cost_fact"]}

    def test_add_kpi(
        self,
        mock_core_context_store: Mock,
        mock_app_logic_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test adding a new KPI."""
        client = KPIBusinessClient(
            core_context_store=mock_core_context_store,
            app_logic_store=mock_app_logic_store,
        )

        kpi = KPI(
            kpi_id="",
            name="Net Profit",
            domain="finance",
            description="Revenue minus all expenses",
            formula="revenue - expenses",
            formula_type="difference",
            input_fields=["revenue", "expenses"],
            output_unit="EUR",
            tags=["finance", "profitability"],
        )

        result = client.add(kpi, tenant=tenant_context, user=user_context)

        assert result == "metric_001"
        mock_core_context_store.upsert_business_metric.assert_called_once()

    def test_update_kpi(
        self,
        mock_core_context_store: Mock,
        mock_app_logic_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test updating an existing KPI."""
        client = KPIBusinessClient(
            core_context_store=mock_core_context_store,
            app_logic_store=mock_app_logic_store,
        )

        updates = KPI(
            kpi_id="metric_001",
            name="Updated Gross Margin",
            domain="finance",
            description="Updated description",
        )

        result = client.update(
            "metric_001", updates, tenant=tenant_context, user=user_context
        )

        assert isinstance(result, KPI)
        # get is called twice: once for existing, once for return
        assert mock_core_context_store.get_business_metric.call_count == 2

    def test_delete_kpi(
        self,
        mock_core_context_store: Mock,
        mock_app_logic_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test deleting a KPI."""
        client = KPIBusinessClient(
            core_context_store=mock_core_context_store,
            app_logic_store=mock_app_logic_store,
        )

        client.delete("metric_001", tenant=tenant_context, user=user_context)

        mock_core_context_store.delete_business_metric.assert_called_once_with(
            "metric_001", tenant=tenant_context, user=user_context
        )


# =============================================================================
# SchemaBusinessClient Tests
# =============================================================================


class TestSchemaBusinessClient:
    """Tests for SchemaBusinessClient."""

    def test_get_schema(
        self,
        mock_customer_context_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test getting schema semantics."""
        client = SchemaBusinessClient(context_store=mock_customer_context_store)

        result = client.get("schema_001", tenant=tenant_context, user=user_context)

        assert isinstance(result, SchemaSemantics)
        assert result.schema_id == "schema_001"
        assert result.name == "Sales Schema"
        assert result.version == 1

    def test_get_full_schemas(
        self,
        mock_customer_context_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test getting full schema with all entities."""
        client = SchemaBusinessClient(context_store=mock_customer_context_store)

        result = client.get_full(tenant=tenant_context, user=user_context)

        assert len(result) == 1
        assert isinstance(result[0], FullSchema)
        assert result[0].schema_id == "schema_001"

    def test_add_relationship(
        self,
        mock_customer_context_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test adding a relationship between fields."""
        client = SchemaBusinessClient(context_store=mock_customer_context_store)

        result = client.add_relationship(
            "sales.customer_id",
            "customers.id",
            {"type": "foreign_key", "description": "Customer reference"},
            tenant=tenant_context,
            user=user_context,
        )

        assert result == "fact_002"
        mock_customer_context_store.add_fact.assert_called_once()

    def test_add_field_metadata(
        self,
        mock_customer_context_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test adding metadata to a field."""
        client = SchemaBusinessClient(context_store=mock_customer_context_store)

        result = client.add_field_metadata(
            "sales.revenue",
            {
                "description": "Total sales revenue in EUR",
                "units": "EUR",
                "data_type": "numeric",
            },
            tenant=tenant_context,
            user=user_context,
        )

        assert result == "fact_002"
        mock_customer_context_store.add_fact.assert_called_once()

    def test_get_entity(
        self,
        mock_customer_context_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test getting an entity with relationships."""
        client = SchemaBusinessClient(context_store=mock_customer_context_store)

        result = client.get_entity(
            "sales.revenue", tenant=tenant_context, user=user_context
        )

        assert isinstance(result, Entity)
        assert result.entity_id == "sales.revenue"
        assert result.entity_type == "field"
        assert result.name == "revenue"


# =============================================================================
# FactsBusinessClient Tests
# =============================================================================


class TestFactsBusinessClient:
    """Tests for FactsBusinessClient."""

    def test_add_fact(
        self,
        mock_customer_context_store: Mock,
        mock_core_context_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test adding a fact to an entity."""
        client = FactsBusinessClient(
            context_store=mock_customer_context_store,
            core_context_store=mock_core_context_store,
        )

        fact = FactCreate(
            text="Revenue includes all product sales",
            source="analyst",
            tags=["definition"],
        )

        result = client.add(
            "sales.revenue",
            fact,
            schema_id="schema_001",
            tenant=tenant_context,
            user=user_context,
        )

        assert result == "fact_002"
        mock_customer_context_store.add_fact.assert_called_once()

    def test_list_facts(
        self,
        mock_customer_context_store: Mock,
        mock_core_context_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test listing facts for an entity."""
        client = FactsBusinessClient(
            context_store=mock_customer_context_store,
            core_context_store=mock_core_context_store,
        )

        result = client.list(
            "sales.revenue",
            schema_id="schema_001",
            tenant=tenant_context,
            user=user_context,
        )

        assert len(result) == 1
        assert isinstance(result[0], FactInfo)
        assert result[0].fact_id == "fact_001"

    def test_get_fact(
        self,
        mock_customer_context_store: Mock,
        mock_core_context_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test getting a specific fact by ID."""
        client = FactsBusinessClient(
            context_store=mock_customer_context_store,
            core_context_store=mock_core_context_store,
        )

        result = client.get(
            "fact_001",
            schema_id="schema_001",
            tenant=tenant_context,
            user=user_context,
        )

        assert isinstance(result, FactInfo)
        assert result.fact_id == "fact_001"

    def test_get_fact_not_found(
        self,
        mock_customer_context_store: Mock,
        mock_core_context_store: Mock,
        mock_schema_record: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test getting a non-existent fact raises KeyError."""
        # Clear facts to simulate not found
        mock_schema_record.facts_by_entity = {}
        mock_customer_context_store.get_schema_context.return_value = mock_schema_record

        client = FactsBusinessClient(
            context_store=mock_customer_context_store,
            core_context_store=mock_core_context_store,
        )

        with pytest.raises(KeyError, match="Fact not found"):
            client.get(
                "non_existent_fact",
                schema_id="schema_001",
                tenant=tenant_context,
                user=user_context,
            )

    def test_update_fact(
        self,
        mock_customer_context_store: Mock,
        mock_core_context_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test updating a fact."""
        client = FactsBusinessClient(
            context_store=mock_customer_context_store,
            core_context_store=mock_core_context_store,
        )

        updates = FactCreate(
            text="Updated fact text",
            source="analyst_v2",
            tags=["updated"],
        )

        result = client.update(
            "fact_001",
            updates,
            schema_id="schema_001",
            tenant=tenant_context,
            user=user_context,
        )

        assert isinstance(result, FactInfo)
        mock_customer_context_store.modify_fact.assert_called_once()

    def test_delete_fact(
        self,
        mock_customer_context_store: Mock,
        mock_core_context_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test deleting a fact."""
        client = FactsBusinessClient(
            context_store=mock_customer_context_store,
            core_context_store=mock_core_context_store,
        )

        client.delete(
            "fact_001",
            schema_id="schema_001",
            tenant=tenant_context,
            user=user_context,
        )

        mock_customer_context_store.delete_fact.assert_called_once_with(
            schema_id="schema_001",
            fact_id="fact_001",
            tenant=tenant_context,
            user=user_context,
        )


# =============================================================================
# SemanticBusinessClient Tests
# =============================================================================


class TestSemanticBusinessClient:
    """Tests for SemanticBusinessClient."""

    def test_search(
        self,
        mock_customer_context_store: Mock,
        mock_core_context_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test semantic search."""
        client = SemanticBusinessClient(
            context_store=mock_customer_context_store,
            core_context_store=mock_core_context_store,
        )

        result = client.search(
            "profit margin", top_k=5, tenant=tenant_context, user=user_context
        )

        assert len(result) > 0
        assert all(isinstance(e, Entity) for e in result)

    def test_search_with_filters(
        self,
        mock_customer_context_store: Mock,
        mock_core_context_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test semantic search with filters."""
        client = SemanticBusinessClient(
            context_store=mock_customer_context_store,
            core_context_store=mock_core_context_store,
        )

        result = client.search(
            "revenue",
            filters={"entity_type": "field"},
            top_k=3,
            tenant=tenant_context,
            user=user_context,
        )

        assert len(result) <= 3

    def test_graph(
        self,
        mock_customer_context_store: Mock,
        mock_core_context_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test semantic graph retrieval."""
        client = SemanticBusinessClient(
            context_store=mock_customer_context_store,
            core_context_store=mock_core_context_store,
        )

        result = client.graph("sales.revenue", tenant=tenant_context, user=user_context)

        assert isinstance(result, GraphResult)
        assert result.entity.entity_id == "sales.revenue"
        assert isinstance(result.neighbors, list)

    def test_add_knowledge_explanation(
        self,
        mock_customer_context_store: Mock,
        mock_core_context_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test adding explanation knowledge."""
        client = SemanticBusinessClient(
            context_store=mock_customer_context_store,
            core_context_store=mock_core_context_store,
        )

        knowledge = KnowledgeObject(
            content="Revenue is calculated before tax deductions",
            knowledge_type="explanation",
            entity_id="sales.revenue",
            source="analyst",
            tags=["explanation", "tax"],
            confidence=0.95,
        )

        result = client.add_knowledge(
            knowledge, tenant=tenant_context, user=user_context
        )

        assert result == "fact_002"
        mock_customer_context_store.add_fact.assert_called_once()

    def test_add_knowledge_definition(
        self,
        mock_customer_context_store: Mock,
        mock_core_context_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test adding definition knowledge."""
        client = SemanticBusinessClient(
            context_store=mock_customer_context_store,
            core_context_store=mock_core_context_store,
        )

        knowledge = KnowledgeObject(
            content="EBITDA is earnings before interest, taxes, depreciation, and amortization",
            knowledge_type="definition",
            source="accounting_standards",
            tags=["finance", "accounting"],
            confidence=1.0,
        )

        result = client.add_knowledge(
            knowledge, tenant=tenant_context, user=user_context
        )

        assert result == "nugget_001"
        mock_core_context_store.upsert_knowledge_nugget.assert_called_once()


# =============================================================================
# ConversationBusinessClient Tests
# =============================================================================


class TestConversationBusinessClient:
    """Tests for ConversationBusinessClient."""

    def test_get_context(
        self,
        mock_app_logic_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test getting conversation context."""
        client = ConversationBusinessClient(app_logic_store=mock_app_logic_store)

        result = client.get_context(
            "thread_001", tenant=tenant_context, user=user_context
        )

        assert isinstance(result, ConversationContext)
        assert result.thread_id == "thread_001"
        assert result.summary == "Discussion about revenue metrics"
        assert "gross_margin" in result.mentioned_entities
        assert len(result.recent_queries) > 0

    def test_get_active_state(
        self,
        mock_app_logic_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test getting active state."""
        client = ConversationBusinessClient(app_logic_store=mock_app_logic_store)

        result = client.get_active_state(
            "thread_001", tenant=tenant_context, user=user_context
        )

        assert isinstance(result, ActiveState)
        assert result.thread_id == "thread_001"
        assert result.active_chart_id == "chart_001"
        assert result.active_dashboard_id == "dashboard_001"
        assert len(result.active_filters) == 1

    def test_add_insight(
        self,
        mock_app_logic_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test adding an insight to a conversation."""
        client = ConversationBusinessClient(app_logic_store=mock_app_logic_store)

        insight = InsightInput(
            summary="Gross margin increased by 5% due to cost reductions",
            detail="Cost optimization in Q4 led to significant margin improvement",
            related_entities=["gross_margin", "cost"],
            related_charts=["chart_001"],
            confidence=0.92,
        )

        result = client.add_insight(
            "thread_001", insight, tenant=tenant_context, user=user_context
        )

        assert result is not None  # UUID string
        mock_app_logic_store.append_message.assert_called_once()

    def test_update_state(
        self,
        mock_app_logic_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test updating conversation state."""
        client = ConversationBusinessClient(app_logic_store=mock_app_logic_store)

        state = StateUpdate(
            active_chart_id="chart_002",
            active_filters=[{"field": "product", "value": "Widget A"}],
        )

        client.update_state(
            "thread_001", state, tenant=tenant_context, user=user_context
        )

        mock_app_logic_store.append_message.assert_called_once()


# =============================================================================
# KnowledgeBusinessClient Tests
# =============================================================================


class TestKnowledgeBusinessClient:
    """Tests for KnowledgeBusinessClient."""

    def test_search_nuggets(
        self,
        mock_core_context_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test searching knowledge nuggets."""
        client = KnowledgeBusinessClient(core_context_store=mock_core_context_store)

        result = client.search(
            "profitability metrics",
            domains=["finance"],
            top_k=5,
            tenant=tenant_context,
            user=user_context,
        )

        assert len(result) == 1
        assert isinstance(result[0], KnowledgeNuggetSummary)
        assert result[0].nugget_id == "nugget_001"
        assert result[0].domain == "finance"
        assert result[0].content == "Gross margin is a key profitability metric"
        mock_core_context_store.search_knowledge_nuggets.assert_called_once_with(
            "profitability metrics",
            domains=["finance"],
            top_k=5,
            tenant=tenant_context,
            user=user_context,
        )

    def test_list_by_domain(
        self,
        mock_core_context_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test listing nuggets by domain."""
        client = KnowledgeBusinessClient(core_context_store=mock_core_context_store)

        result = client.list_by_domain(
            "finance",
            category="definition",
            limit=10,
            tenant=tenant_context,
            user=user_context,
        )

        assert len(result) == 1
        assert isinstance(result[0], KnowledgeNuggetSummary)
        mock_core_context_store.get_knowledge_nuggets_by_domain.assert_called_once_with(
            "finance",
            category="definition",
            limit=10,
            tenant=tenant_context,
            user=user_context,
        )

    def test_get_nugget(
        self,
        mock_core_context_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test getting a knowledge nugget by ID."""
        client = KnowledgeBusinessClient(core_context_store=mock_core_context_store)

        result = client.get("nugget_001", tenant=tenant_context, user=user_context)

        assert isinstance(result, KnowledgeNuggetInfo)
        assert result.nugget_id == "nugget_001"
        assert result.domain == "finance"
        assert result.category == "definition"
        assert result.tags == ["finance", "margin"]
        assert result.sources == ["accounting_handbook"]
        mock_core_context_store.get_knowledge_nugget.assert_called_once_with(
            "nugget_001", tenant=tenant_context, user=user_context
        )

    def test_add_nugget(
        self,
        mock_core_context_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test adding a new knowledge nugget."""
        client = KnowledgeBusinessClient(core_context_store=mock_core_context_store)

        nugget = KnowledgeNuggetCreate(
            domain="agriculture",
            category="processing",
            content="Coffee beans must be dried to 11-12% moisture content",
            tags=["coffee", "post-harvest"],
            sources=["coffee_manual"],
            confidence=0.9,
        )

        result = client.add(nugget, tenant=tenant_context, user=user_context)

        assert result == "nugget_001"
        mock_core_context_store.upsert_knowledge_nugget.assert_called_once()

    def test_update_nugget(
        self,
        mock_core_context_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test updating an existing knowledge nugget."""
        client = KnowledgeBusinessClient(core_context_store=mock_core_context_store)

        updates = KnowledgeNuggetCreate(
            domain="finance",
            category="definition",
            content="Updated content about gross margin",
            confidence=0.98,
        )

        result = client.update(
            "nugget_001", updates, tenant=tenant_context, user=user_context
        )

        assert isinstance(result, KnowledgeNuggetInfo)
        # get is called twice: once for existing, once for return
        assert mock_core_context_store.get_knowledge_nugget.call_count == 2
        mock_core_context_store.upsert_knowledge_nugget.assert_called_once()

    def test_delete_nugget(
        self,
        mock_core_context_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test deleting a knowledge nugget."""
        client = KnowledgeBusinessClient(core_context_store=mock_core_context_store)

        client.delete("nugget_001", tenant=tenant_context, user=user_context)

        mock_core_context_store.delete_knowledge_nugget.assert_called_once_with(
            "nugget_001", tenant=tenant_context, user=user_context
        )


# =============================================================================
# IndustryBusinessClient Tests
# =============================================================================


class TestIndustryBusinessClient:
    """Tests for IndustryBusinessClient."""

    def test_search_terms(
        self,
        mock_core_context_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test searching industry terms."""
        client = IndustryBusinessClient(core_context_store=mock_core_context_store)

        result = client.search(
            "coffee species",
            industries=["coffee"],
            top_k=5,
            tenant=tenant_context,
            user=user_context,
        )

        assert len(result) == 1
        assert isinstance(result[0], IndustryTermSummary)
        assert result[0].term_id == "term_001"
        assert result[0].term == "Arabica"
        assert result[0].industry == "coffee"
        mock_core_context_store.search_industry_terms.assert_called_once_with(
            "coffee species",
            industries=["coffee"],
            top_k=5,
            tenant=tenant_context,
            user=user_context,
        )

    def test_get_term(
        self,
        mock_core_context_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test getting an industry term by ID."""
        client = IndustryBusinessClient(core_context_store=mock_core_context_store)

        result = client.get("term_001", tenant=tenant_context, user=user_context)

        assert isinstance(result, IndustryTermInfo)
        assert result.term_id == "term_001"
        assert result.term == "Arabica"
        assert result.industry == "coffee"
        assert result.synonyms == ["Coffea arabica"]
        assert result.examples == ["Ethiopian Yirgacheffe", "Colombian Supremo"]
        mock_core_context_store.get_industry_term.assert_called_once_with(
            "term_001", tenant=tenant_context, user=user_context
        )

    def test_get_by_name(
        self,
        mock_core_context_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test getting an industry term by name."""
        client = IndustryBusinessClient(core_context_store=mock_core_context_store)

        result = client.get_by_name("Arabica", tenant=tenant_context, user=user_context)

        assert result is not None
        assert isinstance(result, IndustryTermInfo)
        assert result.term == "Arabica"
        mock_core_context_store.get_industry_term_by_name.assert_called_once_with(
            "Arabica", tenant=tenant_context, user=user_context
        )

    def test_get_by_name_not_found(
        self,
        mock_core_context_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test getting a non-existent term by name returns None."""
        mock_core_context_store.get_industry_term_by_name.return_value = None
        client = IndustryBusinessClient(core_context_store=mock_core_context_store)

        result = client.get_by_name(
            "NonExistent", tenant=tenant_context, user=user_context
        )

        assert result is None

    def test_get_related_terms(
        self,
        mock_core_context_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test getting related industry terms."""
        client = IndustryBusinessClient(core_context_store=mock_core_context_store)

        result = client.get_related(
            "term_001", tenant=tenant_context, user=user_context
        )

        assert len(result) == 1
        assert isinstance(result[0], IndustryTermInfo)
        assert result[0].term == "Robusta"
        mock_core_context_store.get_related_industry_terms.assert_called_once_with(
            "term_001", tenant=tenant_context, user=user_context
        )

    def test_add_term(
        self,
        mock_core_context_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test adding a new industry term."""
        client = IndustryBusinessClient(core_context_store=mock_core_context_store)

        term = IndustryTermCreate(
            term="Liberica",
            definition="A rare coffee species with a unique woody flavor",
            industry="coffee",
            synonyms=["Coffea liberica"],
            examples=["Philippine Barako"],
            tags=["coffee", "species", "rare"],
        )

        result = client.add(term, tenant=tenant_context, user=user_context)

        assert result == "term_001"
        mock_core_context_store.upsert_industry_term.assert_called_once()

    def test_update_term(
        self,
        mock_core_context_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test updating an existing industry term."""
        client = IndustryBusinessClient(core_context_store=mock_core_context_store)

        updates = IndustryTermCreate(
            term="Arabica",
            definition="Updated definition for Arabica coffee",
            industry="coffee",
        )

        result = client.update(
            "term_001", updates, tenant=tenant_context, user=user_context
        )

        assert isinstance(result, IndustryTermInfo)
        # get is called twice: once for existing, once for return
        assert mock_core_context_store.get_industry_term.call_count == 2
        mock_core_context_store.upsert_industry_term.assert_called_once()

    def test_link_terms(
        self,
        mock_core_context_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test linking industry terms together."""
        client = IndustryBusinessClient(core_context_store=mock_core_context_store)

        client.link(
            "term_001",
            ["term_002", "term_003"],
            relationship="related",
            tenant=tenant_context,
            user=user_context,
        )

        mock_core_context_store.link_industry_terms.assert_called_once_with(
            "term_001",
            ["term_002", "term_003"],
            relationship="related",
            tenant=tenant_context,
            user=user_context,
        )

    def test_link_terms_synonym(
        self,
        mock_core_context_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test linking industry terms as synonyms."""
        client = IndustryBusinessClient(core_context_store=mock_core_context_store)

        client.link(
            "term_001",
            ["term_004"],
            relationship="synonym",
            tenant=tenant_context,
            user=user_context,
        )

        mock_core_context_store.link_industry_terms.assert_called_once_with(
            "term_001",
            ["term_004"],
            relationship="synonym",
            tenant=tenant_context,
            user=user_context,
        )

    def test_delete_term(
        self,
        mock_core_context_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test deleting an industry term."""
        client = IndustryBusinessClient(core_context_store=mock_core_context_store)

        client.delete("term_001", tenant=tenant_context, user=user_context)

        mock_core_context_store.delete_industry_term.assert_called_once_with(
            "term_001", tenant=tenant_context, user=user_context
        )


# =============================================================================
# BusinessClient (Facade) Tests
# =============================================================================


class TestBusinessClient:
    """Tests for the BusinessClient facade."""

    def test_initialization(
        self,
        mock_customer_context_store: Mock,
        mock_app_logic_store: Mock,
        mock_core_context_store: Mock,
        mock_external_store: Mock,
    ) -> None:
        """Test BusinessClient initializes sub-clients correctly."""
        client = BusinessClient(
            context_store=mock_customer_context_store,
            app_logic_store=mock_app_logic_store,
            core_context_store=mock_core_context_store,
            external_store=mock_external_store,
        )

        assert hasattr(client, "kpi")
        assert hasattr(client, "schema")
        assert hasattr(client, "facts")
        assert hasattr(client, "semantic")
        assert hasattr(client, "conversation")
        assert hasattr(client, "knowledge")
        assert hasattr(client, "industry")
        assert isinstance(client.kpi, KPIBusinessClient)
        assert isinstance(client.schema, SchemaBusinessClient)
        assert isinstance(client.facts, FactsBusinessClient)
        assert isinstance(client.semantic, SemanticBusinessClient)
        assert isinstance(client.conversation, ConversationBusinessClient)
        assert isinstance(client.knowledge, KnowledgeBusinessClient)
        assert isinstance(client.industry, IndustryBusinessClient)

    def test_kpi_via_facade(
        self,
        mock_customer_context_store: Mock,
        mock_app_logic_store: Mock,
        mock_core_context_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test accessing KPIs through the facade."""
        client = BusinessClient(
            context_store=mock_customer_context_store,
            app_logic_store=mock_app_logic_store,
            core_context_store=mock_core_context_store,
        )

        result = client.kpi.list(tenant=tenant_context, user=user_context)

        assert len(result) == 1
        mock_core_context_store.search_business_metrics.assert_called_once()

    def test_schema_via_facade(
        self,
        mock_customer_context_store: Mock,
        mock_app_logic_store: Mock,
        mock_core_context_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test accessing schema through the facade."""
        client = BusinessClient(
            context_store=mock_customer_context_store,
            app_logic_store=mock_app_logic_store,
            core_context_store=mock_core_context_store,
        )

        result = client.schema.get(
            "schema_001", tenant=tenant_context, user=user_context
        )

        assert result.schema_id == "schema_001"
        mock_customer_context_store.get_schema_context.assert_called_once()

    def test_semantic_via_facade(
        self,
        mock_customer_context_store: Mock,
        mock_app_logic_store: Mock,
        mock_core_context_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test accessing semantic operations through the facade."""
        client = BusinessClient(
            context_store=mock_customer_context_store,
            app_logic_store=mock_app_logic_store,
            core_context_store=mock_core_context_store,
        )

        result = client.semantic.search(
            "revenue", tenant=tenant_context, user=user_context
        )

        assert len(result) > 0

    def test_conversation_via_facade(
        self,
        mock_customer_context_store: Mock,
        mock_app_logic_store: Mock,
        mock_core_context_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test accessing conversation through the facade."""
        client = BusinessClient(
            context_store=mock_customer_context_store,
            app_logic_store=mock_app_logic_store,
            core_context_store=mock_core_context_store,
        )

        result = client.conversation.get_context(
            "thread_001", tenant=tenant_context, user=user_context
        )

        assert result.thread_id == "thread_001"
        mock_app_logic_store.get_conversation.assert_called_once()

    def test_initialization_without_external_store(
        self,
        mock_customer_context_store: Mock,
        mock_app_logic_store: Mock,
        mock_core_context_store: Mock,
    ) -> None:
        """Test BusinessClient can be initialized without external store."""
        client = BusinessClient(
            context_store=mock_customer_context_store,
            app_logic_store=mock_app_logic_store,
            core_context_store=mock_core_context_store,
            external_store=None,
        )

        assert client.semantic._external_store is None

    def test_knowledge_via_facade(
        self,
        mock_customer_context_store: Mock,
        mock_app_logic_store: Mock,
        mock_core_context_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test accessing knowledge through the facade."""
        client = BusinessClient(
            context_store=mock_customer_context_store,
            app_logic_store=mock_app_logic_store,
            core_context_store=mock_core_context_store,
        )

        result = client.knowledge.search(
            "margin", tenant=tenant_context, user=user_context
        )

        assert len(result) == 1
        assert result[0].domain == "finance"
        mock_core_context_store.search_knowledge_nuggets.assert_called()

    def test_knowledge_get_via_facade(
        self,
        mock_customer_context_store: Mock,
        mock_app_logic_store: Mock,
        mock_core_context_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test getting a knowledge nugget through the facade."""
        client = BusinessClient(
            context_store=mock_customer_context_store,
            app_logic_store=mock_app_logic_store,
            core_context_store=mock_core_context_store,
        )

        result = client.knowledge.get(
            "nugget_001", tenant=tenant_context, user=user_context
        )

        assert result.nugget_id == "nugget_001"
        mock_core_context_store.get_knowledge_nugget.assert_called()

    def test_industry_via_facade(
        self,
        mock_customer_context_store: Mock,
        mock_app_logic_store: Mock,
        mock_core_context_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test accessing industry terms through the facade."""
        client = BusinessClient(
            context_store=mock_customer_context_store,
            app_logic_store=mock_app_logic_store,
            core_context_store=mock_core_context_store,
        )

        result = client.industry.search(
            "arabica", industries=["coffee"], tenant=tenant_context, user=user_context
        )

        assert len(result) == 1
        assert result[0].term == "Arabica"
        mock_core_context_store.search_industry_terms.assert_called()

    def test_industry_get_via_facade(
        self,
        mock_customer_context_store: Mock,
        mock_app_logic_store: Mock,
        mock_core_context_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test getting an industry term through the facade."""
        client = BusinessClient(
            context_store=mock_customer_context_store,
            app_logic_store=mock_app_logic_store,
            core_context_store=mock_core_context_store,
        )

        result = client.industry.get(
            "term_001", tenant=tenant_context, user=user_context
        )

        assert result.term_id == "term_001"
        assert result.term == "Arabica"
        mock_core_context_store.get_industry_term.assert_called()

    def test_industry_link_via_facade(
        self,
        mock_customer_context_store: Mock,
        mock_app_logic_store: Mock,
        mock_core_context_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test linking industry terms through the facade."""
        client = BusinessClient(
            context_store=mock_customer_context_store,
            app_logic_store=mock_app_logic_store,
            core_context_store=mock_core_context_store,
        )

        client.industry.link(
            "term_001",
            ["term_002"],
            relationship="related",
            tenant=tenant_context,
            user=user_context,
        )

        mock_core_context_store.link_industry_terms.assert_called_once()
