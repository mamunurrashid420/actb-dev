# Creating API Endpoints

A developer and coding-agent guide for adding new API endpoints to the actBI service, with conventions for dependency injection, stateless agents, and state management through the xlake.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Endpoint Anatomy](#endpoint-anatomy)
- [Step-by-Step: Creating a New Endpoint](#step-by-step-creating-a-new-endpoint)
  - [1. Create the Endpoint Directory](#1-create-the-endpoint-directory)
  - [2. Define Schemas](#2-define-schemas)
  - [3. Implement the Service Layer](#3-implement-the-service-layer)
  - [4. Implement the Route](#4-implement-the-route)
  - [5. Wire Configuration and Dependencies](#5-wire-configuration-and-dependencies)
  - [6. Register the Router](#6-register-the-router)
- [Configuration Wiring](#configuration-wiring)
  - [Agent-Specific Config (Pydantic Settings)](#agent-specific-config-pydantic-settings)
  - [Environment File Setup](#environment-file-setup)
- [Dependency Injection](#dependency-injection)
  - [The AgentsContainer (dependency-injector)](#the-agentscontainer-dependency-injector)
  - [FastAPI Depends (Simple Dependencies)](#fastapi-depends-simple-dependencies)
  - [Choosing Between DI Approaches](#choosing-between-di-approaches)
- [Stateless Agents](#stateless-agents)
- [State Management Through the xlake](#state-management-through-the-xlake)
  - [Architecture: Stores and Clients](#architecture-stores-and-clients)
  - [Where to Add State Management](#where-to-add-state-management)
  - [VisualizationClient — Chart Management](#visualizationclient--chart-management)
  - [DataClient — Data Queries and Documents](#dataclient--data-queries-and-documents)
  - [BusinessClient — Business Logic and Semantics](#businessclient--business-logic-and-semantics)
  - [CustomerAppLogicStore — Application State](#customerapplogicstore--application-state)
- [Full Example: Adding an Analytics Endpoint](#full-example-adding-an-analytics-endpoint)
- [Testing](#testing)
- [Best Practices Checklist](#best-practices-checklist)

---

## Architecture Overview

All API endpoints follow the **Route → Agent → Service** pattern:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Route     │────▶│    Agent    │────▶│   Service   │
│  (FastAPI)  │     │ (Stateless) │     │ (Persists)  │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │
       │                   ▼                   ▼
       │              Read from            Write to
       │               xlake                xlake
       ▼
   Response
```

**Key principles:**

1. **Routes** receive requests, inject dependencies, orchestrate the flow, and return responses.
2. **Agents are stateless** — they read from xlake and return results. They never write state directly.
3. **Services handle persistence** — any writes to xlake (saving charts, updating conversations) happen in the service layer.
4. **xlake is the single source of truth** — all state is managed at the store level in xlake and surfaced through clients.

> **Not every endpoint needs an agent.** Many endpoints (CRUD, data queries, lookups) skip the agent entirely and go directly from Route → Service → xlake.

---

## Endpoint Anatomy

Every endpoint follows a three-file convention:

```
service/src/app/api/<domain>/
├── __init__.py     # Module docstring
├── route.py        # FastAPI router with HTTP handlers
├── schema.py       # Pydantic models for request/response validation
└── service.py      # Business logic and persistence layer
```

| File         | Responsibility                           | Imports From         |
| ------------ | ---------------------------------------- | -------------------- |
| `route.py`   | HTTP handling, DI, orchestration         | `schema`, `service`  |
| `schema.py`  | Request/response models (Pydantic)       | Standard lib only    |
| `service.py` | Business logic, xlake persistence        | `xlake.api.client`   |

---

## Step-by-Step: Creating a New Endpoint

### 1. Create the Endpoint Directory

For a standard authenticated endpoint:

```
service/src/app/api/analytics/
├── __init__.py
├── route.py
├── schema.py
└── service.py
```

For a dev-only playground endpoint (no auth, gated by `PLAYGROUND=on`):

```
service/src/app/api/playground/my_agent/
├── __init__.py
├── route.py
├── schema.py
└── service.py
```

### 2. Define Schemas

Schemas are Pydantic models that validate request bodies and structure responses. Keep them in `schema.py`, separate from route logic.

```python
# service/src/app/api/analytics/schema.py
"""Request/response schemas for the analytics endpoint."""

from typing import Any

from pydantic import BaseModel, Field


class AnalyticsQueryRequest(BaseModel):
    """Request body for running an analytics query."""

    query: str = Field(
        description="Natural language query describing the analytics question."
    )
    dataset_id: str = Field(
        description="ID of the dataset to query against."
    )
    tenant_id: str = Field(
        default="playground",
        description="Tenant ID for xlake isolation.",
    )
    user_id: str = Field(
        default="playground",
        description="User ID for xlake permissions.",
    )


class AnalyticsQueryResponse(BaseModel):
    """Response from the analytics query."""

    query_id: str = Field(description="Unique ID for this query execution.")
    sql: str = Field(description="Generated SQL query.")
    results: list[dict[str, Any]] = Field(description="Query result rows.")
    summary: str | None = Field(
        default=None,
        description="Natural language summary of results.",
    )
```

### 3. Implement the Service Layer

The service handles all persistence and business logic. It receives the xlake client and delegates to the appropriate sub-client.

```python
# service/src/app/api/analytics/service.py
"""Service layer for analytics endpoint.

Handles query persistence and result caching via xlake.
The agent (if any) remains stateless — all writes go through this service.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from xlake.core import TenantContext, TenantIdentity, UserContext

if TYPE_CHECKING:
    from xlake.api.client import XLakeClient

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Persistence service for analytics queries."""

    def __init__(self, xlake_client: XLakeClient) -> None:
        self._xlake = xlake_client

    def execute_query(
        self,
        sql: str,
        *,
        tenant_id: str,
        user_id: str,
    ) -> list[dict]:
        """Execute a SQL query against the data lake.

        Uses DataClient.datasets.query() for read-only SQL execution.
        """
        tenant = TenantContext(
            identity=TenantIdentity(
                tenant_id=tenant_id,
                tenant_name=tenant_id,
                industry="default",
                region="default",
                timezone="UTC",
                locale="en_US",
            ),
        )
        user = UserContext(
            user_id=user_id,
            tenant_id=tenant_id,
            role="admin",
        )

        # DataClient handles the SQL execution via CustomerDataLakeStore
        return self._xlake.data.datasets.query(
            sql,
            tenant=tenant,
            user=user,
        )
```

### 4. Implement the Route

The route receives the HTTP request, injects dependencies, invokes the agent (if needed), delegates persistence to the service, and returns the response.

**With an agent (playground-style, using dependency-injector):**

```python
# service/src/app/api/playground/my_agent/route.py
"""My agent playground routes.

Dev-only endpoint (gated by PLAYGROUND=on). No authentication required.
Uses dependency-injector to receive a fresh agent per request.
"""

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, status

from app.containers import AgentsContainer
from xlake.api.client import XLakeClient

from .schema import MyAgentRequest, MyAgentResponse
from .service import MyAgentService

router = APIRouter()


@router.post("/run", response_model=MyAgentResponse)
@inject
async def run_agent(
    request: MyAgentRequest,
    # Agent injected as Factory (new instance per request)
    agent: MyAgent = Depends(Provide[AgentsContainer.my_agent]),
    # xlake_client injected as Singleton (shared across requests)
    xlake_client: XLakeClient = Depends(Provide[AgentsContainer.xlake_client]),
):
    """Run the agent pipeline and persist results."""
    try:
        # 1. Invoke the stateless agent
        result = await agent.run(request.query)

        # 2. Persist via service (not the agent)
        service = MyAgentService(xlake_client)
        service.persist_result(result, tenant_id=request.tenant_id)

        # 3. Return response
        return MyAgentResponse(...)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent execution failed: {e!s}",
        ) from e
```

**Without an agent (standard CRUD, using FastAPI Depends):**

```python
# service/src/app/api/analytics/route.py
"""Analytics API routes."""

from fastapi import APIRouter, Depends, HTTPException, status

from lib.auth.dependencies import get_current_user

from .schema import AnalyticsQueryRequest, AnalyticsQueryResponse
from .service import AnalyticsService

router = APIRouter()


@router.post("/query", response_model=AnalyticsQueryResponse)
async def run_query(
    request: AnalyticsQueryRequest,
    user=Depends(get_current_user),
    service: AnalyticsService = Depends(),
):
    """Execute an analytics query for the authenticated user."""
    try:
        results = service.execute_query(
            sql=request.sql,
            tenant_id=user.user_metadata["tenant_id"],
            user_id=user.id,
        )
        return AnalyticsQueryResponse(
            query_id="...",
            sql=request.sql,
            results=results,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e
```

### 5. Wire Configuration and Dependencies

If your endpoint uses an agent, register its settings and factory in the DI container.

**a) Add agent settings to `containers.py`:**

```python
# service/src/app/containers.py

from agents.my_agent.agent import MyAgent
from agents.my_agent.config import get_my_agent_settings


class AgentsContainer(containers.DeclarativeContainer):
    # ... existing providers ...

    # New agent settings (Singleton — loaded once from env)
    my_agent_settings = providers.Singleton(get_my_agent_settings)

    # New agent factory (Factory — new instance per request)
    my_agent = providers.Factory(
        MyAgent,
        settings=my_agent_settings,
        xlake_client=xlake_client,  # Pass shared resources
    )
```

**b) Wire the route module in `main.py`:**

```python
# service/src/app/main.py — inside lifespan()

wire_modules: list[str] = []

if settings.playground:
    wire_modules.append("app.api.playground.viz_designer.route")
    wire_modules.append("app.api.playground.my_agent.route")  # Add new module

if wire_modules:
    container.wire(modules=wire_modules)
```

### 6. Register the Router

**Standard (authenticated) endpoint:**

```python
# service/src/app/main.py

from app.api.analytics.route import router as analytics_router

app.include_router(analytics_router, prefix="/analytics", tags=["analytics"])
```

**Playground (dev-only) endpoint:**

```python
# service/src/app/main.py

if settings.playground:
    from app.api.playground.my_agent.route import router as my_agent_router

    app.include_router(
        my_agent_router,
        prefix="/playground/my_agent",
        tags=["playground"],
    )
```

---

## Configuration Wiring

### Agent-Specific Config (Pydantic Settings)

Each agent gets its own Pydantic Settings class with an environment prefix. This pattern keeps configuration type-safe, centralized, and overridable.

```python
# agents/src/agents/my_agent/config.py

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class MyAgentSettings(BaseSettings):
    """Configuration for MyAgent.

    Loaded from AGENT_MY_AGENT_* environment variables.
    """

    model_config = SettingsConfigDict(
        env_prefix="AGENT_MY_AGENT_",       # All vars prefixed with this
        env_file=(".env", ".env.local"),     # Load from .env files
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    default_model: str = Field(
        default="gpt-4o-mini",
        description="Default model for the agent pipeline.",
    )
    temperature: float = Field(default=0.0)
    max_tokens: int = Field(default=4000)
    debug: bool = Field(default=False)


@lru_cache
def get_my_agent_settings() -> MyAgentSettings:
    """Get cached settings instance (called once per process)."""
    return MyAgentSettings()
```

**Convention:** Use `AGENT_<AGENT_NAME>_*` as the env prefix. The `@lru_cache` ensures settings are only loaded once.

### Environment File Setup

Create a convenience `.env` template for your endpoint:

```bash
# service/.env.my_agent
# Copy to .env.local and add your API keys.
# Usage: cp .env.my_agent .env.local && just dev-api

PLAYGROUND=on

# LLM API Keys
OPENAI_API_KEY=
ANTHROPIC_API_KEY=

# Agent config overrides
# AGENT_MY_AGENT_DEFAULT_MODEL=anthropic:claude-sonnet-4-20250514
# AGENT_MY_AGENT_DEBUG=true
```

**Loading order** (highest to lowest priority):

1. System environment variables
2. `.env.local` (gitignored, personal overrides)
3. `.env` (checked in, shared defaults)

---

## Dependency Injection

The service uses two DI approaches. Use the right one for each situation.

### The AgentsContainer (dependency-injector)

Used for agents and complex dependencies that need lifecycle management.

```python
# service/src/app/containers.py

class AgentsContainer(containers.DeclarativeContainer):

    # Singletons — created once, shared across all requests
    viz_designer_settings = providers.Singleton(get_viz_designer_settings)
    xlake_settings = providers.Singleton(get_xlake_settings)
    xlake_client = providers.Singleton(create_xlake_client, settings=xlake_settings)

    # Factories — new instance per request for isolation
    viz_designer = providers.Factory(
        VisualizationDesigner,
        settings=viz_designer_settings,
        xlake_client=xlake_client,
    )
```

**Route usage:**

```python
@router.post("/create")
@inject  # Required! Enables Provide[] resolution
async def create_visualization(
    request: VisualizationCreateRequest,
    designer: VisualizationDesigner = Depends(Provide[AgentsContainer.viz_designer]),
    xlake_client: XLakeClient = Depends(Provide[AgentsContainer.xlake_client]),
):
    ...
```

**When to use:** Agent injection, xlake client injection, any dependency that needs Singleton/Factory lifecycle.

### FastAPI Depends (Simple Dependencies)

Used for simpler dependencies like database clients and authentication.

```python
# Route with FastAPI Depends
@router.get("")
async def list_items(
    user=Depends(get_current_user),          # Auth dependency
    service: MyService = Depends(),           # Auto-instantiated
):
    ...

# Service with constructor injection
class MyService:
    def __init__(self, supabase: Client = Depends(get_supabase_client)):
        self.supabase = supabase
```

**When to use:** Authentication, Supabase client, simple services without complex lifecycle.

### Choosing Between DI Approaches

| Scenario                           | Approach                  | Why                                      |
| ---------------------------------- | ------------------------- | ---------------------------------------- |
| Injecting an agent                 | `AgentsContainer` Factory | Per-request isolation, complex lifecycle |
| Injecting `xlake_client`           | `AgentsContainer` Singleton | Shared, expensive resource               |
| Injecting auth/current user        | `FastAPI Depends`         | Simple, framework-native                 |
| Injecting Supabase client          | `FastAPI Depends`         | Simple singleton via `@lru_cache`        |
| Service with no agent dependency   | `FastAPI Depends`         | Auto-instantiation is sufficient         |

---

## Stateless Agents

Agents **must be stateless**. They read context from xlake but never write to it directly. This ensures agents are:

- **Testable** — invoke with mock inputs, assert outputs
- **Reusable** — same agent works in API routes, notebooks, and evals
- **Deterministic** — no hidden side effects from shared mutable state

```
Agent Boundary
┌──────────────────────────────────────────────┐
│  Inputs (read-only):                         │
│    - NLP query                               │
│    - Output schema                           │
│    - Materialized data                       │
│    - Context from xlake (charts, schemas)    │
│                                              │
│  Processing:                                 │
│    - LLM pipeline (selection, refinement)    │
│    - Structured output generation            │
│                                              │
│  Outputs (returned, never persisted):        │
│    - AgentChartResponse / result object      │
└──────────────────────────────────────────────┘
         │
         ▼  Returned to the route
┌──────────────────────────────────────────────┐
│  Service Layer (handles persistence):        │
│    - Writes to xlake stores                  │
│    - Updates conversations                   │
│    - Refreshes cached data                   │
└──────────────────────────────────────────────┘
```

**What the agent can do:**
- Read from xlake (chart catalogs, schemas, context, rules)
- Invoke LLMs
- Return structured results

**What the agent must NOT do:**
- Write to xlake stores
- Manage conversation state
- Cache data between requests
- Hold mutable instance state across invocations

The agent receives a compiled pipeline via `agent.compile()` (which may be cached for performance), but the execution itself is always fresh.

---

## State Management Through the xlake

### Architecture: Stores and Clients

The xlake has two layers: **Stores** (persistence) and **Clients** (API). All state changes should be made at the **store level** and reflected by the **client**.

```
XLakeClient (Facade)
├── .data              → DataClient
│   ├── .datasets      → DatasetsDataClient      → CustomerDataLakeStore
│   └── .documents     → DocumentsDataClient      → CustomerDocStore
│
├── .visualization     → VisualizationClient
│   ├── .charts        → ChartsVisualizationClient → CustomerChartStore
│   ├── .dashboards    → DashboardsVisualizationClient → CustomerChartStore
│   ├── .stacks        → StacksVisualizationClient → CustomerChartStore
│   └── .rules         → RulesVisualizationClient  → CoreContextStore
│
└── .business          → BusinessClient
    ├── .kpi           → KPIBusinessClient         → CoreContextStore
    ├── .schema        → SchemaBusinessClient       → CustomerContextStore
    ├── .facts         → FactsBusinessClient        → CustomerContextStore + CoreContextStore
    ├── .semantic      → SemanticBusinessClient     → CustomerContextStore + CoreContextStore
    ├── .conversation  → ConversationBusinessClient → CustomerAppLogicStore
    ├── .knowledge     → KnowledgeBusinessClient    → CoreContextStore
    └── .industry      → IndustryBusinessClient     → CoreContextStore
```

### Where to Add State Management

**Rule of thumb:** All state changes happen at the xlake store level and are reflected by the client layer.

| What you're managing              | Client to use                     | Backing store(s)                            |
| --------------------------------- | --------------------------------- | ------------------------------------------- |
| Charts, dashboards, chart stacks  | `xlake.visualization`             | `CustomerChartStore`                        |
| Chart data slices, materialized data | `xlake.visualization.charts`   | `CustomerChartStore` (data plane)           |
| Viz design rules                  | `xlake.visualization.rules`       | `CoreContextStore`                          |
| SQL queries against datasets      | `xlake.data.datasets`             | `CustomerDataLakeStore`                     |
| Documents                         | `xlake.data.documents`            | `CustomerDocStore`                          |
| KPIs and business metrics         | `xlake.business.kpi`              | `CoreContextStore`                          |
| Schema semantics and relationships | `xlake.business.schema`          | `CustomerContextStore`                      |
| Business facts                    | `xlake.business.facts`            | `CustomerContextStore` + `CoreContextStore` |
| Semantic search                   | `xlake.business.semantic`         | `CustomerContextStore` + `CoreContextStore` |
| Conversations and app state       | `xlake.business.conversation`     | `CustomerAppLogicStore`                     |
| Version snapshots (git-like)      | Store directly                    | `CustomerAppLogicStore`                     |

### VisualizationClient — Chart Management

Use when creating, updating, or retrieving charts, dashboards, and chart stacks.

```python
# In a service layer
class ChartService:
    def __init__(self, xlake_client: XLakeClient) -> None:
        self._xlake = xlake_client

    def persist_chart(self, chart_proto, *, tenant, user):
        """Create or update a chart in the chart store."""
        self._xlake.visualization.charts.create(
            chart_proto,
            tenant=tenant,
            user=user,
        )

    def get_chart(self, chart_id: str, *, tenant, user):
        """Retrieve a chart by ID."""
        return self._xlake.visualization.charts.get(
            chart_id,
            tenant=tenant,
            user=user,
        )

    def get_chart_data(self, chart_id: str, *, tenant, user):
        """Retrieve materialized data for a chart."""
        return self._xlake.visualization.charts.get_data(
            chart_id=chart_id,
            context="dashboard",
            tenant=tenant,
            user=user,
        )

    def refresh_data(self, slice_id: str, new_data: dict, *, tenant, user):
        """Refresh a chart's materialized data."""
        return self._xlake.visualization.charts.refresh_data(
            slice_id,
            new_data,
            tenant=tenant,
            user=user,
        )
```

### DataClient — Data Queries and Documents

Use when pulling data from sources with SQL queries or managing documents.

```python
class DataQueryService:
    def __init__(self, xlake_client: XLakeClient) -> None:
        self._xlake = xlake_client

    def run_query(self, sql: str, *, tenant, user) -> list[dict]:
        """Execute a read-only SQL query against the data lake.

        The DataClient delegates to CustomerDataLakeStore which
        enforces read-only queries (SELECT/WITH only) via DuckDB.
        """
        return self._xlake.data.datasets.query(
            sql,
            tenant=tenant,
            user=user,
        )

    def list_datasets(self, *, tenant, user):
        """List available datasets for the tenant."""
        return self._xlake.data.datasets.list(
            tenant=tenant,
            user=user,
        )

    def get_schema(self, dataset_id: str, *, tenant, user):
        """Get the schema of a dataset (columns, types)."""
        return self._xlake.data.datasets.get_schema(
            dataset_id,
            tenant=tenant,
            user=user,
        )
```

### BusinessClient — Business Logic and Semantics

Use for KPIs, semantic search, schema relationships, business facts, and conversation state. The `BusinessClient` and `CustomerAppLogicStore` are the most common places to add business logic and application state management.

```python
class BusinessLogicService:
    def __init__(self, xlake_client: XLakeClient) -> None:
        self._xlake = xlake_client

    def search_entities(self, query: str, *, tenant, user):
        """Semantic search across business entities."""
        return self._xlake.business.semantic.search(
            query,
            top_k=10,
            tenant=tenant,
            user=user,
        )

    def get_entity_graph(self, entity_id: str, *, tenant, user):
        """Get an entity with its relationships (KPIs, facts, neighbors)."""
        return self._xlake.business.semantic.graph(
            entity_id,
            tenant=tenant,
            user=user,
        )

    def get_conversation_context(self, thread_id: str, *, tenant, user):
        """Get the active conversation state."""
        return self._xlake.business.conversation.get_context(
            thread_id,
            tenant=tenant,
            user=user,
        )

    def get_kpis(self, *, tenant, user):
        """Retrieve business KPI definitions."""
        return self._xlake.business.kpi.list(
            tenant=tenant,
            user=user,
        )
```

### CustomerAppLogicStore — Application State

For app-level state that doesn't fit into visualization, data, or business domains (conversations, version management, user preferences):

```python
class AppStateService:
    def __init__(self, xlake_client: XLakeClient) -> None:
        self._xlake = xlake_client

    def commit_version(
        self,
        conversation_id: str,
        chart_stack_id: str,
        snapshot: dict,
        description: str,
        *,
        tenant,
        user,
    ):
        """Create a version snapshot (git-like commit).

        Links conversation state to chart stack state for history traversal.
        Uses CustomerAppLogicStore directly for version management.
        """
        return self._xlake.stores.customer_app_logic.commit_version(
            conversation_id=conversation_id,
            message_cursor=0,
            chart_stack_id=chart_stack_id,
            chart_stack_snapshot=snapshot,
            description=description,
            committed_by=user.user_id,
            tenant=tenant,
            user=user,
        )
```

---

## Full Example: Adding an Analytics Endpoint

Here is a complete, end-to-end example of adding a new playground endpoint that uses an agent.

### Directory structure

```
service/src/app/api/playground/analytics/
├── __init__.py
├── route.py
├── schema.py
└── service.py
```

### `__init__.py`

```python
"""Analytics playground endpoint."""
```

### `schema.py`

```python
"""Request/response schemas for the analytics playground endpoint."""

from typing import Any

from pydantic import BaseModel, Field


class AnalyticsRequest(BaseModel):
    """Request body for analytics query."""

    nlp_query: str = Field(description="Natural language analytics question.")
    dataset_id: str = Field(description="Target dataset ID.")
    tenant_id: str = Field(default="playground")
    user_id: str = Field(default="playground")


class AnalyticsResponse(BaseModel):
    """Response from analytics query."""

    query_id: str
    sql: str
    results: list[dict[str, Any]]
    summary: str | None = None
```

### `service.py`

```python
"""Service layer for analytics playground endpoint.

Handles query execution and result persistence via xlake.
The agent (if any) is stateless — all writes go through this service.
"""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING

from xlake.core import TenantContext, TenantIdentity, UserContext

if TYPE_CHECKING:
    from xlake.api.client import XLakeClient

logger = logging.getLogger(__name__)


class AnalyticsPlaygroundService:
    """Persistence and data access for the analytics playground."""

    def __init__(self, xlake_client: XLakeClient) -> None:
        self._xlake = xlake_client

    def execute_and_persist(
        self,
        sql: str,
        *,
        tenant_id: str,
        user_id: str,
    ) -> tuple[str, list[dict]]:
        """Execute SQL and return (query_id, results).

        Uses the DataClient for query execution against the data lake.
        """
        tenant = TenantContext(
            identity=TenantIdentity(
                tenant_id=tenant_id,
                tenant_name=tenant_id,
                industry="playground",
                region="playground",
                timezone="UTC",
                locale="en_US",
            ),
        )
        user = UserContext(
            user_id=user_id,
            tenant_id=tenant_id,
            role="admin",
        )

        query_id = str(uuid.uuid4())
        results = self._xlake.data.datasets.query(sql, tenant=tenant, user=user)

        logger.info(
            "Executed query %s for tenant=%s (%d rows)",
            query_id,
            tenant_id,
            len(results),
        )
        return query_id, results
```

### `route.py`

```python
"""Analytics playground routes.

Dev-only endpoint (gated by PLAYGROUND=on). No authentication required.
Uses dependency-injector for xlake_client.
"""

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, status

from app.containers import AgentsContainer
from xlake.api.client import XLakeClient

from .schema import AnalyticsRequest, AnalyticsResponse
from .service import AnalyticsPlaygroundService

router = APIRouter()


@router.post("/query", response_model=AnalyticsResponse)
@inject
async def run_analytics_query(
    request: AnalyticsRequest,
    xlake_client: XLakeClient = Depends(Provide[AgentsContainer.xlake_client]),
):
    """Run an analytics query (no agent, direct data access)."""
    try:
        service = AnalyticsPlaygroundService(xlake_client)
        query_id, results = service.execute_and_persist(
            sql=f"SELECT * FROM {request.dataset_id} LIMIT 100",
            tenant_id=request.tenant_id,
            user_id=request.user_id,
        )

        return AnalyticsResponse(
            query_id=query_id,
            sql=f"SELECT * FROM {request.dataset_id} LIMIT 100",
            results=results,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analytics query failed: {e!s}",
        ) from e
```

### Register in `main.py`

```python
# In lifespan() — add wire module
if settings.playground:
    wire_modules.append("app.api.playground.viz_designer.route")
    wire_modules.append("app.api.playground.analytics.route")

# After app creation — register router
if settings.playground:
    from app.api.playground.analytics.route import router as analytics_router
    app.include_router(
        analytics_router,
        prefix="/playground/analytics",
        tags=["playground"],
    )
```

---

## Testing

Use FastAPI's `dependency_overrides` to mock DI providers in tests:

```python
# service/tests/api/playground/test_analytics.py

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Test client with mocked xlake."""
    yield TestClient(app)


def test_analytics_query(client):
    """Test the analytics query endpoint."""
    response = client.post(
        "/playground/analytics/query",
        json={
            "nlp_query": "Show me revenue by month",
            "dataset_id": "sales",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "query_id" in data
    assert "results" in data
```

For agent-based endpoints, override the container providers:

```python
from dependency_injector import providers
from app.main import app, container


@pytest.fixture
def mock_agent():
    """Override the agent factory with a mock."""
    mock = MagicMock()
    mock.compile.return_value.ainvoke.return_value = {
        "agent_response": mock_response,
    }
    container.viz_designer.override(providers.Object(mock))
    yield mock
    container.viz_designer.reset_override()
```

---

## Best Practices Checklist

### Endpoint Structure

- [ ] Three files per endpoint: `route.py`, `schema.py`, `service.py`
- [ ] `__init__.py` with a module docstring
- [ ] Schemas use Pydantic `BaseModel` with `Field` descriptions
- [ ] Service layer receives `XLakeClient`, never raw stores

### Agents

- [ ] Agent is stateless — no writes, no side effects
- [ ] Agent is injected via `AgentsContainer` Factory (new per request)
- [ ] Agent reads from xlake only (context, schemas, rules)
- [ ] All persistence happens in the service layer, after the agent returns

### Configuration

- [ ] Agent config uses Pydantic Settings with `AGENT_<NAME>_*` env prefix
- [ ] Config getter uses `@lru_cache` for singleton behavior
- [ ] Convenience `.env.<feature>` template provided for developers
- [ ] Settings registered as `providers.Singleton` in `AgentsContainer`

### Dependency Injection

- [ ] Agents registered as `providers.Factory` (per-request isolation)
- [ ] Shared resources (xlake_client, settings) as `providers.Singleton`
- [ ] Route module added to `wire_modules` in `main.py` `lifespan()`
- [ ] Route handler decorated with `@inject` when using `Provide[]`

### State Management

- [ ] All state changes go through xlake stores
- [ ] Chart management → `VisualizationClient` (`xlake.visualization`)
- [ ] Data queries → `DataClient` (`xlake.data.datasets`)
- [ ] Business logic → `BusinessClient` (`xlake.business`)
- [ ] App state → `CustomerAppLogicStore` (via `xlake.business.conversation` or store directly)
- [ ] Every xlake operation receives `tenant` and `user` context
- [ ] State updates at the store level are reflected by the client layer

### Registration

- [ ] Router registered in `main.py` with appropriate prefix and tags
- [ ] Playground routes gated by `if settings.playground`
- [ ] Authenticated routes use `Depends(get_current_user)`
