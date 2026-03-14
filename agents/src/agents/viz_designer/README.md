# Viz Designer Agent

A 2-stage LangGraph pipeline for visualization design:

1. **Selection** - Choose optimal chart type and initial data mapping
2. **Refinement** - Classify data series, generate highlights (final output)

The agent is stateless — it outputs a semantic chart specification and `AgentChartResponse`, but does NOT persist anything. State management (persistence to CustomerChartStore, data freezing) is handled by the upstream application API layer.

## Configuration

Configuration is loaded from `AGENT_VIZ_DESIGNER_*` environment variables via Pydantic Settings.

```bash
# Default model is gpt-4o-mini. Override for all stages (format: provider:model):
AGENT_VIZ_DESIGNER_DEFAULT_MODEL=anthropic:claude-sonnet-4-20250514

# Enable debug logging
AGENT_VIZ_DESIGNER_DEBUG=true

# Per-stage overrides (optional)
AGENT_VIZ_DESIGNER_SELECTION_MODEL=google:gemini-3-flash-preview
AGENT_VIZ_DESIGNER_REFINEMENT_TEMPERATURE=0.2
```

See `config.py` for all available settings.

## Usage

### Programmatic Usage

```python
from agents.viz_designer import VisualizationDesigner
from agents.lib.utils import create_agent_context

# Create the agent (uses env config by default)
designer = VisualizationDesigner()

# Compile the pipeline (cached after first call)
pipeline = designer.compile()

# Prepare initial state
state = {
    "messages": [],
    "nlp_query": "Show me monthly revenue by region",
    "output_schema": {...},  # Schema dict
    "materialized_data": [...],  # List of row dicts
    "conversation_id": None,
}

# Invoke with per-request context
ctx = create_agent_context(tenant=tenant, user=user)
result = await pipeline.ainvoke(state, context=ctx)
agent_response = result["agent_response"]  # AgentChartResponse
```

### Via FastAPI Playground

The agent is exposed via the FastAPI service playground endpoint at `/playground/viz_designer/create`.

## Eval Setup (Chartviz)

To test the chartviz eval page at `http://localhost:3003/eval` with minimal setup:

1. Copy the template to your local env:
   ```bash
   cd service
   cp .env.viz_designer .env.local
   ```

2. Edit `.env.local` and add your LLM API keys (at least one of `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, or `OPENAI_API_KEY`).

3. Start the API server:
   ```bash
   just dev-api
   ```

4. In another terminal, start chartviz:
   ```bash
   pnpm --filter '@actbi/chartviz' dev
   ```

5. Open http://localhost:3003/eval

The playground routes use xlake with SQLite (dev defaults), so you only need `PLAYGROUND=on` + your LLM API keys. No Supabase required.

## Structure

```
viz_designer/
├── __init__.py          # Public exports
├── agent.py             # VisualizationDesigner pipeline builder
├── config.py            # Pydantic Settings configuration
├── schemas.py           # State schemas, response models
└── prompts/
    ├── __init__.py
    ├── selection.py     # Selection stage prompt
    └── refinement.py    # Refinement stage prompt
```
