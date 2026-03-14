# ActBI Agents

Multi-agent system for ActBI business intelligence platform. This package provides the foundation for building, testing, and evaluating AI agents that power ActBI's data analysis capabilities.

## Quick Start

```bash
# Install dependencies (from repo root)
uv sync

# Run unit tests (fast, no LLM calls)
cd agents && uv run pytest tests/ -v

# Run integration tests (requires LLM API key)
cp .env.example .env  # Then edit .env with your API key
uv run pytest evals/ -v -m integration

# For notebook usage, also add keys to notebooks/.env

# Or run from repo root using just:
# just test-agents
# just test-evals-integration
```

## Architecture Overview

ActBI uses a multi-agent architecture:

| Agent Type | State | Purpose |
|------------|-------|---------|
| **Supervisor** | Stateful | Plans and coordinates capability agents |
| **Capability** | Stateless | Execute specific tasks (e.g., VisualizationDesigner) |
| **Tools** | N/A | Deterministic functions agents can call |

### Currently Implemented

- **VisualizationDesigner** - Selects optimal chart types based on user intent and data characteristics. Uses LLM reasoning (no tools).
- **DataExplorer** - Discovers and retrieves data from external sources. Uses LangGraph ReAct loop with tools (`search_assets`, `describe_asset`, `get_data`).

## Project Structure

```
agents/
├── src/agents/             # Agent implementations
│   ├── base.py             # BaseAgent class (generic, framework-agnostic)
│   ├── llm.py              # LangChain wrapper (multi-provider)
│   ├── tools/              # Shared tools
│   │   ├── data_discovery.py  # search_assets, describe_asset, get_data
│   │   └── sql_execution.py   # SQL execution tool
│   ├── viz_designer/       # Visualization design agent (LLM-only)
│   │   ├── agent.py
│   │   └── schemas.py
│   ├── data_explorer/      # Data discovery agent (LangGraph + tools)
│   │   ├── agent.py
│   │   └── schemas.py
│   └── evals/              # Integration tests (require LLM API)
│       ├── evaluators/     # Custom evaluators
│       ├── datasets/       # Test case definitions
│       ├── mocks/          # Deterministic mocks for tools and data
│       └── conftest.py     # Pytest fixtures
│
├── tests/                  # Unit tests (no LLM calls, fast)
│   ├── test_schemas.py
│   ├── test_evaluators.py
│   ├── test_agent_mocked.py
│   └── test_data_explorer.py
│
└── docs/
    └── ARCHITECTURE.md
```

## Adding a New Agent

1. **Create agent directory**: `src/agents/my_agent/`
2. **Define schemas**: Create Pydantic models for input/output in `schemas.py`
3. **Implement agent**: Extend `BaseAgent[InputT, OutputT]` in `agent.py`
4. **Add evaluators**: Create evaluation functions in `evals/evaluators/`
5. **Create test cases**: Define cases in `evals/datasets/`
6. **Write unit tests**: Mock the LLM in `tests/test_my_agent.py`

Example:
```python
from agents.base import BaseAgent
from agents.llm import LLMClient

class MyAgent(BaseAgent[MyInput, MyOutput]):
    def __init__(self, prompt_override=None, llm=None):
        super().__init__(prompt_override)
        self.llm = llm or LLMClient()  # Dependency injection for testing

    async def arun(self, input: MyInput) -> MyOutput:
        return await self.llm.generate_structured(...)
```

## Running Evaluations

### Via pytest (CI/CD)
```bash
# All integration tests
just test-agents-integration

# Single test
cd evals && uv run pytest src/evals/test_viz_designer.py::test_single_case_temporal -v
```

### Via Notebook (Interactive)
Open `notebooks/eval_runner.ipynb` for:
- Prompt experimentation with live feedback
- Running individual test cases
- Viewing detailed evaluation metrics

## Shared Types

Agent I/O schemas should import types from the shared package to stay in sync with XLake:

```python
from shared.data.types import ChartType, DataShape
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GOOGLE_API_KEY` | For integration tests* | - | Gemini API key |
| `ANTHROPIC_API_KEY` | For integration tests* | - | Claude API key |
| `OPENAI_API_KEY` | For integration tests* | - | OpenAI API key |
| `AGENT_MODEL` | No | `google:gemini-3-flash-preview` | Model (provider:model format) |

*At least one API key required for integration tests.

## Documentation

- **Architecture & Decisions**: `docs/ARCHITECTURE.md`
- **Monorepo Overview**: `../../AI_INSTRUCTIONS.md`
- **Agent Architecture**: `../../docs/Agent-Architecture_.md`
