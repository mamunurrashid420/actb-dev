# Adding a New Agent

This guide covers adding a new agent to the actBI agents package with evaluation support.

## Overview

An agent consists of:

```
src/agents/my_agent/
├── __init__.py      # Export the agent class
├── agent.py         # Agent implementation
└── schemas.py       # Input/output Pydantic models
```

Plus evaluation assets:
- `evals/datasets/my_agent.jsonl` - Test cases
- `evals/configs/my_agent.yaml` - Evaluation config
- Entry in `evals/datasets/manifest.yaml`

## 1. Define Schemas

Create input/output models in `schemas.py`:

```python
from pydantic import BaseModel, Field

class MyAgentInput(BaseModel):
    """Input to the agent."""
    query: str = Field(..., description="User query")
    context: str | None = Field(None, description="Optional context")

class MyAgentOutput(BaseModel):
    """Structured output from the agent."""
    result: str = Field(..., description="Agent response")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score")
```

## 2. Implement the Agent

Create `agent.py` inheriting from `BaseAgent`:

```python
from agents.base import BaseAgent
from agents.my_agent.schemas import MyAgentInput, MyAgentOutput

DEFAULT_PROMPT = """You are a helpful assistant.
Given a query, provide a response with a confidence score."""

class MyAgent(BaseAgent[MyAgentInput, MyAgentOutput]):
    """Description of what this agent does."""

    def default_prompt(self) -> str:
        return DEFAULT_PROMPT

    async def arun(self, input: MyAgentInput) -> MyAgentOutput:
        user_message = f"Query: {input.query}"
        if input.context:
            user_message = f"Context: {input.context}\n{user_message}"

        return await self.llm_client.generate_structured(
            system_prompt=self.prompt,
            user_message=user_message,
            output_schema=MyAgentOutput,
        )
```

Export in `__init__.py`:

```python
from agents.my_agent.agent import MyAgent
from agents.my_agent.schemas import MyAgentInput, MyAgentOutput

__all__ = ["MyAgent", "MyAgentInput", "MyAgentOutput"]
```

## 3. Create Dataset

Create `evals/datasets/my_agent.jsonl` with test cases:

```jsonl
{"name": "simple_query", "inputs": {"query": "What is 2+2?"}, "expected_output": {"result": "4", "confidence": 0.95}, "metadata": {"category": "math"}}
{"name": "with_context", "inputs": {"query": "Summarize", "context": "The sky is blue."}, "expected_output": {"result": "The sky is blue", "confidence": 0.9}, "metadata": {"category": "summarization"}}
```

Add to `evals/datasets/manifest.yaml`:

```yaml
my_agent:
  input: agents.my_agent.schemas:MyAgentInput
  output: agents.my_agent.schemas:MyAgentOutput
```

See [DATASET_REFERENCE.md](DATASET_REFERENCE.md) for full format details.

## 4. Create Config

Create `evals/configs/my_agent.yaml`:

```yaml
name: my_agent_eval
description: MyAgent evaluation suite

agent: agents.my_agent:MyAgent

prompts:
  - py://agents.my_agent.agent:DEFAULT_PROMPT

models:
  - google:gemini-3-flash-preview

dataset: my_agent  # Name from manifest, or module:variable for custom datasets

metrics:
  - exact_match
  - field_f1:
      fields: [result]
  - latency

tags:
  - my_agent
```

## 5. Run Evaluation

```bash
# Validate dataset loads correctly
uv run python -c "from agents.evals import datasets; print(datasets.load('my_agent'))"

# Run evaluation
uv run python -m agents.evals.cli run my_agent
```

## Reference Implementation

See `src/agents/intent_classifier/` as the canonical example:

- `agent.py` - LLM-only agent with structured output
- `schemas.py` - Input/output models with enums
- `evals/datasets/intent_classifier.jsonl` - 14 test cases
- `evals/configs/intent_classifier.yaml` - Multi-metric evaluation

## Agent Patterns

### LLM-Only (Simple)

Like IntentClassifier - single LLM call with structured output:

```python
async def arun(self, input: Input) -> Output:
    return await self.llm_client.generate_structured(...)
```

### ReAct with Tools

Like DataExplorer - LangGraph agent with tool use:

```python
from langgraph.prebuilt import create_react_agent

class DataExplorer(BaseAgent[Input, Output]):
    def __init__(self, ...):
        super().__init__(...)
        self._agent = create_react_agent(
            self.llm_client.llm,
            tools=TOOLS + [respond_tool],
            prompt=self.prompt,
        )
```

See `src/agents/data_explorer/agent.py` for full example.
