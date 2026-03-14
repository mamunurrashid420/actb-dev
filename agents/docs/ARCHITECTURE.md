# Agent Architecture

## Overview

ActBI uses a multi-agent system where:
- **Supervisor Agent** (stateful) - Plans and coordinates
- **Capability Agents** (stateless) - Execute specific tasks
- **Tools** (deterministic) - Perform data operations

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Eval Framework | Pydantic Evals | Lightweight, good print output, no external deps |
| LLM Framework | LangChain | Thin wrapper for LLM calls, structured output |
| Tool Pattern | LangChain @tool | Familiar pattern, direct binding for simplicity |
| Shared Types | `shared.data.types` | Single source of truth for ChartType, DataShape |
| Dataset Format | Python-native | Full IDE support, type checking, importable |
| Tool Mocking | Deterministic mocks | Hash-based responses for reproducibility |

## Directory Structure

```
agents/                           # Agent implementations
├── src/agents/
│   ├── base.py                   # BaseAgent (framework-agnostic)
│   ├── llm.py                    # LangChain LLM wrapper
│   ├── tools/                    # LangChain tools
│   │   ├── __init__.py           # Tool registry
│   │   └── sql_execution.py      # SQL tool (placeholder)
│   └── viz_designer/
│       ├── agent.py              # VisualizationDesigner
│       └── schemas.py            # Pydantic I/O models
└── tests/                        # Unit tests (no LLM calls)

evals/                            # Evaluation framework (separate package)
├── src/evals/
│   ├── evaluators/               # Custom deterministic evaluators
│   ├── datasets/                 # Python test case definitions
│   ├── mocks/                    # Deterministic tool mocks
│   ├── conftest.py               # Pytest fixtures
│   └── test_viz_designer.py      # Pytest tests
└── notebooks/
    └── eval_runner.ipynb         # Interactive evaluation
```

## VisualizationDesigner

- **Type**: Capability agent (stateless)
- **Tools**: None (pure LLM reasoning)
- **Input**: User intent, data shape, available fields
- **Output**: Chart spec with type, encoding, rationale

## Evaluation Strategy

- **Framework**: Pydantic Evals (`from pydantic_evals import ...`)
- **Datasets**: Python-native for IDE support
- **Assertions**: Mostly deterministic (chart type match, schema valid, safety rules)
- **Execution**: Async parallel with semaphore rate limiting

### Running Evaluations

```bash
# Via pytest (from repo root)
just test-evals-integration

# Or directly
cd evals && uv run pytest src/evals/ -v -m integration

# Via notebook
# Open evals/notebooks/eval_runner.ipynb
```

## Future Guidance: Context Engineering

From [Manus](https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus):

### When to Implement

These patterns become critical when:
- Token costs are significant (100:1 input:output ratio)
- Multi-turn conversations are common
- Tool usage is extensive

### Patterns to Adopt

1. **KV-cache optimization**
   - Keep prompt prefixes stable
   - Avoid dynamic tool removal (use logit masking instead)
   - Deterministic JSON key ordering

2. **External memory**
   - Store large observations in file system
   - Keep pointers/summaries in context
   - Aligns with XLake architecture

3. **Todo recitation**
   - Agent maintains todo list at context end
   - Combats "lost in the middle" problem
   - Helps maintain objective focus

4. **Error trace retention**
   - Keep failed actions in context
   - Enables implicit belief updates
   - Better than erasing history

5. **Controlled variation**
   - Minor randomness in action/observation formatting
   - Prevents brittle pattern mimicry from few-shot examples

### Metrics to Track

- KV-cache hit rate
- Token usage per turn
- Input:output ratio
- Tool call patterns

## Two-Tier Tool Selection (Future)

From [Dexter](https://github.com/anthropics/anthropic-cookbook/tree/main/misc/prompt_caching) patterns:

Currently using direct tool binding where agents directly call tools.
When scaling, consider two-tier selection:

1. **Plan Phase**: Define task types (not specific tools)
2. **Execution Phase**: Select actual tools based on task type

This provides:
- Better separation of concerns
- More flexible tool composition
- Easier testing/mocking

## References

- [Agent Architecture Doc](../../docs/Agent-Architecture_.md) - Full architecture
- [Shared Types](../../lib/data/src/shared/data/types.py) - ChartType, DataShape
- [XLake Proto](../../xlake/src/xlake/proto/actbi/v1/chart.proto) - Chart spec
- [Manus Blog](https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus) - Context engineering
