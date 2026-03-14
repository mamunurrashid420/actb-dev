# Agents - AI Reference

## Current State

**Implemented**: VisualizationDesigner and DataExplorer agents with full evaluation framework.

| Component | Status | Location |
|-----------|--------|----------|
| Base Infrastructure | ✅ | `src/agents/base.py`, `src/agents/llm.py` |
| VisualizationDesigner | ✅ | `src/agents/viz_designer/` |
| DataExplorer | ✅ | `src/agents/data_explorer/` |
| Discovery Tools | ✅ | `src/agents/tools/` (search, describe, get_data) |
| Evaluators | ✅ | `src/agents/evals/evaluators/` |
| Datasets | ✅ | `src/agents/evals/datasets/` |
| Unit Tests | ✅ | `tests/` (47 tests, no LLM) |
| Integration Tests | ✅ | `src/agents/evals/` (9 tests, require API key) |

### Project Structure

```
agents/
├── src/agents/
│   ├── base.py                 # BaseAgent (generic, framework-agnostic)
│   ├── llm.py                  # LangChain LLM wrapper (multi-provider)
│   ├── tools/                  # Shared tools
│   │   ├── data_discovery.py   # search_assets, describe_asset, get_data
│   │   └── sql_execution.py    # SQL execution tool
│   ├── viz_designer/
│   │   ├── agent.py            # VisualizationDesigner (LLM-only)
│   │   └── schemas.py          # VizInput, VizOutput, VizEncoding
│   ├── data_explorer/
│   │   ├── agent.py            # DataExplorer (LangGraph ReAct + tools)
│   │   └── schemas.py          # DataExplorerInput, DataExplorerOutput
│   └── evals/                  # Integration tests (require LLM API)
│       ├── evaluators/         # Custom evaluators
│       ├── datasets/           # Test case definitions
│       ├── mocks/              # Deterministic mocks for tools and data
│       ├── conftest.py         # Pytest fixtures
│       ├── test_viz_designer.py
│       └── test_data_explorer.py
├── tests/                      # Unit tests (no LLM calls, fast)
│   ├── test_schemas.py
│   ├── test_evaluators.py
│   ├── test_agent_mocked.py
│   └── test_data_explorer.py
└── docs/
    └── ARCHITECTURE.md
```

## Key Patterns

### Agent Pattern: LLM-Only (VisualizationDesigner)

```python
from agents.base import BaseAgent
from agents.llm import LLMClient
from agents.viz_designer.schemas import VizInput, VizOutput

class VisualizationDesigner(BaseAgent[VizInput, VizOutput]):
    def __init__(self, prompt_override=None, model=None, llm=None):
        super().__init__(prompt_override, model=model, llm=llm)

    async def arun(self, input: VizInput) -> VizOutput:
        return await self.llm_client.generate_structured(
            system_prompt=self.prompt,
            user_message=f"Intent: {input.intent}...",
            output_schema=VizOutput
        )
```

### Agent Pattern: ReAct with Tools (DataExplorer)

```python
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from agents.base import BaseAgent
from agents.tools import DISCOVERY_TOOLS

# Response tool for structured output (no extra LLM call)
@tool(args_schema=DataExplorerOutput)
def respond(assets_found: list, recommended_asset: str | None, ...) -> str:
    """Call this to provide your final response."""
    return "Response recorded"

class DataExplorer(BaseAgent[DataExplorerInput, DataExplorerOutput]):
    def __init__(self, ...):
        super().__init__(...)
        # LangGraph handles the ReAct loop
        self._agent = create_react_agent(
            self.llm_client.llm,
            tools=DISCOVERY_TOOLS + [respond],
            prompt=self.prompt,
        )

    async def arun(self, input: DataExplorerInput) -> DataExplorerOutput:
        result = await self._agent.ainvoke({"messages": [...]})
        # Extract output from respond tool call
        for msg in reversed(result["messages"]):
            if msg.tool_calls and msg.tool_calls[0]["name"] == "respond":
                return DataExplorerOutput(**msg.tool_calls[0]["args"])
```

### Evaluator Pattern (Pydantic Evals)

```python
from dataclasses import dataclass
from pydantic_evals.evaluators import Evaluator, EvaluatorContext

@dataclass
class ChartTypeMatch(Evaluator[VizInput, VizOutput]):
    expected: str

    async def evaluate(self, ctx: EvaluatorContext) -> float:
        return 1.0 if ctx.output.chart_type == self.expected else 0.0
```

### Test Case Pattern (Python-Native)

```python
from pydantic_evals import Case

TEMPORAL_TREND = Case(
    name="temporal_trend",
    inputs=VizInput(intent="show revenue trends", data_shape="temporal", fields=["date", "revenue"]),
    evaluators=[ChartTypeMatch(expected="line"), EncodingFieldsPresent(required_fields=["date", "revenue"])],
)
```

## Commands

```bash
# Unit tests (fast, no LLM)
just test-agents

# Integration tests (requires ANTHROPIC_API_KEY)
just test-agents-integration

# All tests
just test-agents-all
```

## Shared Types

Import from `shared.data.types`:

```python
from shared.data.types import ChartType, DataShape  # Keep in sync with XLake
```

## Environment Variables

```bash
# LLM Provider Keys (at least one required for integration tests)
GOOGLE_API_KEY=...          # For Gemini models
ANTHROPIC_API_KEY=...       # For Claude models
OPENAI_API_KEY=...          # For OpenAI models

# Model selection (provider:model format)
AGENT_MODEL=google:gemini-3-flash-preview  # Default
# AGENT_MODEL=anthropic:claude-sonnet-4-20250514
# AGENT_MODEL=openai:gpt-4o
```

## Discovery

1. **Architecture decisions**: `docs/ARCHITECTURE.md`
2. **Agent implementation**: `src/agents/viz_designer/agent.py`
3. **Evaluator examples**: `evals/evaluators/viz.py`
4. **Test case examples**: `evals/datasets/viz_designer.py`
5. **Shared types**: `../../shared/data/src/shared/data/types.py`
