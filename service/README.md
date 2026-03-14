# actBI Python API Service

FastAPI service that owns all business entities and their schemas.

## Architecture: Agent Invocation Pattern

All API endpoints that invoke agents follow this design pattern:

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

1. **Routes** invoke agents via dependency injection and orchestrate the request/response flow
2. **Agents are stateless** — they only read from xlake (context, schemas, charts) and return results
3. **Services handle persistence** — any state management (saving charts, updating conversations) happens in the service layer, outside the agent
4. **Separation of concerns** — agents focus on AI/LLM logic, services handle data persistence

This pattern ensures agents remain pure, testable, and reusable across different contexts (API, notebooks, evals).

**Example flow (viz_designer):**
1. Route receives request, injects `VisualizationDesigner` agent and `xlake_client`
2. Agent reads chart catalog from xlake, invokes LLM pipeline, returns `AgentChartResponse`
3. Service persists the chart spec to `CustomerChartStore` via xlake
4. Route returns response to client

## Structure

```
service/
├── src/
│   ├── app/                  # FastAPI application
│   │   ├── main.py           # Entry point
│   │   ├── config.py         # Settings
│   │   └── api/              # API routes (like Next.js app/api/)
│   │       ├── users/
│   │       ├── tenants/
│   │       ├── conversations/
│   │       └── ...
│   └── lib/                  # Shared libraries (like Next.js lib/)
│       ├── supabase/         # Supabase client
│       ├── auth/             # Authentication
│       └── utils.py          # Utilities
├── supabase/                 # Database migrations
│   ├── config.toml
│   └── migrations/
└── tests/
```

## Quick Start

```bash
# From repository root
just dev-api

# Or manually
cd service
uv run uvicorn src.app.main:app --reload --port 8000
```

## Environment Variables

Copy `.env.example` to `.env` and configure:

- `SUPABASE_URL` - Supabase project URL (optional for playground routes)
- `SUPABASE_ANON_KEY` - Supabase anonymous key (optional for playground routes)
- `SUPABASE_SERVICE_ROLE_KEY` - (Optional) Service role key for admin operations
- `PLAYGROUND` - Set to `on` to enable dev-only playground routes

## Viz Designer Eval

For testing the viz designer with the chartviz eval page, see [agents/src/agents/viz_designer/README.md](../agents/src/agents/viz_designer/README.md#eval-setup-chartviz).

Quick start: `cp .env.viz_designer .env.local`, add your API keys, run `just dev-api`.

## API Documentation

When running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
